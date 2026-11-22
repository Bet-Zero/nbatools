"""Declare team-record participation meaning without changing other routes."""

import re

from nbatools.commands.entity_resolution import resolve_player

ROSTERED = re.compile(r"\bwhile (?:rostered|on (?:the|this) team)\b", re.I)
ANYWHERE = re.compile(r"\b(?:anywhere in (?:the )?game|on either team|for either team)\b", re.I)
OPPOSING = re.compile(r"\b(?:when (?:the )?opponent|(?:with|without) (?:the )?opponent)\b", re.I)


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
    if scope != "legacy" and re.search(r"\bunless\b", query, re.I):
        kwargs["unsupported_filters"] = sorted(blocked | {"unread_participation_clause"})
        kwargs["participation_scope"] = scope
        return parsed
    # Colloquial OUT/DNP/sits retains the accepted rostered interpretation.
    if (
        not re.search(r"\bwithout\b", query, re.I)
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
            resolved = [resolve_player(name).resolved for name in parts]
            if 1 <= len(parts) <= 2 and all(
                name and _only_the_name(part, name) for part, name in zip(parts, resolved)
            ):
                kwargs[match[1].lower() + "_player"] = " and ".join(resolved)
                kwargs.pop("unsupported_filters", None)
                kwargs.pop("unresolved_availability_player", None)
                parsed["notes"] = [
                    n for n in parsed.get("notes", []) if not n.startswith("unsupported_boundary:")
                ]
    if kwargs.get("with_player") or kwargs.get("without_player"):
        kwargs["participation_scope"] = scope
    return parsed
