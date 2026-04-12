"""Tests for explicit query-intent detection and routing.

Verifies that the engine correctly distinguishes:
- list/finder intent
- count intent
- summary intent
- leaderboard intent
- intent + historical spans (since, career, last N seasons)
- intent + opponent filters
- intent + season type (playoffs)

Tests cover:
1. Intent detection functions (wants_finder, wants_count, wants_summary, wants_leaderboard)
2. Parse state extraction (finder_intent, count_intent in parsed dict)
3. Route selection (explicit intent overrides defaults)
4. Count result semantics (CountResult with correct count)
5. Service/API compatibility (QueryResult envelope)
"""

import pytest

from nbatools.commands.natural_query import (
    _build_parse_state,
    parse_query,
    wants_count,
    wants_finder,
    wants_leaderboard,
    wants_summary,
    wants_team_leaderboard,
)
from nbatools.commands.structured_results import (
    CountResult,
    FinderResult,
    LeaderboardResult,
    NoResult,
    SummaryResult,
)
from nbatools.query_service import (
    QueryResult,
    execute_natural_query,
)

# ===================================================================
# Intent Detection Functions
# ===================================================================


class TestWantsFinder:
    """Test the wants_finder() detection function."""

    def test_show_me(self):
        assert wants_finder("show me jokic games with 30 points")

    def test_list(self):
        assert wants_finder("list celtics games vs bucks since 2021")

    def test_find(self):
        assert wants_finder("find playoff games where tatum had 40+")

    def test_give_me(self):
        assert wants_finder("give me jokic games over 25 points")

    def test_what_games(self):
        assert wants_finder("what games did jokic have 30+ points")

    def test_which_games(self):
        assert wants_finder("which games did tatum score 40+")

    def test_show_all(self):
        assert wants_finder("show all jokic 30 point games")

    def test_show_every(self):
        assert wants_finder("show every celtics win vs lakers")

    def test_show_games(self):
        assert wants_finder("show games where jokic had a triple double")

    def test_no_finder_intent(self):
        assert not wants_finder("jokic summary 2024-25")

    def test_no_finder_for_summary(self):
        assert not wants_finder("summarize jokic vs lakers")

    def test_no_finder_for_count(self):
        assert not wants_finder("how many games did jokic play")


class TestWantsCount:
    """Test the wants_count() detection function."""

    def test_how_many(self):
        assert wants_count("how many 40 point games has tatum had since 2020")

    def test_count(self):
        assert wants_count("count jokic triple-doubles in playoffs since 2021")

    def test_number_of(self):
        assert wants_count("number of celtics games vs bucks since 2022")

    def test_total_games(self):
        assert wants_count("total games with 15+ rebounds vs lakers")

    def test_total_number(self):
        assert wants_count("total number of 30 point games")

    def test_total_count(self):
        assert wants_count("total count of wins vs heat")

    def test_no_count_for_list(self):
        assert not wants_count("show me jokic games")

    def test_no_count_for_summary(self):
        assert not wants_count("jokic career summary")


class TestWantsSummary:
    """Test summary detection (existing + new patterns)."""

    def test_summary(self):
        assert wants_summary("jokic summary 2024-25")

    def test_summarize(self):
        assert wants_summary("summarize jokic vs lakers since 2021")

    def test_average(self):
        assert wants_summary("jokic average 2024-25")

    def test_averages(self):
        assert wants_summary("jokic averages 2024-25")

    def test_career_summary(self):
        assert wants_summary("jokic career summary")

    def test_record(self):
        assert wants_summary("celtics record vs heat since 2020")

    def test_no_summary_for_finder(self):
        assert not wants_summary("show me jokic games with 30 points")


class TestWantsLeaderboard:
    """Test leaderboard detection including new 'rank' keyword."""

    def test_leaders_in(self):
        assert wants_leaderboard("leaders in ts% since 2020")

    def test_top_scorers(self):
        assert wants_leaderboard("top 20 scorers vs lakers since 2018")

    def test_rank(self):
        assert wants_leaderboard("rank players by net rating")

    def test_ranked(self):
        assert wants_leaderboard("ranked by ppg since 2020")

    def test_ranking(self):
        assert wants_leaderboard("ranking by ppg this season")

    def test_who_has_the_most(self):
        assert wants_leaderboard("who has the most ppg since 2020")

    def test_who_led(self):
        assert wants_leaderboard("who led the most in ppg")

    def test_season_leaders(self):
        assert wants_leaderboard("season leaders in ppg 2024-25")

    def test_highest_ts(self):
        assert wants_leaderboard("highest ts% 2024-25")

    def test_lowest_tov(self):
        assert wants_leaderboard("lowest tov pct 2024-25")


class TestWantsTeamLeaderboard:
    """Test team leaderboard detection including 'rank'."""

    def test_rank_teams(self):
        assert wants_team_leaderboard("rank teams by net rating")

    def test_ranked_teams(self):
        assert wants_team_leaderboard("ranked teams by pts")

    def test_best_teams(self):
        assert wants_team_leaderboard("best offensive teams 2024-25")

    def test_top_teams(self):
        assert wants_team_leaderboard("top 10 teams in scoring")


# ===================================================================
# Parse State Extraction
# ===================================================================


class TestParseStateIntents:
    """Verify that _build_parse_state produces correct intent flags."""

    def test_finder_intent_show_me(self):
        parsed = _build_parse_state("show me Jokic games with 30 points 2024-25")
        assert parsed["finder_intent"] is True
        assert parsed["count_intent"] is False

    def test_finder_intent_list(self):
        parsed = _build_parse_state("list Celtics games vs Bucks since 2021")
        assert parsed["finder_intent"] is True

    def test_count_intent_how_many(self):
        parsed = _build_parse_state("how many 40 point games has Jokic had since 2020")
        assert parsed["count_intent"] is True
        assert parsed["finder_intent"] is False

    def test_count_intent_count(self):
        parsed = _build_parse_state("count Jokic games over 25 points 2024-25")
        assert parsed["count_intent"] is True

    def test_no_explicit_intent(self):
        parsed = _build_parse_state("Jokic over 25 points 2024-25")
        assert parsed["finder_intent"] is False
        assert parsed["count_intent"] is False

    def test_summary_intent_preserved(self):
        parsed = _build_parse_state("Jokic career summary")
        assert parsed["summary_intent"] is True
        assert parsed["finder_intent"] is False

    def test_leaderboard_intent_rank(self):
        parsed = _build_parse_state("rank players by ppg 2024-25")
        assert parsed["leaderboard_intent"] is True


# ===================================================================
# Route Selection
# ===================================================================


class TestRouteSelection:
    """Verify that explicit intent correctly influences route selection."""

    def test_finder_intent_routes_to_finder(self):
        parsed = parse_query("show me Jokic games with 30 points since 2020")
        assert parsed["route"] == "player_game_finder"

    def test_finder_intent_overrides_range_summary(self):
        """When both range_intent and finder_intent are present,
        finder_intent should win and route to finder, not summary."""
        parsed = parse_query("show me Jokic games with 30 points since 2020")
        assert parsed["route"] == "player_game_finder"
        # Without finder_intent, range_intent would route to summary

    def test_count_intent_routes_to_finder(self):
        parsed = parse_query("how many 30 point games has Jokic had 2024-25")
        assert parsed["route"] == "player_game_finder"

    def test_count_intent_sets_no_limit(self):
        """Count queries should not limit results for accurate counting."""
        parsed = parse_query("how many 30 point games has Jokic had 2024-25")
        assert parsed["route_kwargs"].get("limit") is None

    def test_finder_intent_keeps_limit(self):
        """Regular finder intent should keep the default limit."""
        parsed = parse_query("show me Jokic games with 30 points 2024-25")
        assert parsed["route_kwargs"].get("limit") == 25

    def test_team_finder_intent(self):
        parsed = parse_query("list Celtics games vs Bucks 2024-25")
        assert parsed["route"] == "game_finder"

    def test_team_count_intent(self):
        parsed = parse_query("how many Celtics games vs Bucks 2024-25")
        assert parsed["route"] == "game_finder"
        assert parsed["route_kwargs"].get("limit") is None

    def test_summary_intent_still_routes_to_summary(self):
        """When summary is explicitly requested, it should still route to summary."""
        parsed = parse_query("summarize Jokic vs Lakers since 2021")
        assert parsed["route"] in ("player_game_summary", "player_compare")

    def test_leaderboard_rank_routes_correctly(self):
        parsed = parse_query("rank players by ppg 2024-25")
        assert parsed["route"] == "season_leaders"

    def test_team_leaderboard_rank(self):
        parsed = parse_query("rank teams by net rating 2024-25")
        assert parsed["route"] == "season_team_leaders"

    def test_plain_player_query_defaults_to_finder(self):
        """Without explicit intent, a player + stat query should still default to finder."""
        parsed = parse_query("Jokic over 25 points 2024-25")
        assert parsed["route"] == "player_game_finder"


# ===================================================================
# Historical + Opponent Integration
# ===================================================================


class TestIntentWithHistorical:
    """Verify intents work with since-year, season ranges, last N, career, playoffs."""

    def test_finder_with_since(self):
        parsed = parse_query("show me Jokic games with 30 points since 2020")
        assert parsed["route"] == "player_game_finder"
        assert parsed.get("start_season") is not None

    def test_count_with_since(self):
        parsed = parse_query("how many 40 point games has Jokic had since 2020")
        assert parsed["route"] == "player_game_finder"
        assert parsed["count_intent"] is True
        assert parsed.get("start_season") is not None

    def test_finder_with_last_n_seasons(self):
        parsed = parse_query("show me Jokic games with 25 points last 3 seasons")
        assert parsed["route"] == "player_game_finder"
        assert parsed.get("start_season") is not None

    def test_count_with_playoffs(self):
        parsed = parse_query("how many playoff games did Jokic have 25 points 2024-25")
        assert parsed["route"] == "player_game_finder"
        assert parsed["count_intent"] is True

    def test_leaderboard_with_since(self):
        parsed = parse_query("leaders in ts% since 2020")
        assert parsed["route"] == "season_leaders"
        assert parsed.get("start_season") is not None

    def test_leaderboard_rank_with_last_n(self):
        parsed = parse_query("rank teams by net rating last 3 seasons")
        assert parsed["route"] == "season_team_leaders"

    def test_summary_with_career(self):
        parsed = parse_query("Jokic career summary")
        assert parsed["route"] == "player_game_summary"


class TestIntentWithOpponent:
    """Verify intents work with opponent filters."""

    def test_finder_with_opponent(self):
        parsed = parse_query("show me Jokic games vs Lakers 2024-25")
        assert parsed["route"] == "player_game_finder"
        assert parsed.get("opponent") is not None

    def test_count_with_opponent(self):
        parsed = parse_query("how many games did Jokic have 30 points vs Lakers since 2020")
        assert parsed["route"] == "player_game_finder"
        assert parsed["count_intent"] is True
        assert parsed.get("opponent") is not None

    def test_team_finder_with_opponent(self):
        parsed = parse_query("list Celtics games vs Bucks since 2021")
        assert parsed["route"] == "game_finder"
        assert parsed.get("opponent") is not None

    def test_team_count_with_opponent(self):
        parsed = parse_query("how many Celtics games vs Heat since 2022")
        assert parsed["route"] == "game_finder"
        assert parsed["count_intent"] is True
        assert parsed.get("opponent") is not None

    def test_leaderboard_with_opponent(self):
        parsed = parse_query("top 20 scorers vs Lakers since 2018")
        assert parsed["route"] == "season_leaders"
        assert parsed.get("opponent") is not None


# ===================================================================
# CountResult Semantics
# ===================================================================


class TestCountResult:
    """Verify CountResult contract and serialization."""

    def test_count_result_to_dict(self):
        import pandas as pd

        games = pd.DataFrame(
            {"rank": [1, 2, 3], "game_date": ["2024-01-01", "2024-01-02", "2024-01-03"]}
        )
        cr = CountResult(count=3, games=games)
        d = cr.to_dict()
        assert d["query_class"] == "count"
        assert d["result_status"] == "ok"
        assert d["sections"]["count"] == [{"count": 3}]
        assert len(d["sections"]["finder"]) == 3

    def test_count_result_zero(self):
        cr = CountResult(count=0)
        d = cr.to_dict()
        assert d["query_class"] == "count"
        assert d["sections"]["count"] == [{"count": 0}]
        assert "finder" not in d["sections"]

    def test_count_result_labeled_text(self):
        import pandas as pd

        games = pd.DataFrame({"rank": [1], "game_date": ["2024-01-01"]})
        cr = CountResult(count=1, games=games)
        text = cr.to_labeled_text()
        assert "COUNT" in text
        assert "1" in text

    def test_count_result_sections_dict(self):
        import pandas as pd

        games = pd.DataFrame({"rank": [1, 2], "game_date": ["2024-01-01", "2024-01-02"]})
        cr = CountResult(count=2, games=games)
        sections = cr.to_sections_dict()
        assert "COUNT" in sections
        assert "FINDER" in sections

    def test_count_result_trust_fields(self):
        cr = CountResult(
            count=5,
            result_status="ok",
            current_through="2025-04-10",
            notes=["test note"],
            caveats=["test caveat"],
        )
        d = cr.to_dict()
        assert d["result_status"] == "ok"
        assert d["current_through"] == "2025-04-10"
        assert "test note" in d["notes"]
        assert "test caveat" in d["caveats"]


# ===================================================================
# Service/API Compatibility (slow tests with real data)
# ===================================================================


@pytest.mark.slow
class TestExplicitIntentExecution:
    """Execute explicit intent queries through the service layer."""

    def test_finder_intent_returns_finder_result(self):
        qr = execute_natural_query("show me Jokic games with 25 points 2024-25")
        assert isinstance(qr, QueryResult)
        assert isinstance(qr.result, FinderResult)
        assert qr.is_ok
        assert qr.route == "player_game_finder"

    def test_count_intent_returns_count_result(self):
        qr = execute_natural_query("how many games did Jokic have 25 points 2024-25")
        assert isinstance(qr, QueryResult)
        assert isinstance(qr.result, CountResult)
        assert qr.is_ok
        assert qr.result.count >= 0
        assert qr.metadata.get("query_class") == "count"

    def test_count_result_has_accurate_count(self):
        """Count result should report the total matching games, not a limited subset."""
        qr = execute_natural_query("how many games did Jokic have 10 points 2024-25")
        assert isinstance(qr.result, CountResult)
        # The count should be the actual number of matching games
        if qr.result.count > 0:
            assert len(qr.result.games) == qr.result.count

    def test_count_with_since(self):
        qr = execute_natural_query("how many 30 point games has Jokic had since 2022")
        assert isinstance(qr.result, (CountResult, NoResult))
        if isinstance(qr.result, CountResult):
            assert qr.result.count >= 0
            assert qr.metadata.get("query_class") == "count"

    def test_count_with_opponent(self):
        qr = execute_natural_query("how many Celtics games vs Heat 2024-25")
        assert isinstance(qr.result, (CountResult, NoResult))
        if isinstance(qr.result, CountResult):
            assert qr.result.count >= 0

    def test_count_zero_returns_ok(self):
        """A count of zero should return status ok with count=0, not an error."""
        qr = execute_natural_query("how many 100 point games has Jokic had 2024-25")
        assert isinstance(qr.result, CountResult)
        assert qr.result.count == 0
        assert qr.result.result_status == "ok"

    def test_finder_intent_overrides_range_to_summary(self):
        """'show me Jokic games with 30 points since 2020' should be finder, not summary."""
        qr = execute_natural_query("show me Jokic games with 30 points since 2020")
        assert isinstance(qr.result, (FinderResult, NoResult))
        assert qr.route == "player_game_finder"

    def test_summary_intent_returns_summary(self):
        qr = execute_natural_query("summarize Jokic 2024-25")
        assert isinstance(qr.result, SummaryResult)
        assert qr.route == "player_game_summary"

    def test_summary_with_opponent(self):
        qr = execute_natural_query("summarize Jokic vs Lakers 2024-25")
        assert isinstance(qr.result, (SummaryResult, NoResult))

    def test_leaderboard_rank(self):
        qr = execute_natural_query("top 5 scorers 2024-25")
        assert isinstance(qr.result, LeaderboardResult)
        assert qr.route == "season_leaders"

    def test_leaderboard_with_opponent(self):
        qr = execute_natural_query("top 10 scorers vs Lakers 2024-25")
        assert isinstance(qr.result, (LeaderboardResult, NoResult))
        assert qr.route == "season_leaders"

    def test_count_result_to_dict_api_compatible(self):
        """CountResult.to_dict() should produce a valid dict for the API response."""
        qr = execute_natural_query("how many games did Jokic have 25 points 2024-25")
        if isinstance(qr.result, CountResult):
            d = qr.result.to_dict()
            assert "query_class" in d
            assert "result_status" in d
            assert "sections" in d
            assert "count" in d["sections"]

    def test_team_list_intent(self):
        qr = execute_natural_query("list Celtics games 2024-25")
        assert isinstance(qr.result, (FinderResult, NoResult))
        assert qr.route == "game_finder"

    def test_team_count_intent(self):
        qr = execute_natural_query("how many Celtics wins 2024-25")
        assert isinstance(qr.result, (CountResult, NoResult))
        if isinstance(qr.result, CountResult):
            assert qr.result.count >= 0

    def test_metadata_preserved_for_count(self):
        """Count results should still carry full metadata."""
        qr = execute_natural_query("how many games did Jokic have 25 points 2024-25")
        assert qr.metadata.get("route") == "player_game_finder"
        assert qr.metadata.get("query_class") == "count"
        if qr.current_through:
            assert isinstance(qr.current_through, str)

    def test_result_status_for_count(self):
        qr = execute_natural_query("how many games did Jokic have 25 points 2024-25")
        assert qr.result_status == "ok"
