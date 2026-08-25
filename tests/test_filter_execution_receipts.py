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
    NOT_EVALUATED,
    FilterExecutionLedger,
    receipt_state,
    receipts_from_metadata,
)
from nbatools.query_service import _badge_filter_id, execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.query, pytest.mark.needs_data]

# The mixed-filter query at the centre of the finding.
MIXED_FILTER_QUERY = "Tatum clutch stats at home on January 1 2024"


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
