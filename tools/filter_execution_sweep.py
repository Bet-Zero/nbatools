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
from collections.abc import Mapping
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

# The public answer sections each supported result type is currently known to
# expose, keyed by result class name. `to_dict()["sections"]` is the canonical
# public-data contract; this registry is the explicit inventory of the section
# policies that have been decided and exercised.
#
# Evidence extraction deliberately does NOT filter through this registry -
# every section a result actually emits is compared, so nothing can be
# silently omitted at runtime. The registry backs the guard tests in
# `tests/test_qa_gate_integrity.py`, which detect a new or removed result type
# and any section reachable from their fully-populated fixtures. A future
# optional section that no fixture populates would still be fingerprinted at
# runtime, but it would not be caught by that fixture-based guard until the
# fixture covers it.
SUPPORTED_RESULT_SECTIONS: dict[str, frozenset[str]] = {
    "NoResult": frozenset(),
    "SummaryResult": frozenset({"summary", "by_season", "game_log", "top_performers"}),
    "ComparisonResult": frozenset({"summary", "comparison"}),
    "SplitSummaryResult": frozenset({"summary", "split_comparison"}),
    "FinderResult": frozenset({"finder"}),
    "LeaderboardResult": frozenset({"leaderboard"}),
    "StreakResult": frozenset({"streak"}),
    "CountResult": frozenset({"count", "finder"}),
}

# `count` is published on every CountResult, including a zero count. A zero
# count is an expected-negative answer, not a populated baseline, so this
# section is the one that needs a value check rather than a row check.
COUNT_SECTION = "count"

# How a completed result failed to publish usable public answer evidence.
# Each is a system-level failure: the answer data could not be read, so it can
# never be compared as if it were an ordinary answer.
MISSING_PUBLIC_CONTRACT = "missing_public_result_contract"
NON_DICT_PUBLIC_PAYLOAD = "non_dict_public_result_payload"
MISSING_PUBLIC_SECTIONS = "missing_public_sections"
NON_DICT_PUBLIC_SECTIONS = "non_dict_public_sections"
MALFORMED_PUBLIC_SECTION = "malformed_public_section"
PUBLIC_CONTRACT_EXCEPTION = "public_result_contract_exception"

PUBLIC_CONTRACT_ERROR_KINDS = frozenset(
    {
        MISSING_PUBLIC_CONTRACT,
        NON_DICT_PUBLIC_PAYLOAD,
        MISSING_PUBLIC_SECTIONS,
        NON_DICT_PUBLIC_SECTIONS,
        MALFORMED_PUBLIC_SECTION,
        PUBLIC_CONTRACT_EXCEPTION,
    }
)


class PublicContractError(Exception):
    """A completed result did not publish usable public answer evidence.

    Raised instead of returning a sentinel, so an unreadable answer can never
    be compared as ordinary data. `_run` converts it into an ERROR row.
    """

    def __init__(self, kind: str, detail: str, sections: list[str] | None = None) -> None:
        super().__init__(detail)
        self.kind = kind
        self.detail = detail
        self.sections = sections or []


class Classification(NamedTuple):
    """One row's verdict, plus why it was not testable or how a side failed."""

    verdict: str
    no_signal_reason: str | None = None
    error_source: str | None = None
    error_kind: str | None = None


def public_sections(result: Any) -> dict[str, Any]:
    """The canonical public answer sections of a structured result.

    Reads `to_dict()["sections"]`, the contract the API and formatters already
    publish, so the evidence covers every displayed answer section rather than
    a hand-maintained attribute list that drifts from the result classes. The
    surrounding `metadata`, `notes`, `caveats`, `current_through`, and status
    fields are presentation and trust metadata, not answer data, and are
    deliberately excluded.

    A result that completed but published no usable contract is a system-level
    failure, not an unusual answer: this raises `PublicContractError` rather
    than returning a comparable value. An empty `sections` mapping is valid -
    `NoResult` publishes exactly that - and is simply not populated.
    """
    if result is None:
        raise PublicContractError(
            MISSING_PUBLIC_CONTRACT, "result object is None; no public answer to read"
        )
    to_dict = getattr(result, "to_dict", None)
    if not callable(to_dict):
        raise PublicContractError(
            MISSING_PUBLIC_CONTRACT,
            f"{type(result).__name__} publishes no callable to_dict()",
        )
    payload = to_dict()
    if not isinstance(payload, dict):
        raise PublicContractError(
            NON_DICT_PUBLIC_PAYLOAD,
            f"{type(result).__name__}.to_dict() returned {type(payload).__name__}, not a dict",
        )
    if "sections" not in payload:
        raise PublicContractError(
            MISSING_PUBLIC_SECTIONS,
            f"{type(result).__name__}.to_dict() has no 'sections' mapping",
        )
    sections = payload["sections"]
    if not isinstance(sections, dict):
        raise PublicContractError(
            NON_DICT_PUBLIC_SECTIONS,
            f"{type(result).__name__}.to_dict()['sections'] is "
            f"{type(sections).__name__}, not a dict",
        )
    _validate_section_shapes(result, sections)
    return sections


def _validate_section_shapes(result: Any, sections: dict[str, Any]) -> None:
    """Reject a malformed answer without validating arbitrary objects.

    The structured contract publishes each section as a list of public
    records. Checking that much rejects a broken answer while leaving the
    record contents to the fingerprint.
    """
    seen: list[str] = []
    for name, rows in sections.items():
        if not isinstance(name, str):
            raise PublicContractError(
                MALFORMED_PUBLIC_SECTION,
                f"{type(result).__name__} published a non-string section name "
                f"{name!r} ({type(name).__name__})",
                sections=seen,
            )
        if not isinstance(rows, list):
            raise PublicContractError(
                MALFORMED_PUBLIC_SECTION,
                f"{type(result).__name__} section {name!r} is "
                f"{type(rows).__name__}, not a list of records",
                sections=seen,
            )
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise PublicContractError(
                    MALFORMED_PUBLIC_SECTION,
                    f"{type(result).__name__} section {name!r} row {index} is "
                    f"{type(row).__name__}, not a record",
                    sections=seen,
                )
        seen.append(name)


def _section_has_answer(name: str, rows: Any) -> bool:
    """True when one public section carries a real answer."""
    if not rows:
        return False
    if name == COUNT_SECTION:
        return any(_is_positive_count(row) for row in rows)
    return True


def _is_positive_count(row: Any) -> bool:
    value = row.get(COUNT_SECTION) if isinstance(row, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return value > 0


def fingerprint_sections(sections: dict[str, Any]) -> str:
    """Stable fingerprint of the public answer data a query returned.

    Section names are part of the fingerprint, so a section appearing or
    disappearing counts as a change. Row order and cell values are preserved
    by the serialization, so a reordered or edited answer is a change too.
    Every emitted section is included, registry or not.
    """
    payload = json.dumps(sections, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"sections[{','.join(sorted(sections))}]:{digest}"


def sections_are_populated(sections: dict[str, Any]) -> bool:
    """True when the public answer data can anchor a comparison.

    An answer with no populated section cannot: two such answers fingerprint
    the same no matter what the filter did.
    """
    if not sections:
        return False
    return any(_section_has_answer(name, rows) for name, rows in sections.items())


def _failed_side(
    kind: str,
    error: str,
    *,
    status: Any = None,
    reason: Any = None,
    route: Any = None,
    badges: list[str] | None = None,
    sections: list[str] | None = None,
) -> dict[str, Any]:
    """One side that failed at the system level, keeping whatever it did tell us."""
    return {
        "error": error,
        "error_kind": kind,
        "route": route,
        "status": status,
        "reason": reason,
        "badges": badges or [],
        "fingerprint": None,
        "populated": False,
        "sections": sections or [],
    }


def _run(query: str) -> dict[str, Any]:
    """Execute one query and reduce it to comparable evidence.

    Every step is inside the protected boundary - execution, status
    inspection, extraction, validation, fingerprinting, and the populated
    decision - so a failure anywhere becomes an ERROR row instead of aborting
    the run before the JSON evidence is written.
    """
    try:
        executed = execute_natural_query(query)
    except Exception as exc:  # noqa: BLE001 - the sweep reports failures, never raises
        return _failed_side(RAISED_EXCEPTION, f"{type(exc).__name__}: {exc}")

    status: Any = None
    reason: Any = None
    route: Any = None
    badges: list[str] = []
    try:
        metadata = executed.metadata or {}
        status = executed.result_status
        reason = executed.result_reason
        route = metadata.get("route")
        badges = [
            f"{badge.get('label')}={badge.get('value')}"
            for badge in (metadata.get("applied_filters") or [])
        ]

        # An already-known system failure is recorded on its own terms; it
        # does not need readable answer evidence first.
        returned_kind = _returned_error_kind(status)
        if returned_kind is not None:
            return _failed_side(
                returned_kind,
                _returned_failure(status, reason) or "returned a system error",
                status=status,
                reason=reason,
                route=route,
                badges=badges,
            )

        # One extraction feeds both the comparison and the populated decision,
        # so they can never disagree about what the answer data was.
        sections = public_sections(executed.result)
        fingerprint = fingerprint_sections(sections)
        populated = sections_are_populated(sections)
        section_names = sorted(sections)
    except PublicContractError as exc:
        return _failed_side(
            exc.kind,
            exc.detail,
            status=status,
            reason=reason,
            route=route,
            badges=badges,
            sections=sorted(exc.sections),
        )
    except Exception as exc:  # noqa: BLE001 - evidence failures are reported, never raised
        return _failed_side(
            PUBLIC_CONTRACT_EXCEPTION,
            f"{type(exc).__name__}: {exc}",
            status=status,
            reason=reason,
            route=route,
            badges=badges,
        )

    return {
        "error": None,
        "error_kind": None,
        "route": route,
        "status": status,
        "reason": reason,
        "badges": badges,
        "fingerprint": fingerprint,
        "populated": populated,
        "sections": section_names,
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
    print(f"  {counts[ERROR]:>4} ERROR      raised, returned a system error, or broke its contract")
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
        print(
            "SYSTEM ERRORS - a query raised, returned a system-error result, "
            "or published unusable answer evidence:"
        )
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
                            "sections": filtered.get("sections"),
                            "error": filtered.get("error"),
                            "error_kind": filtered.get("error_kind"),
                        },
                        "control": {
                            "status": control.get("status"),
                            "reason": control.get("reason"),
                            "route": control.get("route"),
                            "badges": control.get("badges"),
                            "populated": control.get("populated"),
                            "sections": control.get("sections"),
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
