"""A filter counts as applied only where execution proves it ran.

The rejected Phase 1A candidate assumed ``result_reason == "no_match"`` meant
every requested filter had executed. ``Tatum clutch stats at home on January 1
2024`` disproves it: the date and location filters empty the sample, the clutch
filter then runs against zero rows and reports nothing wrong, and the answer
came back claiming all three had been applied. Clutch never touched a game.

These tests pin the replacement contract - per-filter receipts recorded by the
route that does the filtering - at both the route and query-service layers.
"""

from __future__ import annotations

import pytest

from nbatools.commands._filter_receipts import (
    APPLIED,
    MIGRATED_ROUTE_FILTERS,
    NOT_EVALUATED,
    RECEIPT_STATES,
    FilterExecutionLedger,
    receipt_state,
    receipts_from_metadata,
    requested_filter_ids,
)
from nbatools.query_service import _badge_filter_id, execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.query, pytest.mark.needs_data]

# The mixed-filter query at the centre of the finding.
MIXED_FILTER_QUERY = "Tatum clutch stats at home on January 1 2024"

# Filters that always render a badge when they run, so an ``applied`` receipt
# with no badge means truthful context was thrown away.
BADGE_BACKED_FILTERS = frozenset(
    {
        "opponent",
        "home_only",
        "away_only",
        "wins_only",
        "losses_only",
        "clutch",
        "quarter",
        "half",
        "role",
        "position_filter",
        "with_player",
        "without_player",
        "back_to_back",
        "one_possession",
        "nationally_televised",
        "special_event",
    }
)


def _request_view(metadata: dict) -> dict:
    """Route-kwarg-shaped view of what the parser asked the route for."""
    return {
        "opponent": metadata.get("opponent"),
        "home_only": metadata.get("home_only"),
        "away_only": metadata.get("away_only"),
        "wins_only": metadata.get("wins_only"),
        "losses_only": metadata.get("losses_only"),
        "start_date": metadata.get("start_date"),
        "end_date": metadata.get("end_date"),
        "last_n": metadata.get("last_n"),
        "min_value": metadata.get("min_value"),
        "max_value": metadata.get("max_value"),
        "conditions": metadata.get("conditions"),
        "quarter": metadata.get("quarter"),
        "half": metadata.get("half"),
        "opponent_player": metadata.get("opponent_player"),
        "with_player": metadata.get("with_player"),
        "without_player": metadata.get("without_player"),
        "special_event": metadata.get("special_event"),
        "clutch": metadata.get("clutch"),
        "role": metadata.get("role"),
        "position": metadata.get("position_filter"),
        "back_to_back": metadata.get("back_to_back"),
        "rest_days": metadata.get("rest_days"),
        "one_possession": metadata.get("one_possession"),
        "nationally_televised": metadata.get("nationally_televised"),
    }


def _badge_labels(metadata: dict) -> list[str]:
    return [str(entry.get("label")) for entry in (metadata.get("applied_filters") or [])]


def _receipts(executed) -> dict:
    return receipts_from_metadata(getattr(executed.result, "metadata", None))


# ---------------------------------------------------------------------------
# 1. The ledger itself
# ---------------------------------------------------------------------------


class TestLedger:
    def test_declared_filters_start_unevaluated(self):
        ledger = FilterExecutionLedger()
        ledger.declare_all({"clutch": True, "role": None, "home_only": False})

        assert ledger.state("clutch") == NOT_EVALUATED
        # Filters that were never requested are not tracked at all.
        assert ledger.state("role") is None
        assert ledger.state("home_only") is None

    def test_only_declared_filters_can_be_marked(self):
        """A route must not vouch for work nobody asked for."""
        ledger = FilterExecutionLedger()
        ledger.applied("clutch")

        assert ledger.state("clutch") is None

    def test_short_circuit_leaves_applied_filters_alone(self):
        ledger = FilterExecutionLedger()
        ledger.declare_all({"date_range": True, "clutch": True})
        ledger.applied("date_range")
        ledger.short_circuit("sample was empty")

        assert ledger.state("date_range") == APPLIED
        assert ledger.state("clutch") == NOT_EVALUATED
        assert ledger.unproven_ids() == ["clutch"]


# ---------------------------------------------------------------------------
# 2. Routes record what they actually did
# ---------------------------------------------------------------------------


class TestRouteReceipts:
    def test_mixed_filter_query_records_clutch_as_never_evaluated(self):
        executed = execute_natural_query(MIXED_FILTER_QUERY)
        receipts = _receipts(executed)

        assert receipt_state(receipts, "date_range") == APPLIED
        assert receipt_state(receipts, "home_only") == APPLIED
        assert receipt_state(receipts, "clutch") == NOT_EVALUATED

    def test_threshold_that_really_ran_is_recorded_applied(self):
        executed = execute_natural_query("Nikola Jokic games with over 80 points this season")

        assert executed.result_reason == "no_match"
        assert receipt_state(_receipts(executed), "threshold") == APPLIED

    def test_structured_query_records_the_same_receipts(self):
        """The contract is the engine's, not the natural-language layer's."""
        executed = execute_structured_query(
            "player_game_finder",
            player="Jayson Tatum",
            season="2023-24",
            start_date="2024-01-01",
            end_date="2024-01-01",
            home_only=True,
            clutch=True,
        )
        receipts = _receipts(executed)

        assert receipt_state(receipts, "clutch") == NOT_EVALUATED
        assert "Clutch" not in _badge_labels(executed.metadata)


# ---------------------------------------------------------------------------
# 3. applied_filters is derived from receipts, never from the result reason
# ---------------------------------------------------------------------------


class TestAppliedFilterDerivation:
    def test_no_match_does_not_license_a_clutch_badge(self):
        executed = execute_natural_query(MIXED_FILTER_QUERY)
        labels = _badge_labels(executed.metadata)

        assert executed.result_reason == "no_match"
        assert "Clutch" not in labels
        # The filters that genuinely ran keep their badges.
        assert "Location" in labels
        assert "Date range" in labels

    def test_unevaluated_filter_is_reported_as_such(self):
        executed = execute_natural_query(MIXED_FILTER_QUERY)

        assert executed.metadata.get("unevaluated_filters") == ["clutch"]

    def test_never_evaluated_is_not_laundered_into_unsupported(self):
        """Clutch is supported here. It just never got reached."""
        executed = execute_natural_query(MIXED_FILTER_QUERY)

        assert "clutch" not in (executed.metadata.get("unsupported_filters") or [])

    def test_requested_context_survives_the_badge_being_dropped(self):
        executed = execute_natural_query(MIXED_FILTER_QUERY)

        assert executed.metadata.get("clutch") is True

    def test_legitimate_no_match_keeps_its_proven_badges(self):
        executed = execute_natural_query("Nikola Jokic games with over 80 points this season")

        assert executed.result_reason == "no_match"
        assert _badge_labels(executed.metadata) == ["pts min"]

    def test_every_badge_on_a_non_ok_result_has_an_applied_receipt(self):
        """The invariant, stated directly, over a spread of mixed-filter asks."""
        for query in (
            MIXED_FILTER_QUERY,
            "Jokic clutch stats on January 1 2024",
            "LeBron clutch stats in wins on December 25 2023",
            "Lakers clutch record on January 1 2024",
            "Wembanyama clutch stats away in 2018-19",
            "Nikola Jokic games with over 80 points this season",
        ):
            executed = execute_natural_query(query)
            if executed.result_status == "ok":
                continue
            receipts = _receipts(executed)
            for badge in executed.metadata.get("applied_filters") or []:
                filter_id = _badge_filter_id(badge)
                assert receipt_state(receipts, filter_id) == APPLIED, (
                    f"{query!r} claims {badge.get('label')} was applied with "
                    f"receipt {receipt_state(receipts, filter_id)!r}"
                )


# ---------------------------------------------------------------------------
# 4. Coverage blockers are stable metadata, not prose
# ---------------------------------------------------------------------------


class TestCoverageBlockers:
    @pytest.mark.parametrize(
        "query, route",
        [
            ("Tatum clutch stats", "player_game_summary"),
            ("Lakers clutch record", "team_record"),
        ],
    )
    def test_clutch_coverage_failure_names_a_coverage_blocker(self, query, route):
        executed = execute_natural_query(query)

        assert executed.route == route
        assert executed.result_reason == "filter_not_supported"
        assert executed.metadata.get("unsupported_filters") == ["clutch_coverage"]

    def test_unbound_clutch_fragment_is_a_different_blocker(self):
        """An uninterpretable fragment must not be blamed on missing data."""
        executed = execute_natural_query("clutch stats")

        assert executed.metadata.get("unsupported_filters") == ["clutch"]

    def test_role_coverage_failure_names_a_coverage_blocker(self):
        executed = execute_natural_query("top scorers among starters on January 1 2024")

        assert executed.result_reason == "filter_not_supported"
        assert executed.metadata.get("unsupported_filters") == ["role_coverage"]


# ---------------------------------------------------------------------------
# 5. Request detection: a falsy value can still be a request
# ---------------------------------------------------------------------------


class TestFalsyRequests:
    """``0`` is a value for some filters, not an absent slot.

    ``detect_rest_days`` returns ``0`` for "on no rest" / "with zero days rest",
    and every other consumer of that slot tests ``rest_days is not None``. A
    ledger that declared on truthiness dropped the filter entirely, so the one
    record that was supposed to prove what ran had nothing to say about it.
    """

    def test_zero_rest_days_is_declared(self):
        ledger = FilterExecutionLedger()
        ledger.declare("rest_days", 0)

        assert ledger.state("rest_days") == NOT_EVALUATED
        assert "rest_days" in ledger.to_metadata()["filter_receipts"]

    def test_zero_threshold_is_declared(self):
        ledger = FilterExecutionLedger()
        ledger.declare("threshold", 0)

        assert ledger.state("threshold") == NOT_EVALUATED

    def test_none_and_false_are_still_absent(self):
        ledger = FilterExecutionLedger()
        ledger.declare("clutch", False)
        ledger.declare("opponent", None)

        assert ledger.to_metadata()["filter_receipts"] == {}

    def test_zero_rest_days_reaches_the_result_ledger(self):
        executed = execute_structured_query(
            "player_game_summary", player="LeBron James", season="2024-25", rest_days=0
        )

        assert receipt_state(_receipts(executed), "rest_days") is not None


# ---------------------------------------------------------------------------
# 6. The published migration matrix
# ---------------------------------------------------------------------------

# One row per (route, path) the migration advertises. ``expect`` pins the states
# the row exists to prove; completeness is asserted for every requested filter,
# which is the check a partially migrated route fails.
#
# (route, natural query, expected states)
ROUTE_RECEIPT_MATRIX = [
    (
        "player_game_finder",
        "Tatum clutch stats at home on January 1 2024",
        {"date_range": APPLIED, "home_only": APPLIED, "clutch": NOT_EVALUATED},
    ),
    (
        "player_game_finder",
        "LeBron James games with over 30 points at home this season",
        {"threshold": APPLIED, "home_only": APPLIED},
    ),
    (
        "player_game_summary",
        "Stephen Curry stats at home in wins this season",
        {"home_only": APPLIED, "wins_only": APPLIED},
    ),
    (
        "player_game_summary",
        "Stephen Curry clutch averages at home on January 1 2024",
        {"date_range": APPLIED, "home_only": APPLIED, "clutch": NOT_EVALUATED},
    ),
    (
        "player_game_summary",
        "Stephen Curry clutch stats this season",
        {"clutch": "coverage_unavailable"},
    ),
    (
        "season_leaders",
        "top scorers at home this season",
        {"home_only": APPLIED},
    ),
    (
        "season_leaders",
        "top scorers among starters on January 1 2024",
        {"date_range": APPLIED, "role": "coverage_unavailable"},
    ),
    (
        "season_leaders",
        "top scorers among guards this season",
        {"position_filter": APPLIED},
    ),
    (
        "team_record",
        "Lakers clutch record on January 1 2024",
        {"date_range": APPLIED, "clutch": NOT_EVALUATED},
    ),
    (
        "team_record",
        "Lakers record without LeBron James",
        {"without_player": APPLIED},
    ),
    (
        "team_record",
        "Celtics record in the 4th quarter this season",
        {"quarter": APPLIED},
    ),
]


@pytest.mark.parametrize(
    "route, query, expected",
    ROUTE_RECEIPT_MATRIX,
    ids=[f"{row[0]}::{row[1][:40]}" for row in ROUTE_RECEIPT_MATRIX],
)
def test_migrated_route_serializes_every_requested_filter(route, query, expected):
    executed = execute_natural_query(query)
    receipts = _receipts(executed)

    assert executed.route == route, f"{query!r} no longer routes to {route}"
    for filter_id, state in expected.items():
        assert receipt_state(receipts, filter_id) == state, (
            f"{query!r}: {filter_id} receipt was {receipt_state(receipts, filter_id)!r}"
        )
    # Completeness: nothing requested may be missing from the ledger.
    for filter_id in requested_filter_ids(route, _request_view(executed.metadata)):
        assert receipt_state(receipts, filter_id) in RECEIPT_STATES, (
            f"{query!r}: {filter_id} was requested but carries no serialized state"
        )


STRUCTURED_RECEIPT_MATRIX = [
    (
        "player_game_finder",
        {
            "player": "Jayson Tatum",
            "season": "2023-24",
            "start_date": "2024-01-01",
            "end_date": "2024-01-01",
            "home_only": True,
            "clutch": True,
        },
        {"date_range": APPLIED, "home_only": APPLIED, "clutch": NOT_EVALUATED},
    ),
    (
        "player_game_summary",
        {"player": "Stephen Curry", "season": "2024-25", "home_only": True},
        {"home_only": APPLIED},
    ),
    (
        "season_leaders",
        {"season": "2024-25", "stat": "pts", "home_only": True},
        {"home_only": APPLIED},
    ),
    (
        "team_record",
        {"team": "LAL", "season": "2024-25", "home_only": True},
        {"home_only": APPLIED},
    ),
    (
        "team_record",
        {
            "team": "LAL",
            "season": "2023-24",
            "start_date": "2024-01-01",
            "end_date": "2024-01-01",
            "clutch": True,
        },
        {"date_range": APPLIED, "clutch": NOT_EVALUATED},
    ),
]


@pytest.mark.parametrize(
    "route, kwargs, expected",
    STRUCTURED_RECEIPT_MATRIX,
    ids=[row[0] + "::" + ",".join(sorted(row[1])) for row in STRUCTURED_RECEIPT_MATRIX],
)
def test_structured_path_carries_the_same_receipts(route, kwargs, expected):
    """The structured API is not a second, unproven way into the same routes."""
    executed = execute_structured_query(route, **kwargs)
    receipts = _receipts(executed)

    for filter_id, state in expected.items():
        assert receipt_state(receipts, filter_id) == state, f"{route}/{filter_id}"
    for filter_id in requested_filter_ids(route, kwargs):
        assert receipt_state(receipts, filter_id) in RECEIPT_STATES, (
            f"{route}: {filter_id} was requested but carries no serialized state"
        )


@pytest.mark.parametrize(
    "route, query",
    [(row[0], row[1]) for row in ROUTE_RECEIPT_MATRIX],
    ids=[f"{row[0]}::{row[1][:40]}" for row in ROUTE_RECEIPT_MATRIX],
)
def test_applied_receipts_keep_their_badges(route, query):
    """Truthful context survives. Dropping every badge is not a safe default.

    The first receipt pass removed false badges but had nothing to say about
    true ones, so a route that returned no receipts at all scored clean while
    losing every accurate filter description it had.
    """
    executed = execute_natural_query(query)
    receipts = _receipts(executed)
    shown = {_badge_filter_id(badge) for badge in (executed.metadata.get("applied_filters") or [])}

    for filter_id, entry in receipts.items():
        if entry.get("state") != APPLIED or filter_id not in BADGE_BACKED_FILTERS:
            continue
        assert filter_id in shown, f"{query!r}: {filter_id} ran but its badge was dropped"


@pytest.mark.parametrize("route", sorted(MIGRATED_ROUTE_FILTERS))
def test_every_advertised_route_is_exercised_by_the_matrix(route):
    """The advertised scope and the tested scope are the same set."""
    assert any(row[0] == route for row in ROUTE_RECEIPT_MATRIX), (
        f"{route} is advertised as receipt-migrated but has no matrix row"
    )
