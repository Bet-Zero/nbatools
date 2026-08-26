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

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import Any, TypeVar

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

#: Sentinel for "this filter was requested" when the route has no value to pass.
#: Truthy, so it survives any caller that still tests the argument itself.
REQUESTED = True


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
        """Record that *filter_id* was requested.

        ``None`` and ``False`` mean "not requested" - the first is an unset
        optional, the second an unset flag. Every other value counts, ``0``
        included: ``rest_days=0`` is what ``on no rest`` parses to, and every
        other consumer of that slot tests ``rest_days is not None``. Reading it
        as absent dropped a requested filter out of the ledger entirely, which
        is exactly the silence these receipts exist to prevent.

        Pass :data:`REQUESTED` when a route has no value to hand over but knows
        the filter was asked for.
        """
        if requested is None or requested is False:
            return
        self._entries.setdefault(filter_id, {"state": NOT_EVALUATED, "detail": None})

    def declare_all(self, requests: dict[str, Any]) -> None:
        for filter_id, requested in requests.items():
            self.declare(filter_id, requested)

    def declared_ids(self) -> list[str]:
        return list(self._entries)

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


# ---------------------------------------------------------------------------
# Centralized attachment
# ---------------------------------------------------------------------------

# The route currently recording receipts. A route has many exits - validation
# refusals, coverage refusals, empty samples, the successful answer - and
# remembering ``metadata=receipts.to_metadata()`` at each one is a rule that
# holds only until someone adds the next ``return``. The decorator below closes
# every exit at once, including exits that do not exist yet.
_ACTIVE_LEDGER: ContextVar[FilterExecutionLedger | None] = ContextVar(
    "active_filter_ledger", default=None
)

_R = TypeVar("_R")


def active_ledger() -> FilterExecutionLedger:
    """The ledger for the route currently executing.

    Returns a detached ledger outside any :func:`emits_filter_receipts` route so
    helpers stay callable on their own; nothing reads a detached ledger, so it
    can neither leak receipts nor claim work.
    """
    ledger = _ACTIVE_LEDGER.get()
    return ledger if ledger is not None else FilterExecutionLedger()


def attach_receipts(result: _R, ledger: FilterExecutionLedger) -> _R:
    """Stamp *ledger* onto *result*'s metadata. Idempotent."""
    metadata = getattr(result, "metadata", None)
    if not isinstance(metadata, dict):
        return result
    metadata.update(ledger.to_metadata())
    return result


@contextmanager
def receipt_scope() -> Iterator[FilterExecutionLedger]:
    ledger = FilterExecutionLedger()
    token = _ACTIVE_LEDGER.set(ledger)
    try:
        yield ledger
    finally:
        _ACTIVE_LEDGER.reset(token)


def emits_filter_receipts(fn: Callable[..., _R]) -> Callable[..., _R]:
    """Route decorator: every result this route returns carries its receipts.

    The route opens no ledger of its own - it calls :func:`active_ledger` - and
    returns results however it likes. Attachment happens here, once, on the way
    out, so a return path added later is instrumented by construction rather
    than by remembering.
    """

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> _R:
        with receipt_scope() as ledger:
            result = fn(*args, **kwargs)
        return attach_receipts(result, ledger)

    return wrapper


# ---------------------------------------------------------------------------
# The published migration contract
# ---------------------------------------------------------------------------

#: Route -> the filter ids that route declares, marks, and serializes.
#:
#: This is the contract the docs, the validator and the route tests all read, so
#: "which routes are migrated, for which filters" has exactly one answer. A route
#: listed here must serialize a final state for every one of these filters it was
#: asked for, on *every* result it returns - success, no_match, coverage failure
#: and short-circuit alike. Adding a filter to a route means adding it here and
#: marking it where it runs; the validator fails until both are true.
MIGRATED_ROUTE_FILTERS: dict[str, tuple[str, ...]] = {
    "player_game_finder": (
        "opponent",
        "home_only",
        "away_only",
        "wins_only",
        "losses_only",
        "date_range",
        "last_n",
        "threshold",
        "quarter",
        "half",
        "opponent_player",
        "without_player",
        "special_event",
        "clutch",
        "role",
    ),
    "player_game_summary": (
        "opponent",
        "home_only",
        "away_only",
        "wins_only",
        "losses_only",
        "date_range",
        "last_n",
        "threshold",
        "opponent_player",
        "without_player",
        "special_event",
        "clutch",
        "role",
        "back_to_back",
        "rest_days",
        "one_possession",
        "nationally_televised",
    ),
    "season_leaders": (
        "opponent",
        "home_only",
        "away_only",
        "wins_only",
        "losses_only",
        "date_range",
        "last_n",
        "position_filter",
        "clutch",
        "role",
    ),
    "team_record": (
        "opponent",
        "home_only",
        "away_only",
        "wins_only",
        "losses_only",
        "date_range",
        "threshold",
        "with_player",
        "without_player",
        "clutch",
        "quarter",
        "half",
        "back_to_back",
        "rest_days",
        "one_possession",
        "nationally_televised",
    ),
}

#: Every legal final state for a declared filter.
RECEIPT_STATES = frozenset({APPLIED, UNSUPPORTED, UNRESOLVED, NOT_EVALUATED, COVERAGE_UNAVAILABLE})


def _present(value: Any) -> bool:
    """A route argument that was actually supplied.

    ``is not None`` and ``is not False``, matching :meth:`FilterExecutionLedger.declare`
    so a caller can predict from the route kwargs exactly which filters the
    ledger will hold.
    """
    return value is not None and value is not False


#: filter id -> how to read "was this requested?" out of a route's kwargs.
_REQUEST_TESTS: dict[str, Any] = {
    "opponent": lambda kw: _present(kw.get("opponent")),
    "home_only": lambda kw: _present(kw.get("home_only")),
    "away_only": lambda kw: _present(kw.get("away_only")),
    "wins_only": lambda kw: _present(kw.get("wins_only")),
    "losses_only": lambda kw: _present(kw.get("losses_only")),
    "date_range": lambda kw: _present(kw.get("start_date")) or _present(kw.get("end_date")),
    "last_n": lambda kw: _present(kw.get("last_n")),
    "threshold": lambda kw: (
        kw.get("min_value") is not None
        or kw.get("max_value") is not None
        or bool(kw.get("conditions"))
    ),
    "quarter": lambda kw: _present(kw.get("quarter")),
    "half": lambda kw: _present(kw.get("half")),
    "opponent_player": lambda kw: _present(kw.get("opponent_player")),
    "with_player": lambda kw: _present(kw.get("with_player")),
    "without_player": lambda kw: _present(kw.get("without_player")),
    "special_event": lambda kw: _present(kw.get("special_event")),
    "clutch": lambda kw: _present(kw.get("clutch")),
    "role": lambda kw: _present(kw.get("role")),
    "position_filter": lambda kw: _present(kw.get("position")),
    "back_to_back": lambda kw: _present(kw.get("back_to_back")),
    "rest_days": lambda kw: _present(kw.get("rest_days")),
    "one_possession": lambda kw: _present(kw.get("one_possession")),
    "nationally_televised": lambda kw: _present(kw.get("nationally_televised")),
}


def requested_filter_ids(route: str, kwargs: dict[str, Any]) -> set[str]:
    """The tracked filters *route* was asked for, given the arguments it got.

    Lets a caller predict the ledger from the request, which is what makes
    "no declared filter is silently missing" checkable from outside the route.
    """
    return {
        filter_id
        for filter_id in MIGRATED_ROUTE_FILTERS.get(route, ())
        if _REQUEST_TESTS[filter_id](kwargs)
    }
