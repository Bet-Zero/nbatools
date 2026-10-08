"""Shared constants used across command modules."""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# Text normalisation helpers
# ---------------------------------------------------------------------------

STOP_WORDS = r"(?:from|to|in|on|at|with|home|away|road|wins?|loss(?:es)?|summary|average|averages|record|for|during|playoff|playoffs|postseason|last|past|recent|form|split|over|under|between|and|or)"  # noqa: E501


def normalize_text(text: str) -> str:
    normalized = (
        text.replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .lower()
    )
    # Fold diacritics ("Dončić" -> "doncic"). Parser patterns spell names in
    # ASCII ([a-z]), so an accented name split a comparison or opponent phrase
    # mid-word: "Luka Dončić vs Nikola Jokić" lost its second player. Entity
    # resolution maps the ASCII spelling back to the canonical accented name.
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFKD", normalized)
        if not unicodedata.combining(char)
    )
    collapsed = " ".join(normalized.strip().split())
    # Drop end-of-sentence punctuation. Detectors that anchor on a word boundary
    # or end of string stop matching when a "?" is glued to the last token, so
    # "Lakers record against the Celtics?" failed opponent detection and fell
    # through to a looser team scan that read the Celtics as the *subject* -
    # returning Boston's own record. Only trailing punctuation is stripped, and
    # "%" is deliberately excluded so stat phrasing like "fg%" survives.
    return collapsed.rstrip("?!.,;:")


BOOLEAN_OR_PATTERN = re.compile(
    r"\s+or\s+(?!(?:more|fewer|less)\b(?!\s+than))", flags=re.IGNORECASE
)

# "teams .500 or better", ".500 or worse teams", "teams at or above .500": the
# winning-teams bar or the bar that includes .500. Only beside "teams": a
# shooting or win-percentage ".500 or better" is not an opponent.
_TEAM_500_BETTER = re.compile(
    r"\b(?:teams?|opponents?)\s+(?:that|who|which)\s+(?:are|were|finished|have\s+been)\s+"
    r"(?:at\s+)?\.500\s+or\s+(?:better|above|higher)\b"
    r"|\bteams?\s+(?:at\s+)?\.500\s+or\s+(?:better|above|higher)\b"
    r"|(?<![\w.])\.500\s+or\s+(?:better|above|higher)\s+teams?\b"
    r"|\bteams?\s+at\s+or\s+(?:above|better\s+than)\s+\.500\b"
)
_TEAM_500_WORSE = re.compile(
    r"\b(?:teams?|opponents?)\s+(?:that|who|which)\s+(?:are|were|finished|have\s+been)\s+"
    r"(?:at\s+)?\.500\s+or\s+(?:worse|below|lower)\b"
    r"|\bteams?\s+(?:at\s+)?\.500\s+or\s+(?:worse|below|lower)\b"
    r"|(?<![\w.])\.500\s+or\s+(?:worse|below|lower)\s+teams?\b"
    r"|\bteams?\s+at\s+or\s+(?:below|worse\s+than)\s+\.500\b"
)
# "30 points or better", "15 threes or better", "scoring 120 or higher": a
# counting-stat floor the threshold reader takes as "or more". Rates, plus
# minus, percents and game windows are not read that way, so they still refuse.
_WHOLE_NUMBER_BOUND = re.compile(
    r"(?:(?<![\d.])(\d+)(\s+(?:made\s+)?(?:points?|pts|rebounds?|assists?|steals?|blocks?|threes|3s"
    r"|turnovers?))|(?<=\bscoring\s)(\d+)())\s+or\s+(?:(better|higher|above)|(worse|lower|below))\b"
)


def canonicalize_500_team_bars(text: str) -> str:
    text = _TEAM_500_BETTER.sub("winning teams", text)
    return _TEAM_500_WORSE.sub("teams .500 or worse", text)


# "how many teams are .500 or better", "a record of .500 or worse": one
# record bar, never two clauses.
_POPULATION_500_BAR = re.compile(
    r"\b(?:are|were|is|was|finished|finish|ended|end|stand|of)\s+(?:at\s+)?\.500\s+or\s+"
    r"(?:better|above|higher|worse|below|lower)\b"
)


_OPPONENT_CONTEXT = re.compile(
    r"\b(?:against|vs\.?|versus|beat|beaten|beating|over|opponents?|facing|faced|play(?:ed|ing)?)\b"
)


def _or_bounds_read(text: str) -> str:
    # The bar's own name says "or worse"; it is one opponent group.
    text = canonicalize_500_team_bars(text).replace("teams .500 or worse", "teams_500_or_worse")
    if not _OPPONENT_CONTEXT.search(text):
        # Beside an opponent word the bar is the opponents' (read above).
        text = _POPULATION_500_BAR.sub(lambda m: m.group(0).replace(" or ", "_or_"), text)
    return _WHOLE_NUMBER_BOUND.sub(
        lambda m: (
            f"{m.group(1) or m.group(3)}{m.group(2) or ''} or "
            + ("more" if m.group(5) else "fewer")
        ),
        text,
    )


def contains_boolean_or(text: str) -> bool:
    return bool(
        BOOLEAN_OR_PATTERN.search(
            _or_bounds_read(canonicalize_trailing_ceilings(normalize_text(text)))
        )
    )


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
    "offensive rebounds": "oreb",
    "offensive rebound": "oreb",
    "oreb": "oreb",
    "defensive rebounds": "dreb",
    "defensive rebound": "dreb",
    "dreb": "dreb",
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
    "score": "pts",
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
    # Personal fouls
    "personal fouls": "pf",
    "personal foul": "pf",
    "fouls": "pf",
    "foul": "pf",
    "pf": "pf",
    # Turnovers
    "turnovers": "tov",
    "turnover": "tov",
    "tov": "tov",
    # Minutes
    "minutes": "minutes",
    "min": "minutes",
    "mins": "minutes",
    # Box-score makes/attempts
    "field goals made": "fgm",
    "field goal made": "fgm",
    "fgm": "fgm",
    "field goals attempted": "fga",
    "field goal attempts": "fga",
    "field goal attempted": "fga",
    "fga": "fga",
    "three pointers attempted": "fg3a",
    "three pointer attempts": "fg3a",
    "three pointer attempted": "fg3a",
    "three-pointers attempted": "fg3a",
    "three-pointer attempts": "fg3a",
    "three-pointer attempted": "fg3a",
    # The adjectival long form. Its siblings already carry it - "three-point
    # makes" for fg3m, "three point percentage" for fg3_pct - so "3PA" was the
    # only one of the three whose spelled-out form did not resolve, and
    # "total three-point attempts leaders" was read as a points request.
    "three point attempts": "fg3a",
    "three-point attempts": "fg3a",
    "three point attempted": "fg3a",
    "three-point attempted": "fg3a",
    "threes attempted": "fg3a",
    "three attempts": "fg3a",
    "3pa": "fg3a",
    "fg3a": "fg3a",
    "free throws made": "ftm",
    "free throw made": "ftm",
    "ftm": "ftm",
    "free throws attempted": "fta",
    "free throw attempts": "fta",
    "free throw attempted": "fta",
    "fta": "fta",
    # Field goal percentage
    "field goal percentage": "fg_pct",
    "field goal %": "fg_pct",
    "fg%": "fg_pct",
    "fg_pct": "fg_pct",
    # Three-point percentage
    "three point percentage": "fg3_pct",
    "three-point percentage": "fg3_pct",
    "3pt percentage": "fg3_pct",
    "3pt pct": "fg3_pct",
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
    "plus-minus": "plus_minus",
    "plus minus": "plus_minus",
    "plus/minus": "plus_minus",
    "plus_minus": "plus_minus",
    "+/-": "plus_minus",
    # Final margins; margin phrases are rewritten to these forms ("won by
    # 10+" -> "won at 10+ win margin", "decided by 3 or fewer" -> "at 3 or
    # fewer game margin").
    "game margin": "margin",
    "win margin": "win_margin",
    "loss margin": "loss_margin",
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

# "10 assists at most", "30 minutes or under", "score 100 or lower": an
# inclusive ceiling, rewritten to the "or fewer" form the readers handle. A
# number or "than" after "or under" keeps it a boolean "or" ("30 points or
# under 5 turnovers"), and ".500 or below" is left alone.
_TRAILING_STAT_CEILING = re.compile(
    rf"(?<![.\d])\b(\d+(?:\.\d+)?)\s+({STAT_PATTERN}|minutes?|mins?)\s+"
    r"(?:at\s+most|max(?:imum)?|or\s+(?:under|below|lower))\b(?!\s+(?:than|\d|\.\d))"
)
_TRAILING_BARE_CEILING = re.compile(
    r"(?<![.\d])\b(\d+)\s+or\s+(?:under|below|lower)\b(?!\s+(?:than|\d|\.\d))"
)


def canonicalize_trailing_ceilings(text: str) -> str:
    text = _TRAILING_STAT_CEILING.sub(r"\1 \2 or fewer", text)
    return _TRAILING_BARE_CEILING.sub(r"\1 or fewer", text)


# ---------------------------------------------------------------------------
# Stat availability sets
# ---------------------------------------------------------------------------

TEAM_SEASON_ADVANCED_STATS = {"off_rating", "def_rating", "net_rating", "pace"}
TEAM_SEASON_ONLY_STATS = {"off_rating", "def_rating", "net_rating", "pace"}
PLAYER_SEASON_ONLY_STATS = {"off_rating", "def_rating", "net_rating"}
LOWER_IS_BETTER_STATS = {"def_rating", "opponent_pts_per_game", "tov", "tov_pct"}

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
    "player_stretch_leaderboard": QueryIntent.LEADERBOARD,
    "team_stretch_leaderboard": QueryIntent.LEADERBOARD,
    "top_player_games": QueryIntent.LEADERBOARD,
    "top_team_games": QueryIntent.LEADERBOARD,
    "team_record_leaderboard": QueryIntent.LEADERBOARD,
    "player_occurrence_leaders": QueryIntent.LEADERBOARD,
    "team_occurrence_leaders": QueryIntent.LEADERBOARD,
    "playoff_appearances": QueryIntent.LEADERBOARD,
    "record_by_decade_leaderboard": QueryIntent.LEADERBOARD,
    "playoff_round_record": QueryIntent.LEADERBOARD,
    "playoff_series_comebacks": QueryIntent.LEADERBOARD,
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
