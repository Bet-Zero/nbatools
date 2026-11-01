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

import pandas as pd

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
    """Whether exact-game evidence associates ``name`` with ``player`` on a side."""
    side = _same_side_rows(None, player, season, start_season, end_season, season_type)
    if side is None:
        return False
    if not select_player_rows(side, name).empty:
        return True
    # Listed nonparticipants have no appearance row. Exact-game association
    # reads the condition; execution still qualifies every candidate's state.
    from nbatools.commands._parse_helpers import default_season_for_context
    from nbatools.commands._participation_observations import (
        load_observations,
        resolve_observed_name,
    )
    from nbatools.commands.data_utils import load_player_games_for_seasons

    seasons = (
        resolve_seasons(season, start_season, end_season)
        if season or (start_season and end_season)
        else [default_season_for_context(season_type)]
    )
    try:
        if not resolve_observed_name(name, seasons, season_type).is_confident:
            return False
        listed = select_player_rows(load_observations(seasons, season_type), name)
        own = select_player_rows(load_player_games_for_seasons(seasons, season_type), player)
        keys = ["game_id", "team_id", "game_date"]
        listed, own = listed[keys].copy(), own[keys].copy()
        for rows in [listed, own]:
            for col in keys[:2]:
                rows[col] = pd.to_numeric(rows[col], errors="raise")
            rows.game_date = pd.to_datetime(rows.game_date).dt.normalize()
        return not listed.merge(own, on=keys).empty
    except (ValueError, FileNotFoundError, KeyError):
        return False


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
    r"|versus|against|at|on|from|during|when|while|with|without|w/o)\b|[?!,;:]|$)"
)

_PAIR_PARTICIPATION = re.compile(
    r"\s+(?:(?:are|were|is|was)\s+)?(?:both\s+)?"
    r"(?P<state>out|not\s+playing|did\s+not\s+play|dnp|playing|played)$"
)


class AvailabilityClause(NamedTuple):
    mode: str
    players: str
    start: int
    end: int

    def mask_clause(self, text: str) -> str:
        """Preserve offsets while excluding the condition already consumed."""
        return text[: self.start] + " " * (self.end - self.start) + text[self.end :]


class AvailabilityConjunction(NamedTuple):
    """Separately owned scalar clauses, retaining polarity and source spans."""

    clauses: tuple[AvailabilityClause, AvailabilityClause]

    def mask_clause(self, text: str) -> str:
        for clause in self.clauses:
            text = clause.mask_clause(text)
        return text

    def name(self, mode: str) -> str:
        return next(clause.players for clause in self.clauses if clause.mode == mode)


def requested_mixed_availability(text: str) -> AvailabilityConjunction | None:
    """Read two scalar whole-game clauses before resolving either identity.

    A shared name list remains owned by the existing pair reader. A mixed
    conjunction needs its own polarity marker on each side, such as WITHOUT
    A AND WITH B, or WITH A OUT AND B PLAYING. OR and extra actors stay unread.
    """
    from nbatools.commands._matchup_utils import detect_team_in_text
    from nbatools.commands._parse_helpers import detect_stat

    if re.search(r"\bor\b", text):
        return None
    state = (
        r"(?:(?:is|was|are|were)\s+)?(?:out|not\s+playing|did\s+not\s+play|dnp"
        r"|sitting|sits?|sat|playing|plays?|played)"
    )
    state_end = re.compile(rf"\s+({state})$")
    stop = (
        r"(?=\s+(?:and|while|when|but|record|games?|this|last|in|for|since|vs\.?"
        r"|versus|against|at|on|from|during|over|before|after|through|until|home|away)\b"
        r"|[?!,;:]|$)"
    )
    patterns = [
        rf"\b(with|without|w/o|w/)\s+([\w .'\-]+?){stop}",
        r"\b(when|while|and)\s+((?:(?!\b(?:and|or|with|without|when|while)\b)"
        rf"[\w .'\-])+?\s+{state}){stop}",
    ]
    clauses, explicit_states = [], []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            if any(match.start() < c.end and match.end() > c.start for c in clauses):
                continue
            if re.search(r"\b(?:not|unless)\s*$", text[: match.start()]):
                return None
            fragment = match.group(2).strip()
            suffix = state_end.search(fragment)
            mode = "without" if match.group(1) in {"without", "w/o"} else "with"
            if suffix:
                mode = (
                    "without"
                    if mode == "without"
                    or not re.fullmatch(
                        r"(?:(?:is|was|are|were)\s+)?(?:playing|plays?|played)", suffix[1]
                    )
                    else "with"
                )
                fragment = fragment[: suffix.start()].strip()
            if not fragment or re.search(r"\d|\b(?:and|or|with|without|both)\b", fragment):
                return None
            clauses.append(AvailabilityClause(mode, fragment, match.start(), match.end()))
            explicit_states.append(bool(suffix) or match.group(1) in {"without", "w/o"})
    if len(clauses) != 2 or {c.mode for c in clauses} != {"with", "without"}:
        return None
    conjunction = AvailabilityConjunction(tuple(clauses))
    remainder = conjunction.mask_clause(text)
    for tail in re.split(r"\b(?:and|while|when|but)\b|[,;]", remainder)[1:]:
        tail = tail.strip()
        # Date/opponent/schedule scope belongs to the existing scope readers;
        # a bare additional name remains here even when it is not indexed.
        if not tail or not _SCOPE_WORD.sub("", " " + tail).strip() or detect_stat(tail) is not None:
            continue
        if re.search(r"\brecord\b", tail) and detect_team_in_text(tail):
            continue  # A leading condition may precede its explicit team subject.
        return None  # An unowned name/clause is still requested, even if unindexed.
    pair = requested_availability_pair(text)
    if pair:
        # WITH A AND B OUT already has a shared negative scope. Explicit
        # independent state verbs distinguish WITH A PLAYING AND B OUT.
        if not all(explicit_states):
            return None
        remainder = conjunction.mask_clause(text)[pair.start : pair.end]
        if re.sub(r"\band\b|[\s,;]", "", remainder):
            return None
    return conjunction


def requested_scalar_absence(text: str) -> AvailabilityClause | None:
    """One explicit WITH-name-nonparticipation clause, before name resolution.

    WITH introduces the condition; OUT/NOT PLAYING/DNP/SITTING supplies its
    polarity. Preserve the whole span so presence readers cannot reinterpret it.
    Medical causes, unspecified missingness and additional people stay unread.
    """
    name = r"((?:(?!\b(?:and|or|with|without|when|while)\b)[\w .'\-])+?)"
    pattern = (
        rf"\b(?:with|w/)\s+{name}\s+(?:(?:is|was|are|were)\s+)?"
        r"(?:out|not\s+playing|did\s+not\s+play|dnp|sitting)\b"
    )
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        return None
    match = matches[0]
    fragment = match.group(1).strip()
    if re.search(r"\d|\b(?:not|unless)\s*$", fragment) or re.search(
        r"\b(?:not|unless)\s*$", text[: match.start()]
    ):
        return None
    return AvailabilityClause("without", fragment, match.start(), match.end())


def exact_condition_name(fragment: str, resolved: str) -> bool:
    """A resolved identity must consume the name, not ignore unrelated words."""
    from nbatools.commands._matchup_utils import _is_exact_player_reference_phrase

    return _only_the_name(fragment, resolved) or _is_exact_player_reference_phrase(
        fragment, resolved
    )


def requested_availability_pair(text: str) -> AvailabilityClause | None:
    """Preserve a raw name-list condition BEFORE any scalar name resolution.

    This reads scope only. Returned names are unresolved and must never be
    passed to an execution consumer until availability_pair qualifies them.
    Numeric/stat clauses and understood setting tails are not name lists.
    """
    from nbatools.commands._matchup_utils import _tail_is_read_scope
    from nbatools.commands._parse_helpers import detect_stat

    for match in _PAIR.finditer(text):
        fragment = match.group(2).strip()
        suffix = _PAIR_PARTICIPATION.search(fragment)
        absent = match.group(1) != "with"
        if suffix:
            absent = absent or suffix.group("state") not in ("playing", "played")
            fragment = fragment[: suffix.start()]
        parts = [part.strip(" .") for part in fragment.split(" and ")]
        if len(parts) >= 2 and all(
            part
            and not re.search(r"\d", part)
            and detect_stat(part) is None
            and not _tail_is_read_scope(" " + part, 0)
            for part in parts
        ):
            return AvailabilityClause(
                "without" if absent else "with", fragment, match.start(), match.end()
            )
    return None


def played_matchup_pair(text: str) -> AvailabilityClause | None:
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
        rf"(?:\s+(?:both\s+)?{played})?(?=\s+(?:in|within|among|of|during|for|vs\.?|versus|against|at|on|this|last|since)\b|[?.!]|$)",
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
                AvailabilityClause("with", " and ".join(names), match.start(), match.end())
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
    season_list: list[str] | None = None,
) -> AvailabilityClause | None:
    """A qualified two-teammate condition and its complete source span."""
    from nbatools.commands._matchup_utils import (
        _joins_second_player,
        detect_player,
        detect_unresolved_availability_player,
    )
    from nbatools.commands._participation_observations import resolve_observed_name

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
        if mode == "without" and state == "played":
            return None
        # "without A and B playing" keeps WITHOUT's negative polarity;
        # PLAYING completes the participation clause, not a second condition.
        if mode != "without":
            mode = suffix_mode
        fragment = fragment[: suffix.start()]
    parts = [part.strip(" .") for part in fragment.split(" and ")]
    if len(parts) != 2:
        return None
    if _joins_second_player(text, m):
        return None
    if any(
        other is not m
        and (
            detect_player(other.group(2))
            or detect_unresolved_availability_player(
                other.group(), mode="with" if other.group(1) == "with" else "without"
            )
        )
        for other in matches
    ):
        # A separate named presence/absence clause cannot be erased by the pair.
        return None
    side = None
    names = []
    for part in parts:
        from nbatools.commands._parse_helpers import default_season_for_context

        seasons = season_list or (
            resolve_seasons(season, start_season, end_season)
            if season or (start_season and end_season)
            else [default_season_for_context(season_type)]
        )
        observed = resolve_observed_name(part, seasons, season_type)
        if observed.confidence != "none":
            if not observed.is_confident:
                return None
            # Exact listed identity is enough to read a condition, not to
            # prove play/absence/tenure. The consumer still qualifies both
            # predicates on every original candidate game and actual side.
            names.append(observed.resolved)
            continue
        name = detect_player(part) or resolve_teammate(
            part,
            team=team,
            player=player,
            season=season,
            start_season=start_season,
            end_season=end_season,
            season_type=season_type,
        )
        if side is None:
            side = _same_side_rows(team, player, season, start_season, end_season, season_type)
        if side is None:
            return None
        if not name or not _only_the_name(part, name) or select_player_rows(side, name).empty:
            return None
        names.append(name)
    if names[0] == names[1]:
        return None
    return AvailabilityClause(mode, " and ".join(names), m.start(), m.end())
