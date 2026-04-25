"""Leaderboard stat alias tables and phrase-detection helpers."""

from __future__ import annotations

import re

from nbatools.commands._constants import STAT_ALIASES

# Player leaderboard aliases: extends STAT_ALIASES with leaderboard-only entries.
_LEADERBOARD_ONLY: dict[str, str] = {
    # Per-game forms
    "assists per game": "ast",
    "rebounds per game": "reb",
    "points per game": "pts",
    "steals per game": "stl",
    "blocks per game": "blk",
    "turnovers per game": "tov",
    # Milestone-game counts
    "30-point games": "games_30p",
    "30 point games": "games_30p",
    "40-point games": "games_40p",
    "40 point games": "games_40p",
    "20-point games": "games_20p",
    "20 point games": "games_20p",
    "10-assist games": "games_10a",
    "10 assist games": "games_10a",
    "10-rebound games": "games_10r",
    "10 rebound games": "games_10r",
    # Noun-agent forms
    "scorer": "pts",
    "scorers": "pts",
    "rebounder": "reb",
    "rebounders": "reb",
    "playmaker": "ast",
    "playmakers": "ast",
    "rim protector": "blk",
    "rim protectors": "blk",
    "shot blockers": "blk",
    "shot blocker": "blk",
    "shot-blockers": "blk",
    "shot-blocker": "blk",
    "offensive rebounder": "oreb",
    "offensive rebounders": "oreb",
    # Skill-description forms
    "hottest from three": "fg3_pct",
    "hottest from 3": "fg3_pct",
    "hot from three": "fg3_pct",
    "hot from 3": "fg3_pct",
    "best from three": "fg3_pct",
    "best from 3": "fg3_pct",
    "best shooting": "fg_pct",
    "shoot the best": "fg_pct",
    "shooting best from three": "fg3_pct",
    "shooting the best from three": "fg3_pct",
    "most efficient": "ts_pct",
    "efficient": "ts_pct",
    # Per-game abbreviations
    "apg": "ast",
    "rpg": "reb",
    "ppg": "pts",
    "spg": "stl",
    "bpg": "blk",
    # Space-separated pct forms not in base dict
    "ts pct": "ts_pct",
    "efg pct": "efg_pct",
    "usg pct": "usg_pct",
    "ast pct": "ast_pct",
    "reb pct": "reb_pct",
    "tov pct": "tov_pct",
}

LEADERBOARD_STAT_ALIASES: dict[str, str] = {**STAT_ALIASES, **_LEADERBOARD_ONLY}

TEAM_LEADERBOARD_STAT_ALIASES: dict[str, str] = {
    "best offensive teams": "off_rating",
    "offensive teams": "off_rating",
    "best offense": "off_rating",
    "offensive rating": "off_rating",
    "off rating": "off_rating",
    "off_rating": "off_rating",
    "worst offensive teams": "off_rating",
    "best defensive teams": "def_rating",
    "defensive teams": "def_rating",
    "best defense": "def_rating",
    "defensive rating": "def_rating",
    "def rating": "def_rating",
    "def_rating": "def_rating",
    "worst defensive teams": "def_rating",
    "teams with most threes": "fg3m",
    "most threes per game teams": "fg3m",
    "most threes per game": "fg3m",
    "best team 3 point percentage": "fg3_pct",
    "best team 3-point percentage": "fg3_pct",
    "best team three point percentage": "fg3_pct",
    "best team three-point percentage": "fg3_pct",
    "team 3 point percentage": "fg3_pct",
    "team 3-point percentage": "fg3_pct",
    "team 3pt%": "fg3_pct",
    "team fg%": "fg_pct",
    "best team fg%": "fg_pct",
    "team field goal percentage": "fg_pct",
    "best team field goal percentage": "fg_pct",
    "team ft%": "ft_pct",
    "best team ft%": "ft_pct",
    "team free throw percentage": "ft_pct",
    "best team free throw percentage": "ft_pct",
    "teams with best efg%": "efg_pct",
    "teams with best efg pct": "efg_pct",
    "best team efg%": "efg_pct",
    "best efg% teams": "efg_pct",
    "teams with best ts%": "ts_pct",
    "teams with best ts pct": "ts_pct",
    "best team ts%": "ts_pct",
    "best ts% teams": "ts_pct",
    "best net rating teams": "net_rating",
    "best net rating": "net_rating",
    "net rating": "net_rating",
    "net_rating": "net_rating",
    "worst net rating teams": "net_rating",
    "fastest teams": "pace",
    "fastest pace teams": "pace",
    "highest pace teams": "pace",
    "slowest teams": "pace",
    "slowest pace teams": "pace",
    "lowest pace teams": "pace",
    "pace": "pace",
    "most steals teams": "stl",
    "team steals": "stl",
    "most blocks teams": "blk",
    "team blocks": "blk",
    "most turnovers teams": "tov",
    "team turnovers": "tov",
    "lowest turnover teams": "tov",
    "fewest turnovers teams": "tov",
    "fewest turnover teams": "tov",
    "best plus minus teams": "plus_minus",
    "best plus/minus teams": "plus_minus",
    "team plus minus": "plus_minus",
    "most wins": "wins",
    "most wins teams": "wins",
    "teams with most wins": "wins",
    "best record teams": "win_pct",
    "best record": "win_pct",
    "best records": "win_pct",
    "best records teams": "win_pct",
    "best winning percentage": "win_pct",
    "best win pct": "win_pct",
    "highest winning percentage": "win_pct",
    "most losses": "losses",
    "most losses teams": "losses",
    "teams with most losses": "losses",
    "fewest losses": "losses",
    "fewest losses teams": "losses",
    "best scoring teams": "pts",
    "highest scoring teams": "pts",
    "most points per game teams": "pts",
    "most rebounds teams": "reb",
    "most assists teams": "ast",
    "best road record": "win_pct",
    "road record": "win_pct",
    "best home record": "win_pct",
    "home record": "win_pct",
}


def _matches_loose_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text))


def _detect_leaderboard_stat(text: str, aliases: dict[str, str]) -> str | None:
    for key in sorted(aliases.keys(), key=len, reverse=True):
        if _matches_loose_phrase(text, key):
            return aliases[key]
    return None


def detect_player_leaderboard_stat(text: str) -> str | None:
    return _detect_leaderboard_stat(text, LEADERBOARD_STAT_ALIASES)


def detect_team_leaderboard_stat(text: str) -> str | None:
    return _detect_leaderboard_stat(text, TEAM_LEADERBOARD_STAT_ALIASES)


def wants_ascending_leaderboard(text: str) -> bool:
    """Detect if the leaderboard should sort ascending (lowest/fewest/least/bottom)."""
    return bool(re.search(r"\blowest\b|\bfewest\b|\bleast\b|\bworst\b|\bbottom\b", text))
