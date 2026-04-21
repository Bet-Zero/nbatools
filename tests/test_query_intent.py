"""Tests for QueryIntent enum and intent field in parse state."""

import pytest

from nbatools.commands._constants import (
    QueryIntent,
    route_to_intent,
)
from nbatools.commands.natural_query import parse_query

# ---------------------------------------------------------------------------
# Unit tests for route_to_intent mapping
# ---------------------------------------------------------------------------


class TestRouteToIntent:
    """Verify the route_to_intent function and ROUTE_TO_INTENT mapping."""

    def test_none_route_returns_unsupported(self):
        assert route_to_intent(None) == QueryIntent.UNSUPPORTED

    def test_unknown_route_returns_unsupported(self):
        assert route_to_intent("nonexistent_route") == QueryIntent.UNSUPPORTED

    def test_finder_with_count_intent_returns_count(self):
        assert route_to_intent("player_game_finder", count_intent=True) == QueryIntent.COUNT

    def test_finder_without_count_intent_returns_finder(self):
        assert route_to_intent("player_game_finder", count_intent=False) == QueryIntent.FINDER

    def test_game_finder_with_count_intent_returns_count(self):
        assert route_to_intent("game_finder", count_intent=True) == QueryIntent.COUNT

    @pytest.mark.parametrize(
        "route, expected",
        [
            ("player_game_summary", QueryIntent.SUMMARY),
            ("game_summary", QueryIntent.SUMMARY),
            ("team_record", QueryIntent.SUMMARY),
            ("playoff_history", QueryIntent.SUMMARY),
            ("record_by_decade", QueryIntent.SUMMARY),
            ("player_compare", QueryIntent.COMPARISON),
            ("team_compare", QueryIntent.COMPARISON),
            ("team_matchup_record", QueryIntent.COMPARISON),
            ("playoff_matchup_history", QueryIntent.COMPARISON),
            ("matchup_by_decade", QueryIntent.COMPARISON),
            ("player_game_finder", QueryIntent.FINDER),
            ("game_finder", QueryIntent.FINDER),
            ("player_split_summary", QueryIntent.SPLIT),
            ("team_split_summary", QueryIntent.SPLIT),
            ("season_leaders", QueryIntent.LEADERBOARD),
            ("season_team_leaders", QueryIntent.LEADERBOARD),
            ("player_stretch_leaderboard", QueryIntent.LEADERBOARD),
            ("top_player_games", QueryIntent.LEADERBOARD),
            ("top_team_games", QueryIntent.LEADERBOARD),
            ("team_record_leaderboard", QueryIntent.LEADERBOARD),
            ("player_occurrence_leaders", QueryIntent.LEADERBOARD),
            ("team_occurrence_leaders", QueryIntent.LEADERBOARD),
            ("playoff_appearances", QueryIntent.LEADERBOARD),
            ("record_by_decade_leaderboard", QueryIntent.LEADERBOARD),
            ("playoff_round_record", QueryIntent.LEADERBOARD),
            ("player_streak_finder", QueryIntent.STREAK),
            ("team_streak_finder", QueryIntent.STREAK),
            ("player_on_off", QueryIntent.ON_OFF),
            ("lineup_summary", QueryIntent.LINEUP),
            ("lineup_leaderboard", QueryIntent.LINEUP),
        ],
    )
    def test_all_routes_mapped(self, route, expected):
        assert route_to_intent(route) == expected

    def test_count_only_affects_finder_routes(self):
        """count_intent should not change intent for non-finder routes."""
        assert route_to_intent("player_game_summary", count_intent=True) == QueryIntent.SUMMARY
        assert route_to_intent("season_leaders", count_intent=True) == QueryIntent.LEADERBOARD


# ---------------------------------------------------------------------------
# Integration tests: intent field in parse_query output
# ---------------------------------------------------------------------------


class TestParseQueryIntentField:
    """Verify that parse_query populates the intent field correctly."""

    @pytest.mark.parser
    def test_summary_intent(self):
        result = parse_query("Jokic last 10 games")
        assert "intent" in result
        assert result["intent"] == QueryIntent.SUMMARY

    @pytest.mark.parser
    def test_finder_intent(self):
        result = parse_query("Jokic games over 30 points")
        assert result["intent"] == QueryIntent.FINDER

    @pytest.mark.parser
    def test_count_intent(self):
        result = parse_query("how many Jokic games with 30+ points")
        assert result["intent"] == QueryIntent.COUNT

    @pytest.mark.parser
    def test_comparison_intent(self):
        result = parse_query("Jokic vs Embiid this season")
        assert result["intent"] == QueryIntent.COMPARISON

    @pytest.mark.parser
    def test_leaderboard_intent(self):
        result = parse_query("points leaders last 10 games")
        assert result["intent"] == QueryIntent.LEADERBOARD

    @pytest.mark.parser
    def test_streak_intent(self):
        result = parse_query("Jokic longest streak of 30 point games")
        assert result["intent"] == QueryIntent.STREAK

    @pytest.mark.parser
    def test_split_intent(self):
        result = parse_query("Jokic home away split")
        assert result["intent"] == QueryIntent.SPLIT

    @pytest.mark.parser
    def test_team_summary_intent(self):
        result = parse_query("Lakers record this season")
        assert result["intent"] == QueryIntent.SUMMARY

    @pytest.mark.parser
    def test_team_leaderboard_intent(self):
        result = parse_query("team scoring leaders")
        assert result["intent"] == QueryIntent.LEADERBOARD

    @pytest.mark.parser
    def test_team_streak_intent(self):
        result = parse_query("longest Lakers winning streak")
        assert result["intent"] == QueryIntent.STREAK

    @pytest.mark.parser
    def test_team_comparison_intent(self):
        result = parse_query("Celtics vs Lakers this season")
        assert result["intent"] == QueryIntent.COMPARISON

    @pytest.mark.parser
    def test_team_finder_intent(self):
        result = parse_query("Lakers games over 120 points")
        assert result["intent"] == QueryIntent.FINDER

    @pytest.mark.parser
    def test_season_high_intent(self):
        result = parse_query("season high points")
        assert result["intent"] == QueryIntent.LEADERBOARD

    @pytest.mark.parser
    def test_team_record_intent(self):
        result = parse_query("Celtics record this season")
        assert result["intent"] == QueryIntent.SUMMARY

    @pytest.mark.parser
    def test_on_off_intent(self):
        result = parse_query("Jokic on/off")
        assert result["intent"] == QueryIntent.ON_OFF

    @pytest.mark.parser
    def test_lineup_intent(self):
        result = parse_query("best 5-man lineups this season")
        assert result["intent"] == QueryIntent.LINEUP

    @pytest.mark.parser
    def test_stretch_queries_use_leaderboard_intent(self):
        result = parse_query("hottest 3-game scoring stretch this year")
        assert result["intent"] == QueryIntent.LEADERBOARD

    @pytest.mark.parser
    def test_intent_always_present(self):
        """Every parse result should have an intent field."""
        queries = [
            "Jokic career averages",
            "LeBron 2023-24",
            "rebounds leaders",
            "Curry 5+ threes",
            "Bucks win streak",
        ]
        for q in queries:
            result = parse_query(q)
            assert "intent" in result, f"Missing intent for query: {q}"
            assert result["intent"] in {
                QueryIntent.SUMMARY,
                QueryIntent.COMPARISON,
                QueryIntent.FINDER,
                QueryIntent.COUNT,
                QueryIntent.SPLIT,
                QueryIntent.LEADERBOARD,
                QueryIntent.STREAK,
                QueryIntent.ON_OFF,
                QueryIntent.LINEUP,
                QueryIntent.UNSUPPORTED,
            }, f"Invalid intent '{result['intent']}' for query: {q}"
