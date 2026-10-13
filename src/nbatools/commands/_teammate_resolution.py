"""Read a bare first or last name in an availability clause as a teammate.

"Lakers record without Davis" and "LeBron stats with Austin" name a player
by one word. Across the league that word is shared ("Davis", "Austin"), so
it stayed unresolved and the question refused. Among the players who played
for the team (or alongside the player) in the requested seasons it is usually
one person; only then is the name read.
"""

from __future__ import annotations

import re

from nbatools.commands._franchise import team_value_mask
from nbatools.commands._player_identity import select_player_rows
from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.entity_resolution import (
    _get_player_first_name_index,
    _strip_accents,
    player_ids_for_name,
    player_last_name_candidates,
)

_NOT_A_NAME = re.compile(
    r"^(?:the|a|an|his|her|their|them|him|he|she|they|it|starters?|bench|rest|home|road"
    r"|away|everyone|anyone|someone|nobody|teammates?|stars?|healthy|available)$"
)


# Scope the parser reads on its own: "without Davis this season", "with
# Davis since 2024-25", "with Davis vs Celtics" keep only the name.
_SCOPE_WORD = re.compile(
    r"\s+(?:this|last|since|in|vs\.?|versus|against|at|on|from|during|over|before|after"
    r"|through|until|playoffs?|postseason|regular|career|home|away|road|past|when|while"
    r"|for|with|without|under|between)\b.*$"
)


def name_before_scope(fragment: str | None) -> str:
    """The name in an availability fragment, without the scope after it."""
    return _SCOPE_WORD.sub("", (fragment or "").strip().lower())


def resolve_teammate(
    fragment: str | None,
    *,
    team: str | None,
    player: str | None,
    season: str | None,
    start_season: str | None,
    end_season: str | None,
    season_type: str,
) -> str | None:
    """The one teammate ``fragment`` (a single first or last name) names, or None."""
    word = name_before_scope(fragment)
    if not re.fullmatch(r"[a-z][a-z.'\-]+", word) or _NOT_A_NAME.match(word):
        return None
    if not (team or player):
        return None
    key = _strip_accents(word)
    candidates = set(player_last_name_candidates(key)) | set(
        _get_player_first_name_index().get(key, [])
    )
    if not candidates:
        return None
    ids: set[str] = set()
    for name in candidates:
        ids |= set(player_ids_for_name(name))
    if not ids:
        return None

    side = _same_side_rows(team, player, season, start_season, end_season, season_type)
    if side is None:
        return None
    matched = side[side["player_id"].astype(str).isin(ids)]
    if matched["player_id"].nunique() != 1:
        return None
    return str(matched["player_name"].mode().iloc[0])


def shares_side(
    name: str,
    *,
    player: str,
    season: str | None,
    start_season: str | None,
    end_season: str | None,
    season_type: str,
) -> bool:
    """Whether ``name`` played alongside ``player`` in the requested seasons."""
    side = _same_side_rows(None, player, season, start_season, end_season, season_type)
    if side is None:
        return False
    return not select_player_rows(side, name).empty


def _same_side_rows(team, player, season, start_season, end_season, season_type):
    """Rows of the team's players, or of the player's teammates, in the seasons."""
    from nbatools.commands._parse_helpers import default_season_for_context
    from nbatools.commands.data_utils import load_player_games_for_seasons

    try:
        if start_season and end_season and not season:
            seasons = resolve_seasons(None, start_season, end_season)
        else:
            seasons = [season or default_season_for_context(season_type)]
        games = load_player_games_for_seasons(seasons, season_type)
    except (ValueError, FileNotFoundError):
        return None
    if games.empty or "player_id" not in games.columns:
        return None

    if team:
        side = games[team_value_mask(games, team)]
    else:
        own = select_player_rows(games, player)
        if own.empty or "team_id" not in own.columns:
            return None
        pairs = set(zip(own["game_id"].astype(str), own["team_id"].astype(str)))
        keys = zip(games["game_id"].astype(str), games["team_id"].astype(str))
        side = games[[k in pairs for k in keys]]
        side = side[~side["player_id"].astype(str).isin(set(own["player_id"].astype(str)))]

    return side
