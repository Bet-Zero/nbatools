"""Read a bare first or last name in an availability clause as a teammate.

"Lakers record without Davis" and "LeBron stats with Austin" name a player
by one word. Across the league that word is shared ("Davis", "Austin"), so
it stayed unresolved and the question refused. Among the players who played
for the team (or alongside the player) in the requested seasons it is usually
one person; only then is the name read.
"""

from __future__ import annotations

import re
import unicodedata

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
    from nbatools.commands._matchup_utils import _STAT_COUNT_PHRASE

    text = (fragment or "").strip().lower()
    # A named participation clause and a box-score predicate are independent
    # conditions. Find their boundary before removing scope ("at least" is a
    # comparator, whereas "at home" is scope). Leave unknown predicates intact
    # so they cannot be mistaken for a fully resolved name.
    for conjunction in re.finditer(r"\s+and\s+", text):
        if _STAT_COUNT_PHRASE.match(text, conjunction.end()):
            text = text[: conjunction.start()]
            break
    text = _SCOPE_WORD.sub("", text).strip()
    return re.sub(r"\s+(?:both\s+)?playing$", "", text)


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


_AVAILABILITY_CLAUSE = re.compile(
    r"\b(with|without|w/o)\s+(.+?)(?=\s+(?:with|without|w/o)\b|[?!,;:]|$)"
)


def availability_name_clauses(text: str) -> list[tuple[str, list[str]]]:
    """Explicit participation names, with common stat/scope boundaries.

    All clauses are inspected: an earlier "with 24 points" must not hide a
    later teammate, and an opponent after two names must not hide the second.
    The same fragments drive pair detection and resolution. Unknown name tails
    remain present so resolution fails rather than accepting only the first.
    """
    from nbatools.commands._matchup_utils import _STAT_COUNT_PHRASE

    clauses = []
    for match in _AVAILABILITY_CLAUSE.finditer(text):
        fragment = match.group(2).strip(" .")
        if _STAT_COUNT_PHRASE.match(fragment):
            continue
        fragment = name_before_scope(fragment)
        fragment = re.split(r"\s+(?:record|games?)\b", fragment, maxsplit=1)[0]
        parts = [part.strip(" .") for part in fragment.split(" and ")]
        clauses.append(("with" if match.group(1) == "with" else "without", parts))
    return clauses


def _words(text: str) -> list[str]:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z0-9']+", plain.lower().replace("-", " ").replace(".", ""))


def _only_the_name(part: str, name: str) -> bool:
    """Whether the part is the name and nothing else: "davis and reaves out" is not."""
    return set(_words(part)) <= set(_words(name))


def availability_pair(
    text: str,
    *,
    team: str | None,
    player: str | None,
    season: str | None,
    start_season: str | None,
    end_season: str | None,
    season_type: str,
) -> tuple[str, str] | None:
    """("with" | "without", "A and B") when both names are the subject's teammates."""
    from nbatools.commands._matchup_utils import detect_player

    if team is None and player is None:
        return None
    candidates = [
        (mode, parts) for mode, parts in availability_name_clauses(text) if len(parts) == 2
    ]
    if len(candidates) != 1:
        return None
    mode, parts = candidates[0]
    side = _same_side_rows(team, player, season, start_season, end_season, season_type)
    if side is None:
        return None
    names = []
    for part in parts:
        name = detect_player(part) or resolve_teammate(
            part,
            team=team,
            player=player,
            season=season,
            start_season=start_season,
            end_season=end_season,
            season_type=season_type,
        )
        if not name or not _only_the_name(part, name) or select_player_rows(side, name).empty:
            return None
        names.append(name)
    if names[0] == names[1]:
        return None
    return mode, " and ".join(names)
