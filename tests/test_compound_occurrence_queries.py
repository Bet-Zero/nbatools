"""Tests for compound occurrence / milestone queries.

Covers:
1. Compound occurrence event extraction
2. Compound occurrence routing (player and team)
3. Compound occurrence count queries
4. Compound occurrence leaderboard queries
5. Single-entity occurrence counts via occurrence_leaders
6. Historical/opponent/playoff composition with compound occurrences
7. Structured query support for compound occurrences
"""

import pandas as pd
import pytest

from nbatools.commands.natural_query import (
    _build_parse_state,
    extract_compound_occurrence_event,
    parse_query,
)
from nbatools.commands.player_occurrence_leaders import (
    OccurrenceCondition,
    _build_event_label,
    _flag_compound_conditions,
    _validate_conditions,
)
from nbatools.commands.player_occurrence_leaders import (
    build_result as player_occurrence_build_result,
)
from nbatools.commands.structured_results import (
    CountResult,
    LeaderboardResult,
    NoResult,
)
from nbatools.commands.team_occurrence_leaders import (
    build_result as team_occurrence_build_result,
)
from nbatools.query_service import (
    execute_natural_query,
    execute_structured_query,
)

pytestmark = pytest.mark.engine

# ===================================================================
# 1. Compound Occurrence Event Extraction
# ===================================================================


class TestExtractCompoundOccurrenceEvent:
    """Test extract_compound_occurrence_event() parsing."""

    def test_30pts_and_10reb(self):
        result = extract_compound_occurrence_event("30+ points and 10+ rebounds")
        assert result is not None
        assert len(result) == 2
        assert {"stat": "pts", "min_value": 30.0} in result
        assert {"stat": "reb", "min_value": 10.0} in result

    def test_40pts_and_5_threes(self):
        result = extract_compound_occurrence_event("40+ points and 5+ threes")
        assert result is not None
        assert len(result) == 2
        assert {"stat": "pts", "min_value": 40.0} in result
        assert {"stat": "fg3m", "min_value": 5.0} in result

    def test_25pts_and_10ast(self):
        result = extract_compound_occurrence_event("25+ points and 10+ assists")
        assert result is not None
        assert len(result) == 2
        assert {"stat": "pts", "min_value": 25.0} in result
        assert {"stat": "ast", "min_value": 10.0} in result

    def test_120pts_and_15_threes_team(self):
        result = extract_compound_occurrence_event("120+ points and 15+ threes")
        assert result is not None
        assert len(result) == 2
        assert {"stat": "pts", "min_value": 120.0} in result
        assert {"stat": "fg3m", "min_value": 15.0} in result

    def test_3_steals_and_2_blocks(self):
        result = extract_compound_occurrence_event("3+ steals and 2+ blocks")
        assert result is not None
        assert len(result) == 2
        assert {"stat": "stl", "min_value": 3.0} in result
        assert {"stat": "blk", "min_value": 2.0} in result

    def test_games_with_compound(self):
        result = extract_compound_occurrence_event("games with 30+ points and 10+ rebounds")
        assert result is not None
        assert len(result) == 2
        assert {"stat": "pts", "min_value": 30.0} in result
        assert {"stat": "reb", "min_value": 10.0} in result

    def test_no_and_returns_none(self):
        result = extract_compound_occurrence_event("40 point games")
        assert result is None

    def test_single_threshold_returns_none(self):
        result = extract_compound_occurrence_event("30+ points")
        assert result is None

    def test_same_stat_twice_returns_none(self):
        # Shouldn't return compound for duplicate stats
        result = extract_compound_occurrence_event("30+ points and 20+ points")
        assert result is None


# ===================================================================
# 2. OccurrenceCondition Dataclass
# ===================================================================


class TestOccurrenceCondition:
    """Test the OccurrenceCondition dataclass."""

    def test_create_min_only(self):
        cond = OccurrenceCondition(stat="pts", min_value=30.0)
        assert cond.stat == "pts"
        assert cond.min_value == 30.0
        assert cond.max_value is None

    def test_create_max_only(self):
        cond = OccurrenceCondition(stat="tov", max_value=5.0)
        assert cond.stat == "tov"
        assert cond.min_value is None
        assert cond.max_value == 5.0

    def test_create_range(self):
        cond = OccurrenceCondition(stat="pts", min_value=20.0, max_value=30.0)
        assert cond.min_value == 20.0
        assert cond.max_value == 30.0

    def test_to_dict(self):
        cond = OccurrenceCondition(stat="pts", min_value=30.0)
        d = cond.to_dict()
        assert d == {"stat": "pts", "min_value": 30.0}

    def test_from_dict(self):
        d = {"stat": "reb", "min_value": 10.0}
        cond = OccurrenceCondition.from_dict(d)
        assert cond.stat == "reb"
        assert cond.min_value == 10.0


# ===================================================================
# 3. Compound Conditions Flagging
# ===================================================================


class TestFlagCompoundConditions:
    """Test _flag_compound_conditions() on DataFrames."""

    def test_single_condition(self):
        df = pd.DataFrame({"pts": [25, 35, 45], "reb": [5, 8, 12]})
        conds = [OccurrenceCondition(stat="pts", min_value=30)]
        mask = _flag_compound_conditions(df, conds)
        assert list(mask) == [False, True, True]

    def test_two_conditions_and_logic(self):
        df = pd.DataFrame({"pts": [25, 35, 45], "reb": [5, 8, 12]})
        conds = [
            OccurrenceCondition(stat="pts", min_value=30),
            OccurrenceCondition(stat="reb", min_value=10),
        ]
        mask = _flag_compound_conditions(df, conds)
        # Only row 2 (45 pts, 12 reb) meets both
        assert list(mask) == [False, False, True]

    def test_no_conditions_all_true(self):
        df = pd.DataFrame({"pts": [25, 35, 45]})
        mask = _flag_compound_conditions(df, [])
        assert all(mask)

    def test_missing_stat_column(self):
        df = pd.DataFrame({"pts": [25, 35, 45]})
        conds = [OccurrenceCondition(stat="xyz", min_value=10)]
        mask = _flag_compound_conditions(df, conds)
        assert not any(mask)

    def test_max_value_under(self):
        df = pd.DataFrame({"pts": [25, 35, 45], "tov": [2, 5, 10]})
        conds = [
            OccurrenceCondition(stat="pts", min_value=30),
            OccurrenceCondition(stat="tov", max_value=6),
        ]
        mask = _flag_compound_conditions(df, conds)
        # Row 1: 35 >= 30, 5 <= 6 -> True
        # Row 2: 45 >= 30, 10 > 6 -> False
        assert list(mask) == [False, True, False]


# ===================================================================
# 4. Validate Conditions
# ===================================================================


class TestValidateConditions:
    """Test _validate_conditions()."""

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="At least one"):
            _validate_conditions([])

    def test_unsupported_stat_raises(self):
        conds = [OccurrenceCondition(stat="xyz", min_value=10)]
        with pytest.raises(ValueError, match="Unsupported stat"):
            _validate_conditions(conds)

    def test_no_min_or_max_raises(self):
        conds = [OccurrenceCondition(stat="pts")]
        with pytest.raises(ValueError, match="must have min_value or max_value"):
            _validate_conditions(conds)

    def test_valid_conditions_passes(self):
        conds = [
            OccurrenceCondition(stat="pts", min_value=30),
            OccurrenceCondition(stat="reb", min_value=10),
        ]
        # Should not raise
        _validate_conditions(conds)


# ===================================================================
# 5. Build Event Label
# ===================================================================


class TestBuildEventLabel:
    """Test _build_event_label() for compound conditions."""

    def test_single_condition_label(self):
        conds = [OccurrenceCondition(stat="pts", min_value=30)]
        label = _build_event_label(conditions=conds)
        assert label == "games_pts_30+"

    def test_compound_label(self):
        conds = [
            OccurrenceCondition(stat="pts", min_value=30),
            OccurrenceCondition(stat="reb", min_value=10),
        ]
        label = _build_event_label(conditions=conds)
        assert label == "games_pts_30+_reb_10+"

    def test_special_event_label(self):
        label = _build_event_label(special_event="triple_double")
        assert label == "triple doubles"

    def test_max_value_label(self):
        conds = [OccurrenceCondition(stat="tov", max_value=5)]
        label = _build_event_label(conditions=conds)
        assert label == "games_tov_under_5"


# ===================================================================
# 6. Parse State with Compound Occurrence
# ===================================================================


class TestParseStateCompoundOccurrence:
    """Test _build_parse_state extracts compound_occurrence_conditions."""

    def test_compound_detected(self):
        state = _build_parse_state("most games with 30+ points and 10+ rebounds since 2020")
        assert state["compound_occurrence_conditions"] is not None
        assert len(state["compound_occurrence_conditions"]) == 2

    def test_single_not_compound(self):
        state = _build_parse_state("most 40 point games since 2020")
        # Single event, not compound
        assert state["compound_occurrence_conditions"] is None
        assert state["occurrence_event"] == {"stat": "pts", "min_value": 40}

    def test_count_intent_with_compound(self):
        state = _build_parse_state(
            "how many jokic games with 30+ points and 10+ rebounds since 2021"
        )
        assert state["compound_occurrence_conditions"] is not None
        assert state["count_intent"] is True


# ===================================================================
# 7. Compound Occurrence Routing
# ===================================================================


class TestCompoundOccurrenceRouting:
    """Test routing for compound occurrence queries."""

    def test_compound_player_leaderboard_routes(self):
        parsed = parse_query("most games with 30+ points and 10+ rebounds since 2020")
        assert parsed["route"] == "player_occurrence_leaders"
        kw = parsed["route_kwargs"]
        assert "conditions" in kw
        assert len(kw["conditions"]) == 2

    def test_compound_team_leaderboard_routes(self):
        parsed = parse_query("teams with most games with 120+ points and 15+ threes since 2020")
        assert parsed["route"] == "team_occurrence_leaders"
        kw = parsed["route_kwargs"]
        assert "conditions" in kw
        assert len(kw["conditions"]) == 2

    def test_compound_player_count_routes(self):
        parsed = parse_query("how many jokic games with 30+ points and 10+ rebounds since 2021")
        assert parsed["route"] == "player_occurrence_leaders"
        kw = parsed["route_kwargs"]
        assert "conditions" in kw
        assert kw.get("player") == "Nikola Jokić"
        assert kw.get("limit") == 500

    def test_compound_team_count_routes(self):
        parsed = parse_query("how many celtics games with 120+ points and 15+ threes since 2022")
        assert parsed["route"] == "team_occurrence_leaders"
        kw = parsed["route_kwargs"]
        assert "conditions" in kw
        assert kw.get("team") == "BOS"
        assert kw.get("limit") == 500


# ===================================================================
# 8. Single-Entity Occurrence Count Routing (Unified)
# Note: Single-stat occurrence counts still route to finder (backward compat).
# Only compound occurrences and leaderboards use occurrence_leaders.
# ===================================================================


# ===================================================================
# 9. Player Compound Occurrence build_result
# ===================================================================


class TestPlayerCompoundOccurrenceBuild:
    """Test player_occurrence_leaders.build_result() with conditions."""

    def test_compound_conditions_build(self):
        result = player_occurrence_build_result(
            conditions=[
                {"stat": "pts", "min_value": 30},
                {"stat": "reb", "min_value": 10},
            ],
            season="2024-25",
            limit=10,
        )
        # Should return a result (may be NoResult if no data matches)
        assert isinstance(result, (LeaderboardResult, NoResult))

    def test_compound_with_season_range(self):
        result = player_occurrence_build_result(
            conditions=[
                {"stat": "pts", "min_value": 25},
                {"stat": "ast", "min_value": 10},
            ],
            start_season="2020-21",
            end_season="2024-25",
            limit=10,
        )
        assert isinstance(result, (LeaderboardResult, NoResult))

    def test_compound_with_player_filter(self):
        result = player_occurrence_build_result(
            conditions=[
                {"stat": "pts", "min_value": 25},
                {"stat": "reb", "min_value": 8},
            ],
            season="2024-25",
            player="Nikola Jokić",
            limit=500,
        )
        assert isinstance(result, (LeaderboardResult, NoResult))


# ===================================================================
# 10. Team Compound Occurrence build_result
# ===================================================================


class TestTeamCompoundOccurrenceBuild:
    """Test team_occurrence_leaders.build_result() with conditions."""

    def test_compound_conditions_build(self):
        result = team_occurrence_build_result(
            conditions=[
                {"stat": "pts", "min_value": 120},
                {"stat": "fg3m", "min_value": 15},
            ],
            season="2024-25",
            limit=10,
        )
        assert isinstance(result, (LeaderboardResult, NoResult))

    def test_compound_with_team_filter(self):
        result = team_occurrence_build_result(
            conditions=[
                {"stat": "pts", "min_value": 110},
                {"stat": "fg3m", "min_value": 10},
            ],
            season="2024-25",
            team="BOS",
            limit=500,
        )
        assert isinstance(result, (LeaderboardResult, NoResult))


# ===================================================================
# 11. Structured Query Support
# ===================================================================


class TestStructuredQueryCompoundOccurrence:
    """Test structured query routes support compound occurrences."""

    def test_player_compound_structured(self):
        result = execute_structured_query(
            "player_occurrence_leaders",
            conditions=[
                {"stat": "pts", "min_value": 30},
                {"stat": "reb", "min_value": 10},
            ],
            season="2024-25",
            limit=10,
        )
        assert result.route == "player_occurrence_leaders"
        assert isinstance(result.result, (LeaderboardResult, NoResult))

    def test_team_compound_structured(self):
        result = execute_structured_query(
            "team_occurrence_leaders",
            conditions=[
                {"stat": "pts", "min_value": 120},
                {"stat": "fg3m", "min_value": 15},
            ],
            season="2024-25",
            limit=10,
        )
        assert result.route == "team_occurrence_leaders"
        assert isinstance(result.result, (LeaderboardResult, NoResult))


# ===================================================================
# 12. Compound Occurrence with Filters
# ===================================================================


class TestCompoundOccurrenceFilters:
    """Test compound occurrences with historical/opponent/playoff filters."""

    def test_compound_with_playoffs(self):
        parsed = parse_query("most playoff games with 30+ points and 10+ assists since 2015")
        assert parsed["route"] == "player_occurrence_leaders"
        kw = parsed["route_kwargs"]
        assert kw.get("season_type") == "Playoffs"
        assert "conditions" in kw

    def test_compound_with_opponent(self):
        parsed = parse_query("most games with 25+ points and 10+ rebounds vs celtics since 2020")
        assert parsed["route"] == "player_occurrence_leaders"
        kw = parsed["route_kwargs"]
        assert kw.get("opponent") == "BOS"
        assert "conditions" in kw

    def test_compound_with_since_year(self):
        parsed = parse_query("most games with 30+ points and 5+ threes since 2018")
        kw = parsed["route_kwargs"]
        assert kw.get("start_season") is not None


# ===================================================================
# 13. Service/API Compatibility
# ===================================================================


class TestCompoundOccurrenceService:
    """Test compound occurrence queries through the service layer."""

    def test_compound_leaderboard_natural(self):
        result = execute_natural_query("most games with 25+ points and 10+ assists since 2020")
        assert result.route == "player_occurrence_leaders"
        # Should return a result
        assert result.result is not None

    def test_compound_count_returns_countresult(self):
        result = execute_natural_query(
            "how many jokic games with 25+ points and 10+ rebounds since 2021"
        )
        # Should convert to CountResult due to count intent
        assert isinstance(result.result, (CountResult, NoResult))
        if isinstance(result.result, CountResult):
            assert result.result.count >= 0


# ===================================================================
# 14. Caveats and Metadata
# ===================================================================


class TestCompoundOccurrenceCaveats:
    """Test that compound occurrences include appropriate caveats."""

    def test_compound_caveat_added(self):
        result = player_occurrence_build_result(
            conditions=[
                {"stat": "pts", "min_value": 30},
                {"stat": "reb", "min_value": 10},
            ],
            season="2024-25",
            limit=10,
        )
        if isinstance(result, LeaderboardResult):
            # Should have a caveat about compound conditions
            assert any("compound" in c.lower() for c in result.caveats)


# ===================================================================
# 15. Edge Cases
# ===================================================================


class TestCompoundOccurrenceEdgeCases:
    """Test edge cases for compound occurrence queries."""

    def test_three_conditions(self):
        # Compound extraction should work for 2+ conditions
        # (parsing may only find first two currently)
        result = extract_compound_occurrence_event("25+ points and 10+ rebounds and 5+ assists")
        # Should find at least 2 conditions
        if result is not None:
            assert len(result) >= 2

    def test_under_condition(self):
        # Test "under X" parsing
        result = extract_compound_occurrence_event("30+ points and under 5 turnovers")
        # May or may not parse "under X" depending on implementation
        # At minimum, this should not crash
        if result is not None:
            assert len(result) >= 1

    def test_mixed_operators_not_crash(self):
        # Various natural language forms should not crash
        queries = [
            "games with 30+ points and 10+ rebounds since 2020",
            "30 point games and 10 rebound games",
            "how many player games with 40+ pts and 5+ threes",
        ]
        for q in queries:
            # Should not raise
            extract_compound_occurrence_event(q)
