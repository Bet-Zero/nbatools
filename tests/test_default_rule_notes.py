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
