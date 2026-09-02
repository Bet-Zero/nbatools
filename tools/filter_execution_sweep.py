"""Find filters the app accepts, displays as applied, and then ignores.

Asks every question twice - once with a filter phrase, once without - and
compares the data that comes back. Identical data means the filter did nothing.
No hand-verified answer is needed, so this covers far more phrasings than
qa/raw_query_answer_corpus.yaml, which remains the stronger check (it verifies
the numbers are *correct*, not merely that filtering happened).

A pair can only test filter execution when the control question - the same
question without the filter phrase - came back with a populated answer to
compare against. When it did not, the pair proves nothing: it is reported as
NO_SIGNAL rather than counted as an honest refusal. A run against an empty data
root therefore reports NO_SIGNAL and exits non-zero instead of claiming that
every filter was refused honestly and no filter lied.

Usage:
    python tools/filter_execution_sweep.py
    python tools/filter_execution_sweep.py --only position_guards,last_n
    python tools/filter_execution_sweep.py --json outputs/sweep.json

Each combination lands in one of six buckets: APPLIED (the answer changed),
REFUSED (the app declined the filtered question against a populated control),
LIED (unfiltered answer behind a badge claiming otherwise), DROPPED (the words
were ignored, but nothing was claimed), NO_SIGNAL (no populated control answer,
so nothing was testable), or ERROR (a system-level failure).

The result contract separates expected negative outcomes from system failures,
and so does this sweep. `result_status=no_result` is expected: on the filtered
side it is an honest REFUSED, on the control side it leaves NO_SIGNAL.
`result_status=error` is a system-level failure - `unrouted` and internal
failures arrive that way - and is ERROR on either side, exactly like a raised
exception. Neither is rounded down to an honest refusal or a coverage gap.

The run as a whole reports PASS, PASS_WITH_GAPS, FAIL, or NO_SIGNAL.

Exit codes:
    0  PASS or PASS_WITH_GAPS - every comparable row behaved honestly
    1  FAIL - a verified defect (LIED) or a system-level failure (ERROR)
    2  NO_SIGNAL - nothing was comparable; no verdict about filters was earned

See docs/operations/filter_execution_sweep.md for the full evidence model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nbatools.commands.structured_results import ResultStatus  # noqa: E402
from nbatools.data_source import data_generation_context  # noqa: E402
from nbatools.query_service import execute_natural_query  # noqa: E402

DEFAULT_CONFIG = REPO_ROOT / "qa" / "filter_execution_sweep.yaml"

# What happened to a filter on a given question.
APPLIED = "APPLIED"  # data changed - the filter did something
REFUSED = "REFUSED"  # app declined the filtered question - honest
LIED = "LIED"  # same data, and a badge claiming this filter was applied
DROPPED = "DROPPED"  # same data, no badge - the words were silently ignored
NO_SIGNAL = "NO_SIGNAL"  # no populated control answer - nothing was testable
ERROR = "ERROR"  # raised, or came back as a system-error envelope

# How a side failed. A raised exception and a returned `result_status=error`
# envelope are both system-level failures; only the delivery differs.
RAISED_EXCEPTION = "raised_exception"
RETURNED_ERROR_STATUS = "returned_error_status"
UNKNOWN_RESULT_STATUS = "unknown_result_status"

# The canonical statuses the result contract may produce. Anything else is a
# contract violation, so the sweep fails closed rather than guessing.
CANONICAL_RESULT_STATUSES = frozenset(status.value for status in ResultStatus)

# Only these verdicts were reached by actually comparing two populated answers.
COMPARABLE_VERDICTS = (APPLIED, REFUSED, LIED, DROPPED)
VERDICTS = (APPLIED, REFUSED, LIED, DROPPED, NO_SIGNAL, ERROR)

# What the run as a whole proved.
STATUS_PASS = "PASS"  # every configured row was comparable and behaved
STATUS_PASS_WITH_GAPS = "PASS_WITH_GAPS"  # the comparable rows behaved; some were not testable
STATUS_FAIL = "FAIL"  # a verified defect or an execution error
STATUS_NO_SIGNAL = "NO_SIGNAL"  # nothing was comparable; no verdict was earned

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_NO_SIGNAL = 2

EXIT_CODES = {
    STATUS_PASS: EXIT_PASS,
    STATUS_PASS_WITH_GAPS: EXIT_PASS,
    STATUS_FAIL: EXIT_FAIL,
    STATUS_NO_SIGNAL: EXIT_NO_SIGNAL,
}

# Bumped when the shape of the --json artifact changes.
JSON_SCHEMA_VERSION = 2

# Result frames that carry comparable answer data.
FINGERPRINT_ATTRS = ("games", "leaders", "streaks", "summary", "splits", "comparison")


class Classification(NamedTuple):
    """One row's verdict, plus why it was not testable or how a side failed."""

    verdict: str
    no_signal_reason: str | None = None
    error_source: str | None = None
    error_kind: str | None = None


def _frames(result: Any) -> Iterator[tuple[str, Any]]:
    """Yield the result frames that carry comparable answer data."""
    for attr in FINGERPRINT_ATTRS:
        frame = getattr(result, attr, None)
        if frame is None or not hasattr(frame, "to_csv"):
            continue
        yield attr, frame


def _fingerprint(result: Any) -> str:
    """Stable fingerprint of the data a query actually returned."""
    if result is None:
        return "NONE"
    parts: list[str] = []
    for attr, frame in _frames(result):
        digest = hashlib.md5(frame.to_csv(index=False).encode()).hexdigest()[:16]
        parts.append(f"{attr}:{frame.shape}:{digest}")
    return "||".join(parts) or f"type={type(result).__name__}"


def _populated(result: Any) -> bool:
    """True when the result carries at least one row of comparable data.

    An answer with no populated frame cannot anchor a comparison: two such
    answers fingerprint the same no matter what the filter did.
    """
    return any(getattr(frame, "shape", (0,))[0] > 0 for _, frame in _frames(result))


def _run(query: str) -> dict[str, Any]:
    try:
        executed = execute_natural_query(query)
    except Exception as exc:  # noqa: BLE001 - the sweep reports failures, never raises
        return {
            "error": f"{type(exc).__name__}: {exc}",
            "error_kind": RAISED_EXCEPTION,
            "route": None,
            "status": None,
            "reason": None,
            "badges": [],
            "fingerprint": None,
            "populated": False,
        }
    metadata = executed.metadata or {}
    status = executed.result_status
    reason = executed.result_reason
    return {
        "error": _returned_failure(status, reason),
        "error_kind": _returned_error_kind(status),
        "route": metadata.get("route"),
        "status": status,
        "reason": reason,
        "badges": [
            f"{badge.get('label')}={badge.get('value')}"
            for badge in (metadata.get("applied_filters") or [])
        ],
        "fingerprint": _fingerprint(executed.result),
        "populated": _populated(executed.result),
    }


def _returned_error_kind(status: Any) -> str | None:
    """How a completed query failed at the system level, if it did.

    `result_status=error` is the contract's system-level failure envelope -
    `unrouted` and internal failures arrive this way rather than as an
    exception. A status outside the canonical set is a contract violation, so
    it fails closed too.
    """
    if status == ResultStatus.ERROR:
        return RETURNED_ERROR_STATUS
    if status not in CANONICAL_RESULT_STATUSES:
        return UNKNOWN_RESULT_STATUS
    return None


def _returned_failure(status: Any, reason: Any) -> str | None:
    kind = _returned_error_kind(status)
    if kind is None:
        return None
    return f"result_status={status!s} result_reason={reason!s}"


def control_gap(control: dict[str, Any]) -> str | None:
    """Why this control cannot anchor a comparison, or None when it can.

    This describes coverage gaps only: an expected negative outcome that left
    no baseline. A control that raised or returned a system-error envelope is
    a failure, not a gap, and `_classify` settles that before calling this.

    A control is comparable only when the unfiltered question came back with a
    populated answer. A refusal, missing local data, uncovered season
    coverage, or an empty answer all leave nothing to compare against.
    """
    status = control.get("status")
    if status != ResultStatus.OK:
        return f"control_{status or 'unknown'}:{control.get('reason') or 'unknown'}"
    if not control.get("populated"):
        return "control_empty_result"
    return None


def _classify(
    filtered: dict[str, Any], control: dict[str, Any], badge: str | None
) -> Classification:
    # A system-level failure on either side is a defect worth surfacing
    # regardless of what the other side did - whether it arrived as a raised
    # exception or as a returned `result_status=error` envelope.
    if filtered.get("error_kind"):
        return Classification(ERROR, error_source="filtered", error_kind=filtered["error_kind"])
    if control.get("error_kind"):
        return Classification(ERROR, error_source="control", error_kind=control["error_kind"])
    # Without a populated control this pair tests nothing. Saying "refused
    # honestly" here would turn missing data into a clean bill of health.
    gap = control_gap(control)
    if gap is not None:
        return Classification(NO_SIGNAL, no_signal_reason=gap)
    # An expected negative outcome on the filtered side only. System errors
    # were already settled above, so this is a genuine refusal.
    if filtered.get("status") != ResultStatus.OK:
        return Classification(REFUSED)
    if filtered.get("fingerprint") != control.get("fingerprint"):
        return Classification(APPLIED)
    # Same data as without the filter. Whether that is a lie or a silent drop
    # depends on whether the app claimed *this* filter was applied - an
    # unrelated badge from a threshold in the same query does not count.
    claimed = badge is not None and any(
        shown.split("=", 1)[0] == badge for shown in (filtered.get("badges") or [])
    )
    return Classification(LIED if claimed else DROPPED)


def run_status(counts: Mapping[str, int], comparable: int) -> str:
    """Classify the run from its rows.

    A verified defect or an execution error fails the run. Otherwise a run
    proves something only if at least one row was actually comparable.
    """
    if counts[LIED] or counts[ERROR]:
        return STATUS_FAIL
    if comparable == 0:
        return STATUS_NO_SIGNAL
    if counts[NO_SIGNAL]:
        return STATUS_PASS_WITH_GAPS
    return STATUS_PASS


def build_summary(
    rows: list[dict[str, Any]],
    *,
    configured_comparisons: int,
    data_generation: str,
    config_path: Path,
    only: str | None,
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    counts = Counter({verdict: 0 for verdict in VERDICTS})
    counts.update(row["verdict"] for row in rows)
    comparable = sum(1 for row in rows if row["comparable"])
    status = run_status(counts, comparable)
    reasons = Counter(row["no_signal_reason"] for row in rows if row["verdict"] == NO_SIGNAL)
    return {
        "schema_version": JSON_SCHEMA_VERSION,
        "status": status,
        "exit_code": EXIT_CODES[status],
        "configured_comparisons": configured_comparisons,
        "executed_comparisons": len(rows),
        "comparable_comparisons": comparable,
        "no_signal_comparisons": counts[NO_SIGNAL],
        "verdict_counts": {verdict: counts[verdict] for verdict in VERDICTS},
        "no_signal_reason_counts": dict(sorted(reasons.items())),
        "data_generation": data_generation,
        "config": str(config_path),
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "only": only,
        "started_at": started_at,
        "completed_at": completed_at,
    }


def _print_report(summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    counts = summary["verdict_counts"]
    comparable = summary["comparable_comparisons"]
    configured = summary["configured_comparisons"]

    print()
    print("=" * 78)
    print(f"RESULT: {summary['status']}   (exit {summary['exit_code']})")

    if comparable == 0:
        print()
        print(f"  0 of {configured} configured comparisons had a populated control answer.")
        print("  Nothing about filter execution was tested by this run.")
        print("  APPLIED / REFUSED / LIED / DROPPED were not measured here, so none of")
        print("  them is a verified zero. This is not a clean result.")
    else:
        print()
        print(
            f"  {comparable} of {configured} configured comparisons had a populated "
            "control to test against"
        )
        print(f"  {counts[APPLIED]:>4} APPLIED    the answer changed - the filter did something")
        print(f"  {counts[REFUSED]:>4} REFUSED    declined the filtered question, honestly")
        print(f"  {counts[LIED]:>4} LIED       answered unfiltered while claiming it filtered")
        print(f"  {counts[DROPPED]:>4} DROPPED    words ignored, but nothing was claimed")
    print(f"  {counts[ERROR]:>4} ERROR      the query raised or returned a system error")
    print(f"  {counts[NO_SIGNAL]:>4} NO_SIGNAL  no populated control - nothing was testable")

    if counts[NO_SIGNAL]:
        print()
        print("  Why those comparisons were not meaningful:")
        for reason, count in summary["no_signal_reason_counts"].items():
            print(f"    {count:>4}  {reason}")

    if summary["status"] == STATUS_PASS_WITH_GAPS:
        print()
        print(f"  This verdict covers the {comparable} comparable rows only, not the")
        print(f"  full {configured}-row configured matrix. The {counts[NO_SIGNAL]} NO_SIGNAL rows")
        print("  were never tested and are not evidence that those filters are honest.")

    if summary["status"] == STATUS_NO_SIGNAL:
        print()
        print("  Re-run against a populated data generation before drawing any")
        print("  conclusion about whether these filters are honest.")

    lied = [row for row in rows if row["verdict"] == LIED]
    dropped = [row for row in rows if row["verdict"] == DROPPED]
    errored = [row for row in rows if row["verdict"] == ERROR]

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
        print("SYSTEM ERRORS - a query raised or returned a system-error result:")
        for row in errored:
            side = row["error_source"]
            detail = row[side] if side in ("filtered", "control") else {}
            print(f"  {row['query']}")
            print(f"      {side} {row['error_kind']}: {row['error']}")
            print(f"      route={detail.get('route')}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--only", help="comma-separated filter ids to run")
    parser.add_argument("--json", type=Path, help="write full results here")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

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

    started_at = datetime.now(UTC).isoformat()
    with data_generation_context() as data_generation:
        for seed in seeds:
            if seed["id"] not in control_cache:
                control_cache[seed["id"]] = _run(seed["query"])
            control = control_cache[seed["id"]]

            for flt in filters:
                if seed["id"] in (flt.get("skip_seeds") or []):
                    continue
                query = f"{seed['query']} {flt['phrase']}"
                filtered = _run(query)
                classified = _classify(filtered, control, flt.get("badge"))
                verdict = classified.verdict
                done += 1
                print(
                    f"[{done}/{total}] {verdict:<9} {seed['id']}+{flt['id']}: {query}",
                    flush=True,
                )
                failing_side = control if classified.error_source == "control" else filtered
                rows.append(
                    {
                        "seed": seed["id"],
                        "filter": flt["id"],
                        "query": query,
                        "control_query": seed["query"],
                        "verdict": verdict,
                        "comparable": verdict in COMPARABLE_VERDICTS,
                        "no_signal_reason": classified.no_signal_reason,
                        "error_source": classified.error_source,
                        "error_kind": classified.error_kind,
                        "route": filtered.get("route"),
                        "badges": filtered.get("badges"),
                        "error": failing_side.get("error"),
                        "fingerprint_match": (
                            None
                            if filtered.get("fingerprint") is None
                            or control.get("fingerprint") is None
                            else filtered.get("fingerprint") == control.get("fingerprint")
                        ),
                        "filtered": {
                            "status": filtered.get("status"),
                            "reason": filtered.get("reason"),
                            "route": filtered.get("route"),
                            "badges": filtered.get("badges"),
                            "populated": filtered.get("populated"),
                            "error": filtered.get("error"),
                            "error_kind": filtered.get("error_kind"),
                        },
                        "control": {
                            "status": control.get("status"),
                            "reason": control.get("reason"),
                            "route": control.get("route"),
                            "badges": control.get("badges"),
                            "populated": control.get("populated"),
                            "error": control.get("error"),
                            "error_kind": control.get("error_kind"),
                        },
                    }
                )
    completed_at = datetime.now(UTC).isoformat()

    summary = build_summary(
        rows,
        configured_comparisons=total,
        data_generation=data_generation,
        config_path=args.config,
        only=args.only,
        started_at=started_at,
        completed_at=completed_at,
    )
    _print_report(summary, rows)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {
                    "schema_version": JSON_SCHEMA_VERSION,
                    "summary": summary,
                    "rows": rows,
                },
                indent=2,
                default=str,
            )
        )
        print(f"\nfull results: {args.json}")

    return summary["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
