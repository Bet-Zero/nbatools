"""Shared constants used across command modules."""

from __future__ import annotations

STAT_ALIASES: dict[str, str] = {
    "points": "pts",
    "point": "pts",
    "pts": "pts",
    "rebounds": "reb",
    "rebound": "reb",
    "reb": "reb",
    "assists": "ast",
    "assist": "ast",
    "ast": "ast",
    "steals": "stl",
    "steal": "stl",
    "stl": "stl",
    "blocks": "blk",
    "block": "blk",
    "blk": "blk",
    "threes made": "fg3m",
    "three pointers made": "fg3m",
    "three-point makes": "fg3m",
    "threes": "fg3m",
    "3pm": "fg3m",
    "3s": "fg3m",
    "fg3m": "fg3m",
    "turnovers": "tov",
    "turnover": "tov",
    "tov": "tov",
    "effective field goal percentage": "efg_pct",
    "effective field goal %": "efg_pct",
    "effective field goal": "efg_pct",
    "effective fg %": "efg_pct",
    "effective fg": "efg_pct",
    "efg%": "efg_pct",
    "efg_pct": "efg_pct",
    "true shooting percentage": "ts_pct",
    "true shooting %": "ts_pct",
    "true shooting": "ts_pct",
    "ts%": "ts_pct",
    "ts_pct": "ts_pct",
    "plus minus": "plus_minus",
    "plus/minus": "plus_minus",
    "plus_minus": "plus_minus",
    "+/-": "plus_minus",
}


STAT_PATTERN = (
    r"(points|point|pts|rebounds|rebound|reb|assists|assist|ast|"
    r"steals|steal|stl|blocks|block|blk|"
    r"threes made|three pointers made|three-point makes|threes|3pm|3s|fg3m|"
    r"turnovers|turnover|tov|"
    r"effective field goal percentage|effective field goal %|effective field goal|"
    r"effective fg %|effective fg|efg%|efg_pct|"
    r"true shooting percentage|true shooting %|true shooting|ts%|ts_pct|"
    r"plus minus|plus/minus|plus_minus|\+/-)"
)
