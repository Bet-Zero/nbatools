"""Tests for real-world UI query failure fixes.

Covers six categories of failures identified from manual usage:
1. Player-vs-player-as-opponent routing
2. Season-high / single-game queries
3. Stat phrase expansion (fg%, 3pt%, "field goal percentage", etc.)
4. With/without player filtering
5. Distinct entity count queries
6. Entity resolution (Bronny James)
"""

import pytest

from nbatools.commands._constants import STAT_ALIASES
from nbatools.commands._leaderboard_utils import (
    LEADERBOARD_STAT_ALIASES,
    TEAM_LEADERBOARD_STAT_ALIASES,
)
from nbatools.commands._matchup_utils import (
    detect_opponent_player,
    detect_without_player,
    extract_player_vs_player_as_opponent,
)
from nbatools.commands._parse_helpers import (
    detect_distinct_player_count,
    detect_distinct_team_count,
    detect_season_high_intent,
    wants_leaderboard,
)
from nbatools.commands.entity_resolution import resolve_player
from nbatools.commands.natural_query import _build_parse_state, parse_query
from nbatools.query_service import execute_natural_query

pytestmark = pytest.mark.query


# ---------------------------------------------------------------------------
# 1. Player-vs-player-as-opponent
# ---------------------------------------------------------------------------


class TestPlayerVsPlayerAsOpponent:
    """'LeBron stats vs Kevin Durant' should NOT be a comparison —
    it should be LeBron's summary filtered to games where KD played."""

    def test_detect_opponent_player_basic(self):
        opp, cleaned = detect_opponent_player("stats vs Kevin Durant")
        assert opp == "Kevin Durant"

    def test_detect_opponent_player_against(self):
        opp, cleaned = detect_opponent_player("averages against Stephen Curry")
        assert opp == "Stephen Curry"

    def test_detect_opponent_player_none_when_team(self):
        opp, cleaned = detect_opponent_player("games vs Lakers")
        assert opp is None

    def test_extract_player_vs_player_as_opponent(self):
        result = extract_player_vs_player_as_opponent("LeBron James stats vs Kevin Durant")
        assert result is not None
        player_a, opponent = result
        assert player_a == "LeBron James"
        assert opponent == "Kevin Durant"

    def test_extract_comparison_not_opponent_when_direct_vs(self):
        """'LeBron vs KD' (no context words) should remain a comparison,
        not be treated as opponent filtering."""
        result = extract_player_vs_player_as_opponent("LeBron James vs Kevin Durant")
        # No context words → (None, None), meaning no opponent-filter intent
        assert result is None or result == (None, None)

    def test_route_lebron_stats_vs_kd(self):
        parsed = parse_query("LeBron stats vs Kevin Durant")
        # May route to finder or summary; key behavior is opponent_player is set
        assert parsed["route"] in ("player_game_finder", "player_game_summary")
        assert parsed["player"] == "LeBron James"
        assert parsed.get("opponent_player") == "Kevin Durant"

    def test_route_jokic_averages_against_curry(self):
        parsed = parse_query("Jokic averages against Stephen Curry")
        assert parsed["route"] == "player_game_summary"
        assert "joki" in parsed["player"].lower()
        assert parsed.get("opponent_player") == "Stephen Curry"


# ---------------------------------------------------------------------------
# 2. Season-high / single-game queries
# ---------------------------------------------------------------------------


class TestSeasonHighQueries:
    """'Cade Cunningham season high' should route to finder, not leaderboard.
    'highest scoring games this season' should route to top player games."""

    def test_detect_season_high_intent_basic(self):
        assert detect_season_high_intent("Cade Cunningham season high") is True

    def test_detect_season_high_intent_best_game(self):
        assert detect_season_high_intent("LeBron best game this season") is True

    def test_detect_season_high_intent_highest_scoring(self):
        assert detect_season_high_intent("highest scoring games this season") is True

    def test_detect_season_high_intent_negative(self):
        assert detect_season_high_intent("most points this season") is False

    def test_wants_leaderboard_excludes_season_high(self):
        assert wants_leaderboard("Cade Cunningham season high") is False

    def test_wants_leaderboard_excludes_highest_scoring_games(self):
        assert wants_leaderboard("highest scoring games this season") is False

    def test_route_player_season_high(self):
        parsed = parse_query("Cade Cunningham season high")
        # Should route to finder (top games), not leaderboard
        assert parsed["route"] == "player_game_finder"
        assert parsed["player"] == "Cade Cunningham"

    def test_route_highest_scoring_games(self):
        parsed = parse_query("highest scoring games this season")
        # Should route to top_player_games, not ppg leaderboard
        assert parsed["route"] == "top_player_games"


# ---------------------------------------------------------------------------
# 3. Stat phrase expansion
# ---------------------------------------------------------------------------


class TestStatPhraseExpansion:
    """Various percentage stat phrasings should resolve correctly."""

    def test_normalize_3_point_percentage(self):
        assert STAT_ALIASES.get("3 point percentage") == "fg3_pct"

    def test_normalize_3_point_pct_hyphen(self):
        assert STAT_ALIASES.get("3-point percentage") == "fg3_pct"

    def test_normalize_3_point_percent(self):
        assert STAT_ALIASES.get("3 point %") == "fg3_pct"

    def test_leaderboard_field_goal_percentage(self):
        assert LEADERBOARD_STAT_ALIASES.get("field goal percentage") == "fg_pct"

    def test_leaderboard_fg_pct(self):
        assert LEADERBOARD_STAT_ALIASES.get("fg%") == "fg_pct"

    def test_leaderboard_3pt_percentage(self):
        assert LEADERBOARD_STAT_ALIASES.get("3 point percentage") == "fg3_pct"

    def test_leaderboard_three_point_percentage(self):
        assert LEADERBOARD_STAT_ALIASES.get("three point percentage") == "fg3_pct"

    def test_leaderboard_free_throw_percentage(self):
        assert LEADERBOARD_STAT_ALIASES.get("free throw percentage") == "ft_pct"

    def test_team_leaderboard_3pt(self):
        assert TEAM_LEADERBOARD_STAT_ALIASES.get("best team 3 point percentage") == "fg3_pct"

    def test_team_leaderboard_fg_pct(self):
        assert TEAM_LEADERBOARD_STAT_ALIASES.get("team fg%") == "fg_pct"

    def test_team_leaderboard_ft_pct(self):
        assert TEAM_LEADERBOARD_STAT_ALIASES.get("team ft%") == "ft_pct"

    def test_route_3pt_percentage_leaders(self):
        parsed = parse_query("best 3 point percentage")
        assert parsed["route"] in ("season_leaders", "player_occurrence_leaders")
        assert parsed["stat"] == "fg3_pct"

    def test_route_best_team_3pt_pct(self):
        parsed = parse_query("best team 3 point percentage")
        assert parsed["route"] == "season_team_leaders"
        assert parsed["stat"] == "fg3_pct"


# ---------------------------------------------------------------------------
# 4. With/without player
# ---------------------------------------------------------------------------


class TestWithoutPlayer:
    """'Lakers record without LeBron' should filter out games LeBron played."""

    def test_detect_without_player_basic(self):
        player, cleaned = detect_without_player("Lakers record without LeBron James")
        assert player == "LeBron James"

    def test_detect_without_player_no_match(self):
        player, cleaned = detect_without_player("Lakers record")
        assert player is None

    def test_detect_without_player_strips_from_text(self):
        player, cleaned = detect_without_player("Lakers record without Steph Curry")
        # "Steph Curry" may be resolved to "Stephen Curry"
        assert player in ("Steph Curry", "Stephen Curry")
        assert "without" not in cleaned.lower()
        assert "curry" not in cleaned.lower()

    def test_route_team_without_player(self):
        parsed = parse_query("Lakers record without LeBron James")
        assert parsed["route"] == "team_record"
        assert parsed["team"] == "LAL"
        assert parsed.get("without_player") == "LeBron James"

    def test_route_team_wins_without_player(self):
        parsed = parse_query("Warriors wins without Stephen Curry")
        assert parsed["team"] == "GSW"
        assert parsed.get("without_player") == "Stephen Curry"

    def test_record_without_player_wrong_team_returns_no_match(self):
        qr = execute_natural_query("Celtics record when Giannis out")
        assert qr.route == "team_record"
        assert qr.result.result_reason == "no_match"
        assert qr.result.notes == ["No games matched the specified filters"]

    def test_record_leaderboard_without_player_returns_no_match(self):
        qr = execute_natural_query("best record without Stephen Curry")
        assert qr.route == "team_record_leaderboard"
        assert qr.result.result_reason == "no_match"
        assert qr.result.notes == ["No games matched the specified filters"]


# ---------------------------------------------------------------------------
# 5. Distinct entity count
# ---------------------------------------------------------------------------


class TestDistinctEntityCount:
    """'How many players scored 40+' should count distinct players."""

    def test_detect_distinct_player_count_basic(self):
        assert detect_distinct_player_count("how many players scored 40 points") is True

    def test_detect_distinct_player_count_number_of(self):
        assert detect_distinct_player_count("number of players with 10 assists") is True

    def test_detect_distinct_player_count_negative(self):
        assert detect_distinct_player_count("LeBron 40 point games") is False

    def test_detect_distinct_team_count(self):
        assert detect_distinct_team_count("how many teams scored 130 points") is True

    def test_route_how_many_players(self):
        parsed = parse_query("how many players scored 40 points this season")
        assert parsed["route"] == "player_occurrence_leaders"


# ---------------------------------------------------------------------------
# 6. Entity resolution: Bronny James
# ---------------------------------------------------------------------------


class TestBronnyJamesResolution:
    """'Bronny James' and 'Bronny' should resolve confidently."""

    def test_resolve_bronny_james_full(self):
        r = resolve_player("Bronny James")
        assert r.is_confident
        assert r.resolved == "Bronny James"

    def test_resolve_bronny_nickname(self):
        r = resolve_player("Bronny")
        assert r.is_confident
        assert r.resolved == "Bronny James"

    def test_route_bronny_stats(self):
        parsed = parse_query("Bronny James stats")
        assert parsed["player"] == "Bronny James"


# ---------------------------------------------------------------------------
# 7. Build-parse-state integration: new keys present
# ---------------------------------------------------------------------------


class TestBuildParseStateNewKeys:
    """Verify _build_parse_state returns the new detection keys."""

    def test_season_high_intent_key(self):
        state = _build_parse_state("LeBron season high")
        assert "season_high_intent" in state

    def test_distinct_player_count_key(self):
        state = _build_parse_state("how many players scored 40")
        assert "distinct_player_count" in state
        assert state["distinct_player_count"] is True

    def test_opponent_player_key(self):
        state = _build_parse_state("LeBron stats vs Kevin Durant")
        assert "opponent_player" in state

    def test_without_player_key(self):
        state = _build_parse_state("Lakers record without LeBron")
        assert "without_player" in state
