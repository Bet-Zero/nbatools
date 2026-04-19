"""Tests for default-rule ``notes`` entries in ``_finalize_route``.

Phase C formalizes implicit defaults by adding ``notes`` entries that
document which default rule fired.  These tests verify the notes are
present when expected and absent when the route was triggered by explicit
user intent.
"""

import pytest

from nbatools.commands.natural_query import parse_query

pytestmark = pytest.mark.query

# ===================================================================
# Item 2: <player> + <timeframe> → summary default
# ===================================================================

DEFAULT_PLAYER_TIMEFRAME_NOTE = "default: <player> + <timeframe> → summary"


class TestPlayerTimeframeSummaryDefault:
    """The default fires when a player + timeframe is present with no
    more-specific signal (no stat filter, opponent, threshold, etc.)."""

    def test_jokic_last_10(self):
        parsed = parse_query("Jokic last 10")
        assert parsed["route"] == "player_game_summary"
        assert DEFAULT_PLAYER_TIMEFRAME_NOTE in parsed.get("notes", [])

    def test_embiid_this_season(self):
        parsed = parse_query("Embiid this season")
        assert parsed["route"] == "player_game_summary"
        assert DEFAULT_PLAYER_TIMEFRAME_NOTE in parsed.get("notes", [])

    def test_lebron_season(self):
        parsed = parse_query("LeBron 2023-24")
        assert parsed["route"] == "player_game_summary"
        assert DEFAULT_PLAYER_TIMEFRAME_NOTE in parsed.get("notes", [])

    def test_curry_last_5_games(self):
        parsed = parse_query("Curry last 5 games")
        assert parsed["route"] == "player_game_summary"
        assert DEFAULT_PLAYER_TIMEFRAME_NOTE in parsed.get("notes", [])

    def test_sga_last_20(self):
        parsed = parse_query("SGA last 20")
        assert parsed["route"] == "player_game_summary"
        assert DEFAULT_PLAYER_TIMEFRAME_NOTE in parsed.get("notes", [])

    def test_tatum_last_15_games(self):
        parsed = parse_query("Tatum last 15 games")
        assert parsed["route"] == "player_game_summary"
        assert DEFAULT_PLAYER_TIMEFRAME_NOTE in parsed.get("notes", [])

    def test_luka_lately(self):
        parsed = parse_query("Luka lately")
        assert parsed["route"] == "player_game_summary"
        assert DEFAULT_PLAYER_TIMEFRAME_NOTE in parsed.get("notes", [])


class TestPlayerTimeframeDefaultNotFired:
    """The default note must NOT appear when the user explicitly requested
    summary or when a more-specific signal routes the query elsewhere."""

    def test_explicit_summary_intent(self):
        """Explicit 'summary' keyword → no default note."""
        parsed = parse_query("Jokic summary 2024-25")
        assert parsed["route"] == "player_game_summary"
        assert DEFAULT_PLAYER_TIMEFRAME_NOTE not in parsed.get("notes", [])

    def test_explicit_career_intent(self):
        parsed = parse_query("Jokic career summary")
        assert parsed["route"] == "player_game_summary"
        assert DEFAULT_PLAYER_TIMEFRAME_NOTE not in parsed.get("notes", [])

    def test_explicit_averages(self):
        parsed = parse_query("Jokic averages 2024-25")
        assert parsed["route"] == "player_game_summary"
        assert DEFAULT_PLAYER_TIMEFRAME_NOTE not in parsed.get("notes", [])

    def test_recent_form_is_explicit_summary(self):
        """'recent form' sets summary_intent, so no default note."""
        parsed = parse_query("Jokic recent form")
        assert parsed["route"] == "player_game_summary"
        assert DEFAULT_PLAYER_TIMEFRAME_NOTE not in parsed.get("notes", [])

    def test_stat_filter_prevents_default(self):
        """Player + stat filter routes to finder, not summary default."""
        parsed = parse_query("Jokic 30+ points last 10")
        assert parsed["route"] != "player_game_summary" or (
            DEFAULT_PLAYER_TIMEFRAME_NOTE not in parsed.get("notes", [])
        )

    def test_opponent_prevents_default(self):
        """Player + opponent routes elsewhere (finder), not summary default."""
        parsed = parse_query("Jokic vs Lakers last 10")
        assert DEFAULT_PLAYER_TIMEFRAME_NOTE not in parsed.get("notes", [])


# ===================================================================
# Item 3: <metric> only → league-wide leaderboard default
# ===================================================================

DEFAULT_LEADERBOARD_NOTE = "default: <metric> only → league-wide leaderboard"


class TestMetricOnlyLeaderboardDefault:
    """No-subject leaderboard fires when a stat/leaderboard signal is
    present but no player or team entity is resolved."""

    def test_points_leaders(self):
        parsed = parse_query("points leaders")
        assert parsed["route"] in ("season_leaders", "season_team_leaders")
        assert DEFAULT_LEADERBOARD_NOTE in parsed.get("notes", [])

    def test_scoring_leaders(self):
        parsed = parse_query("scoring leaders")
        assert parsed["route"] in ("season_leaders", "season_team_leaders")
        assert DEFAULT_LEADERBOARD_NOTE in parsed.get("notes", [])

    def test_rebounds_last_10(self):
        parsed = parse_query("rebounds leaders last 10")
        assert parsed["route"] in ("season_leaders", "season_team_leaders")
        assert DEFAULT_LEADERBOARD_NOTE in parsed.get("notes", [])

    def test_assists_leaders(self):
        parsed = parse_query("assists leaders")
        assert parsed["route"] in ("season_leaders", "season_team_leaders")
        assert DEFAULT_LEADERBOARD_NOTE in parsed.get("notes", [])

    def test_team_leaderboard_no_subject(self):
        parsed = parse_query("team scoring leaders")
        assert parsed["route"] == "season_team_leaders"
        assert DEFAULT_LEADERBOARD_NOTE in parsed.get("notes", [])


# ===================================================================
# Item 4: <player> + <threshold> → finder default
# ===================================================================

DEFAULT_THRESHOLD_FINDER_NOTE = "default: <player> + <threshold> → finder"


class TestPlayerThresholdFinderDefault:
    """When a player + threshold is present with no explicit finder/count
    intent, the fallback routes to player_game_finder."""

    def test_jokic_over_25_points(self):
        parsed = parse_query("Jokic over 25 points")
        assert parsed["route"] == "player_game_finder"
        assert DEFAULT_THRESHOLD_FINDER_NOTE in parsed.get("notes", [])

    def test_curry_5_plus_threes(self):
        parsed = parse_query("Curry 5+ threes")
        assert parsed["route"] == "player_game_finder"
        assert DEFAULT_THRESHOLD_FINDER_NOTE in parsed.get("notes", [])

    def test_embiid_30_plus_points_2024(self):
        parsed = parse_query("Embiid 30+ points 2024-25")
        assert parsed["route"] == "player_game_finder"
        assert DEFAULT_THRESHOLD_FINDER_NOTE in parsed.get("notes", [])

    def test_luka_under_20_points(self):
        parsed = parse_query("Luka under 20 points")
        assert parsed["route"] == "player_game_finder"
        assert DEFAULT_THRESHOLD_FINDER_NOTE in parsed.get("notes", [])

    def test_sga_between_25_and_35(self):
        parsed = parse_query("SGA between 25 and 35 points")
        assert parsed["route"] == "player_game_finder"
        assert DEFAULT_THRESHOLD_FINDER_NOTE in parsed.get("notes", [])


class TestPlayerThresholdDefaultNotFired:
    """The threshold-finder default note must NOT appear when the user
    explicitly requested a count or list."""

    def test_explicit_count_intent(self):
        """Explicit 'how many' → count mode, not fallback default."""
        parsed = parse_query("how many Jokic 30+ point games")
        assert parsed["route"] == "player_game_finder"
        assert DEFAULT_THRESHOLD_FINDER_NOTE not in parsed.get("notes", [])

    def test_explicit_list_intent(self):
        """Explicit 'list' → finder, not fallback default."""
        parsed = parse_query("list Jokic games with 30 points")
        assert parsed["route"] == "player_game_finder"
        assert DEFAULT_THRESHOLD_FINDER_NOTE not in parsed.get("notes", [])


# ===================================================================
# Item 5: Remaining default-branch notes
# ===================================================================


class TestSeasonHighLeagueWideNote:
    """League-wide season-high routes should document the default."""

    def test_highest_scoring_games(self):
        parsed = parse_query("highest scoring games this season")
        assert parsed["route"] == "top_player_games"
        assert "season_high: league-wide top single-game performances" in parsed.get("notes", [])


class TestTopPlayerGamesNote:
    """Top-games keyword routing documents the default sort stat.
    Note: the 'top' keyword branch (`"top" in q and "games" in q`) is
    unreachable because 'top' sets leaderboard_intent, which is excluded.
    League-wide top games route through season_high_intent instead."""

    def test_highest_scoring_games_note(self):
        parsed = parse_query("highest scoring games this season")
        assert parsed["route"] == "top_player_games"
        assert "season_high: league-wide top single-game performances" in parsed.get("notes", [])

    def test_season_high_games_note(self):
        parsed = parse_query("season high games")
        assert parsed["route"] == "top_player_games"
        assert "season_high: league-wide top single-game performances" in parsed.get("notes", [])


class TestTopTeamGamesNote:
    """'Top team games' keyword routing documents the default sort stat."""

    def test_top_team_games(self):
        parsed = parse_query("top team games")
        assert parsed["route"] == "top_team_games"
        notes = parsed.get("notes", [])
        assert any(n.startswith("default: top team games ranked by") for n in notes)

    def test_top_team_scoring_games(self):
        parsed = parse_query("top team scoring games this season")
        assert parsed["route"] == "top_team_games"
        notes = parsed.get("notes", [])
        assert any(n.startswith("default: top team games ranked by") for n in notes)


class TestStreakDefaultWindowNote:
    """Streak routes without an explicit season document the three-season
    window default."""

    def test_player_streak_no_season(self):
        parsed = parse_query("Jokic 5 straight games with 20+ points")
        assert parsed["route"] == "player_streak_finder"
        notes = parsed.get("notes", [])
        assert any("three-season window" in n for n in notes)

    def test_player_streak_with_season_no_note(self):
        parsed = parse_query("Jokic 5 straight games with 20+ points 2024-25")
        assert parsed["route"] == "player_streak_finder"
        notes = parsed.get("notes", [])
        assert not any("three-season window" in n for n in notes)

    def test_team_streak_no_season(self):
        parsed = parse_query("longest Lakers winning streak")
        assert parsed["route"] == "team_streak_finder"
        notes = parsed.get("notes", [])
        assert any("three-season window" in n for n in notes)

    def test_team_streak_with_season_no_note(self):
        parsed = parse_query("longest Lakers winning streak 2024-25")
        assert parsed["route"] == "team_streak_finder"
        notes = parsed.get("notes", [])
        assert not any("three-season window" in n for n in notes)


class TestTeamThresholdFinderNote:
    """Team + threshold fallback to game_finder documents the default."""

    def test_team_over_120_points(self):
        parsed = parse_query("Lakers over 120 points")
        assert parsed["route"] == "game_finder"
        assert "default: <team> + <threshold> → finder" in parsed.get("notes", [])

    def test_team_explicit_finder_no_note(self):
        """Explicit finder intent should not produce the fallback note."""
        parsed = parse_query("list Lakers games over 120 points")
        assert parsed["route"] == "game_finder"
        assert "default: <team> + <threshold> → finder" not in parsed.get("notes", [])
