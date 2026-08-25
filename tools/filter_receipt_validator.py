"""Fail when the product shows an applied-filter badge it cannot prove it earned.

``tools/filter_execution_sweep.py`` cannot see this class of defect: it buckets
every ``no_result`` as REFUSED before looking at the badges, so a non-ok answer
carrying a false applied-filter claim is invisible to it.

The claim this validator checks is narrow and absolute:

    every badge on a non-ok result must have an execution receipt proving the
    filter actually ran

A ``no_match`` whose filters really did run passes - the receipts say so. The
rejected Phase 1A candidate fails, because ``Tatum clutch stats at home on
January 1 2024`` showed a Clutch badge over a sample that was empty before the
clutch filter was reached.

Usage:
    python tools/filter_receipt_validator.py
    python tools/filter_receipt_validator.py --json outputs/receipts.json

Exit code is 1 when any case fails, so this can gate CI.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nbatools.query_service import execute_natural_query  # noqa: E402

try:  # pragma: no cover - exercised by running against an older candidate
    from nbatools.commands._filter_receipts import APPLIED
    from nbatools.query_service import _badge_filter_id
except ImportError:
    # A build that predates execution receipts. Keep running rather than
    # crashing, so this validator can demonstrate the defect on the candidate
    # it was written to reject: with no receipts at all, every badge on a
    # non-ok result is by definition unproven.
    APPLIED = "applied"

    def _badge_filter_id(badge: dict[str, Any]) -> str | None:
        if badge.get("kind") == "threshold":
            return "threshold"
        return str(badge.get("label", "")) or None


PASS = "PASS"
FALSE_CLAIM = "FALSE_CLAIM"
ERROR = "ERROR"

# Queries that mix filters applied at different depths of route execution, so an
# early one can empty the sample before a later one is ever reached. Each is a
# place a badge could be claimed without the work behind it.
CASES: list[dict[str, str]] = [
    # The confirmed defect: date + location empty the sample before clutch runs.
    {"query": "Tatum clutch stats at home on January 1 2024", "why": "date/location before clutch"},
    {"query": "Jokic clutch stats on January 1 2024", "why": "date before clutch"},
    {"query": "Curry clutch stats at home in 2019-20", "why": "location before clutch"},
    {
        "query": "LeBron clutch stats in wins on December 25 2023",
        "why": "outcome+date before clutch",
    },
    {"query": "Tatum 4th quarter stats on January 1 2024", "why": "date before period filter"},
    {"query": "top scorers among starters on January 1 2024", "why": "date before role filter"},
    {"query": "Lakers clutch record on January 1 2024", "why": "date before team clutch"},
    {
        "query": "Jokic clutch stats with over 200 points this season",
        "why": "threshold before clutch",
    },
    {"query": "Wembanyama clutch stats away in 2018-19", "why": "pre-career season empties sample"},
    # Controls: filters that genuinely ran and legitimately matched nothing.
    {
        "query": "Nikola Jokic games with over 80 points this season",
        "why": "control: threshold ran",
    },
    {"query": "Jokic games with over 100 points at home this season", "why": "control: both ran"},
]


def _check(query: str) -> dict[str, Any]:
    try:
        executed = execute_natural_query(query)
    except Exception as exc:  # noqa: BLE001 - the validator reports, never raises
        return {"query": query, "verdict": ERROR, "detail": f"{type(exc).__name__}: {exc}"}

    metadata = executed.metadata or {}
    status = executed.result_status
    badges = metadata.get("applied_filters") or []
    receipts = (getattr(executed.result, "metadata", None) or {}).get("filter_receipts") or {}

    if status == "ok":
        return {"query": query, "verdict": PASS, "status": status, "detail": "successful answer"}

    unproven: list[str] = []
    for badge in badges:
        filter_id = _badge_filter_id(badge)
        entry = receipts.get(filter_id) if filter_id else None
        state = entry.get("state") if isinstance(entry, dict) else None
        if state != APPLIED:
            unproven.append(f"{badge.get('label')}={badge.get('value')} (receipt={state})")

    return {
        "query": query,
        "verdict": FALSE_CLAIM if unproven else PASS,
        "status": status,
        "reason": executed.result_reason,
        "route": metadata.get("route"),
        "badges": [f"{b.get('label')}={b.get('value')}" for b in badges],
        "receipts": {k: v.get("state") for k, v in receipts.items() if isinstance(v, dict)},
        "unevaluated_filters": metadata.get("unevaluated_filters"),
        "unproven": unproven,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="write full results here")
    args = parser.parse_args()

    rows = []
    for case in CASES:
        row = _check(case["query"])
        row["why"] = case["why"]
        rows.append(row)
        marker = {PASS: "ok  ", FALSE_CLAIM: "FAIL", ERROR: "ERR "}[row["verdict"]]
        print(f"  {marker}  {case['query']}")
        if row["verdict"] == FALSE_CLAIM:
            for claim in row["unproven"]:
                print(f"          unproven applied-filter claim: {claim}")
        elif row["verdict"] == ERROR:
            print(f"          {row['detail']}")

    failures = [row for row in rows if row["verdict"] != PASS]
    print()
    print(f"cases: {len(rows)}  pass: {len(rows) - len(failures)}  fail: {len(failures)}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(rows, indent=2, default=str))
        print(f"full results: {args.json}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
