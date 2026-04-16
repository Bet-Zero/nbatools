"""Tests for occurrence / milestone / threshold-event querying.

Covers:
1. Occurrence event extraction (extract_occurrence_event)
2. Occurrence leaderboard intent detection (wants_occurrence_leaderboard)
3. Player occurrence count routing (count_intent + occurrence event)
4. Player occurrence leaderboard routing
5. Team occurrence count routing
6. Team occurrence leaderboard routing
7. Special events (triple double, double double)
8. Historical/opponent/playoff composition
9. Structured query support
10. Service/API compatibility
"""

import pandas as pd
import pytest

from nbatools.commands.natural_query import (
    _build_parse_state,
    extract_occurrence_event,
    parse_query,
    wants_occurrence_leaderboard,
)
from nbatools.commands.player_occurrence_leaders import (
    SPECIAL_EVENT_STATS,
    _flag_special_event,
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
    QueryResult,
    execute_natural_query,
    execute_structured_query,
)

pytestmark = pytest.mark.engine

# ===================================================================
# 1. Occurrence Event Extraction
# ===================================================================


class TestExtractOccurrenceEvent:
    """Test extract_occurrence_event() parsing."""

    def test_40_point_games(self):
        result = extract_occurrence_event("40 point games")
        assert result == {"stat": "pts", "min_value": 40}

    def test_40_point_games_with_dash(self):
        result = extract_occurrence_event("40-point games")
        assert result == {"stat": "pts", "min_value": 40}

    def test_30_point_games(self):
        result = extract_occurrence_event("30 point games")
        assert result == {"stat": "pts", "min_value": 30}

    def test_5_three_games(self):
        result = extract_occurrence_event("5+ three games")
        assert result == {"stat": "fg3m", "min_value": 5}

    def test_5_three_games_no_plus(self):
        result = extract_occurrence_event("5 three games")
        assert result == {"stat": "fg3m", "min_value": 5}

    def test_15_rebound_games(self):
        result = extract_occurrence_event("15 rebound games")
        assert result == {"stat": "reb", "min_value": 15}

    def test_10_assist_games(self):
        result = extract_occurrence_event("10 assist games")
        assert result == {"stat": "ast", "min_value": 10}

    def test_5_steal_games(self):
        result = extract_occurrence_event("5 steal games")
        assert result == {"stat": "stl", "min_value": 5}

    def test_5_block_games(self):
        result = extract_occurrence_event("5 block games")
        assert result == {"stat": "blk", "min_value": 5}

    def test_triple_doubles(self):
        result = extract_occurrence_event("triple doubles")
        assert result == {"special_event": "triple_double"}

    def test_triple_double_singular(self):
        result = extract_occurrence_event("triple double")
        assert result == {"special_event": "triple_double"}

    def test_double_doubles(self):
        result = extract_occurrence_event("double doubles")
        assert result == {"special_event": "double_double"}

    def test_double_double_singular(self):
        result = extract_occurrence_event("double double")
        assert result == {"special_event": "double_double"}

    def test_games_with_stat(self):
        result = extract_occurrence_event("games with 5+ threes")
        assert result == {"stat": "fg3m", "min_value": 5}

    def test_games_scoring_40(self):
        result = extract_occurrence_event("games scoring 40+ points")
        assert result == {"stat": "pts", "min_value": 40}

    def test_120_point_team_games(self):
        result = extract_occurrence_event("120 point games")
        assert result == {"stat": "pts", "min_value": 120}

    def test_no_occurrence_event(self):
        assert extract_occurrence_event("jokic last 10 games") is None

    def test_no_occurrence_plain_query(self):
        assert extract_occurrence_event("celtics season summary") is None


# ===================================================================
# 2. Occurrence Leaderboard Intent Detection
# ===================================================================


class TestWantsOccurrenceLeaderboard:
    """Test wants_occurrence_leaderboard() detection."""

    def test_most_40_point_games(self):
        assert wants_occurrence_leaderboard("most 40 point games since 2015")

    def test_leaders_triple_doubles(self):
        assert wants_occurrence_leaderboard("leaders in triple doubles since 2020")

    def test_top_5_three_games(self):
        assert wants_occurrence_leaderboard("top 10 players with 5+ three games")

    def test_most_double_doubles(self):
        assert wants_occurrence_leaderboard("most double doubles this season")

    def test_who_has_most_40pt(self):
        assert wants_occurrence_leaderboard("who has the most 40 point games")

    def test_not_triggered_count(self):
        # "how many" is count, not leaderboard
        assert not wants_occurrence_leaderboard("how many 40 point games has tatum had")

    def test_not_triggered_no_event(self):
        assert not wants_occurrence_leaderboard("most points per game")


# ===================================================================
# 3. Parse State: Occurrence Event Extraction
# ===================================================================


class TestParseStateOccurrenceEvent:
    """Verify _build_parse_state extracts occurrence_event."""

    def test_40_point_games_parse(self):
        state = _build_parse_state("most 40 point games since 2020")
        assert state["occurrence_event"] == {"stat": "pts", "min_value": 40}
        assert state["occurrence_leaderboard_intent"] is True

    def test_triple_doubles_parse(self):
        state = _build_parse_state("most triple doubles since 2020")
        assert state["occurrence_event"] == {"special_event": "triple_double"}
        assert state["occurrence_leaderboard_intent"] is True

    def test_count_intent_with_occurrence(self):
        state = _build_parse_state("how many 40 point games has tatum had since 2020")
        assert state["occurrence_event"] == {"stat": "pts", "min_value": 40}
        assert state["count_intent"] is True

    def test_no_occurrence_event_simple(self):
        state = _build_parse_state("jokic last 10 games")
        assert state["occurrence_event"] is None
        assert state["occurrence_leaderboard_intent"] is False


# ===================================================================
# 4. Route Selection: Occurrence Leaderboard
# ===================================================================


class TestOccurrenceLeaderboardRouting:
    """Verify occurrence leaderboard queries route correctly."""

    def test_most_50pt_games_routes_to_occurrence_leaders(self):
        parsed = parse_query("most 50 point games since 2020")
        assert parsed["route"] == "player_occurrence_leaders"
        kw = parsed["route_kwargs"]
        assert kw["stat"] == "pts"
        assert kw["min_value"] == 50

    def test_most_triple_doubles_routes_correctly(self):
        parsed = parse_query("most triple doubles since 2020")
        assert parsed["route"] == "player_occurrence_leaders"
        kw = parsed["route_kwargs"]
        assert kw["special_event"] == "triple_double"

    def test_most_double_doubles_routes_correctly(self):
        parsed = parse_query("most double doubles since 2020")
        assert parsed["route"] == "player_occurrence_leaders"
        kw = parsed["route_kwargs"]
        assert kw["special_event"] == "double_double"

    def test_most_5_three_games_routes_correctly(self):
        parsed = parse_query("most 5+ three games since 2018")
        assert parsed["route"] == "player_occurrence_leaders"
        kw = parsed["route_kwargs"]
        assert kw["stat"] == "fg3m"
        assert kw["min_value"] == 5

    def test_season_range_propagated(self):
        parsed = parse_query("most 15 rebound games since 2020")
        kw = parsed["route_kwargs"]
        assert kw.get("start_season") is not None

    def test_opponent_filter_propagated(self):
        parsed = parse_query("most 50 point games vs celtics since 2021")
        kw = parsed["route_kwargs"]
        assert kw["opponent"] == "BOS"

    def test_playoffs_propagated(self):
        parsed = parse_query("most triple doubles in playoffs since 2020")
        kw = parsed["route_kwargs"]
        assert kw["season_type"] == "Playoffs"


# ===================================================================
# 5. Route Selection: Team Occurrence Leaderboard
# ===================================================================


class TestTeamOccurrenceLeaderboardRouting:
    """Verify team occurrence leaderboard queries route correctly."""

    def test_most_120pt_team_games(self):
        parsed = parse_query("teams with most 120 point games since 2020")
        assert parsed["route"] == "team_occurrence_leaders"
        kw = parsed["route_kwargs"]
        assert kw["stat"] == "pts"
        assert kw["min_value"] == 120

    def test_most_team_games_15_threes(self):
        parsed = parse_query("most team games with 15+ threes since 2018")
        assert parsed["route"] in ("team_occurrence_leaders", "player_occurrence_leaders")
        # Just verify the event is detected
        kw = parsed["route_kwargs"]
        assert kw.get("stat") == "fg3m" or kw.get("stat") is not None


# ===================================================================
# 6. Route Selection: Occurrence Count (Single Entity)
# ===================================================================


class TestOccurrenceCountRouting:
    """Verify occurrence count queries route correctly for specific players/teams."""

    def test_how_many_40pt_tatum(self):
        parsed = parse_query("how many 40 point games has tatum had since 2020")
        assert parsed["route"] in ("player_game_finder", "player_occurrence_leaders")
        # count_intent should be set
        assert parsed.get("count_intent") is True

    def test_count_triple_doubles_routes_to_occurrence(self):
        parsed = parse_query("count jokic triple doubles since 2021")
        assert parsed["route"] == "player_occurrence_leaders"

    def test_how_many_celtics_120pt(self):
        parsed = parse_query("how many celtics games with 120+ points since 2022")
        # Should route to game_finder with count intent
        assert parsed["route"] in ("game_finder", "team_occurrence_leaders")
        assert parsed.get("count_intent") is True


# ===================================================================
# 7. Special Event Flagging
# ===================================================================


class TestSpecialEventFlagging:
    """Test _flag_special_event on DataFrames."""

    def test_triple_double_detected(self):
        df = pd.DataFrame(
            {
                "pts": [30, 12, 8],
                "reb": [15, 11, 6],
                "ast": [12, 10, 7],
                "stl": [2, 1, 0],
                "blk": [1, 0, 0],
            }
        )
        flags = _flag_special_event(df, "triple_double")
        assert flags.tolist() == [True, True, False]

    def test_double_double_detected(self):
        df = pd.DataFrame(
            {
                "pts": [25, 8, 15],
                "reb": [12, 6, 3],
                "ast": [5, 4, 11],
                "stl": [1, 0, 0],
                "blk": [0, 0, 0],
            }
        )
        flags = _flag_special_event(df, "double_double")
        assert flags.tolist() == [True, False, True]

    def test_triple_double_near_miss(self):
        df = pd.DataFrame(
            {
                "pts": [10, 9],
                "reb": [10, 10],
                "ast": [10, 10],
                "stl": [0, 0],
                "blk": [0, 0],
            }
        )
        flags = _flag_special_event(df, "triple_double")
        # First row: 3 categories >= 10 (pts, reb, ast) → True
        # Second row: 2 categories >= 10 (reb, ast) → False for triple_double
        assert flags.tolist() == [True, False]


# ===================================================================
# 8. Player Occurrence Leaders build_result
# ===================================================================


class TestPlayerOccurrenceLeadersBuild:
    """Test player_occurrence_leaders.build_result() directly."""

    def test_stat_threshold_build(self):
        """Test with stat + min_value for 30-point games."""
        result = player_occurrence_build_result(
            stat="pts",
            min_value=30,
            season="2024-25",
            season_type="Regular Season",
            limit=10,
        )
        # Either LeaderboardResult or NoResult depending on data
        assert isinstance(result, (LeaderboardResult, NoResult))
        if isinstance(result, LeaderboardResult):
            assert not result.leaders.empty
            assert "rank" in result.leaders.columns
            assert result.current_through is not None

    def test_special_event_triple_double(self):
        """Test triple-double occurrence leaderboard."""
        result = player_occurrence_build_result(
            special_event="triple_double",
            season="2024-25",
            season_type="Regular Season",
            limit=10,
        )
        assert isinstance(result, (LeaderboardResult, NoResult))
        if isinstance(result, LeaderboardResult):
            assert not result.leaders.empty
            assert "rank" in result.leaders.columns

    def test_special_event_double_double(self):
        """Test double-double occurrence leaderboard."""
        result = player_occurrence_build_result(
            special_event="double_double",
            season="2024-25",
            season_type="Regular Season",
            limit=10,
        )
        assert isinstance(result, (LeaderboardResult, NoResult))
        if isinstance(result, LeaderboardResult):
            assert not result.leaders.empty

    def test_with_opponent(self):
        """Test with opponent filter."""
        result = player_occurrence_build_result(
            stat="pts",
            min_value=30,
            season="2024-25",
            season_type="Regular Season",
            opponent="BOS",
            limit=10,
        )
        assert isinstance(result, (LeaderboardResult, NoResult))
        if isinstance(result, LeaderboardResult):
            assert any("BOS" in c for c in result.caveats)

    def test_multi_season(self):
        """Test across multiple seasons."""
        result = player_occurrence_build_result(
            stat="pts",
            min_value=40,
            start_season="2022-23",
            end_season="2024-25",
            season_type="Regular Season",
            limit=10,
        )
        assert isinstance(result, (LeaderboardResult, NoResult))
        if isinstance(result, LeaderboardResult):
            assert any("seasons" in c.lower() or "aggregated" in c.lower() for c in result.caveats)

    def test_validation_no_stat_no_event(self):
        """Should raise if neither stat nor special_event is provided."""
        with pytest.raises(ValueError, match="Either stat"):
            player_occurrence_build_result(season="2024-25")

    def test_validation_both_stat_and_event(self):
        """Should raise if both stat and special_event are provided."""
        with pytest.raises(ValueError, match="Cannot combine"):
            player_occurrence_build_result(
                stat="pts", min_value=30, special_event="triple_double", season="2024-25"
            )

    def test_validation_stat_without_min(self):
        """Should raise if stat provided without min_value."""
        with pytest.raises(ValueError, match="must have min_value or max_value"):
            player_occurrence_build_result(stat="pts", season="2024-25")

    def test_validation_unsupported_stat(self):
        """Should raise for unsupported stats."""
        with pytest.raises(ValueError, match="Unsupported stat"):
            player_occurrence_build_result(stat="efg_pct", min_value=0.5, season="2024-25")


# ===================================================================
# 9. Team Occurrence Leaders build_result
# ===================================================================


class TestTeamOccurrenceLeadersBuild:
    """Test team_occurrence_leaders.build_result() directly."""

    def test_team_120pt_games(self):
        """Test team occurrence for 120+ point games."""
        result = team_occurrence_build_result(
            stat="pts",
            min_value=120,
            season="2024-25",
            season_type="Regular Season",
            limit=10,
        )
        assert isinstance(result, (LeaderboardResult, NoResult))
        if isinstance(result, LeaderboardResult):
            assert not result.leaders.empty
            assert "rank" in result.leaders.columns
            assert result.current_through is not None

    def test_team_15_three_games(self):
        """Test team occurrence for 15+ three-pointer games."""
        result = team_occurrence_build_result(
            stat="fg3m",
            min_value=15,
            season="2024-25",
            season_type="Regular Season",
            limit=10,
        )
        assert isinstance(result, (LeaderboardResult, NoResult))

    def test_team_with_opponent(self):
        """Test team occurrence with opponent filter."""
        result = team_occurrence_build_result(
            stat="pts",
            min_value=120,
            season="2024-25",
            season_type="Regular Season",
            opponent="LAL",
            limit=10,
        )
        assert isinstance(result, (LeaderboardResult, NoResult))
        if isinstance(result, LeaderboardResult):
            assert any("LAL" in c for c in result.caveats)

    def test_team_multi_season(self):
        """Test team occurrence across multiple seasons."""
        result = team_occurrence_build_result(
            stat="pts",
            min_value=130,
            start_season="2022-23",
            end_season="2024-25",
            season_type="Regular Season",
            limit=10,
        )
        assert isinstance(result, (LeaderboardResult, NoResult))

    def test_team_validation_unsupported_stat(self):
        """Should raise for unsupported stats."""
        with pytest.raises(ValueError, match="Unsupported stat"):
            team_occurrence_build_result(stat="fg_pct", min_value=0.5, season="2024-25")


# ===================================================================
# 10. Structured Query Support
# ===================================================================


class TestStructuredQueryRoutes:
    """Verify occurrence routes work via execute_structured_query."""

    def test_player_occurrence_structured(self):
        result = execute_structured_query(
            "player_occurrence_leaders",
            stat="pts",
            min_value=30,
            season="2024-25",
            limit=5,
        )
        assert isinstance(result, QueryResult)
        assert isinstance(result.result, (LeaderboardResult, NoResult))

    def test_team_occurrence_structured(self):
        result = execute_structured_query(
            "team_occurrence_leaders",
            stat="pts",
            min_value=120,
            season="2024-25",
            limit=5,
        )
        assert isinstance(result, QueryResult)
        assert isinstance(result.result, (LeaderboardResult, NoResult))

    def test_player_triple_double_structured(self):
        result = execute_structured_query(
            "player_occurrence_leaders",
            special_event="triple_double",
            season="2024-25",
            limit=5,
        )
        assert isinstance(result, QueryResult)
        assert isinstance(result.result, (LeaderboardResult, NoResult))


# ===================================================================
# 11. Service / API Compatibility
# ===================================================================


class TestServiceCompatibility:
    """Verify occurrence queries return valid QueryResult envelopes."""

    def test_occurrence_leaderboard_natural(self):
        qr = execute_natural_query("most triple doubles this season")
        assert isinstance(qr, QueryResult)
        assert isinstance(qr.result, (LeaderboardResult, NoResult))
        if isinstance(qr.result, LeaderboardResult):
            d = qr.result.to_dict()
            assert d["query_class"] == "leaderboard"
            assert "leaderboard" in d["sections"]

    def test_occurrence_count_natural(self):
        """Count query for a player should yield CountResult."""
        qr = execute_natural_query("how many 30 point games has lebron had this season")
        assert isinstance(qr, QueryResult)
        # Should be CountResult or NoResult
        assert isinstance(qr.result, (CountResult, NoResult))
        if isinstance(qr.result, CountResult):
            assert qr.result.count >= 0
            d = qr.result.to_dict()
            assert d["query_class"] == "count"
            assert "count" in d["sections"]

    def test_triple_double_leaderboard_natural(self):
        qr = execute_natural_query("most triple doubles this season")
        assert isinstance(qr, QueryResult)
        assert isinstance(qr.result, (LeaderboardResult, NoResult))

    def test_result_has_status_fields(self):
        qr = execute_natural_query("most triple doubles this season")
        assert isinstance(qr, QueryResult)
        assert qr.result_status in ("ok", "no_result", "error")

    def test_result_serialization(self):
        """Verify to_dict() works for occurrence results."""
        qr = execute_natural_query("most triple doubles this season")
        if isinstance(qr.result, LeaderboardResult):
            d = qr.result.to_dict()
            assert "query_class" in d
            assert "result_status" in d
            assert "sections" in d
            assert "notes" in d
            assert "caveats" in d


# ===================================================================
# 12. Historical / Opponent / Playoff Composition
# ===================================================================


class TestOccurrenceComposition:
    """Verify occurrence queries compose with historical/opponent/playoff contexts."""

    def test_since_year_parsing(self):
        parsed = parse_query("most 50 point games since 2020")
        assert parsed["route"] == "player_occurrence_leaders"
        kw = parsed["route_kwargs"]
        assert kw.get("start_season") is not None

    def test_last_n_seasons_parsing(self):
        parsed = parse_query("most triple doubles last 3 seasons")
        assert parsed["route"] == "player_occurrence_leaders"
        kw = parsed["route_kwargs"]
        assert kw.get("start_season") is not None

    def test_playoffs_only(self):
        parsed = parse_query("most 15 rebound games in playoffs since 2020")
        assert parsed["route"] == "player_occurrence_leaders"
        kw = parsed["route_kwargs"]
        assert kw["season_type"] == "Playoffs"

    def test_opponent_filter(self):
        parsed = parse_query("most 5+ three games vs lakers since 2021")
        kw = parsed["route_kwargs"]
        assert kw["opponent"] == "LAL"

    def test_team_occurrence_since_year(self):
        parsed = parse_query("teams with most 130 point games since 2020")
        assert parsed["route"] == "team_occurrence_leaders"
        kw = parsed["route_kwargs"]
        assert kw.get("start_season") is not None


# ===================================================================
# 13. Leaderboard Result Contract
# ===================================================================


class TestOccurrenceResultContract:
    """Verify occurrence results follow result contract conventions."""

    def test_leaderboard_result_fields(self):
        result = player_occurrence_build_result(
            stat="pts",
            min_value=30,
            season="2024-25",
            limit=5,
        )
        if isinstance(result, LeaderboardResult):
            assert hasattr(result, "leaders")
            assert hasattr(result, "result_status")
            assert hasattr(result, "current_through")
            assert hasattr(result, "caveats")
            assert hasattr(result, "notes")
            # to_dict contract
            d = result.to_dict()
            assert "query_class" in d
            assert d["query_class"] == "leaderboard"
            assert "sections" in d
            assert "leaderboard" in d["sections"]
            records = d["sections"]["leaderboard"]
            if records:
                assert "rank" in records[0]
                assert "player_name" in records[0]

    def test_no_result_fields(self):
        result = player_occurrence_build_result(
            stat="pts",
            min_value=999,  # ridiculously high threshold
            season="2024-25",
            limit=5,
        )
        if isinstance(result, NoResult):
            assert result.result_status == "no_result"
            d = result.to_dict()
            assert d["query_class"] in ("leaderboard", "count")


# ===================================================================
# 14. SPECIAL_EVENT_STATS constant
# ===================================================================


class TestSpecialEventStatsConstant:
    """Verify SPECIAL_EVENT_STATS is well-formed."""

    def test_triple_double_spec(self):
        spec = SPECIAL_EVENT_STATS["triple_double"]
        assert spec["threshold"] == 10
        assert spec["min_categories"] == 3
        assert "pts" in spec["stats"]
        assert "reb" in spec["stats"]
        assert "ast" in spec["stats"]

    def test_double_double_spec(self):
        spec = SPECIAL_EVENT_STATS["double_double"]
        assert spec["threshold"] == 10
        assert spec["min_categories"] == 2
        assert "pts" in spec["stats"]
        assert "reb" in spec["stats"]
        assert "ast" in spec["stats"]
