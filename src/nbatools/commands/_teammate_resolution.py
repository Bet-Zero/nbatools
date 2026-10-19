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
from typing import NamedTuple

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


_PAIR = re.compile(
    r"\b(with|without|w/o)\s+(.+?)(?=\s+(?:record|games?|this|that|last|in|for|since|vs\.?"
    r"|versus|against|at|on|from|during|when|while|with|without|w/o)\b|[?.!,;:]|$)"
)

_PAIR_PARTICIPATION = re.compile(
    r"\s+(?:(?:are|were|is|was)\s+)?(?:both\s+)?"
    r"(?P<state>out|not\s+playing|did\s+not\s+play|dnp|playing|played)$"
)


class AvailabilityPair(NamedTuple):
    mode: str
    players: str
    start: int
    end: int

    def mask_clause(self, text: str) -> str:
        """Preserve offsets while excluding the condition already consumed."""
        return text[: self.start] + " " * (self.end - self.start) + text[self.end :]


def played_matchup_pair(text: str) -> AvailabilityPair | None:
    """Read exactly two whole-game played predicates, preserving their full span.

    An explicit matchup consumer qualifies each player's own/opposing side and
    complete game-day coverage at execution. Name recognition alone proves none
    of those facts. Other availability modes keep their existing reader.
    """
    from nbatools.commands._matchup_utils import (
        _is_exact_player_reference_phrase,
        _tail_is_read_scope,
        detect_player,
    )

    name = r"[\w .'’\-]+?"
    played = r"(?:plays?|played|playing)"
    patterns = [
        # Separate predicates: "with Tatum playing while Reaves plays".
        rf"\b(?:with|when|while)\s+({name})\s+{played}"
        rf"\s*(?:,\s*(?:and\s+)?|\s+(?:and|while)\s+)(?:with\s+)?"
        rf"({name})\s+{played}\b",
        # Shared predicate, including the established bare "with A and B".
        rf"\bwith\s+({name})\s*(?:\s+and\s+|,\s*(?:and\s+)?)({name})"
        rf"(?:\s+(?:both\s+)?{played})?(?=\s+(?:in|during|for|vs\.?|versus|against|at|on|this|last|since)\b|[?.!]|$)",
        rf"\b(?:when|while)\s+({name})\s+and\s+({name})\s+(?:both\s+)?{played}\b",
    ]
    matches = [match for pattern in patterns for match in re.finditer(pattern, text)]
    qualified = []
    for match in matches:
        if re.search(r"\b(?:not|unless)\s*$", text[: match.start()]):
            continue
        if re.search(r"\b(?:with|without|w/o|when|while)\b", text[: match.start()]):
            # A second with/when fragment is a separate condition, not noise
            # before this pair. Never promote a suffix of a longer request.
            continue
        if not _tail_is_read_scope(text, match.end()):
            continue
        names = []
        for part in match.groups():
            part = part.strip(" .")
            resolved = detect_player(part)
            if not resolved or not (
                _is_exact_player_reference_phrase(part, resolved) or _only_the_name(part, resolved)
            ):
                break
            names.append(resolved)
        if len(names) == 2 and names[0] != names[1]:
            qualified.append(
                AvailabilityPair("with", " and ".join(names), match.start(), match.end())
            )
    # Overlapping readings must agree on the complete consumed predicate.
    return qualified[0] if len(set(qualified)) == 1 else None


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
) -> AvailabilityPair | None:
    """A qualified two-teammate condition and its complete source span."""
    from nbatools.commands._matchup_utils import detect_player

    if team is None and player is None:
        return None
    # Stat-bound clauses can precede the named pair. They are not teammate
    # predicates; inspect each complete with/without fragment instead of taking
    # the first "with" in the question.
    matches = list(_PAIR.finditer(text))
    pairs = [m for m in matches if " and " in m.group(2)]
    if len(pairs) != 1:
        return None
    m = pairs[0]
    if re.search(r"\b(?:not|unless)\s*$", text[: m.start()]):
        return None
    fragment = m.group(2)
    mode = "with" if m.group(1) == "with" else "without"
    suffix = _PAIR_PARTICIPATION.search(fragment)
    if suffix:
        state = suffix.group("state")
        suffix_mode = "with" if state in ("playing", "played") else "without"
        if mode == "without" and suffix_mode == "with":
            return None
        mode = suffix_mode
        fragment = fragment[: suffix.start()]
    parts = [part.strip(" .") for part in fragment.split(" and ")]
    if len(parts) != 2:
        return None
    if any(other is not m and detect_player(other.group(2)) for other in matches):
        # A separate named presence/absence clause cannot be erased by the pair.
        return None
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
    return AvailabilityPair(mode, " and ".join(names), m.start(), m.end())
