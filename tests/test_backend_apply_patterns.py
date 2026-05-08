"""Tests for the 6 backend patterns applied from docs/query_intent_audit.md.

Patterns covered
----------------
1. Multi-period historical context: ``scope_kind`` in metadata; ``game_log``
   in ``SummaryResult.to_sections_dict``.
2. Filter context in metadata: ``applied_filters`` list on filtered queries.
3. Count vs list intent: ``primary_count`` and ``count_phrase`` on count
   flavored results.
7. Honest no-result for un-filterable queries: routes that cannot transport a
   filter return ``NoResult(reason="filter_not_supported")`` instead of
   executing unfiltered.
8. Ambiguous query recovery: entity-ambiguity carries structured ``candidates``
   list; fragment ambiguity carries ``suggested_queries`` list.
9. Routing rule clarity: explicit team_matchup_record vs team_compare split;
   expanded top_team_games trigger.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.commands.structured_results import NoResult, ResultReason, SummaryResult

pytestmark = pytest.mark.parser


# ---------------------------------------------------------------------------
# Pattern 1 — scope_kind
# ---------------------------------------------------------------------------


class TestScopeKind:
    """Verify scope_kind is present and correct in parse + metadata."""

    def test_single_season_scope(self):
        parsed = parse_query("Kobe 40 point games summary in 2005-06")
        assert parsed.get("season") == "2005-06"
        assert parsed.get("career_intent", False) is False
        assert parsed.get("start_season") is None

    def test_season_range_route_kwargs(self):
        parsed = parse_query("LeBron summary from 2018-19 to 2022-23")
        assert parsed.get("start_season") == "2018-19"
        assert parsed.get("end_season") == "2022-23"
        assert parsed.get("season") is None

    def test_career_intent_flag(self):
        parsed = parse_query("Kobe career scoring summary")
        # career_intent should be set when "career" appears
        assert parsed.get("career_intent") is True

    def test_summary_result_to_sections_dict_includes_game_log(self):
        """to_sections_dict must include GAME_LOG when game_log is non-empty."""
        import pandas as pd

        summary_df = pd.DataFrame({"games": [5], "pts": [32.0]})
        game_log_df = pd.DataFrame({"game_date": ["2023-01-01"], "pts": [40], "wl": ["W"]})
        by_season_df = pd.DataFrame({"season": ["2023-24"], "pts": [32.0]})

        result = SummaryResult(
            query_class="summary",
            summary=summary_df,
            game_log=game_log_df,
            by_season=by_season_df,
        )

        sections = result.to_sections_dict()
        assert "SUMMARY" in sections
        assert "BY_SEASON" in sections
        assert "GAME_LOG" in sections, "game_log section must appear in to_sections_dict"

    def test_summary_result_to_sections_dict_omits_empty_game_log(self):
        """to_sections_dict must not include GAME_LOG when game_log is empty."""
        import pandas as pd

        summary_df = pd.DataFrame({"games": [5], "pts": [32.0]})

        result = SummaryResult(
            query_class="summary",
            summary=summary_df,
        )

        sections = result.to_sections_dict()
        assert "GAME_LOG" not in sections


# ---------------------------------------------------------------------------
# Pattern 2 — applied_filters in metadata
# ---------------------------------------------------------------------------


class TestAppliedFilters:
    """Verify applied_filters list presence and correctness."""

    def test_opponent_filter_present(self):
        """A query with an opponent filter must carry applied_filters."""
        from nbatools.query_service import _build_query_metadata

        parsed = parse_query("Kobe 40 point games summary vs Dallas in 2005-06")
        meta = _build_query_metadata(parsed, "Kobe 40 point games summary vs Dallas in 2005-06")
        filters = meta.get("applied_filters", [])
        opponent_filters = [f for f in filters if f["label"] == "Opponent"]
        assert opponent_filters, "Opponent applied_filter expected"
        assert opponent_filters[0]["kind"] == "team"

    def test_home_only_filter_present(self):
        from nbatools.query_service import _build_query_metadata

        parsed = parse_query("Boston home wins vs Milwaukee from 2021-22 to 2023-24")
        meta = _build_query_metadata(
            parsed, "Boston home wins vs Milwaukee from 2021-22 to 2023-24"
        )
        filters = meta.get("applied_filters", [])
        location_filters = [f for f in filters if f["label"] == "Location"]
        assert location_filters, "Location applied_filter expected for home_only"
        assert location_filters[0]["value"] == "Home"

    def test_wins_only_filter_present(self):
        from nbatools.query_service import _build_query_metadata

        parsed = parse_query("Boston home wins vs Milwaukee from 2021-22 to 2023-24")
        meta = _build_query_metadata(
            parsed, "Boston home wins vs Milwaukee from 2021-22 to 2023-24"
        )
        filters = meta.get("applied_filters", [])
        outcome_filters = [f for f in filters if f["label"] == "Outcome"]
        assert outcome_filters, "Outcome applied_filter expected for wins_only"
        assert outcome_filters[0]["value"] == "Wins"

    def test_no_filters_when_unfiltered(self):
        """A plain season query must not inject spurious applied_filters."""
        from nbatools.query_service import _build_query_metadata

        parsed = parse_query("Kobe summary in 2005-06")
        meta = _build_query_metadata(parsed, "Kobe summary in 2005-06")
        filters = meta.get("applied_filters", [])
        assert filters == [], f"Expected no applied_filters but got {filters}"

    def test_season_range_filter_present(self):
        from nbatools.query_service import _build_query_metadata

        parsed = parse_query("LeBron summary from 2018-19 to 2022-23")
        meta = _build_query_metadata(parsed, "LeBron summary from 2018-19 to 2022-23")
        filters = meta.get("applied_filters", [])
        range_filters = [f for f in filters if f["label"] == "Season range"]
        assert range_filters, "Season range applied_filter expected"
        assert "2018-19" in range_filters[0]["value"]
        assert "2022-23" in range_filters[0]["value"]

    def test_opponent_quality_filter_uses_surface_term(self):
        from nbatools.query_service import _build_query_metadata

        parsed = parse_query("How has Jayson Tatum played against good teams")
        meta = _build_query_metadata(parsed, "How has Jayson Tatum played against good teams")
        filters = meta.get("applied_filters", [])
        quality_filters = [f for f in filters if f["kind"] == "quality"]
        assert quality_filters, "Opponent-quality applied_filter expected"
        assert quality_filters[0]["label"] == "Opponent quality"
        assert quality_filters[0]["value"] == "good teams"


# ---------------------------------------------------------------------------
# Pattern 3 — primary_count and count_phrase
# ---------------------------------------------------------------------------


class TestCountMetadata:
    """Verify primary_count and count_phrase are set for count-intent queries."""

    def test_build_count_phrase_single(self):
        from nbatools.query_service import _build_count_phrase

        phrase = _build_count_phrase(
            1,
            {"occurrence_event": "triple_double"},
            {"player": "Nikola Jokić", "season": "2023-24", "season_type": "Regular Season"},
        )
        assert "1 triple-double" in phrase
        assert "Nikola Jokić" in phrase

    def test_build_count_phrase_plural(self):
        from nbatools.query_service import _build_count_phrase

        phrase = _build_count_phrase(
            47,
            {"occurrence_event": "triple_double"},
            {"player": "Nikola Jokić", "season": "2023-24", "season_type": "Regular Season"},
        )
        assert "47 triple-doubles" in phrase
        assert "Nikola Jokić" in phrase

    def test_build_count_phrase_season_range(self):
        from nbatools.query_service import _build_count_phrase

        phrase = _build_count_phrase(
            23,
            {"occurrence_event": "triple_double"},
            {
                "player": "Nikola Jokić",
                "start_season": "2021-22",
                "end_season": "2023-24",
                "season_type": "Regular Season",
            },
        )
        assert "2021-22" in phrase
        assert "2023-24" in phrase


# ---------------------------------------------------------------------------
# Pattern 7 — filter_not_supported ResultReason
# ---------------------------------------------------------------------------


class TestFilterNotSupportedReason:
    """Verify FILTER_NOT_SUPPORTED is in ResultReason and _EXPECTED_REASONS."""

    def test_result_reason_enum_has_filter_not_supported(self):
        assert hasattr(ResultReason, "FILTER_NOT_SUPPORTED")
        assert ResultReason.FILTER_NOT_SUPPORTED == "filter_not_supported"

    def test_expected_reasons_contains_filter_not_supported(self):
        from nbatools.query_service import _EXPECTED_REASONS

        assert "filter_not_supported" in _EXPECTED_REASONS

    def test_reason_to_status_maps_to_no_result(self):
        from nbatools.query_service import reason_to_status

        assert reason_to_status("filter_not_supported") == "no_result"

    def test_noresult_filter_not_supported_fields(self):
        result = NoResult(
            query_class="summary",
            reason="filter_not_supported",
            notes=["clutch: data not available"],
        )
        assert result.reason == "filter_not_supported"
        assert result.result_reason == "filter_not_supported"
        assert result.result_status == "no_result"

    def test_route_context_filter_blocks_clutch_on_unsupported_route(self):
        """A route not in _PHASE_G_CLUTCH_TRANSPORT_ROUTES must block clutch."""
        from nbatools.commands._natural_query_execution import (
            _route_context_filters_for_execution,
        )

        _, _, blocked = _route_context_filters_for_execution(
            "season_team_leaders", {"clutch": True}
        )
        assert "clutch" in blocked

    def test_route_context_filter_passes_clutch_on_supported_route(self):
        """A route in _PHASE_G_CLUTCH_TRANSPORT_ROUTES must not block clutch."""
        from nbatools.commands._natural_query_execution import (
            _route_context_filters_for_execution,
        )

        _, _, blocked = _route_context_filters_for_execution(
            "player_game_summary", {"clutch": True}
        )
        assert "clutch" not in blocked

    def test_route_context_filter_blocks_period_on_unsupported_route(self):
        """Quarter filter on a non-period-transport route must be blocked."""
        from nbatools.commands._natural_query_execution import (
            _route_context_filters_for_execution,
        )

        _, _, blocked = _route_context_filters_for_execution("season_leaders", {"quarter": 4})
        assert "quarter" in blocked

    def test_route_context_filter_blocks_schedule_context(self):
        """back_to_back on a non-schedule-context route must be blocked."""
        from nbatools.commands._natural_query_execution import (
            _route_context_filters_for_execution,
        )

        _, _, blocked = _route_context_filters_for_execution(
            "season_leaders", {"back_to_back": True}
        )
        assert "back_to_back" in blocked

    def test_route_context_filter_passes_schedule_context_on_supported_route(self):
        """back_to_back on player_game_summary (schedule route) must not block."""
        from nbatools.commands._natural_query_execution import (
            _route_context_filters_for_execution,
        )

        _, _, blocked = _route_context_filters_for_execution(
            "player_game_summary", {"back_to_back": True}
        )
        assert "back_to_back" not in blocked

    def test_route_context_filter_empty_filters_no_block(self):
        """An empty / filter-free kwarg dict must return empty blocked_filters."""
        from nbatools.commands._natural_query_execution import (
            _route_context_filters_for_execution,
        )

        _, _, blocked = _route_context_filters_for_execution(
            "season_leaders", {"stat": "pts", "limit": 10}
        )
        assert blocked == []


# ---------------------------------------------------------------------------
# Pattern 8 — ambiguous query recovery
# ---------------------------------------------------------------------------


class TestAmbiguousRecovery:
    """Verify suggested_queries is populated for fragment-ambiguous queries."""

    def test_fragment_ambiguity_has_suggested_queries(self):
        """Ambiguous fragment: 'jokic triple doubles' → suggested_queries present."""
        from nbatools.query_service import _build_suggested_queries_for_fragment

        parsed_with_occurrence = {
            "player": "Nikola Jokić",
            "occurrence_event": "triple_double",
            "season": "2023-24",
        }
        suggestions = _build_suggested_queries_for_fragment(parsed_with_occurrence)
        assert isinstance(suggestions, list)
        assert len(suggestions) >= 1
        # At least one suggestion should mention the player or the event
        assert any("jokić" in s.lower() or "triple" in s.lower() for s in suggestions)

    def test_fragment_suggestions_for_player_without_occurrence(self):
        from nbatools.query_service import _build_suggested_queries_for_fragment

        suggestions = _build_suggested_queries_for_fragment(
            {"player": "LeBron James", "season": "2023-24"}
        )
        assert len(suggestions) >= 2
        assert any("lebron" in s.lower() for s in suggestions)

    def test_fragment_suggestions_for_team_fragment(self):
        from nbatools.query_service import _build_suggested_queries_for_fragment

        suggestions = _build_suggested_queries_for_fragment({"team": "BOS", "season": "2023-24"})
        assert len(suggestions) >= 2
        assert any("bos" in s.lower() for s in suggestions)

    def test_fragment_suggestions_capped_at_four(self):
        from nbatools.query_service import _build_suggested_queries_for_fragment

        suggestions = _build_suggested_queries_for_fragment(
            {
                "player": "Stephen Curry",
                "occurrence_event": "triple_double",
                "stat": "pts",
                "season": "2023-24",
            }
        )
        assert len(suggestions) <= 4

    def test_entity_ambiguity_candidates_reach_response_metadata(self):
        from nbatools.query_service import execute_natural_query

        metadata = execute_natural_query("Brown last 10").to_dict()["metadata"]
        candidates = metadata.get("candidates", [])
        assert candidates
        assert all("display_name" in candidate for candidate in candidates)

    def test_fragment_suggestions_reach_response_metadata(self):
        from nbatools.query_service import execute_natural_query

        metadata = execute_natural_query("Jokic triple doubles").to_dict()["metadata"]
        suggestions = metadata.get("suggested_queries", [])
        assert suggestions
        assert all("{" not in suggestion for suggestion in suggestions)


# ---------------------------------------------------------------------------
# Pattern 9 — routing rule clarity
# ---------------------------------------------------------------------------


class TestRoutingRules:
    """Verify corrected routing decisions for team-vs-team and top_team_games."""

    # -- team_matchup_record vs team_compare --

    def test_two_teams_with_record_intent_routes_to_matchup_record(self):
        parsed = parse_query("Lakers vs Celtics record 2023-24")
        assert parsed["route"] == "team_matchup_record"

    def test_two_teams_without_record_intent_routes_to_team_compare(self):
        parsed = parse_query("Lakers vs Celtics stats comparison 2023-24")
        assert parsed["route"] == "team_compare"

    def test_two_teams_head_to_head_routes_to_team_compare(self):
        """Head-to-head is a comparison filter, not a record query.

        Two-team head-to-head routes to team_compare (which supports
        head_to_head=True) rather than team_matchup_record.  Record queries
        require an explicit W/L outcome keyword ("record", "wins", etc.) which
        triggers record_intent.
        """
        parsed = parse_query("Celtics vs Bucks head to head 2023-24")
        assert parsed["route"] == "team_compare"
        assert parsed["route_kwargs"].get("head_to_head") is True

    # -- without_player + team → team_record --

    def test_team_without_player_routes_to_team_record(self):
        parsed = parse_query("Lakers record without LeBron 2022-23")
        assert parsed["route"] == "team_record"
        assert parsed["route_kwargs"].get("without_player") is not None

    # -- top_team_games trigger expansion --

    def test_top_team_literal_trigger(self):
        parsed = parse_query("top team scoring games 2023-24")
        assert parsed["route"] == "top_team_games"

    def test_top_team_games_literal_trigger(self):
        parsed = parse_query("top team games by points 2023-24")
        assert parsed["route"] == "top_team_games"

    def test_highest_scoring_team_games_trigger(self):
        parsed = parse_query("highest scoring team games 2023-24")
        assert parsed["route"] == "top_team_games"

    def test_best_team_performances_trigger(self):
        parsed = parse_query("best team performances this season")
        assert parsed["route"] == "top_team_games"

    def test_biggest_team_scoring_nights_trigger(self):
        parsed = parse_query("biggest team scoring nights 2023-24")
        assert parsed["route"] == "top_team_games"
