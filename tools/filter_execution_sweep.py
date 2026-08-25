"""Find filters the app accepts, displays as applied, and then ignores.

Asks every question twice - once with a filter phrase, once without - and
compares the data that comes back. Identical data means the filter did nothing.
No hand-verified answer is needed, so this covers far more phrasings than
qa/raw_query_answer_corpus.yaml, which remains the stronger check (it verifies
the numbers are *correct*, not merely that filtering happened).

Usage:
    python tools/filter_execution_sweep.py
    python tools/filter_execution_sweep.py --only position_guards,last_n
    python tools/filter_execution_sweep.py --json outputs/sweep.json

Each combination lands in one of five buckets: APPLIED (the answer changed),
REFUSED (the app said it could not do it), LIED (unfiltered answer behind a
badge claiming otherwise), DROPPED (the words were ignored, but nothing was
claimed), or ERROR.

Exit code is 1 when any LIED case is found, so this can gate CI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nbatools.commands._filter_receipts import APPLIED as RECEIPT_APPLIED  # noqa: E402
from nbatools.query_service import _badge_filter_id, execute_natural_query  # noqa: E402

DEFAULT_CONFIG = REPO_ROOT / "qa" / "filter_execution_sweep.yaml"

# What happened to a filter on a given question.
APPLIED = "APPLIED"  # data changed - the filter did something
REFUSED = "REFUSED"  # app said it cannot do this - honest
LIED = "LIED"  # same data, and a badge claiming this filter was applied
DROPPED = "DROPPED"  # same data, no badge - the words were silently ignored
ERROR = "ERROR"  # blew up


def _fingerprint(result: Any) -> str:
    """Stable fingerprint of the data a query actually returned."""
    if result is None:
        return "NONE"
    parts: list[str] = []
    for attr in ("games", "leaders", "streaks", "summary", "splits", "comparison"):
        frame = getattr(result, attr, None)
        if frame is None or not hasattr(frame, "to_csv"):
            continue
        digest = hashlib.md5(frame.to_csv(index=False).encode()).hexdigest()[:16]
        parts.append(f"{attr}:{frame.shape}:{digest}")
    return "||".join(parts) or f"type={type(result).__name__}"


def _run(query: str) -> dict[str, Any]:
    try:
        executed = execute_natural_query(query)
    except Exception as exc:  # noqa: BLE001 - the sweep reports failures, never raises
        return {"error": f"{type(exc).__name__}: {exc}"}
    metadata = executed.metadata or {}
    receipts = (getattr(executed.result, "metadata", None) or {}).get("filter_receipts") or {}
    badges = metadata.get("applied_filters") or []
    return {
        "route": metadata.get("route"),
        "status": executed.result_status,
        "reason": executed.result_reason,
        "badges": [f"{badge.get('label')}={badge.get('value')}" for badge in badges],
        # Badges on a non-ok answer that no execution receipt backs. Comparing
        # data cannot catch these: there is no data to compare.
        "unproven_badges": [
            f"{badge.get('label')}={badge.get('value')}"
            for badge in badges
            if executed.result_status != "ok"
            and _receipt_state(receipts, _badge_filter_id(badge)) != RECEIPT_APPLIED
        ],
        "fingerprint": _fingerprint(executed.result),
    }


def _receipt_state(receipts: dict[str, Any], filter_id: str | None) -> str | None:
    entry = receipts.get(filter_id) if filter_id else None
    return entry.get("state") if isinstance(entry, dict) else None


def _classify(filtered: dict[str, Any], control: dict[str, Any], badge: str | None) -> str:
    if "error" in filtered:
        return ERROR
    if filtered.get("status") == "no_result":
        # A refusal is only honest if it stops claiming filters it never ran.
        # Without this check every no_result was waved through as REFUSED, which
        # is why a false applied-filter badge on an empty answer was invisible.
        return LIED if filtered.get("unproven_badges") else REFUSED
    if "error" in control:
        return APPLIED  # nothing to compare against; not evidence of a lie
    if filtered.get("fingerprint") != control.get("fingerprint"):
        return APPLIED
    # Same data as without the filter. Whether that is a lie or a silent drop
    # depends on whether the app claimed *this* filter was applied - an
    # unrelated badge from a threshold in the same query does not count.
    claimed = badge is not None and any(
        shown.split("=", 1)[0] == badge for shown in (filtered.get("badges") or [])
    )
    return LIED if claimed else DROPPED


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--only", help="comma-separated filter ids to run")
    parser.add_argument("--json", type=Path, help="write full results here")
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text())
    seeds = config["seeds"]
    filters = config["filters"]
    if args.only:
        wanted = {value.strip() for value in args.only.split(",")}
        filters = [entry for entry in filters if entry["id"] in wanted]

    control_cache: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    total = sum(
        1 for seed in seeds for flt in filters if seed["id"] not in (flt.get("skip_seeds") or [])
    )
    done = 0

    for seed in seeds:
        if seed["id"] not in control_cache:
            control_cache[seed["id"]] = _run(seed["query"])
        control = control_cache[seed["id"]]

        for flt in filters:
            if seed["id"] in (flt.get("skip_seeds") or []):
                continue
            query = f"{seed['query']} {flt['phrase']}"
            filtered = _run(query)
            verdict = _classify(filtered, control, flt.get("badge"))
            done += 1
            print(
                f"[{done}/{total}] {verdict:<8} {seed['id']}+{flt['id']}: {query}",
                flush=True,
            )
            rows.append(
                {
                    "seed": seed["id"],
                    "filter": flt["id"],
                    "query": query,
                    "control_query": seed["query"],
                    "verdict": verdict,
                    "route": filtered.get("route"),
                    "badges": filtered.get("badges"),
                    "error": filtered.get("error"),
                }
            )

    counts = Counter(row["verdict"] for row in rows)
    lied = [row for row in rows if row["verdict"] == LIED]
    dropped = [row for row in rows if row["verdict"] == DROPPED]
    errored = [row for row in rows if row["verdict"] == ERROR]

    print()
    print("=" * 78)
    print("RESULT")
    print(f"  {counts[APPLIED]:>4} filters actually changed the answer")
    print(f"  {counts[REFUSED]:>4} were refused honestly")
    print(f"  {counts[LIED]:>4} LIED - answered unfiltered while claiming the filter applied")
    print(f"  {counts[DROPPED]:>4} were silently dropped (no badge, no claim)")
    print(f"  {counts[ERROR]:>4} crashed")

    if lied:
        print()
        print("LIED - the app claimed it filtered, and did not:")
        for row in lied:
            badges = ", ".join(row["badges"] or []) or "(no badge)"
            print(f"  {row['query']}")
            print(f"      route={row['route']}  showing: {badges}")

    if dropped:
        print()
        print("SILENTLY DROPPED - words ignored, but nothing was claimed:")
        for row in dropped:
            print(f"  {row['query']}  [route={row['route']}]")

    if errored:
        print()
        print("CRASHED:")
        for row in errored:
            print(f"  {row['query']}\n      {row['error']}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(rows, indent=2))
        print(f"\nfull results: {args.json}")

    return 1 if lied else 0


if __name__ == "__main__":
    raise SystemExit(main())
