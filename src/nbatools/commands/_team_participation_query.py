"""Declare team-record participation meaning without changing other routes."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast

from nbatools.commands.entity_resolution import resolve_player

ROSTERED = re.compile(r"\bwhile (?:rostered|on (?:the|this) team)\b", re.I)
ANYWHERE = re.compile(r"\b(?:anywhere in (?:the )?game|on either team|for either team)\b", re.I)
OPPOSING = re.compile(
    r"\b(?:when (?:the )?opponent(?=\s+[\w .'’\-]+?\s+(?:plays?|played|playing)\b)"
    r"|(?:with|without) (?:the )?opponent)\b",
    re.I,
)
_PARTICIPATION_INTRO = re.compile(r"\b(without|w/o|with|w/)\s+", re.I)
_EXCLUSION = re.compile(
    r"\b(?:not|except|excluding|exclude|unless|never|neither|nor|other\s+than)\b", re.I
)
AppearanceScope = Literal["team", "opponent", "game"]
ParticipationScope = Literal["team", "opponent", "game", "rostered", "legacy"]


@dataclass(frozen=True)
class ParticipationPredicate:
    names: tuple[str, ...]
    played: bool

    @classmethod
    def from_reference(cls, reference: str, *, played: bool) -> "ParticipationPredicate":
        return cls(tuple(re.split(r"\s+and\s+", reference, flags=re.I)), played)


def participation_predicates(
    with_player: str | None, without_player: str | None
) -> tuple[ParticipationPredicate, ...]:
    return tuple(
        ParticipationPredicate.from_reference(name, played=played)
        for name, played in ((with_player, True), (without_player, False))
        if name
    )


@dataclass(frozen=True)
class TeamRecordParticipation:
    """Bind the team, season, actor conditions and the requested record sample."""

    team: str
    season: str | None
    season_type: str
    scope: ParticipationScope
    predicates: tuple[ParticipationPredicate, ...]
    last_n: int | None
    last_n_scope: str | None
    wins_only: bool
    losses_only: bool

    @classmethod
    def from_record(cls, kwargs: Mapping[str, Any]) -> "TeamRecordParticipation":
        scope = participation_scope_for(kwargs)
        if scope not in {"team", "opponent", "game", "rostered", "legacy"}:
            raise ValueError("Unknown participation scope")
        return cls(
            team=kwargs["team"],
            season=kwargs.get("season"),
            season_type=kwargs.get("season_type", "Regular Season"),
            scope=scope,
            predicates=participation_predicates(
                kwargs.get("with_player"), kwargs.get("without_player")
            ),
            last_n=kwargs.get("last_n"),
            last_n_scope=kwargs.get("last_n_scope", "qualifying"),
            wins_only=kwargs.get("wins_only", False),
            losses_only=kwargs.get("losses_only", False),
        )

    @property
    def appearance_scope(self) -> AppearanceScope | None:
        if self.scope in {"team", "opponent", "game"}:
            return cast(AppearanceScope, self.scope)
        return None


def _scalar_role_clause(query, kwargs, scope):
    """Bind a global role only to one completely consumed actor/polarity span.

    Different actor roles need separate predicates; one global scope cannot
    represent them. Numeric team-stat clauses remain the existing parser's.
    """
    from nbatools.commands._matchup_utils import (
        _is_exact_player_reference_phrase,
        _stat_count_phrase,
        _tail_is_read_scope,
    )

    predicates = participation_predicates(kwargs.get("with_player"), kwargs.get("without_player"))
    if len(predicates) != 1 or len(predicates[0].names) != 1:
        return False
    (name,) = predicates[0].names
    if re.search(r"\band\b|[,;&]", name, re.I):
        return False
    mode = "with" if predicates[0].played else "without"
    text = query.lower()
    if scope == "opponent":
        if ANYWHERE.search(text) or ROSTERED.search(text):
            return False
        pattern = (
            r"\b(?P<intro>when|with|without)\s+(?:the\s+)?opponent\s+"
            r"(?P<name>[\w .'’\-]+?)(?:\s+(?P<state>plays?|played|playing))?"
            r"(?=\s+(?:in|on|at|vs\.?|versus|against|this|last|from|since|for|and|with|without|when|while)\b|[?!.]|$)"
        )
        matches = list(re.finditer(pattern, text))
        if len(matches) != 1:
            return False
        clause = matches[0]
        if clause["intro"] == "when" and clause["state"] is None:
            return False
        declared = "without" if clause["intro"] == "without" else "with"
        fragment = clause["name"]
        start, end = clause.span()
    else:
        markers = list(ANYWHERE.finditer(text))
        if len(markers) != 1 or OPPOSING.search(text) or ROSTERED.search(text):
            return False
        marker = markers[0]
        introductions = list(re.finditer(r"\b(with|without)\s+", text[: marker.start()]))
        if not introductions:
            return False
        intro = introductions[-1]
        declared = intro[1]
        fragment = text[intro.end() : marker.start()].strip()
        start, end = intro.start(), marker.end()
    if (
        declared != mode
        or not _is_exact_player_reference_phrase(fragment, name)
        or not _tail_is_read_scope(text, end)
    ):
        return False
    # A second actor, including the SAME name with a separate polarity or role,
    # cannot disappear behind a scalar role declaration. Only fully consumed
    # primary numeric-stat clauses may remain alongside ordinary scope.
    remaining = text[:start] + " " * (end - start) + text[end:]
    if _EXCLUSION.search(remaining):
        return False  # Negation/exclusion of the role is not a parsed operator.
    for marker in re.finditer(r"\b(with|without|when|while|if)\s+", remaining):
        if marker[1] not in {"with", "when"}:
            return False
        pos = marker.end()
        verb = re.match(r"(?:scoring|allowing|making|having)\s+", remaining[pos:])
        if verb:
            pos += verb.end()
        count = _stat_count_phrase(remaining, pos)
        if count is None or not _tail_is_read_scope(remaining, count.end()):
            return False
    return True


def participation_scope_for(kwargs):
    """Retain the accepted explicit-matchup pair; scalar defaults are TEAM."""
    if kwargs.get("participation_scope"):
        return kwargs["participation_scope"]
    if (
        kwargs.get("opponent")
        and kwargs.get("with_player")
        and not kwargs.get("without_player")
        and len(re.split(r"\s+and\s+", kwargs["with_player"], flags=re.I)) == 2
    ):
        return "legacy"
    return "team"


def clean_scope_words(query):
    if not re.search(r"\brecord\b", query, re.I):
        return query
    return ANYWHERE.sub("", ROSTERED.sub("", query))


def contextual_team_actor(reference, kwargs, scope) -> str | None:
    """Resolve a whole single-token reference only in the selected TEAM scope."""
    if (
        scope != "team"
        or not isinstance(reference, str)
        or not reference.replace("'", "").replace("-", "").isalpha()
        or not isinstance(kwargs.get("team"), str)
        or not isinstance(kwargs.get("season"), str)
        or kwargs.get("start_season")
        or kwargs.get("end_season")
    ):
        return None
    from nbatools.commands._team_appearances import resolve_complete_team_actor

    return resolve_complete_team_actor(
        reference, kwargs["team"], kwargs["season"], kwargs.get("season_type", "Regular Season")
    )


def _bind_condition(parsed, mode, name):
    kwargs = parsed["route_kwargs"]
    kwargs[mode + "_player"] = name
    kwargs.pop("unsupported_filters", None)
    kwargs.pop("unresolved_availability_player", None)
    parsed["notes"] = [
        n for n in parsed.get("notes", []) if not n.startswith("unsupported_boundary:")
    ]


def _bind_contextual_condition(query, parsed, scope):
    from nbatools.commands._constants import normalize_text
    from nbatools.commands._matchup_utils import _tail_is_read_scope

    kwargs = parsed["route_kwargs"]
    reference = kwargs.get("unresolved_availability_player")
    if not reference or kwargs.get("with_player") or kwargs.get("without_player"):
        return
    text = normalize_text(query)
    intros = list(_PARTICIPATION_INTRO.finditer(text))
    if len(intros) != 1 or _EXCLUSION.search(text):
        return
    (intro,) = intros
    actor = re.compile(rf"{re.escape(reference)}(?![\w.'\-])").match(text, intro.end())
    if actor is None or not _tail_is_read_scope(text, actor.end()):
        return
    name = contextual_team_actor(reference, kwargs, scope)
    if not name:
        return
    ambiguity = parsed.get("entity_ambiguity")
    if ambiguity and (ambiguity.get("type") != "player" or name not in ambiguity["candidates"]):
        return
    mode = "without" if intro[1] in {"without", "w/o"} else "with"
    _bind_condition(parsed, mode, name)
    if ambiguity:
        parsed["entity_ambiguity"] = None


def apply_team_participation_scope(query, parsed):
    if parsed.get("route") != "team_record":
        return parsed
    kwargs = parsed["route_kwargs"]
    blocked = set(kwargs.get("unsupported_filters") or [])
    if kwargs.get("without_player_reason") or blocked.intersection(
        {"availability_status", "on_court_presence", "teammate_stat_condition"}
    ):
        kwargs["participation_scope"] = "legacy"
        return parsed
    scope = (
        "rostered"
        if ROSTERED.search(query)
        else "game"
        if ANYWHERE.search(query)
        else "opponent"
        if OPPOSING.search(query)
        else participation_scope_for(kwargs)
    )
    conflicting_roles = (
        sum(bool(pattern.search(query)) for pattern in (ROSTERED, ANYWHERE, OPPOSING)) > 1
    )
    if (
        conflicting_roles
        or scope in {"opponent", "game"}
        and not _scalar_role_clause(query, kwargs, scope)
    ):
        # Preserve the entire request and prior blockers; never retarget its
        # retained actor or reduce a mixed-role request to one condition.
        kwargs["unsupported_filters"] = sorted(blocked | {"mixed_participation_roles"})
        return parsed
    if scope != "legacy" and re.search(r"\bunless\b", query, re.I):
        kwargs["unsupported_filters"] = sorted(blocked | {"unread_participation_clause"})
        kwargs["participation_scope"] = scope
        return parsed
    # Colloquial OUT/DNP/sits retains the accepted rostered interpretation.
    if (
        not re.search(r"\b(?:without|w/o)\b", query, re.I)
        and kwargs.get("without_player")
        and scope == "team"
    ):
        scope = "legacy"
    allowed = {
        "unresolved_player_availability",
        "multi_player_availability",
        "with_player",
        "without_player",
        "unresolved_with_player",
        "unresolved_without_player",
    }
    simple_clause = len(re.findall(r"\b(?:with|without)\b", clean_scope_words(query), re.I)) == 1
    unread_timing = re.search(
        r"\b(?:quarter|half|minutes|during|first|last|consecutive|before|after)\b",
        clean_scope_words(query),
        re.I,
    )
    if blocked and blocked <= allowed and simple_clause and not unread_timing and scope != "legacy":
        # Resolve whole names globally, not through a presumed team roster.
        # Every name must resolve; never clear a boundary after a partial read.
        from nbatools.commands._teammate_resolution import _only_the_name, name_before_scope

        match = re.search(r"\b(without|with)\s+(.+)", clean_scope_words(query), re.I)
        if match:
            fragment = name_before_scope(match[2].lower())
            parts = re.split(r"\s+and\s+", fragment)
            resolutions = [resolve_player(name) for name in parts]
            resolved = [r.resolved for r in resolutions]
            if 1 <= len(parts) <= 2 and all(
                name
                and result.source in {"full_name", "full_name_alias"}
                and _only_the_name(part, name)
                for part, name, result in zip(parts, resolved, resolutions)
            ):
                _bind_condition(parsed, match[1].lower(), " and ".join(resolved))
    if kwargs.get("unsupported_filters") == ["unresolved_player_availability"]:
        _bind_contextual_condition(query, parsed, scope)
    if kwargs.get("with_player") or kwargs.get("without_player"):
        kwargs["participation_scope"] = scope
    return parsed
