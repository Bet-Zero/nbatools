"""Shared constants used across command modules."""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Text normalisation helpers
# ---------------------------------------------------------------------------

STOP_WORDS = r"(?:from|to|in|on|at|with|home|away|road|wins?|loss(?:es)?|summary|average|averages|record|for|during|playoff|playoffs|postseason|last|past|recent|form|split|over|under|between|and|or)"  # noqa: E501


def normalize_text(text: str) -> str:
    return " ".join(text.lower().strip().split())


# ---------------------------------------------------------------------------
# Stat aliases & pattern
# ---------------------------------------------------------------------------

STAT_ALIASES: dict[str, str] = {
    # Points
    "points": "pts",
    "point": "pts",
    "pts": "pts",
    # Rebounds
    "rebounds": "reb",
    "rebound": "reb",
    "rebounded": "reb",
    "rebounding": "reb",
    "boards": "reb",
    "reb": "reb",
    # Assists
    "assists": "ast",
    "assist": "ast",
    "assisted": "ast",
    "assisting": "ast",
    "dimes": "ast",
    "ast": "ast",
    # Scoring (verbal forms — noun "points" already above)
    "scored": "pts",
    "scoring": "pts",
    "scores": "pts",
    # Steals
    "steals": "stl",
    "steal": "stl",
    "stolen": "stl",
    "stealing": "stl",
    "swipes": "stl",
    "stl": "stl",
    # Blocks
    "blocks": "blk",
    "block": "blk",
    "blocked": "blk",
    "blocking": "blk",
    "swats": "blk",
    "blk": "blk",
    # Threes
    "threes made": "fg3m",
    "three pointers made": "fg3m",
    "three-point makes": "fg3m",
    "threes": "fg3m",
    "3pm": "fg3m",
    "3s": "fg3m",
    "fg3m": "fg3m",
    # Turnovers
    "turnovers": "tov",
    "turnover": "tov",
    "tov": "tov",
    # Minutes
    "minutes": "minutes",
    # Field goal percentage
    "field goal percentage": "fg_pct",
    "field goal %": "fg_pct",
    "fg%": "fg_pct",
    "fg_pct": "fg_pct",
    # Three-point percentage
    "three point percentage": "fg3_pct",
    "three-point percentage": "fg3_pct",
    "3 point percentage": "fg3_pct",
    "3-point percentage": "fg3_pct",
    "three point %": "fg3_pct",
    "three-point %": "fg3_pct",
    "3 point %": "fg3_pct",
    "3-point %": "fg3_pct",
    "3pt%": "fg3_pct",
    "3p%": "fg3_pct",
    "fg3_pct": "fg3_pct",
    # Free throw percentage
    "free throw percentage": "ft_pct",
    "free throw %": "ft_pct",
    "ft%": "ft_pct",
    "ft_pct": "ft_pct",
    # Effective FG%
    "effective field goal percentage": "efg_pct",
    "effective field goal %": "efg_pct",
    "effective field goal": "efg_pct",
    "effective fg %": "efg_pct",
    "effective fg": "efg_pct",
    "efg%": "efg_pct",
    "efg_pct": "efg_pct",
    # True shooting %
    "true shooting percentage": "ts_pct",
    "true shooting %": "ts_pct",
    "true shooting": "ts_pct",
    "ts%": "ts_pct",
    "ts_pct": "ts_pct",
    # Plus/minus
    "plus minus": "plus_minus",
    "plus/minus": "plus_minus",
    "plus_minus": "plus_minus",
    "+/-": "plus_minus",
    # Usage rate
    "usage rate": "usg_pct",
    "usage percentage": "usg_pct",
    "usage %": "usg_pct",
    "usage": "usg_pct",
    "usg%": "usg_pct",
    "usg_pct": "usg_pct",
    "usg": "usg_pct",
    # Assist percentage
    "assist percentage": "ast_pct",
    "assist %": "ast_pct",
    "ast%": "ast_pct",
    "ast_pct": "ast_pct",
    # Rebound percentage
    "rebound percentage": "reb_pct",
    "rebound %": "reb_pct",
    "reb%": "reb_pct",
    "reb_pct": "reb_pct",
    # Turnover percentage
    "turnover percentage": "tov_pct",
    "turnover %": "tov_pct",
    "turnover rate": "tov_pct",
    "tov%": "tov_pct",
    "tov_pct": "tov_pct",
    # Offensive rating
    "offensive rating": "off_rating",
    "off rating": "off_rating",
    "off_rating": "off_rating",
    # Defensive rating
    "defensive rating": "def_rating",
    "def rating": "def_rating",
    "def_rating": "def_rating",
    # Net rating
    "net rating": "net_rating",
    "net_rating": "net_rating",
    # Pace
    "pace": "pace",
}


def _build_stat_pattern(aliases: dict[str, str]) -> str:
    """Auto-generate a regex alternation from alias keys, longest-first."""
    sorted_keys = sorted(aliases.keys(), key=len, reverse=True)
    escaped = "|".join(re.escape(k) for k in sorted_keys)
    return f"({escaped})"


STAT_PATTERN = _build_stat_pattern(STAT_ALIASES)

# ---------------------------------------------------------------------------
# Query intent enum & route mapping
# ---------------------------------------------------------------------------


class QueryIntent:
    """Explicit intent labels for parsed queries.

    Each value corresponds to a query class / result shape.  The ``intent``
    field in the parse state carries one of these values so consumers don't
    have to infer intent from boolean-flag combinations.
    """

    SUMMARY = "summary"
    COMPARISON = "comparison"
    FINDER = "finder"
    COUNT = "count"
    SPLIT = "split_summary"
    LEADERBOARD = "leaderboard"
    STREAK = "streak"
    ON_OFF = "on_off"
    LINEUP = "lineup"
    UNSUPPORTED = "unsupported"


ROUTE_TO_INTENT: dict[str, str] = {
    # Summary routes
    "player_game_summary": QueryIntent.SUMMARY,
    "game_summary": QueryIntent.SUMMARY,
    "team_record": QueryIntent.SUMMARY,
    "playoff_history": QueryIntent.SUMMARY,
    "record_by_decade": QueryIntent.SUMMARY,
    # Comparison routes
    "player_compare": QueryIntent.COMPARISON,
    "team_compare": QueryIntent.COMPARISON,
    "team_matchup_record": QueryIntent.COMPARISON,
    "playoff_matchup_history": QueryIntent.COMPARISON,
    "matchup_by_decade": QueryIntent.COMPARISON,
    # Finder routes
    "player_game_finder": QueryIntent.FINDER,
    "game_finder": QueryIntent.FINDER,
    # Split routes
    "player_split_summary": QueryIntent.SPLIT,
    "team_split_summary": QueryIntent.SPLIT,
    # Leaderboard routes
    "season_leaders": QueryIntent.LEADERBOARD,
    "season_team_leaders": QueryIntent.LEADERBOARD,
    "top_player_games": QueryIntent.LEADERBOARD,
    "top_team_games": QueryIntent.LEADERBOARD,
    "team_record_leaderboard": QueryIntent.LEADERBOARD,
    "player_occurrence_leaders": QueryIntent.LEADERBOARD,
    "team_occurrence_leaders": QueryIntent.LEADERBOARD,
    "playoff_appearances": QueryIntent.LEADERBOARD,
    "record_by_decade_leaderboard": QueryIntent.LEADERBOARD,
    "playoff_round_record": QueryIntent.LEADERBOARD,
    # Streak routes
    "player_streak_finder": QueryIntent.STREAK,
    "team_streak_finder": QueryIntent.STREAK,
    # On/off routes
    "player_on_off": QueryIntent.ON_OFF,
    # Lineup routes
    "lineup_summary": QueryIntent.LINEUP,
    "lineup_leaderboard": QueryIntent.LINEUP,
}


def route_to_intent(route: str | None, *, count_intent: bool = False) -> str:
    """Map a route name to its ``QueryIntent`` value.

    When *count_intent* is ``True`` and the route is a finder, the intent
    is ``count`` rather than ``finder`` — the count query class is a finder
    executed in count mode.
    """
    if route is None:
        return QueryIntent.UNSUPPORTED
    base = ROUTE_TO_INTENT.get(route, QueryIntent.UNSUPPORTED)
    if count_intent and base == QueryIntent.FINDER:
        return QueryIntent.COUNT
    return base
