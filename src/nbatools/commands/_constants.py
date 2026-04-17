"""Shared constants used across command modules."""

from __future__ import annotations

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
    "reb": "reb",
    # Assists
    "assists": "ast",
    "assist": "ast",
    "ast": "ast",
    # Steals
    "steals": "stl",
    "steal": "stl",
    "stl": "stl",
    # Blocks
    "blocks": "blk",
    "block": "blk",
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
    "three point %": "fg3_pct",
    "three-point %": "fg3_pct",
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


STAT_PATTERN = (
    r"(points|point|pts|rebounds|rebound|reb|assists|assist|ast|"
    r"steals|steal|stl|blocks|block|blk|"
    r"threes made|three pointers made|three-point makes|threes|3pm|3s|fg3m|"
    r"turnovers|turnover|tov|minutes|"
    r"field goal percentage|field goal %|fg%|fg_pct|"
    r"three point percentage|three-point percentage|three point %|three-point %|3pt%|3p%|fg3_pct|"
    r"free throw percentage|free throw %|ft%|ft_pct|"
    r"effective field goal percentage|effective field goal %|effective field goal|"
    r"effective fg %|effective fg|efg%|efg_pct|"
    r"true shooting percentage|true shooting %|true shooting|ts%|ts_pct|"
    r"plus minus|plus/minus|plus_minus|\+/-|"
    r"usage rate|usage percentage|usage %|usage|usg%|usg_pct|usg|"
    r"assist percentage|assist %|ast%|ast_pct|"
    r"rebound percentage|rebound %|reb%|reb_pct|"
    r"turnover percentage|turnover %|turnover rate|tov%|tov_pct|"
    r"offensive rating|off rating|off_rating|"
    r"defensive rating|def rating|def_rating|"
    r"net rating|net_rating|pace)"
)
