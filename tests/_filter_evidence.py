"""Shared public-answer evidence checks for the filter-integrity tests.

Validation-only. The canonical extraction lives in
`tools/filter_execution_sweep.py`; this module wraps it in the assertions the
data-backed integrity test makes, so that test and the sweep judge "did the
answer change" from exactly the same evidence. Product code must not import
this module, and this module must not be imported by product code.

The executor is injected so the same logic can be proved deterministically
without NBA data.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from tools import filter_execution_sweep as sweep


class EvidenceFailure(AssertionError):
    """A query failed at the system level, so it proves nothing about filters.

    Distinct from an ordinary assertion failure about filter behavior: this
    says the run could not produce usable evidence at all.
    """


@dataclass(frozen=True)
class QueryEvidence:
    """One executed query reduced to its complete public answer evidence."""

    query: str
    status: str
    reason: str | None
    badges: list[tuple[str, str]]
    fingerprint: str
    populated: bool
    sections: list[str]


def collect_evidence(query: str, execute: Callable[[str], Any]) -> QueryEvidence:
    """Execute one query and reduce it to comparable public answer evidence.

    Raises `EvidenceFailure` for every system-level outcome - a raised
    exception, a returned `result_status=error` envelope, a status outside the
    contract, or an unusable public-sections contract. None of those may be
    mistaken for "the filter changed the answer".
    """
    try:
        executed = execute(query)
    except Exception as exc:  # noqa: BLE001 - reported as an explicit evidence failure
        raise EvidenceFailure(f"{query!r} raised {type(exc).__name__}: {exc}") from exc

    metadata = getattr(executed, "metadata", None) or {}
    status = str(executed.result_status)
    reason = executed.result_reason
    badges = [
        (str(badge.get("label")), str(badge.get("value")))
        for badge in (metadata.get("applied_filters") or [])
    ]

    if status not in sweep.CANONICAL_RESULT_STATUSES:
        raise EvidenceFailure(
            f"{query!r} returned result_status={status!r}, which is outside the result "
            f"contract. Decide its meaning explicitly before treating it as an answer."
        )
    if status == str(sweep.ResultStatus.ERROR):
        raise EvidenceFailure(
            f"{query!r} failed at the system level: result_status='error' "
            f"result_reason={reason!r}. A system error is not a changed answer."
        )

    try:
        sections = sweep.public_sections(executed.result)
        fingerprint = sweep.fingerprint_sections(sections)
        populated = sweep.sections_are_populated(sections)
    except sweep.PublicContractError as exc:
        raise EvidenceFailure(
            f"{query!r} published unusable answer evidence [{exc.kind}]: {exc.detail}"
        ) from exc

    return QueryEvidence(
        query=query,
        status=status,
        reason=reason,
        badges=badges,
        fingerprint=fingerprint,
        populated=populated,
        sections=sorted(sections),
    )


def assert_filter_applied_or_refused(
    filtered_query: str,
    control_query: str,
    badge_label: str,
    execute: Callable[[str], Any],
) -> None:
    """A filter must change the complete public answer, or be refused honestly.

    Returning the unfiltered answer while displaying the badge is the one
    outcome that is never acceptable.
    """
    filtered = collect_evidence(filtered_query, execute)
    control = collect_evidence(control_query, execute)

    if filtered.status == str(sweep.ResultStatus.NO_RESULT):
        # Honest refusal: the engine must not also advertise the filter as applied.
        assert not any(label == badge_label for label, _ in filtered.badges), (
            f"{filtered_query!r} refused but still displays a {badge_label!r} badge"
        )
        return

    # "The answer changed" only means something against a real baseline.
    if control.status != str(sweep.ResultStatus.OK):
        raise EvidenceFailure(
            f"control {control_query!r} returned result_status={control.status!r}; "
            f"it cannot serve as a comparison baseline"
        )
    if not control.populated:
        raise EvidenceFailure(
            f"control {control_query!r} returned no populated public answer "
            f"(sections={control.sections}); it cannot serve as a comparison baseline"
        )

    assert filtered.fingerprint != control.fingerprint, (
        f"{filtered_query!r} returned identical public answer data to the unfiltered "
        f"control {control_query!r} while displaying badges {filtered.badges}. Compared "
        f"sections: {filtered.sections}. The filter was detected but never executed."
    )
