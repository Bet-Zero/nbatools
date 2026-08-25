"""Per-filter execution receipts recorded by the route that does the filtering.

A final result reason cannot prove that every requested filter ran. The clearest
counterexample is ``Tatum clutch stats at home on January 1 2024``: the date and
location filters empty the sample, and the clutch filter then runs against zero
rows, finds nothing to check coverage for, and reports no problem. The result is
``no_match`` and every requested filter looks like it executed. Clutch never did.

So execution is recorded where it happens. A route opens a ledger, declares what
it was asked to filter by, and marks each filter as it actually applies it.
Whatever is still unmarked when the route returns early was never evaluated.

Only the route that performs the filtering may mark a filter ``applied``.
``query_service`` reads these receipts; it never infers execution from parse
state, the selected route, or the final result reason.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Receipt states
# ---------------------------------------------------------------------------

#: Requested by the user and proven to have run against the sample.
APPLIED = "applied"
#: Requested, but this route has no code that can express it.
UNSUPPORTED = "unsupported"
#: Requested, but the entity or value it needed never resolved.
UNRESOLVED = "unresolved"
#: Requested and supported, but execution returned before reaching it - normally
#: because an earlier filter had already emptied the sample. Not a refusal: the
#: filter is fine, it simply had nothing to run against.
NOT_EVALUATED = "not_evaluated"
#: Requested and supported, but the trusted source coverage it needs is missing.
COVERAGE_UNAVAILABLE = "coverage_unavailable"

#: States that mean the answer was not filtered the way the request implied.
UNPROVEN_STATES = frozenset({UNSUPPORTED, UNRESOLVED, NOT_EVALUATED, COVERAGE_UNAVAILABLE})

#: Metadata key carrying the serialized ledger.
RECEIPTS_KEY = "filter_receipts"


class FilterExecutionLedger:
    """Ordered record of what each requested filter actually did.

    Usage inside a route::

        receipts = FilterExecutionLedger()
        receipts.declare("date_range", start_date or end_date)
        receipts.declare("clutch", clutch)
        ...
        receipts.applied("date_range")          # after it really ran
        if df.empty:
            receipts.short_circuit("sample was empty before this filter ran")
            return NoResult(..., metadata=receipts.to_metadata())
    """

    def __init__(self) -> None:
        # filter_id -> {"state": str, "detail": str | None}. Insertion-ordered so
        # the serialized ledger reads in the order the route processes filters.
        self._entries: dict[str, dict[str, Any]] = {}

    # -- declaration ------------------------------------------------------

    def declare(self, filter_id: str, requested: Any) -> None:
        """Record that *filter_id* was requested. Falsy *requested* is ignored.

        ``0`` and ``False`` are genuinely "not requested" for every filter this
        ledger tracks, so plain truthiness is the right test.
        """
        if not requested:
            return
        self._entries.setdefault(filter_id, {"state": NOT_EVALUATED, "detail": None})

    def declare_all(self, requests: dict[str, Any]) -> None:
        for filter_id, requested in requests.items():
            self.declare(filter_id, requested)

    # -- outcomes ---------------------------------------------------------

    def _set(self, filter_id: str, state: str, detail: str | None) -> None:
        if filter_id not in self._entries:
            # A route may only report on filters it was asked for; recording an
            # undeclared filter would be a claim about work nobody requested.
            return
        self._entries[filter_id] = {"state": state, "detail": detail}

    def applied(self, filter_id: str, detail: str | None = None) -> None:
        self._set(filter_id, APPLIED, detail)

    def unsupported(self, filter_id: str, detail: str | None = None) -> None:
        self._set(filter_id, UNSUPPORTED, detail)

    def unresolved(self, filter_id: str, detail: str | None = None) -> None:
        self._set(filter_id, UNRESOLVED, detail)

    def coverage_unavailable(self, filter_id: str, detail: str | None = None) -> None:
        self._set(filter_id, COVERAGE_UNAVAILABLE, detail)

    def not_evaluated(self, filter_id: str, detail: str | None = None) -> None:
        self._set(filter_id, NOT_EVALUATED, detail)

    def short_circuit(self, detail: str) -> None:
        """Mark every filter still awaiting execution as never evaluated."""
        for filter_id, entry in self._entries.items():
            if entry["state"] == NOT_EVALUATED and entry["detail"] is None:
                self._entries[filter_id] = {"state": NOT_EVALUATED, "detail": detail}

    # -- inspection -------------------------------------------------------

    def state(self, filter_id: str) -> str | None:
        entry = self._entries.get(filter_id)
        return entry["state"] if entry else None

    def applied_ids(self) -> list[str]:
        return [fid for fid, entry in self._entries.items() if entry["state"] == APPLIED]

    def unproven_ids(self) -> list[str]:
        return [fid for fid, entry in self._entries.items() if entry["state"] in UNPROVEN_STATES]

    def to_metadata(self) -> dict[str, Any]:
        """Serialize as ``{RECEIPTS_KEY: {filter_id: {state, detail}}}``."""
        return {
            RECEIPTS_KEY: {
                filter_id: {
                    "state": entry["state"],
                    **({"detail": entry["detail"]} if entry["detail"] else {}),
                }
                for filter_id, entry in self._entries.items()
            }
        }

    def merge_into(self, metadata: dict[str, Any] | None) -> dict[str, Any]:
        """Return *metadata* with this ledger attached."""
        merged = dict(metadata or {})
        merged.update(self.to_metadata())
        return merged


def receipts_from_metadata(metadata: Any) -> dict[str, dict[str, Any]]:
    """Read a serialized ledger back out of result metadata."""
    if not isinstance(metadata, dict):
        return {}
    receipts = metadata.get(RECEIPTS_KEY)
    return receipts if isinstance(receipts, dict) else {}


def receipt_state(receipts: dict[str, dict[str, Any]], filter_id: str) -> str | None:
    entry = receipts.get(filter_id)
    if not isinstance(entry, dict):
        return None
    state = entry.get("state")
    return state if isinstance(state, str) else None


def clutch_coverage_blocked(
    query_class: str,
    note: str,
    receipts: FilterExecutionLedger | None = None,
):
    """The one construction for "clutch was understood but has no coverage".

    Four routes execute clutch filters and each used to build this refusal by
    hand. They must agree on the blocker id, the result reason, and the receipt
    state, because the frontend uses all three to tell a coverage failure apart
    from a clutch fragment nobody could interpret.
    """
    from nbatools.commands.structured_results import NoResult

    metadata: dict[str, Any] = {"unsupported_filters": ["clutch_coverage"]}
    if receipts is not None:
        receipts.coverage_unavailable("clutch", note)
        metadata.update(receipts.to_metadata())
    return NoResult(
        query_class=query_class,
        reason="filter_not_supported",
        result_status="no_result",
        result_reason="filter_not_supported",
        metadata=metadata,
        notes=[note],
    )
