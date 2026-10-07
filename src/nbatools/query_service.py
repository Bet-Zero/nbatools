"""Query service / engine facade for nbatools.

This module is the primary entry point for executing NBA queries
programmatically.  Both natural-language and structured (route-based)
queries are supported and return structured result objects directly.

The web UI, HTTP API, and library callers use these functions instead of
going through CLI wrappers.

Entry points
------------
``execute_natural_query(query)``
    Parse a natural-language query string, route it, execute the
    matching command, and return a structured result object.

``execute_structured_query(route, **kwargs)``
    Execute a named route directly with explicit keyword arguments
    and return a structured result object.

Both return one of the typed result classes defined in
``nbatools.commands.structured_results`` (``SummaryResult``,
``ComparisonResult``, ``FinderResult``, ``LeaderboardResult``,
``StreakResult``, ``SplitSummaryResult``, ``CountResult``, ``NoResult``).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from nbatools.commands._compound_event_authorization import (
    is_compound_event_refusal,
    publishes_condition_metric_as_stat,
    ranking_key,
)
from nbatools.commands._condition_utils import normalize_stat_conditions
from nbatools.commands._constants import contains_boolean_or
from nbatools.commands._leaderboard_eligibility import is_boundary_refusal
from nbatools.commands._natural_query_execution import (
    _execute_build_result,
    _execute_grouped_boolean_build_result,
    _execute_or_query_build_result,
    _extract_grouped_condition_text,
    _unsupported_filter_note,
)
from nbatools.commands._player_identity import select_player_rows
from nbatools.commands.entity_resolution import ALL_TEAM_ABBRS, resolve_team
from nbatools.commands.format_output import route_to_query_class
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.natural_query import (
    _build_parse_state,
    normalize_text,
    parse_query,
)
from nbatools.commands.query_boolean_parser import (
    boolean_filter_mode,
    expression_contains_boolean_ops,
)

# Re-export result types so callers can import everything from one place.
from nbatools.commands.structured_results import (  # noqa: F401
    ComparisonResult,
    CountResult,
    FinderResult,
    LeaderboardResult,
    NoResult,
    ResultReason,
    ResultStatus,
    SplitSummaryResult,
    StreakResult,
    SummaryResult,
)
from nbatools.data_source import (
    data_generation_context,
    data_glob,
    data_read_csv_dicts,
    data_source_cache_key,
)

_COUNT_THRESHOLD_EPSILON = 0.0001


def _is_trusted_empty_count_result(result: Any) -> bool:
    """Return whether a negative result proves a fully evaluated empty sample."""
    if (
        getattr(result, "result_status", None) != ResultStatus.NO_RESULT
        or getattr(result, "result_reason", None) != ResultReason.NO_MATCH
    ):
        return False
    if isinstance(result, FinderResult):
        return result.games.empty
    if isinstance(result, LeaderboardResult):
        return result.leaders.empty
    if isinstance(result, CountResult):
        return result.count == 0 and result.games.empty
    return isinstance(result, NoResult)


def _count_no_result(result: Any) -> NoResult:
    """Preserve a negative result while exposing the requested count class."""
    reason = getattr(result, "result_reason", None)
    status = getattr(result, "result_status", ResultStatus.NO_RESULT)
    if reason is None:
        reason = ResultReason.ERROR if status == ResultStatus.ERROR else ResultReason.UNSUPPORTED
    return NoResult(
        query_class="count",
        reason=str(reason),
        result_status=str(status),
        result_reason=str(reason),
        current_through=getattr(result, "current_through", None),
        metadata=dict(getattr(result, "metadata", {})),
        notes=list(getattr(result, "notes", [])),
        caveats=list(getattr(result, "caveats", [])),
    )


# ---------------------------------------------------------------------------
# Metadata helper
# ---------------------------------------------------------------------------


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _identity_key(value: Any) -> str:
    text = _clean_text(value) or ""
    normalized = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(stripped.lower().split())


def _coerce_int(value: Any) -> int | None:
    text = _clean_text(value)
    if text is None or not text.isdigit():
        return None
    number = int(text)
    return number if number > 0 else None


def _read_csv_dicts(path: Path) -> list[dict[str, str]]:
    return data_read_csv_dicts(path)


@lru_cache(maxsize=1)
def _player_identity_lookup(generation_key: str) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for csv_path in data_glob("raw/rosters/*.csv"):
        for row in _read_csv_dicts(csv_path):
            player_id = _coerce_int(row.get("player_id"))
            player_name = _clean_text(row.get("player_name"))
            if player_id is None or player_name is None:
                continue
            lookup[_identity_key(player_name)] = {
                "player_id": player_id,
                "player_name": player_name,
            }
    return lookup


@lru_cache(maxsize=1)
def _team_identity_lookup(generation_key: str) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}

    def add_row(row: dict[str, Any]) -> None:
        team_id = _coerce_int(row.get("team_id"))
        team_abbr = _clean_text(row.get("team_abbr"))
        team_name = _clean_text(row.get("team_name"))
        if team_id is None or team_abbr is None or team_name is None:
            return

        context = {
            "team_id": team_id,
            "team_abbr": team_abbr.upper(),
            "team_name": team_name,
        }
        labels = [
            team_abbr,
            team_name,
            row.get("city"),
            row.get("franchise_label"),
        ]
        city = _clean_text(row.get("city"))
        if city:
            labels.append(f"{city} {team_name}")

        for label in labels:
            key = _identity_key(label)
            if key:
                lookup[key] = context

    history_path = "data/raw/teams/team_history_reference.csv"
    for row in _read_csv_dicts(history_path):
        add_row(row)

    teams_path = "data/raw/teams/teams_reference.csv"
    for row in _read_csv_dicts(teams_path):
        add_row(row)

    return lookup


def _resolve_player_context(player_name: Any) -> dict[str, Any] | None:
    key = _identity_key(player_name)
    if not key:
        return None
    generation_key = data_source_cache_key()
    context = _player_identity_lookup(generation_key).get(key)
    if context is None:
        _player_identity_lookup.cache_clear()
        context = _player_identity_lookup(generation_key).get(key)
    return dict(context) if context else None


def _resolve_team_context(team_value: Any) -> dict[str, Any] | None:
    text = _clean_text(team_value)
    if text is None:
        return None

    generation_key = data_source_cache_key()
    lookup = _team_identity_lookup(generation_key)
    resolved = resolve_team(text)
    candidates: list[str] = []
    if resolved.is_confident and resolved.resolved:
        candidates.append(resolved.resolved)
    candidates.append(text)

    for candidate in candidates:
        context = lookup.get(_identity_key(candidate))
        if context:
            return dict(context)
    _team_identity_lookup.cache_clear()
    lookup = _team_identity_lookup(generation_key)
    for candidate in candidates:
        context = lookup.get(_identity_key(candidate))
        if context:
            return dict(context)
    if resolved.is_confident and resolved.resolved in ALL_TEAM_ABBRS:
        return {"team_abbr": resolved.resolved}
    return None


def _dedupe_contexts(contexts: list[dict[str, Any]], id_key: str) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[Any] = set()
    for context in contexts:
        identity = context.get(id_key)
        if identity in seen:
            continue
        seen.add(identity)
        deduped.append(context)
    return deduped


def _add_identity_contexts(
    meta: dict[str, Any],
    *,
    player_values: list[Any],
    team_values: list[Any],
    opponent_value: Any,
) -> None:
    player_contexts = _dedupe_contexts(
        [
            context
            for value in player_values
            if (context := _resolve_player_context(value)) is not None
        ],
        "player_id",
    )
    if len(player_contexts) == 1:
        meta["player_context"] = player_contexts[0]
    elif len(player_contexts) > 1:
        meta["players_context"] = player_contexts

    team_contexts = _dedupe_contexts(
        [context for value in team_values if (context := _resolve_team_context(value)) is not None],
        "team_id",
    )
    if len(team_contexts) == 1:
        meta["team_context"] = team_contexts[0]
    elif len(team_contexts) > 1:
        meta["teams_context"] = team_contexts

    opponent_context = _resolve_team_context(opponent_value)
    if opponent_context is not None:
        meta["opponent_context"] = opponent_context


def _opponent_quality_surface_term(value: Any) -> str | None:
    if isinstance(value, dict):
        return _clean_text(value.get("surface_term"))
    return _clean_text(value)


def _special_event_filter_label(value: Any) -> str | None:
    text = _clean_text(value)
    if not text:
        return None

    labels = {
        "triple_double": "Triple Double",
        "double_double": "Double Double",
    }
    return labels.get(text, text.replace("_", " ").title())


def _threshold_filter_value(value: int | float, *, minimum: bool) -> str:
    phrase = _minimum_threshold_phrase(value) if minimum else _maximum_threshold_phrase(value)
    strict_prefix = "over " if minimum else "under "
    if phrase.startswith(strict_prefix):
        return f"{phrase.removeprefix(strict_prefix)} (exclusive)"
    return str(value)


def _build_applied_filters(
    source: dict[str, Any],
    *,
    route_kwargs: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    route_kwargs = route_kwargs or {}
    applied_filters: list[dict[str, str]] = []

    opponent_conference = source.get("opponent_conference") or route_kwargs.get(
        "opponent_conference"
    )
    if opponent_conference:
        applied_filters.append(
            {
                "label": "Opponent conference",
                "value": str(opponent_conference),
                "kind": "conference",
            }
        )
    opponent_division = source.get("opponent_division") or route_kwargs.get("opponent_division")
    if opponent_division:
        applied_filters.append(
            {
                "label": "Opponent division",
                "value": str(opponent_division),
                "kind": "division",
            }
        )
    if source.get("opponent"):
        applied_filters.append({"label": "Opponent", "value": source["opponent"], "kind": "team"})
    if source.get("without_player"):
        applied_filters.append(
            {"label": "Without player", "value": source["without_player"], "kind": "player"}
        )
    if source.get("with_player"):
        applied_filters.append(
            {"label": "With player", "value": source["with_player"], "kind": "player"}
        )
    if source.get("home_only"):
        applied_filters.append({"label": "Location", "value": "Home", "kind": "location"})
    if source.get("away_only"):
        applied_filters.append({"label": "Location", "value": "Away", "kind": "location"})
    if source.get("wins_only"):
        applied_filters.append({"label": "Outcome", "value": "Wins", "kind": "outcome"})
    if source.get("losses_only"):
        applied_filters.append({"label": "Outcome", "value": "Losses", "kind": "outcome"})
    if source.get("clutch"):
        applied_filters.append({"label": "Clutch", "value": "True", "kind": "situation"})
    if source.get("series_situation"):
        from nbatools.commands.playoff_history import series_situation_label

        applied_filters.append(
            {
                "label": "Series situation",
                "value": series_situation_label(source["series_situation"]),
                "kind": "situation",
            }
        )
    if source.get("back_to_back"):
        applied_filters.append({"label": "Back-to-back", "value": "True", "kind": "schedule"})
    if source.get("rest_days") is not None:
        applied_filters.append(
            {"label": "Rest days", "value": str(source["rest_days"]), "kind": "schedule"}
        )
    if source.get("one_possession"):
        applied_filters.append(
            {"label": "One-possession game", "value": "True", "kind": "situation"}
        )
    if source.get("nationally_televised"):
        applied_filters.append(
            {"label": "Nationally televised", "value": "True", "kind": "schedule"}
        )
    if source.get("role"):
        applied_filters.append({"label": "Role", "value": source["role"], "kind": "role"})
    if source.get("quarter") is not None:
        applied_filters.append(
            {"label": "Quarter", "value": str(source["quarter"]), "kind": "period"}
        )
    if source.get("half") is not None:
        applied_filters.append({"label": "Half", "value": str(source["half"]), "kind": "period"})
    if source.get("position_filter"):
        applied_filters.append(
            {"label": "Position", "value": source["position_filter"], "kind": "position"}
        )
    opponent_quality_value = _opponent_quality_surface_term(source.get("opponent_quality"))
    if opponent_quality_value:
        applied_filters.append(
            {
                "label": "Opponent quality",
                "value": opponent_quality_value,
                "kind": "quality",
            }
        )

    occurrence_event = source.get("occurrence_event")
    special_event = None
    if isinstance(occurrence_event, dict):
        special_event = occurrence_event.get("special_event")
    special_event = (
        special_event or source.get("special_event") or route_kwargs.get("special_event")
    )
    special_event_label = _special_event_filter_label(special_event)
    if special_event_label:
        applied_filters.append(
            {
                "label": "Special Event",
                "value": special_event_label,
                "kind": "special_event",
            }
        )

    conditions = normalize_stat_conditions(
        route_kwargs.get("conditions") or source.get("conditions")
    )
    if conditions:
        for cond in conditions:
            stat = cond["stat"]
            if cond.get("min_value") is not None:
                label = f"{_filter_stat_label(stat)} min"
                applied_filters.append(
                    {
                        "label": label,
                        "value": _threshold_filter_value(cond["min_value"], minimum=True),
                        "kind": "threshold",
                    }
                )
            if cond.get("max_value") is not None:
                label = f"{_filter_stat_label(stat)} max"
                applied_filters.append(
                    {
                        "label": label,
                        "value": _threshold_filter_value(cond["max_value"], minimum=False),
                        "kind": "threshold",
                    }
                )
    else:
        stat = source.get("stat") or route_kwargs.get("stat")
        min_value = (
            source.get("min_value")
            if source.get("min_value") is not None
            else route_kwargs.get("min_value")
        )
        max_value = (
            source.get("max_value")
            if source.get("max_value") is not None
            else route_kwargs.get("max_value")
        )
        if stat and min_value is not None:
            label = f"{_filter_stat_label(stat)} min"
            applied_filters.append(
                {
                    "label": label,
                    "value": _threshold_filter_value(min_value, minimum=True),
                    "kind": "threshold",
                }
            )
        if stat and max_value is not None:
            label = f"{_filter_stat_label(stat)} max"
            applied_filters.append(
                {
                    "label": label,
                    "value": _threshold_filter_value(max_value, minimum=False),
                    "kind": "threshold",
                }
            )
    if source.get("start_season") and source.get("end_season"):
        applied_filters.append(
            {
                "label": "Season range",
                "value": f"{source['start_season']} – {source['end_season']}",
                "kind": "season",
            }
        )
    elif source.get("explicit_relative_season") and source.get("season"):
        applied_filters.append(
            {
                "label": "Season",
                "value": str(source["season"]),
                "kind": "season",
            }
        )
    if source.get("start_date") or source.get("end_date"):
        date_value = " – ".join(filter(None, [source.get("start_date"), source.get("end_date")]))
        applied_filters.append({"label": "Date range", "value": date_value, "kind": "date"})

    last_n = source.get("last_n")
    if last_n is None:
        last_n = route_kwargs.get("last_n")
    if last_n is not None:
        applied_filters.append({"label": "Last N games", "value": str(last_n), "kind": "window"})

    return applied_filters


def _build_query_metadata(
    parsed: dict,
    query: str,
    grouped_boolean_used: bool = False,
) -> dict[str, Any]:
    """Build metadata dict from a parsed query state.

    Decoupled from CLI-specific concerns.
    """
    if not parsed:
        return {"query_text": query}

    route = parsed.get("route")
    query_class = route_to_query_class(route)

    player_a = parsed.get("player_a")
    player_b = parsed.get("player_b")
    player = parsed.get("player")
    if not player:
        if player_a and player_b:
            player = f"{player_a}, {player_b}"
        else:
            player = player_a or player_b

    team_a = parsed.get("team_a")
    team_b = parsed.get("team_b")
    team = parsed.get("team")
    if not team:
        if team_a and team_b:
            team = f"{team_a}, {team_b}"
        else:
            team = team_a or team_b

    route_kwargs = parsed.get("route_kwargs")
    if not isinstance(route_kwargs, dict):
        route_kwargs = {}
    if isinstance(route_kwargs.get("team"), list):
        # "Lakers and Celtics leading scorers" ranks both teams.
        team = ", ".join(route_kwargs["team"])
    unsupported_filters = parsed.get("unsupported_filters") or route_kwargs.get(
        "unsupported_filters"
    )

    notes = parsed.get("notes") or []

    # current_through from season info
    current_through: str | None = None
    season = parsed.get("season")
    start_season = parsed.get("start_season")
    end_season = parsed.get("end_season")
    season_type = parsed.get("season_type") or "Regular Season"

    if season:
        current_through = compute_current_through_for_seasons([season], season_type)
    elif start_season and end_season:
        from nbatools.commands._seasons import int_to_season, season_to_int

        seasons = [
            int_to_season(y)
            for y in range(season_to_int(start_season), season_to_int(end_season) + 1)
        ]
        current_through = compute_current_through_for_seasons(seasons, season_type)

    meta: dict[str, Any] = {
        "query_text": query,
        "route": route,
        "query_class": query_class,
        "season": season,
        "start_season": start_season,
        "end_season": end_season,
        "explicit_relative_season": parsed.get("explicit_relative_season"),
        "season_type": parsed.get("season_type"),
        "start_date": parsed.get("start_date"),
        "end_date": parsed.get("end_date"),
        "player": player,
        "team": team,
        "opponent": parsed.get("opponent"),
        "opponent_conference": parsed.get("opponent_conference")
        or route_kwargs.get("opponent_conference"),
        "opponent_division": parsed.get("opponent_division")
        or route_kwargs.get("opponent_division"),
        "opponent_team_abbrs": route_kwargs.get("opponent_team_abbrs"),
        "with_player": parsed.get("with_player") or route_kwargs.get("with_player"),
        "without_player": parsed.get("without_player"),
        "unresolved_availability_player": route_kwargs.get("unresolved_availability_player"),
        "unsupported_filters": unsupported_filters,
        "opponent_quality": parsed.get("opponent_quality"),
        "lineup_members": parsed.get("lineup_members"),
        "presence_state": parsed.get("presence_state"),
        "unit_size": parsed.get("unit_size"),
        "minute_minimum": parsed.get("minute_minimum"),
        "window_size": parsed.get("window_size"),
        "stretch_metric": parsed.get("stretch_metric"),
        "stretch_display_mode": _stretch_display_mode_metadata(
            route,
            player=player,
            dedupe_players=route_kwargs.get("dedupe_players"),
        ),
        "min_streak_length": route_kwargs.get("min_streak_length"),
        # A refused ranking executed nothing, so it publishes no metric. The
        # parser's own `stat` is a detector reading, and presenting it here as
        # the answer metric is how a refusal came to look like a partial
        # answer. What was asked for is published separately, below.
        "stat": (
            None
            if (
                is_boundary_refusal(route_kwargs)
                or is_compound_event_refusal(route_kwargs)
                or publishes_condition_metric_as_stat(route, route_kwargs)
            )
            else parsed.get("stat") or route_kwargs.get("stat")
        ),
        # What the rows are ordered by, said outright. A compound occurrence
        # route ranks by a count of matching games, and reading its ranking off
        # a stat field that names one of the counted conditions is how a
        # threshold came to look like the answer's metric.
        "ranking_key": ranking_key(route, route_kwargs),
        "requested_stat": route_kwargs.get("requested_stat"),
        "requested_metrics": route_kwargs.get("requested_metrics"),
        # What a compound/event refusal was about: the conditions it stated, the
        # availability it asked for. Published as *requested*, never as applied.
        "requested_event_conditions": route_kwargs.get("requested_event_conditions"),
        "unsupported_availability": route_kwargs.get("unsupported_availability"),
        "unsupported_scope": route_kwargs.get("unsupported_scope"),
        "requested_aggregation": route_kwargs.get("requested_aggregation"),
        "available_aggregation": route_kwargs.get("available_aggregation"),
        "min_value": (
            parsed.get("min_value")
            if parsed.get("min_value") is not None
            else route_kwargs.get("min_value")
        ),
        "max_value": (
            parsed.get("max_value")
            if parsed.get("max_value") is not None
            else route_kwargs.get("max_value")
        ),
        "sort_by": parsed.get("sort_by") or route_kwargs.get("sort_by"),
        "ascending": route_kwargs.get("ascending"),
        "ranked_intent": bool(
            parsed.get("leaderboard_intent")
            or parsed.get("season_high_intent")
            or parsed.get("top_n")
        ),
        "threshold_conditions": normalize_stat_conditions(parsed.get("threshold_conditions")),
        "extra_conditions": parsed.get("extra_conditions"),
        "conditions": route_kwargs.get("conditions") or parsed.get("conditions"),
        "occurrence_event": parsed.get("occurrence_event"),
        "split_type": parsed.get("split_type"),
        "clutch": parsed.get("clutch"),
        "back_to_back": parsed.get("back_to_back"),
        "series_situation": parsed.get("series_situation"),
        "rest_days": parsed.get("rest_days"),
        "one_possession": parsed.get("one_possession"),
        "nationally_televised": parsed.get("nationally_televised"),
        "role": parsed.get("role"),
        "quarter": parsed.get("quarter"),
        "half": parsed.get("half"),
        "position_filter": parsed.get("position_filter"),
        "grouped_boolean_used": grouped_boolean_used,
        "boolean_filter_mode": parsed.get("boolean_filter_mode"),
        "head_to_head_used": bool(parsed.get("head_to_head")),
    }

    if current_through is not None:
        meta["current_through"] = current_through

    if route_kwargs.get("ambiguous_intent"):
        meta["ambiguous_intent"] = route_kwargs["ambiguous_intent"]
    if route_kwargs.get("clarification_options"):
        meta["clarification_options"] = route_kwargs["clarification_options"]

    if notes:
        meta["notes"] = notes

    # ---- Pattern 1: scope_kind — how many seasons / career context ----
    career_intent = parsed.get("career_intent", False)
    by_decade_intent = parsed.get("by_decade_intent", False)
    if career_intent:
        # career = player-specific arc; all_time = cross-entity (no specific player)
        scope_kind = "career" if parsed.get("player") else "all_time"
    elif by_decade_intent:
        scope_kind = "decade"
    elif start_season and end_season:
        scope_kind = "season_range"
    elif season:
        scope_kind = "playoffs" if season_type == "Playoffs" else "single_season"
    else:
        scope_kind = "single_season"
    meta["scope_kind"] = scope_kind

    # ---- Pattern 2: applied_filters — structured list of active filters ----
    applied_filters = (
        [] if unsupported_filters else _build_applied_filters(parsed, route_kwargs=route_kwargs)
    )
    if applied_filters:
        meta["applied_filters"] = applied_filters

    player_values = [value for value in [player_a, player_b] if value]
    if not player_values and player:
        player_values = [player]
    team_values = [value for value in [team_a, team_b] if value]
    if not team_values and team:
        team_values = [team]
    _add_identity_contexts(
        meta,
        player_values=player_values,
        team_values=team_values,
        opponent_value=parsed.get("opponent"),
    )

    # Phase D fields: confidence, intent, alternates
    if parsed.get("confidence") is not None:
        meta["confidence"] = parsed["confidence"]
    if parsed.get("intent") is not None:
        meta["intent"] = parsed["intent"]
    alternates = parsed.get("alternates")
    if alternates:
        meta["alternates"] = alternates

    # Day-window queries ("yesterday", "this week") are anchored to the
    # data's latest day; say so whether the window matched games or not.
    if parsed.get("fuzzy_date_window") and meta.get("current_through"):
        existing = meta.get("notes") or []
        meta["notes"] = list(existing) + [
            f"data is current through {meta['current_through']}; day-based "
            f"windows like 'yesterday' or 'this week' are anchored to that "
            f"date, not today"
        ]

    return meta


def _stretch_display_mode_metadata(
    route: str | None,
    *,
    player: str | None,
    dedupe_players: Any,
) -> str | None:
    if route != "player_stretch_leaderboard":
        return None
    if player:
        return "named_player"
    return "players" if bool(dedupe_players) else "windows"


def _merge_metadata_notes(metadata: dict[str, Any], result_notes: list[str]) -> None:
    """Merge parse-time and execution-time notes without duplicating text."""
    if not result_notes:
        return
    merged = list(metadata.get("notes") or [])
    for note in result_notes:
        if note not in merged:
            merged.append(note)
    if merged:
        metadata["notes"] = merged


# Stats whose per-game values can be meaningfully summed into a season
# total for "how many <stat> did <player> ..." asks. Percentage and rating
# stats must never be summed.
_SUMMABLE_COUNT_STATS = {
    "pts",
    "reb",
    "ast",
    "stl",
    "blk",
    "fg3m",
    "tov",
    "fgm",
    "ftm",
    "oreb",
    "dreb",
}


def _stat_total_count(parsed: dict, games: Any) -> int | None:
    """Total of a stat across matched games for bare-stat count asks.

    "how many threes did curry hit" asks for the number of threes, not the
    number of games. Fires only for a bare summable stat with no
    thresholds, no occurrence event, and no explicit "games" wording —
    "how many 30 point games" keeps counting games.
    """
    stat = parsed.get("stat")
    if not isinstance(stat, str) or stat not in _SUMMABLE_COUNT_STATS:
        return None
    if parsed.get("min_value") is not None or parsed.get("max_value") is not None:
        return None
    if parsed.get("occurrence_event") or parsed.get("conditions"):
        return None
    query_text = parsed.get("normalized_query") or ""
    if re.search(r"\bgames?\b", query_text):
        return None
    if games is None or not hasattr(games, "columns") or stat not in games.columns:
        return None
    return int(games[stat].sum())


def _margin_text(kwargs: dict) -> str:
    """ " by 20+ points", " by exactly 1 point", " by 3 to 5 points"."""
    low, high = kwargs.get("min_value"), kwargs.get("max_value")

    def points(value: Any) -> str:
        return f"{_count_threshold_text(value)} point{'' if value == 1 else 's'}"

    if low is not None and high is not None:
        if low == high:
            return f" by exactly {points(low)}"
        return f" by {_count_threshold_text(low)} to {points(high)}"
    if low is not None:
        return f" by {_count_threshold_text(low)}+ points"
    if high is not None:
        return f" by {points(high).replace(' point', ' or fewer point', 1)}"
    return ""


def _build_count_phrase(
    count: int,
    parsed: dict,
    metadata: dict,
    games: Any = None,
) -> str:
    """Build a natural-language count phrase for count-intent queries (Pattern 3).

    Example: "Nikola Jokić has had 47 triple-doubles in the 2023-24 regular season."
    """
    player = metadata.get("player")
    team = metadata.get("team")
    entity = player or _team_subject(metadata, games) or "Result"
    team_subject = bool(team and not player)

    if parsed.get("boolean_query_used"):
        game_word = "matching game" if count == 1 else "matching games"
        verb = "have had" if team_subject else "has had"
        context = _count_context(
            metadata,
            player=bool(player),
            last_n=parsed.get("last_n"),
            last_n_scope=parsed.get("last_n_scope"),
        )
        return f"{entity} {verb} {count} {game_word} {context}."

    if parsed.get("streak_count"):
        return _streak_count_phrase(count, parsed, metadata, games)

    outcome = parsed.get("route_kwargs") or {}
    if (
        (
            (team and not player and parsed.get("route") == "game_finder")
            or (player and parsed.get("route") == "player_game_finder")
        )
        and (outcome.get("wins_only") or outcome.get("losses_only"))
        and outcome.get("stat") in (None, "win_margin", "loss_margin")
        and not normalize_stat_conditions(outcome.get("conditions"))
        and not parsed.get("occurrence_event")
    ):
        # "how many times did the Lakers beat the Celtics": wins, not "games".
        verb = "won" if outcome.get("wins_only") else "lost"
        times = "game" if count == 1 else "games"
        opponent = outcome.get("opponent")
        against = ""
        if (
            isinstance(opponent, str)
            and opponent
            and games is not None
            and hasattr(games, "columns")
        ):
            names = games.get("opponent_team_name")
            label = names.mode().iloc[0] if names is not None and not names.empty else None
            context_name = (metadata.get("opponent_context") or {}).get("team_name")
            against = f" against the {label or context_name or opponent}"
        quality = outcome.get("opponent_quality")
        if not against and isinstance(quality, dict) and quality.get("surface_term"):
            against = f" against {quality['surface_term']}"
        context = _count_context(
            metadata,
            player=False,
            last_n=parsed.get("last_n"),
            last_n_scope=parsed.get("last_n_scope"),
        )
        subject = player or _team_subject(metadata, games) or "The team"
        have = "has" if player else "have"
        margin = _margin_text(outcome) if outcome.get("stat") else ""
        venue = " at home" if outcome.get("home_only") else ""
        venue = " on the road" if outcome.get("away_only") else venue
        return f"{subject} {have} {verb} {count} {times}{margin}{against}{venue} {context}."

    if metadata.get("stat") == "opponent_pts" and team:
        max_value = metadata.get("max_value")
        min_value = metadata.get("min_value")
        if max_value is None and min_value is not None:
            # "allow 110 or more points": a floor, not "held opponents under".
            # "over 119" is stored as 119.0001: say "more than 119".
            floor = _count_threshold_text(min_value)
            if float(min_value).is_integer():
                action = f"allowed {floor}+ points"
            else:
                action = f"allowed more than {floor} points"
        elif isinstance(max_value, (int, float)) and float(max_value).is_integer():
            # "held opponents to 100 or fewer" includes 100.
            action = f"held opponents to {_count_threshold_text(max_value)} or fewer points"
        else:
            action = f"held opponents under {_count_threshold_text(max_value)} points"
        entity = _team_subject(metadata, games)
        context = _count_context(
            metadata,
            player=bool(player),
            last_n=parsed.get("last_n"),
            last_n_scope=parsed.get("last_n_scope"),
        )
        times = "time" if count == 1 else "times"
        record = _record_suffix(games)
        return f"{entity} have {action} {count} {times} {context}{record}."

    # Stat totals read as the stat itself ("has made 247 threes"), not as
    # a count of games.
    if parsed.get("count_kind") == "stat_total":
        stat = parsed.get("stat") or ""
        stat_name = stat_phrase_label(stat)
        if count == 1 and stat_name.endswith("s"):
            stat_name = stat_name[:-1]
        singular_verb = {
            "fg3m": "has made",
            "fgm": "has made",
            "ftm": "has made",
            "pts": "has scored",
        }.get(stat, "has recorded")
        verb = singular_verb.replace("has ", "have ", 1) if team_subject else singular_verb
        context = _count_context(
            metadata,
            player=bool(player),
            last_n=parsed.get("last_n"),
            last_n_scope=parsed.get("last_n_scope"),
        )
        return f"{entity} {verb} {count} {stat_name} {context}."

    conditions = normalize_stat_conditions(
        metadata.get("conditions")
        or metadata.get("threshold_conditions")
        or parsed.get("conditions")
        or parsed.get("threshold_conditions")
    )
    if len(conditions) == 1:
        occurrence = _occurrence_label(conditions[0])
    elif len(conditions) >= 2:
        occurrence = _compound_occurrence_label(conditions)
    elif parsed.get("occurrence_event"):
        occurrence = _occurrence_label(parsed.get("occurrence_event"))
    elif parsed.get("min_value") is not None or parsed.get("max_value") is not None:
        # A thresholded stat ("5 assists") reads "games with 5+ assists", not
        # the bare stat name ("166 asts").
        occurrence = _occurrence_label(
            {
                "stat": parsed.get("stat"),
                "min_value": parsed.get("min_value"),
                "max_value": parsed.get("max_value"),
            }
        )
    else:
        occurrence = _occurrence_label(parsed.get("stat"))
    if parsed.get("distinct_player_count") and not player:
        # The count is players, not games: "18 players have had a game with 30+ points".
        context = _count_context(
            metadata,
            player=False,
            last_n=parsed.get("last_n"),
            last_n_scope=parsed.get("last_n_scope"),
        )
        min_occurrences = parsed.get("min_occurrences")
        if occurrence.startswith("games with ") and not (min_occurrences or 0) > 1:
            occurrence = "game with " + occurrence[len("games with ") :]
        subject = "1 player has" if count == 1 else f"{count} players have"
        if (min_occurrences or 0) > 1:
            # "16 players have had 20+ games with at most 10 points".
            article = f"{min_occurrences}+"
            if not occurrence.startswith("games"):
                occurrence = pluralize_occurrence(occurrence)
        else:
            article = "a"
        role = {"bench": " off the bench", "starter": " as a starter"}.get(
            metadata.get("role") or ""
        )
        opponent = ""
        if metadata.get("opponent_conference"):
            opponent = f" against the {metadata['opponent_conference']}"
        elif metadata.get("opponent_division"):
            opponent = f" against the {metadata['opponent_division']} Division"
        elif isinstance(metadata.get("opponent"), str) and metadata["opponent"]:
            opponent = f" against {metadata['opponent']}"
        return f"{subject} had {article} {occurrence}{role or ''}{opponent} {context}."
    count_noun = occurrence if count == 1 else pluralize_occurrence(occurrence)
    if count == 1 and count_noun.startswith("games with "):
        # "1 game with 30+ points", not "1 games".
        count_noun = "game with " + count_noun[len("games with ") :]
    context = _count_context(
        metadata,
        player=bool(player),
        last_n=parsed.get("last_n"),
        last_n_scope=parsed.get("last_n_scope"),
    )
    if count_noun.startswith(("games with ", "game with ")):
        verb = "have had" if team_subject else "has had"
    else:
        verb = "have recorded" if team_subject else "has recorded"
    return f"{entity} {verb} {count} {count_noun} {context}."


def _streak_count_phrase(count: int, parsed: dict, metadata: dict, streaks: Any) -> str:
    """ "The Boston Celtics have had 2 winning streaks of 10+ games ..."."""
    kwargs = parsed.get("route_kwargs") or {}
    special = kwargs.get("special_condition")
    bounds = normalize_stat_conditions(kwargs.get("conditions"))
    if kwargs.get("stat"):
        bounds = [
            {
                "stat": kwargs["stat"],
                "min_value": kwargs.get("min_value"),
                "max_value": kwargs.get("max_value"),
            },
            *bounds,
        ]
    games_with = ""
    if len(bounds) == 1:
        games_with = _occurrence_label(bounds[0])
    elif bounds:
        games_with = _compound_occurrence_label(bounds)
    length = f"{kwargs.get('min_streak_length')}+"
    if special in ("wins", "losses"):
        noun = "winning streak" if special == "wins" else "losing streak"
        tail = f"of {length} games"
        if games_with:
            tail += f" ({games_with.replace('games with', 'every game with', 1)})"
    else:
        noun = "streak"
        condition = {
            "made_three": "with a made three",
            "triple_double": "with a triple-double",
            "double_double": "with a double-double",
        }.get(special or "")
        if condition is None:
            condition = (
                games_with.replace("games ", "", 1) if games_with else "meeting the condition"
            )
        tail = f"of {length} straight games {condition}"
    player = bool(parsed.get("player"))
    context = _count_context(metadata, player=player)
    if kwargs.get("team") is None and kwargs.get("player") is None:
        unit = "team" if parsed.get("route") == "team_streak_finder" else "player"
        subject = f"1 {unit} has" if count == 1 else f"{count} {unit}s have"
        return f"{subject} had a {noun} {tail} {context}."
    entity = metadata.get("player") or _team_subject(metadata, streaks) or "Result"
    verb = "has had" if player else "have had"
    if count != 1:
        noun = noun.replace("streak", "streaks", 1)
    return f"{entity} {verb} {count} {noun} {tail} {context}."


def _team_subject(metadata: dict, games: Any = None) -> str | None:
    team_context = metadata.get("team_context")
    if isinstance(team_context, dict):
        team_name = _clean_text(team_context.get("team_name"))
        if team_name:
            return f"The {team_name}"
    # Team finders carry only the abbreviation; name the team from its rows
    # ("The Los Angeles Lakers", not "The LAL").
    if (
        metadata.get("team")
        and games is not None
        and hasattr(games, "columns")
        and "team_name" in games.columns
        and not games.empty
    ):
        team_name = _clean_text(games["team_name"].mode().iloc[0])
        if team_name:
            return f"The {team_name}"
    team = _clean_text(metadata.get("team"))
    return f"The {team}" if team else None


def _count_context(
    metadata: dict,
    *,
    player: bool,
    last_n: int | None = None,
    last_n_scope: str | None = None,
) -> str:
    query_text = (_clean_text(metadata.get("query_text")) or "").lower()
    if last_n:
        if last_n_scope == "outcome_window":
            owner = "his" if player else "their"
            unit = "losses" if metadata.get("losses_only") else "wins"
            if last_n == 1:
                unit = "loss" if unit == "losses" else "win"
                return f"in {owner} last {unit}"
            return f"in {owner} last {last_n} {unit}"
        if last_n_scope != "window":
            # "last 10 games where he scored 30": the count is capped at N,
            # so say so rather than claiming a 10-game window.
            return f"(limited to the {last_n} most recent)"
        owner = "his" if player else "their"
        noun = "game" if last_n == 1 else f"{last_n} games"
        return f"in {owner} last {noun}"
    season = metadata.get("season")
    start_s = metadata.get("start_season")
    end_s = metadata.get("end_season")
    season_type = (metadata.get("season_type") or "Regular Season").lower()

    if re.search(r"\bthis\s+(?:season|year)\b", query_text):
        return "this season"
    if season:
        if season_type == "playoffs":
            return f"in the {season} playoffs"
        return f"in the {season} {season_type}"
    if start_s and end_s:
        return f"from {start_s} to {end_s} in the {season_type}"
    return f"in his {season_type} career" if player else f"all time in the {season_type}"


def _count_threshold_text(value: Any) -> str:
    if isinstance(value, (int, float)):
        numeric = float(value)
        rounded = round(numeric)
        if abs((numeric + _COUNT_THRESHOLD_EPSILON) - rounded) < 0.001:
            return str(int(rounded))
    return compact_number(value) if isinstance(value, (int, float)) else "the threshold"


def _record_suffix(games: Any) -> str:
    if games is None or not hasattr(games, "empty") or games.empty or "wl" not in games.columns:
        return ""
    wins = int((games["wl"] == "W").sum())
    losses = int((games["wl"] == "L").sum())
    if wins + losses == 0:
        return ""
    return f", going {wins}-{losses}"


_TEAM_ADVANCED_SCALAR_LABELS = {
    "off_rating": "offensive rating",
    "def_rating": "defensive rating",
    "net_rating": "net rating",
    "pace": "pace",
}


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _add_team_advanced_scalar_answer_metadata(metadata: dict[str, Any], result: Any) -> None:
    """Answer phrase for single-team advanced-stat scalar asks.

    "wolves defensive rating" routes to the full team leaderboard; the
    headline pinpoints the asked team's value and league rank.
    """
    if metadata.get("route") != "season_team_leaders":
        return
    stat = metadata.get("stat")
    team = _clean_text(metadata.get("team"))
    if not team or stat not in _TEAM_ADVANCED_SCALAR_LABELS:
        return
    if not isinstance(result, LeaderboardResult) or result.leaders.empty:
        return
    leaders = result.leaders
    if "team_abbr" not in leaders.columns or stat not in leaders.columns:
        return
    match = leaders[leaders["team_abbr"].astype(str).str.upper() == team.upper()]
    if match.empty:
        return
    row = match.iloc[0]
    value = row[stat]
    try:
        rank = int(row["rank"]) if "rank" in leaders.columns else int(match.index[0]) + 1
    except (TypeError, ValueError):
        return
    team_label = _clean_text(row.get("team_name")) or team
    season = metadata.get("season")
    season_type = (metadata.get("season_type") or "Regular Season").lower()
    context = f"in the {season} {season_type}" if season else f"in the {season_type}"
    label = _TEAM_ADVANCED_SCALAR_LABELS[stat]
    article = "an" if label[0] in "aeiou" else "a"
    metadata["answer_phrase"] = (
        f"The {team_label} have {article} {label} of {_format_one_decimal(float(value))} "
        f"({_ordinal(rank)} of {len(leaders)}) {context}."
    )


_TEAM_STRETCH_PHRASES = {
    "pts": "points per game",
    "opp_pts": "points allowed per game",
    "plus_minus": "point differential per game",
    "reb": "rebounds per game",
    "ast": "assists per game",
    "stl": "steals per game",
    "blk": "blocks per game",
    "fg3m": "threes per game",
    "tov": "turnovers per game",
    "fg_pct": "FG%",
    "fg3_pct": "3P%",
    "ft_pct": "FT%",
    "efg_pct": "eFG%",
    "ts_pct": "TS%",
    "off_rating": "offensive rating",
    "def_rating": "defensive rating",
    "net_rating": "net rating",
}


_ROUND_PROSE = {
    "First Round": "first round",
    "Second Round": "second round",
    "Conference Finals": "conference finals",
    "Finals": "Finals",
}


def _series_line(row: Any) -> str:
    verb = {"Won": "beat", "Lost": "lost to"}.get(str(row["result"]), "are playing")
    stage = _ROUND_PROSE.get(row["playoff_round"], str(row["playoff_round"]).lower())
    return (
        f"{verb} the {row['opponent_team_name']} {int(row['wins'])}-{int(row['losses'])} "
        f"in the {stage}"
    )


def _add_playoff_history_answer_metadata(metadata: dict[str, Any], result: Any) -> None:
    """Headline for a team's playoff run, series record or round record."""
    if metadata.get("route") != "playoff_history" or not isinstance(result, SummaryResult):
        return
    series = result.series
    if result.summary.empty or series is None or series.empty:
        return
    row = result.summary.iloc[0]
    team = row["team_name"]
    player = row.get("player_name") if "player_name" in result.summary else None
    if isinstance(player, str) and player:
        _add_player_series_phrase(metadata, row, series, player)
        return
    games = f"{int(row['wins'])}-{int(row['losses'])}"
    won, lost = int(row.get("series_won", 0)), int(row.get("series_lost", 0))
    first, last = row["season_start"], row["season_end"]
    round_label = row.get("playoff_round")
    # An opponent filter narrows every count to the series against that team.
    vs = ""
    if metadata.get("opponent") and "opponent_team_name" in series:
        vs = f" against the {series['opponent_team_name'].iloc[0]}"
    if isinstance(round_label, str) and round_label:
        span = f"from {first} to {last}" if first != last else f"in {first}"
        stage = _ROUND_PROSE.get(round_label, round_label.lower())
        metadata["answer_phrase"] = (
            f"The {team} won {won} of {won + lost} {stage} series{vs} {span}, "
            f"going {games} in those games."
        )
        return
    query_text = str(metadata.get("query_text") or "").lower()
    if re.search(r"\b(?:titles?|championships?|champions?)\b", query_text) and not vs:
        metadata["answer_phrase"] = _team_titles_phrase(team, series, metadata)
        return
    if first == last:
        runs = "; ".join(_series_line(r) for _, r in series.iterrows())
        title = " and won the title" if int(row.get("titles", 0) or 0) and not vs else ""
        metadata["answer_phrase"] = (
            f"The {team} went {games}{vs} in the {first} playoffs{title}: {runs}."
        )
        return
    titles = int(row.get("titles", 0) or 0)
    title_text = (
        f", with {titles} {'title' if titles == 1 else 'titles'}" if titles and not vs else ""
    )
    metadata["answer_phrase"] = (
        f"From {first} to {last}, the {team} won {won} of {won + lost} playoff series{vs} "
        f"({games} in games){title_text}."
    )


_PLAYOFF_DATA_START = "1996-97"


def _add_player_series_phrase(metadata: dict, row: Any, series: Any, player: str) -> None:
    """ "LeBron James won 1 of 1 playoff series in 2025-26 (5-1 in games)."."""
    won, lost = int(row.get("series_won", 0)), int(row.get("series_lost", 0))
    games = f"{int(row['wins'])}-{int(row['losses'])}"
    first, last = row["season_start"], row["season_end"]
    span = f"in {first}" if first == last else f"from {first} to {last}"
    round_label = row.get("playoff_round")
    stage = (
        _ROUND_PROSE.get(round_label, str(round_label).lower())
        if isinstance(round_label, str) and round_label
        else "playoff"
    )
    vs = ""
    if metadata.get("opponent") and "opponent_team_name" in series:
        vs = f" against the {series['opponent_team_name'].iloc[0]}"
    total = won + lost
    open_series = int((series["result"] == "In progress").sum()) if "result" in series else 0
    pending = f", with {open_series} in progress" if open_series else ""
    metadata["answer_phrase"] = (
        f"{player} won {won} of {total} {stage} series{vs} {span} "
        f"({games} in those games){pending}."
    )


_SEASON_TOTAL_NOUNS = {
    "pts_total": "points",
    "reb_total": "rebounds",
    "ast_total": "assists",
    "stl_total": "steals",
    "blk_total": "blocks",
    "fg3m_total": "threes",
}


def _add_season_total_answer_metadata(metadata: dict[str, Any], result: Any) -> None:
    """ "17 players have 1,000+ points this season: Luka Dončić (1,677), ..."."""
    request = next(
        (
            note
            for note in metadata.get("notes") or []
            if isinstance(note, str) and note.startswith("season_total_list:")
        ),
        None,
    )
    match = request and re.search(r"([\d.]+)\+ \w+ \((\w+)\)((?:\|[^|]+)*)$", request)
    if not match:
        return
    if isinstance(result, LeaderboardResult):
        rows = result.leaders
    elif isinstance(result, CountResult):
        rows = result.games
    else:
        return
    column = match.group(2)
    noun = _SEASON_TOTAL_NOUNS.get(column)
    if noun is None:
        return
    value = float(match.group(1))
    # "over 1500" is a strict floor.
    line = f"{value:,.0f}+ {noun}" if value.is_integer() else f"more than {int(value):,} {noun}"
    result_meta = getattr(result, "metadata", None) or {}
    opponent = result_meta.get("opponent_name") or (metadata.get("opponent_context") or {}).get(
        "team_abbr"
    )
    filters = [
        part.replace("{opponent}", f"the {opponent}" if opponent else "that opponent")
        for part in match.group(3).split("|")
        if part
    ]
    # "in a season since 2010": one row per player season.
    per_season = any(
        isinstance(note, str) and note.startswith("single_season")
        for note in metadata.get("notes") or []
    )
    start, end = metadata.get("start_season"), metadata.get("end_season")
    context = _count_context(metadata, player=False)
    if per_season and start and end:
        context = f"in a single season from {start} to {end}"
    elif start and end and not metadata.get("season"):
        context = f"combined {context}"
    if filters:
        context = " ".join(filters) + " " + context
    players = int(rows["player_id"].nunique()) if "player_id" in rows else len(rows)
    team_name = (getattr(result, "metadata", None) or {}).get("team_name") or (
        (metadata.get("team_context") or {}).get("team_name")
    )
    who = f"{team_name} " if team_name else ""
    population = re.search(
        r"\b(rookie|sophomore|guard|forward|center|starter|bench player)s?\b",
        str(metadata.get("query_text") or "").lower(),
    )
    unit = population.group(1) if population else "player"
    if players == 0:
        metadata["answer_phrase"] = f"No {who}{unit} has {line} {context}."
    else:
        listed = []
        for _, row in rows.head(5).iterrows():
            where = f" in {row['season']}" if per_season and "season" in row else ""
            listed.append(f"{row['player_name']} ({int(row[column]):,}{where})")
        if len(rows) > 5:
            extra = len(rows) - 5
            more = ("season" if extra == 1 else "seasons") if per_season else ""
            listed.append(f"{extra} more {more}".strip())
        joined = listed[0] if len(listed) == 1 else ", ".join(listed[:-1]) + f" and {listed[-1]}"
        subject = f"1 {who}{unit} has" if players == 1 else f"{players} {who}{unit}s have"
        metadata["answer_phrase"] = f"{subject} {line} {context}: {joined}."
    if metadata.get("query_class") == "count":
        metadata["count_phrase"] = metadata["answer_phrase"]


def _add_opponent_record_list_answer_metadata(metadata: dict[str, Any], result: Any) -> None:
    """ "2 teams beat the Los Angeles Lakers in the 2025-26 regular season: the
    Boston Celtics (8 times) and the New York Knicks (5)."."""
    if not isinstance(result, LeaderboardResult) or result.leaders.empty:
        return
    request = next(
        (
            note
            for note in metadata.get("notes") or []
            if isinstance(note, str) and note.startswith("opponent_record_list:")
        ),
        None,
    )
    match = request and re.search(r"(\d+)\+ (wins|losses)(?:; (home|road))?", request)
    opponent = (result.metadata or {}).get("opponent_name") or (
        metadata.get("opponent_context") or {}
    ).get("team_name")
    if not match or not opponent or int(match.group(1)) < 1:
        # "the most" is a ranking; the board answers it.
        return
    minimum, stat, venue = int(match.group(1)), match.group(2), match.group(3)
    board = result.leaders
    k = len(board)
    counts = [int(n) for n in board[stat].head(5)]
    names = [f"the {name}" for name in board["team_name"].head(5)]
    if all(n == 1 for n in counts):
        listed = names + ([f"{k - 5} more"] if k > 5 else [])
        each = " (once each)" if k > 1 else " (once)"
    else:
        listed = [
            f"{name} ({n} times)" if i == 0 else f"{name} ({n})"
            for i, (name, n) in enumerate(zip(names, counts))
        ] + ([f"{k - 5} more"] if k > 5 else [])
        each = ""
    joined = listed[0] if len(listed) == 1 else ", ".join(listed[:-1]) + f" and {listed[-1]}"
    context = _count_context(metadata, player=False)
    where = {"home": " at home", "road": " on the road"}.get(venue or "", "")
    teams = "1 team" if k == 1 else f"{k} teams"
    often = {1: "", 2: " at least twice"}.get(minimum, f" at least {minimum} times")
    if stat == "wins":
        # The named team's home: "beat the Lakers at home" is in Los Angeles.
        place = {"home": " in their home games", "road": " in their road games"}.get(
            venue or "", ""
        )
        metadata["answer_phrase"] = (
            f"{teams} beat the {opponent}{place}{often} {context}: {joined}{each}."
        )
    else:
        metadata["answer_phrase"] = (
            f"The {opponent} beat {teams}{where}{often} {context}: {joined}{each}."
        )


def _add_titles_leaderboard_answer_metadata(metadata: dict[str, Any], result: Any) -> None:
    """Headline for "which team has won the most titles since 2000"."""
    if metadata.get("route") != "playoff_appearances" or not isinstance(result, LeaderboardResult):
        return
    board = result.leaders
    if board.empty or "titles" not in board:
        return
    if "player_name" in board:
        _add_player_rings_answer_metadata(metadata, board)
        return
    top = board.iloc[0]
    if "season" in board and "finals_opponent" in board:
        # One season: who won it and whom they beat.
        metadata["answer_phrase"] = (
            f"The {top['team_name']} won the {top['season']} title, beating the "
            f"{top['finals_opponent']} {top['finals_score']} in the Finals."
        )
        return
    start, end = metadata.get("start_season"), metadata.get("end_season")
    if not (start and end):
        start = end = metadata.get("season")
    span = f"in {start}" if start == end else f"from {start} to {end}"
    if str(start) < _PLAYOFF_DATA_START:
        span = f"from {_PLAYOFF_DATA_START} (where the data starts) to {end}"
    most = int(top["titles"])
    leaders = board[board["titles"] == most]
    count = f"{most} {'title' if most == 1 else 'titles'}"
    if len(leaders) == 1:
        metadata["answer_phrase"] = (
            f"The {top['team_name']} won the most titles {span}: {count} ({top['title_seasons']})."
        )
        return
    names = [f"the {name}" for name in leaders["team_name"]]
    joined = ", ".join(names[:-1]) + f" and {names[-1]}"
    joined = joined[0].upper() + joined[1:]
    metadata["answer_phrase"] = f"{joined} tied for the most titles {span}, with {count} each."


_APPEARANCE_STAGE = {
    "Playoffs": "the playoffs",
    "First Round": "the first round",
    "Second Round": "the second round",
    "Conference Finals": "the conference finals",
    "Finals": "the Finals",
}
_LAST_WORDS = re.compile(r"\b(?:last|latest|most\s+recent|recent)\b")
_RUN_WORDS = re.compile(r"\b(?:consecutive|straight|in\s+a\s+row|streak|running)\b")
_DROUGHT_WORDS = re.compile(r"\bdrought\b")
_MISS_WORDS = re.compile(r"\bmiss(?:ed|es|ing)?\b")


def _seasons_word(n: int) -> str:
    return f"{n} {'season' if n == 1 else 'seasons'}"


def _possessive(name: str) -> str:
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def _span_text(first: Any, last: Any) -> str:
    return f"from {first} to {last}" if first != last else f"in {first}"


def _run_span(start: Any, end: Any) -> str:
    return f"({start})" if start == end else f"({start} to {end})"


def _named_list(names: list[str], limit: int = 6) -> str:
    shown = names[:limit]
    if len(names) > limit:
        return ", ".join(shown) + f" and {len(names) - limit} others"
    if len(shown) == 1:
        return shown[0]
    return ", ".join(shown[:-1]) + f" and {shown[-1]}"


def _run_phrase(subject: str, row: Any, stage: str, span: str, query_text: str) -> str | None:
    """Last appearance, run, drought or misses for one team or player row."""
    if _DROUGHT_WORDS.search(query_text):
        since = int(row["seasons_since_last"])
        if since:
            verb = "have" if subject.startswith("The ") else "has"
            current = f"{subject} {verb} missed {stage} the last {_seasons_word(since)}"
        else:
            current = (
                f"{subject} reached {stage} in {row['last_appearance']}, "
                "so there is no current drought"
            )
        longest = int(row["longest_drought"])
        worst = (
            f"; the longest drought {span} was {_seasons_word(longest)} "
            f"{_run_span(row['longest_drought_start'], row['longest_drought_end'])}"
            if longest
            else f"; no drought {span}"
        )
        return f"{current}{worst}."
    if _RUN_WORDS.search(query_text):
        longest = int(row["longest_streak"])
        if not longest:
            return f"{subject} did not reach {stage} {span}."
        current = int(row["current_streak"])
        length = "1 season" if longest == 1 else f"{longest} straight seasons"
        return (
            f"{_possessive(subject)} longest run {span} was {length} in {stage} "
            f"{_run_span(row['longest_streak_start'], row['longest_streak_end'])}; "
            f"the current run is {_seasons_word(current)}."
        )
    if _LAST_WORDS.search(query_text) and not re.search(r"\blast\s+\d+", query_text):
        if row["last_appearance"] is None or pd.isna(row["last_appearance"]):
            return f"{subject} did not reach {stage} {span}."
        return f"{subject} last reached {stage} in {row['last_appearance']}."
    if _MISS_WORDS.search(query_text):
        return (
            f"{subject} missed {stage} in {int(row['missed'])} of "
            f"{int(row['seasons_played'])} seasons {span}."
        )
    return None


def _add_appearances_answer_metadata(metadata: dict[str, Any], result: Any) -> None:
    """Headline for playoff appearances: counts, last, runs, droughts, players."""
    if metadata.get("route") != "playoff_appearances":
        return
    query_text = str(metadata.get("query_text") or "").lower()
    if isinstance(result, LeaderboardResult):
        board = result.leaders
        if board.empty:
            return
        top = board.iloc[0]
        stage = _APPEARANCE_STAGE.get(str(top.get("round")), "the playoffs")
        span_label = top.get("seasons") if "seasons" in board else top.get("season")
        span = f"from {span_label}" if " to " in str(span_label) else f"in {span_label}"
        for column, verb in (
            ("longest_streak", "the longest run of seasons in"),
            ("longest_drought", "the longest drought without reaching"),
        ):
            if column in board and "player_name" not in board:
                value = int(top[column])
                leaders = board[board[column] == value]
                names = _named_list([f"the {name}" for name in leaders["team_name"]])
                names = names[0].upper() + names[1:]
                length = _seasons_word(value)
                if len(leaders) == 1:
                    metadata["answer_phrase"] = (
                        f"{names} have {verb} {stage} {span}: {length} "
                        f"{_run_span(top['run_start'], top['run_end'])}."
                    )
                else:
                    metadata["answer_phrase"] = (
                        f"{names} share {verb} {stage} {span}, {length} each."
                    )
                return
        if "missed" in board and "player_name" not in board:
            if "season" in board:
                names = _named_list([f"the {name}" for name in board["team_name"]], limit=40)
                count = len(board)
                metadata["answer_phrase"] = (
                    f"{count} {'team' if count == 1 else 'teams'} missed {stage} in "
                    f"{span_label}: {names}."
                )
            else:
                most = int(top["missed"])
                leaders = board[board["missed"] == most]
                names = _named_list([f"the {name}" for name in leaders["team_name"]])
                names = names[0].upper() + names[1:]
                metadata["answer_phrase"] = (
                    f"{names} missed {stage} the most {span}: {_seasons_word(most)}."
                )
            return
        if "appearances" not in board:
            return
        if "player_name" not in board:
            if re.search(r"\b(?:fewest|least)\b", query_text):
                fewest = int(top["appearances"])
                leaders = board[board["appearances"] == fewest]
                names = _named_list([f"the {name}" for name in leaders["team_name"]])
                names = names[0].upper() + names[1:]
                times = "time" if fewest == 1 else "times"
                metadata["answer_phrase"] = (
                    f"{names} reached {stage} the fewest times {span}: {fewest} {times}."
                )
                return
            if "season" in board and not re.search(r"\bmost\b", query_text):
                names = _named_list([f"the {name}" for name in board["team_name"]], limit=40)
                count = len(board)
                metadata["answer_phrase"] = (
                    f"{count} {'team' if count == 1 else 'teams'} reached {stage} in "
                    f"{span_label}: {names}."
                )
            return
        if (metadata.get("route_kwargs") or {}).get("player") or metadata.get("player"):
            subject = str(top["player_name"])
            if "longest_streak" in board:
                run = _run_phrase(subject, top, stage, span, query_text)
                if run:
                    metadata["answer_phrase"] = run
                    return
            count = int(top["appearances"])
            if count == 0:
                metadata["answer_phrase"] = f"{subject} did not reach {stage} ({span_label})."
                return
            times = "1 season" if count == 1 else f"{count} seasons"
            metadata["answer_phrase"] = (
                f"{subject} reached {stage} in {times} ({top['appearance_seasons']})."
            )
            return
        most = int(top["appearances"])
        leaders = board[board["appearances"] == most]
        metadata["answer_phrase"] = (
            f"Most seasons reaching {stage} ({span_label}): "
            f"{_named_list(list(leaders['player_name']))}, with {most}."
        )
        return
    if not isinstance(result, SummaryResult) or result.summary.empty:
        return
    row = result.summary.iloc[0]
    if "last_appearance" not in row:
        return
    subject = f"The {row['team_name']}"
    stage = _APPEARANCE_STAGE.get(str(row.get("round")), "the playoffs")
    first, last = row["season_start"], row["season_end"]
    span = _span_text(first, last)
    run = _run_phrase(subject, row, stage, span, query_text)
    if run:
        metadata["answer_phrase"] = run
        return
    count = int(row["appearances"])
    if first == last or not count:
        reached = "reached" if count else "did not reach"
        metadata["answer_phrase"] = f"{subject} {reached} {stage} {span}."
        return
    times = "time" if count == 1 else "times"
    metadata["answer_phrase"] = f"{subject} reached {stage} {count} {times} {span}."


_MAX_LISTED_SERIES = 5


def _add_series_comebacks_answer_metadata(metadata: dict[str, Any], result: Any) -> None:
    """Headline for "teams that came back from 3-1 down" / "blew a 3-1 lead"."""
    if metadata.get("route") != "playoff_series_comebacks":
        return
    if not isinstance(result, LeaderboardResult) or result.leaders.empty:
        return
    kwargs = result.metadata
    wins, losses = kwargs.get("deficit_wins"), kwargs.get("deficit_losses")
    if wins is None or losses is None:
        return
    high, low = max(wins, losses), min(wins, losses)
    blown = bool(kwargs.get("blown"))
    what = f"blew a {high}-{low} series lead" if blown else f"came back from {high}-{low} down"
    what += str(kwargs.get("scope") or "")
    # The seasons the list covered, including a span the route filled in.
    start, end = kwargs.get("first_season"), kwargs.get("last_season")
    if not (start and end):
        start, end = metadata.get("start_season"), metadata.get("end_season")
    if not (start and end):
        start = end = metadata.get("season")
    span = f"in {start}" if start == end else f"from {start} to {end}"
    if str(start) < _PLAYOFF_DATA_START:
        span = f"from {_PLAYOFF_DATA_START} (where the data starts) to {end}"
    rows = result.leaders
    count = len(rows)
    listed = [
        f"{row['season']} {row['playoff_round']} vs the {row['opponent_team_name']} "
        f"({'lost' if blown else 'won'} {row['series']})"
        for _, row in rows.head(_MAX_LISTED_SERIES).iterrows()
    ]
    more = f", and {count - len(listed)} more" if count > len(listed) else ""
    if kwargs.get("team_filter"):
        team_name = str(rows["team_name"].iloc[0])
        times = "once" if count == 1 else "twice" if count == 2 else f"{count} times"
        metadata["answer_phrase"] = (
            f"The {team_name} {what} {times} {span}: {'; '.join(listed)}{more}."
        )
        return
    teams = [
        f"the {row['season']} {row['team_name']} ({row['playoff_round']} vs the "
        f"{row['opponent_team_name']}, {'lost' if blown else 'won'} {row['series']})"
        for _, row in rows.head(_MAX_LISTED_SERIES).iterrows()
    ]
    lead = f"Teams {what} in {count} series {span}"
    metadata["answer_phrase"] = f"{lead}: {'; '.join(teams)}{more}."


def _add_player_rings_answer_metadata(metadata: dict[str, Any], board: Any) -> None:
    """Headline for "how many rings does LeBron have" and "who has the most rings"."""
    start, end = metadata.get("start_season"), metadata.get("end_season")
    if not (start and end):
        start = end = metadata.get("season")
    span = f"in {start}" if start == end else f"from {start} to {end}"
    if str(start) < _PLAYOFF_DATA_START:
        span = f"from {_PLAYOFF_DATA_START} (where the data starts) to {end}"
    top = board.iloc[0]
    most = int(top["titles"])
    count = f"{most} {'title' if most == 1 else 'titles'}"
    if (metadata.get("route_kwargs") or {}).get("player") or metadata.get("player"):
        if most == 0:
            metadata["answer_phrase"] = f"{top['player_name']} won no titles {span}."
            return
        teams = ", ".join(dict.fromkeys(str(top["title_teams"]).split(", ")))
        detail = teams if start == end else f"{top['title_seasons']}; {teams}"
        metadata["answer_phrase"] = f"{top['player_name']} won {count} {span} ({detail})."
        return
    leaders = board[board["titles"] == most]
    if len(leaders) == 1:
        metadata["answer_phrase"] = (
            f"{top['player_name']} won the most titles {span}: {count} ({top['title_seasons']})."
        )
        return
    names = list(leaders["player_name"])
    shown = names if len(names) <= 6 else names[:6]
    joined = ", ".join(shown[:-1]) + f" and {shown[-1]}"
    if len(names) > len(shown):
        joined = ", ".join(shown) + f" and {len(names) - len(shown)} others"
    metadata["answer_phrase"] = f"{joined} tied for the most titles {span}, with {count} each."


def _team_titles_phrase(team: str, series: Any, metadata: dict[str, Any]) -> str:
    """ "Lakers titles since 2000": Finals series won, with the seasons."""
    start, end = metadata.get("start_season"), metadata.get("end_season")
    if not (start and end):
        start = end = metadata.get("season")
    span = f"in {start}" if start == end else f"from {start} to {end}"
    if str(start) < _PLAYOFF_DATA_START:
        # Earlier titles are not in the data, so never count from before it.
        span = f"from {_PLAYOFF_DATA_START} (where the data starts) to {end}"
        start = _PLAYOFF_DATA_START
    finals = series[series["playoff_round"] == "Finals"]
    won = finals[finals["result"] == "Won"]
    reached = len(finals)
    # A run is still going when its last series is unfinished, or won short of the Finals.
    last = series.sort_values(["season", "start_date"]).iloc[-1] if not series.empty else None
    still_going = last is not None and (
        last["result"] == "In progress"
        or (last["result"] == "Won" and last["playoff_round"] != "Finals")
    )
    if won.empty and still_going:
        season = last["season"]
        return (
            f"The {team} have not won a title {span}; "
            f"their {season} playoff run is still in progress."
        )
    if start == end and reached:
        # One season: name the Finals opponent and the series score.
        final = finals.iloc[-1]
        score = f"{int(final['wins'])}-{int(final['losses'])}"
        opponent = final["opponent_team_name"]
        if final["result"] == "Won":
            won_text = f"won the {start} title, beating the {opponent} {score} in the Finals"
            return f"The {team} {won_text}."
        return (
            f"The {team} did not win the {start} title; "
            f"they lost to the {opponent} {score} in the Finals."
        )
    if won.empty:
        if not reached:
            return f"The {team} did not win a title {span}; they did not reach the Finals."
        times = "once" if reached == 1 else f"{reached} times"
        return f"The {team} did not win a title {span}; they reached the Finals {times}."
    titles = "title" if len(won) == 1 else "titles"
    seasons = ", ".join(str(season) for season in won["season"])
    appearances = "appearance" if reached == 1 else "appearances"
    return (
        f"The {team} won {len(won)} {titles} {span} ({seasons}), in {reached} Finals {appearances}."
    )


def _add_team_stretch_answer_metadata(metadata: dict[str, Any], result: Any) -> None:
    """Headline for "Celtics best 10 game stretch": record, dates and margin."""
    if metadata.get("route") != "team_stretch_leaderboard":
        return
    if not isinstance(result, LeaderboardResult) or result.leaders.empty:
        return
    row = result.leaders.iloc[0]
    size = int(row["window_size"])
    metric = str(row["stretch_metric"])
    direction = "worst" if result.metadata.get("worst") else "best"
    net = float(row["net_per_game"])
    margin = f"{'+' if net > 0 else ''}{_format_one_decimal(net)} per game"
    record = f"{int(row['wins'])}-{int(row['losses'])}"
    span = f"from {row['window_start_date']} to {row['window_end_date']}"
    if metric == "wins":
        detail = f"went {record} {span} ({margin})"
    else:
        value = float(row["stretch_value"])
        label = _TEAM_STRETCH_PHRASES.get(metric, metric)
        if metric.endswith("_pct"):
            shown = f"{value:.1%}"
            detail = f"posted {_indefinite_article(shown)} {shown} {label} {span}, going {record}"
        elif metric == "plus_minus":
            verb = "outscored opponents" if value >= 0 else "were outscored"
            margin_text = _format_one_decimal(abs(value))
            detail = f"{verb} by {margin_text} points per game {span}, going {record}"
        elif metric.endswith("_rating"):
            shown = _format_one_decimal(value)
            detail = f"posted {_indefinite_article(shown)} {shown} {label} {span}, going {record}"
        else:
            detail = f"averaged {_format_one_decimal(value)} {label} {span}, going {record}"
    teams = result.metadata.get("teams")
    if teams:
        either = "either team" if len(teams) == 2 else f"the {len(teams)} teams"
        scope = f"the {direction} {size}-game stretch by {either}"
    elif result.metadata.get("team"):
        scope = f"their {direction} {size}-game stretch"
    else:
        scope = f"the league's {direction} {size}-game stretch"
    when = (
        f"the {row['season']} playoffs"
        if metadata.get("season_type") == "Playoffs"
        else str(row["season"])
    )
    connector = "in" if teams else "of"
    seasons = sorted({str(season) for season in result.leaders["season"]})
    first = metadata.get("start_season") or seasons[0]
    last = metadata.get("end_season") or seasons[-1]
    if teams and first != last:
        # Each team's best window can fall in any season searched.
        playoffs = " playoffs" if metadata.get("season_type") == "Playoffs" else ""
        connector, when = (
            "from",
            f"the {first} to {last}{playoffs}" if playoffs else f"{first} to {last}",
        )
    metadata["answer_phrase"] = f"The {row['team_name']} {detail}, {scope} {connector} {when}."


_PLAYER_STRETCH_RATE_PHRASES = {
    "fg_pct": "shooting",
    "fg3_pct": "from three",
    "ft_pct": "from the line",
    "efg_pct": "effective field goal shooting",
    "ts_pct": "true shooting",
}


def _add_player_stretch_answer_metadata(metadata: dict[str, Any], result: Any) -> None:
    """Headline for "Jokic best 5 game scoring stretch": value, dates and scope."""
    if metadata.get("route") != "player_stretch_leaderboard":
        return
    if not isinstance(result, LeaderboardResult) or result.leaders.empty:
        return
    row = result.leaders.iloc[0]
    size = int(row["window_size"])
    metric = str(row["stretch_metric"])
    value = float(row["stretch_value"])
    if metric == "game_score":
        score = _format_one_decimal(value)
        shown = f"{_indefinite_article(score)} {score} Game Score average"
    elif metric.endswith("_pct"):
        shown = f"{value:.1%} {_PLAYER_STRETCH_RATE_PHRASES.get(metric, metric)}"
    else:
        label = _TEAM_STRETCH_PHRASES.get(metric, metric.replace("_", " "))
        shown = f"{_format_one_decimal(value)} {label}"

    def _day(stamp: Any) -> str:
        return str(pd.Timestamp(stamp).date()) if pd.notna(stamp) else str(stamp)

    span = f"from {_day(row['window_start_date'])} to {_day(row['window_end_date'])}"
    seasons = sorted(
        {str(s) for s in result.leaders["window_start_season"]}
        | {str(s) for s in result.leaders["window_end_season"]}
    )
    first = metadata.get("start_season") or seasons[0]
    last = metadata.get("end_season") or seasons[-1]
    playoffs = " playoffs" if metadata.get("season_type") == "Playoffs" else ""
    if first == last:
        when = f"of the {first}{playoffs}" if playoffs else f"of {first}"
    else:
        when = f"from the {first} to {last}{playoffs}" if playoffs else f"from {first} to {last}"
    direction = "worst" if result.metadata.get("worst") else "best"
    if metadata.get("player"):
        metadata["answer_phrase"] = (
            f"{row['player_name']}'s {direction} {size}-game stretch {when} was {shown} {span}."
        )
    else:
        team_context = metadata.get("team_context")
        team = (
            _clean_text(team_context.get("team_name")) if isinstance(team_context, dict) else None
        ) or _clean_text(metadata.get("team"))
        whose = f"by any {team} player" if team else "by any player"
        metadata["answer_phrase"] = (
            f"{row['player_name']} had the {direction} {size}-game stretch {when} {whose}: "
            f"{shown} {span}."
        )


def _indefinite_article(number_text: str) -> str:
    """'an 84.4', 'an 11.2', 'an 18-point' but 'a 104.5'."""
    whole = number_text.split(".")[0].lstrip("-")
    return "an" if whole.startswith("8") or whole in {"11", "18"} else "a"


def _add_game_summary_answer_metadata(metadata: dict[str, Any], result: Any) -> None:
    if not isinstance(result, SummaryResult) or metadata.get("route") != "game_summary":
        return
    if result.summary.empty:
        return

    row = result.summary.iloc[0]
    games = _series_int(row, "games")
    wins = _series_int(row, "wins")
    losses = _series_int(row, "losses")
    pts_avg = _series_float(row, "pts_avg")
    if games is None or wins is None or losses is None:
        return

    metadata["record_wins"] = wins
    metadata["record_losses"] = losses
    metadata["record"] = f"{wins}-{losses}"
    metadata["primary_count"] = games

    team = _team_subject(metadata) or _clean_text(row.get("team_name")) or "The team"
    game_word = "game" if games == 1 else "games"
    without_player = _clean_text(metadata.get("without_player"))
    context = f" without {without_player}" if without_player else ""
    ppg = f", averaging {_format_one_decimal(pts_avg)} PPG" if pts_avg is not None else ""
    metadata["answer_phrase"] = f"{team} are {wins}-{losses} in {games} {game_word}{context}{ppg}."


def _series_int(row: Any, key: str) -> int | None:
    value = row.get(key)
    if pd.notna(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    return None


def _series_float(row: Any, key: str) -> float | None:
    value = row.get(key)
    if pd.notna(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _format_one_decimal(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.1f}"


def _occurrence_label(occurrence: Any) -> str:
    if isinstance(occurrence, dict):
        special = occurrence.get("special_event")
        if special == "triple_double":
            return "triple-double"
        if special == "double_double":
            return "double-double"

        stat = occurrence.get("stat")
        min_value = occurrence.get("min_value")
        max_value = occurrence.get("max_value")
        if isinstance(stat, str):
            stat_name = stat_phrase_label(stat)
            if isinstance(min_value, (int, float)) and isinstance(max_value, (int, float)):
                return f"games with {_range_phrase(min_value, max_value)} {stat_name}"
            if isinstance(min_value, (int, float)):
                return f"games with {_minimum_threshold_phrase(min_value)} {stat_name}"
            if isinstance(max_value, (int, float)):
                return f"games with {_maximum_threshold_phrase(max_value)} {stat_name}"
            return f"games with {stat_name}"

    if isinstance(occurrence, str) and occurrence:
        return occurrence.replace("_", "-")
    return "game"


def _compound_occurrence_label(conditions: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for cond in conditions:
        stat = cond.get("stat")
        if not isinstance(stat, str):
            continue
        stat_name = stat_phrase_label(stat)
        min_value = cond.get("min_value")
        max_value = cond.get("max_value")
        if isinstance(min_value, (int, float)) and isinstance(max_value, (int, float)):
            parts.append(f"{_range_phrase(min_value, max_value)} {stat_name}")
        elif isinstance(min_value, (int, float)):
            parts.append(f"{_minimum_threshold_phrase(min_value)} {stat_name}")
        elif isinstance(max_value, (int, float)):
            parts.append(f"{_maximum_threshold_phrase(max_value)} {stat_name}")
        else:
            parts.append(stat_name)
    if not parts:
        return "game"
    return "games with " + " and ".join(parts)


def _minimum_threshold_phrase(value: int | float) -> str:
    numeric = float(value)
    rounded = round(numeric)
    if abs(numeric - (rounded + _COUNT_THRESHOLD_EPSILON)) < 0.000001:
        return f"over {compact_number(rounded)}"
    return f"{compact_number(value)}+"


def _range_phrase(low: int | float, high: int | float) -> str:
    # "between 20 and 30 points" reads as "20-30", not "20+".
    return f"{compact_number(low)}-{compact_number(high)}"


def _maximum_threshold_phrase(value: int | float) -> str:
    numeric = float(value)
    rounded = round(numeric)
    if abs(numeric - (rounded - _COUNT_THRESHOLD_EPSILON)) < 0.000001:
        return f"under {compact_number(rounded)}"
    return f"at most {compact_number(value)}"


def pluralize_occurrence(label: str) -> str:
    if label.startswith("games with "):
        return label
    if label.endswith("s"):
        return label
    return f"{label}s"


def _filter_stat_label(stat: str) -> str:
    """Filter-chip label: "OPP PTS", "OPP FG3M", or the stat id."""
    if stat.startswith("opponent_"):
        return f"OPP {stat[len('opponent_') :].upper()}"
    return stat


def stat_phrase_label(stat: str) -> str:
    labels = {
        "ast": "assists",
        "blk": "blocks",
        "fg3m": "threes",
        "pts": "points",
        "reb": "rebounds",
        "stl": "steals",
        "tov": "turnovers",
        "fgm": "made field goals",
        "fga": "field goal attempts",
        "fg3a": "three-point attempts",
        "ftm": "made free throws",
        "fta": "free throw attempts",
        "oreb": "offensive rebounds",
        "dreb": "defensive rebounds",
    }
    key = stat.lower()
    if key.startswith("opponent_") and key[len("opponent_") :] in labels:
        # "games with 15+ opponent threes"
        return f"opponent {labels[key[len('opponent_') :]]}"
    return labels.get(key, stat.replace("_", " "))


def compact_number(value: int | float) -> str:
    numeric = float(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:g}"


def _build_suggested_queries_for_fragment(parsed: dict) -> list[str]:
    """Build concrete rephrasing suggestions for ambiguous-fragment queries (Pattern 8).

    Inspects the parsed slot context (player / team / stat / occurrence) and
    returns 2-4 concrete alternative query strings the user could run instead
    of the ambiguous fragment.
    """
    player = parsed.get("player")
    team = parsed.get("team")
    stat = parsed.get("stat")
    occurrence = parsed.get("occurrence_event")
    season = parsed.get("season") or "this season"

    suggestions: list[str] = []

    if player:
        base = player
        if occurrence:
            occurrence_label = _occurrence_label(occurrence)
            suggestions.append(
                f"how many {pluralize_occurrence(occurrence_label)} has {base} had {season}"
            )
            suggestions.append(f"{base} {occurrence_label} games {season}")
            suggestions.append(
                f"most {pluralize_occurrence(occurrence_label)} this season leaderboard"
            )
        elif stat:
            suggestions.append(f"{base} {stat} summary {season}")
            suggestions.append(f"{base} games with high {stat} {season}")
        else:
            suggestions.append(f"{base} summary {season}")
            suggestions.append(f"{base} game log {season}")
            suggestions.append(f"{base} last 10 games")
    elif team:
        base = team
        if occurrence:
            suggestions.append(f"{base} {occurrence} games {season}")
            suggestions.append(f"{base} game log {season}")
        else:
            suggestions.append(f"{base} record {season}")
            suggestions.append(f"{base} summary {season}")
            suggestions.append(f"{base} last 10 games")
    else:
        # Generic fallback — minimal but honest
        suggestions.append("add a player name, team name, or stat to your query")

    return suggestions[:4]


# ---------------------------------------------------------------------------
# Query envelope
# ---------------------------------------------------------------------------

# Reasons that represent expected/anticipated failures → no_result status.
# All other reasons represent system-level failures → error status.
_EXPECTED_REASONS: frozenset[str] = frozenset(
    {
        "unsupported",
        "no_data",
        "no_match",
        "ambiguous",
        "ambiguous_query",
        "filter_not_supported",
    }
)


def reason_to_status(reason: str) -> str:
    """Map a result reason to its canonical result status.

    Expected failures (unsupported filters, missing data, zero matches,
    entity ambiguity) map to ``"no_result"``.  System-level failures
    (unrouted, internal error) map to ``"error"``.
    """
    return "no_result" if reason in _EXPECTED_REASONS else "error"


@dataclass
class QueryResult:
    """Envelope returned by the query service entry points.

    Wraps a structured result object with query-level metadata so that
    consumers get everything they need in one object.

    Attributes
    ----------
    result : object
        A typed result (``SummaryResult``, ``FinderResult``, etc.) or
        ``NoResult``.
    metadata : dict
        Query-level metadata: route, query_class, season, player, team,
        current_through, notes, etc.
    query : str
        The original query string (natural) or a synthetic description
        (structured).
    route : str | None
        The resolved route name.
    """

    result: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    query: str = ""
    route: str | None = None

    # Convenience accessors ------------------------------------------------

    @property
    def is_ok(self) -> bool:
        return not isinstance(self.result, NoResult)

    @property
    def result_status(self) -> str:
        return getattr(self.result, "result_status", "ok")

    @property
    def result_reason(self) -> str | None:
        return getattr(self.result, "result_reason", None)

    @property
    def current_through(self) -> str | None:
        return getattr(self.result, "current_through", None) or self.metadata.get("current_through")

    def to_dict(self) -> dict[str, Any]:
        """Full dict representation suitable for JSON serialization."""
        result_dict = self.result.to_dict() if hasattr(self.result, "to_dict") else {}
        result_dict["metadata"] = dict(self.metadata)
        return result_dict


def _apply_count_intent(
    result: Any,
    parsed: dict[str, Any],
    *,
    allow_stat_total: bool,
) -> Any:
    """Convert an executed result to the trusted count contract when requested."""
    if not parsed.get("count_intent", False):
        return result

    if getattr(result, "result_status", None) != ResultStatus.OK:
        if _is_trusted_empty_count_result(result):
            return CountResult(
                count=0,
                result_status=ResultStatus.OK,
                current_through=result.current_through,
                metadata=result.metadata,
                notes=result.notes,
                caveats=result.caveats,
            )
        return _count_no_result(result)

    if isinstance(result, StreakResult):
        if not parsed.get("streak_count"):
            return result
        return CountResult(
            count=len(result.streaks),
            games=result.streaks,
            result_status=result.result_status,
            result_reason=result.result_reason,
            current_through=result.current_through,
            metadata=result.metadata,
            notes=result.notes,
            caveats=result.caveats,
            detail_section="streak",
        )

    if isinstance(result, FinderResult):
        stat_total = _stat_total_count(parsed, result.games) if allow_stat_total else None
        if stat_total is not None:
            parsed["count_kind"] = "stat_total"
        return CountResult(
            count=stat_total if stat_total is not None else len(result.games),
            games=result.games,
            result_status=result.result_status,
            result_reason=result.result_reason,
            current_through=result.current_through,
            metadata=result.metadata,
            notes=result.notes,
            caveats=result.caveats,
        )

    if not isinstance(result, LeaderboardResult):
        return result

    route_kwargs = parsed.get("route_kwargs")
    if not isinstance(route_kwargs, dict):
        route_kwargs = {}

    player_name = parsed.get("player")
    team_name = route_kwargs.get("team")
    entity_count: int | None = None
    missing_entity_reason: str | None = None
    detail = pd.DataFrame()

    if route_kwargs.get("min_total") is not None:
        # "how many players scored 2000 points (in a season)": distinct players
        # at the line, not their seasons and not a team's row.
        leaders = result.leaders
        entity_count = (
            int(leaders["player_id"].nunique()) if "player_id" in leaders else len(leaders)
        )
        detail = leaders
    elif parsed.get("distinct_player_count") or parsed.get("distinct_team_count"):
        entity_count = len(result.leaders)
    elif player_name:
        if "player_name" not in result.leaders.columns:
            missing_entity_reason = "filter_not_supported"
        else:
            match = select_player_rows(result.leaders, player_name)
            if match.empty:
                missing_entity_reason = "no_match"
            else:
                skip_cols = {
                    "rank",
                    "player_name",
                    "player_id",
                    "team_abbr",
                    "games_played",
                    "season",
                    "seasons",
                    "season_type",
                }
                event_cols = [column for column in match.columns if column not in skip_cols]
                if event_cols:
                    entity_count = int(match.iloc[0][event_cols[0]])
                else:
                    missing_entity_reason = "filter_not_supported"
    elif team_name:
        team_upper = team_name.upper()
        team_match = None
        for column in ["team_abbr", "team_name"]:
            if column in result.leaders.columns:
                candidate = result.leaders[
                    result.leaders[column].astype(str).str.upper() == team_upper
                ]
                if not candidate.empty:
                    team_match = candidate
                    break
        if team_match is None:
            if any(column in result.leaders.columns for column in ["team_abbr", "team_name"]):
                missing_entity_reason = "no_match"
            else:
                missing_entity_reason = "filter_not_supported"
        else:
            skip_cols = {
                "rank",
                "team_abbr",
                "team_name",
                "games_played",
                "season",
                "seasons",
                "season_type",
            }
            event_cols = [column for column in team_match.columns if column not in skip_cols]
            if event_cols:
                entity_count = int(team_match.iloc[0][event_cols[0]])
            else:
                missing_entity_reason = "filter_not_supported"
    elif len(result.leaders) == 1:
        skip_cols = {
            "rank",
            "player_name",
            "player_id",
            "team_abbr",
            "team_name",
            "games_played",
            "season",
            "seasons",
            "season_type",
        }
        event_cols = [column for column in result.leaders.columns if column not in skip_cols]
        if event_cols:
            entity_count = int(result.leaders.iloc[0][event_cols[0]])

    if entity_count is None:
        if missing_entity_reason is None:
            entity_count = 0
        else:
            return NoResult(
                query_class="count",
                reason=missing_entity_reason,
                result_status="no_result",
                result_reason=missing_entity_reason,
                current_through=result.current_through,
                metadata=result.metadata,
                notes=result.notes,
                caveats=result.caveats,
            )

    return CountResult(
        count=entity_count,
        games=detail,
        result_status=result.result_status,
        result_reason=result.result_reason,
        current_through=result.current_through,
        metadata=result.metadata,
        notes=result.notes,
        caveats=result.caveats,
        detail_section="leaderboard" if not detail.empty else "finder",
    )


def _finalize_natural_query_result(
    result: Any,
    parsed: dict[str, Any],
    query: str,
    *,
    grouped_boolean_used: bool,
    boolean_query_used: bool = False,
) -> QueryResult:
    """Apply shared result overlays and metadata after every execution path."""
    count_intent = bool(parsed.get("count_intent", False))
    result = _apply_count_intent(
        result,
        parsed,
        allow_stat_total=not boolean_query_used,
    )
    metadata = _build_query_metadata(
        parsed,
        query,
        grouped_boolean_used=grouped_boolean_used,
    )
    if count_intent:
        metadata["query_class"] = "count"
    if count_intent and isinstance(result, CountResult):
        metadata["primary_count"] = result.count
        phrase_state = dict(parsed)
        phrase_state["boolean_query_used"] = boolean_query_used
        metadata["count_phrase"] = _build_count_phrase(
            result.count,
            phrase_state,
            metadata,
            result.games,
        )
    _add_game_summary_answer_metadata(metadata, result)
    _add_team_advanced_scalar_answer_metadata(metadata, result)
    _add_team_stretch_answer_metadata(metadata, result)
    _add_player_stretch_answer_metadata(metadata, result)
    _add_playoff_history_answer_metadata(metadata, result)
    _add_titles_leaderboard_answer_metadata(metadata, result)
    _add_appearances_answer_metadata(metadata, result)
    _add_series_comebacks_answer_metadata(metadata, result)
    _add_opponent_record_list_answer_metadata(metadata, result)
    _add_season_total_answer_metadata(metadata, result)
    if getattr(result, "notes", None):
        _merge_metadata_notes(metadata, list(result.notes))
    return QueryResult(
        result=result,
        metadata=metadata,
        query=query,
        route=parsed.get("route"),
    )


# ---------------------------------------------------------------------------
# Natural query entry point
# ---------------------------------------------------------------------------


def execute_natural_query(query: str) -> QueryResult:
    """Execute a natural query against one request-pinned data generation."""
    with data_generation_context():
        return _execute_natural_query_in_generation(query)


def _execute_natural_query_in_generation(query: str) -> QueryResult:
    """Execute a natural-language NBA query and return a structured result.

    This is the primary entry point for natural queries.  It parses the
    query, detects intent, routes to the appropriate command, executes
    it, and wraps the result.

    Parameters
    ----------
    query : str
        A natural-language query such as ``"Jokic last 10 games"`` or
        ``"top 5 scorers 2024-25"``.

    Returns
    -------
    QueryResult
        An envelope containing the structured result and metadata.
    """
    normalized = normalize_text(query)

    grouped_boolean_used = expression_contains_boolean_ops(normalized) and (
        "(" in normalized or ")" in normalized
    )

    def _build_special_path_error_result(
        exc: FileNotFoundError | KeyError | TypeError | ValueError,
        parsed: dict,
        grouped_boolean_used: bool,
    ) -> QueryResult:
        route = parsed.get("route")
        if isinstance(exc, FileNotFoundError):
            reason = "no_data"
        elif isinstance(exc, ValueError):
            reason = "unsupported"
        elif route is None:
            reason = "unrouted"
        else:
            reason = "error"
        notes = [str(exc)] if isinstance(exc, ValueError) else []
        result = NoResult(
            query_class=route_to_query_class(route),
            reason=reason,
            result_status=reason_to_status(reason),
            notes=notes,
        )
        return _finalize_natural_query_result(
            result,
            parsed,
            query,
            grouped_boolean_used=grouped_boolean_used,
            boolean_query_used=True,
        )

    # -- Grouped boolean path --
    if grouped_boolean_used:
        # Guarantee parsed is always assigned before the execution try block.
        parsed = _build_parse_state(query)
        try:
            parsed = parse_query(query)
        except ValueError:
            pass  # keep _build_parse_state result
        condition_text = _extract_grouped_condition_text(
            query,
            player=parsed.get("player"),
            team=parsed.get("team"),
        )
        try:
            parsed["boolean_filter_mode"] = boolean_filter_mode(condition_text)
            result = _execute_grouped_boolean_build_result(condition_text, parsed)
        except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
            return _build_special_path_error_result(exc, parsed, grouped_boolean_used=True)

        return _finalize_natural_query_result(
            result,
            parsed,
            query,
            grouped_boolean_used=True,
            boolean_query_used=True,
        )

    # -- OR query path --
    if contains_boolean_or(normalized):
        try:
            result, parsed = _execute_or_query_build_result(query)
            parsed["boolean_filter_mode"] = "any"
        except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
            try:
                parsed = parse_query(query)
            except ValueError:
                parsed = _build_parse_state(query)
            parsed["boolean_filter_mode"] = "any"
            return _build_special_path_error_result(exc, parsed, grouped_boolean_used=False)

        return _finalize_natural_query_result(
            result,
            parsed,
            query,
            grouped_boolean_used=False,
            boolean_query_used=True,
        )

    # -- Standard query path --
    try:
        parsed = parse_query(query)
    except ValueError:
        parsed = _build_parse_state(query)
        metadata = _build_query_metadata(parsed, query, grouped_boolean_used=False)
        result = NoResult(query_class="unknown", reason="unrouted", result_status="error")
        return QueryResult(
            result=result,
            metadata=metadata,
            query=query,
            route=None,
        )

    route = parsed["route"]
    kwargs = parsed["route_kwargs"]
    extra_conditions = parsed.get("extra_conditions", [])

    unsupported_filters = kwargs.get("unsupported_filters")
    if route is None and unsupported_filters:
        metadata = _build_query_metadata(parsed, query, grouped_boolean_used=False)
        normalized_filters = [str(value) for value in unsupported_filters if str(value)]
        notes = list(parsed.get("notes") or [])
        if normalized_filters:
            note = _unsupported_filter_note(normalized_filters[0], normalized_filters)
            if note not in notes:
                notes.append(note)
        result = NoResult(
            query_class="unknown",
            reason="filter_not_supported",
            result_status="no_result",
            result_reason="filter_not_supported",
            notes=notes,
        )
        _merge_metadata_notes(metadata, notes)
        return QueryResult(
            result=result,
            metadata=metadata,
            query=query,
            route=None,
        )

    # -- Entity ambiguity: return structured ambiguity result --
    entity_ambiguity = parsed.get("entity_ambiguity")
    if entity_ambiguity and route is None:
        metadata = _build_query_metadata(parsed, query, grouped_boolean_used=False)
        notes = parsed.get("notes", [])

        # Pattern 8: enrich the entity_ambiguity payload.
        enriched_ambiguity = dict(entity_ambiguity)
        ambiguity_source = entity_ambiguity.get("source", "")
        if ambiguity_source not in ("ambiguous_fragment", "placeholder_template"):
            # Player / team name matched multiple candidates — add structured
            # candidate list so callers can present a disambiguation picker.
            raw_candidates = entity_ambiguity.get("candidates", [])
            structured_candidates = []
            for name in raw_candidates:
                ctx = _resolve_player_context(name) or {}
                structured_candidates.append(
                    {
                        "id": ctx.get("player_id"),
                        "display_name": ctx.get("player_name", name),
                        "team_abbr": ctx.get("team_abbr"),
                        "position": ctx.get("position"),
                    }
                )
            enriched_ambiguity["candidates"] = structured_candidates
            if structured_candidates:
                metadata["candidates"] = structured_candidates
        else:
            # Ambiguous fragment / intent — add suggested_queries so callers
            # can surface concrete alternatives.
            suggested_queries = _build_suggested_queries_for_fragment(parsed)
            enriched_ambiguity["suggested_queries"] = suggested_queries
            if suggested_queries:
                metadata["suggested_queries"] = suggested_queries
        metadata["entity_ambiguity"] = enriched_ambiguity

        result = NoResult(
            query_class="unknown",
            reason="ambiguous",
            result_status="no_result",
            result_reason="ambiguous",
            notes=list(notes),
            metadata={"entity_ambiguity": enriched_ambiguity},
        )
        return QueryResult(
            result=result,
            metadata=metadata,
            query=query,
            route=None,
        )

    try:
        result = _execute_build_result(route, kwargs, extra_conditions)
    except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, FileNotFoundError):
            reason = "no_data"
        elif isinstance(exc, ValueError):
            reason = "unsupported"
        elif route is None:
            reason = "unrouted"
        else:
            reason = "error"
        notes: list[str] = []
        if isinstance(exc, ValueError):
            notes = [str(exc)]
        result = NoResult(
            query_class=route_to_query_class(route),
            reason=reason,
            result_status=reason_to_status(reason),
            notes=notes,
        )
        return _finalize_natural_query_result(
            result,
            parsed,
            query,
            grouped_boolean_used=False,
        )

    return _finalize_natural_query_result(
        result,
        parsed,
        query,
        grouped_boolean_used=False,
    )


# ---------------------------------------------------------------------------
# Structured query entry point
# ---------------------------------------------------------------------------

# Valid route names — the same set used by the build_result map.
VALID_ROUTES = frozenset(
    [
        "top_player_games",
        "top_team_games",
        "season_leaders",
        "season_team_leaders",
        "player_game_summary",
        "game_summary",
        "player_game_finder",
        "game_finder",
        "player_compare",
        "team_compare",
        "team_record",
        "team_matchup_record",
        "team_record_leaderboard",
        "player_split_summary",
        "team_split_summary",
        "player_streak_finder",
        "team_streak_finder",
        "player_occurrence_leaders",
        "team_occurrence_leaders",
        "player_on_off",
        "lineup_summary",
        "lineup_leaderboard",
        "player_stretch_leaderboard",
        "team_stretch_leaderboard",
        "playoff_history",
        "playoff_appearances",
        "playoff_matchup_history",
        "playoff_round_record",
        "playoff_series_comebacks",
        "record_by_decade",
        "record_by_decade_leaderboard",
        "matchup_by_decade",
    ]
)


def execute_structured_query(route: str, **kwargs: Any) -> QueryResult:
    """Execute a structured query against one request-pinned data generation."""
    with data_generation_context():
        return _execute_structured_query_in_generation(route, **kwargs)


def _execute_structured_query_in_generation(route: str, **kwargs: Any) -> QueryResult:
    """Execute a structured (route-based) query and return a result.

    This is the primary entry point for programmatic / structured queries.
    The caller specifies the route name and keyword arguments directly
    instead of relying on natural-language parsing.

    Parameters
    ----------
    route : str
        One of the known route names (e.g. ``"player_game_summary"``).
    **kwargs
        Arguments forwarded to the matching ``build_result()`` function.

    Returns
    -------
    QueryResult
        An envelope containing the structured result and metadata.

    Raises
    ------
    ValueError
        If *route* is not a recognised route name.
    """
    if route not in VALID_ROUTES:
        result = NoResult(
            query_class="unknown",
            reason="unsupported",
            result_status="no_result",
            notes=[f"Unknown route {route!r}. Valid routes: {sorted(VALID_ROUTES)}"],
        )
        return QueryResult(
            result=result,
            metadata={"route": route},
            query=f"structured:{route}",
            route=route,
        )

    query_class = route_to_query_class(route)

    # Build metadata from kwargs
    player_a = kwargs.get("player_a")
    player_b = kwargs.get("player_b")
    player = kwargs.get("player")
    if not player and player_a and player_b:
        player = f"{player_a}, {player_b}"
    elif not player:
        player = player_a or player_b

    team_a = kwargs.get("team_a")
    team_b = kwargs.get("team_b")
    team = kwargs.get("team")
    if not team and team_a and team_b:
        team = f"{team_a}, {team_b}"
    elif not team:
        team = team_a or team_b

    # current_through
    current_through: str | None = None
    season = kwargs.get("season")
    start_season = kwargs.get("start_season")
    end_season = kwargs.get("end_season")
    season_type = kwargs.get("season_type") or "Regular Season"

    if season:
        current_through = compute_current_through_for_seasons([season], season_type)
    elif start_season and end_season:
        from nbatools.commands._seasons import int_to_season, season_to_int

        seasons = [
            int_to_season(y)
            for y in range(season_to_int(start_season), season_to_int(end_season) + 1)
        ]
        current_through = compute_current_through_for_seasons(seasons, season_type)

    unsupported_filters = kwargs.get("unsupported_filters")

    metadata: dict[str, Any] = {
        "route": route,
        "query_class": query_class,
        "season": season,
        "start_season": start_season,
        "end_season": end_season,
        "season_type": kwargs.get("season_type"),
        "start_date": kwargs.get("start_date"),
        "end_date": kwargs.get("end_date"),
        "player": player,
        "team": team,
        "opponent": kwargs.get("opponent"),
        "opponent_conference": kwargs.get("opponent_conference"),
        "opponent_division": kwargs.get("opponent_division"),
        "opponent_team_abbrs": kwargs.get("opponent_team_abbrs"),
        "with_player": kwargs.get("with_player"),
        "without_player": kwargs.get("without_player"),
        "unresolved_availability_player": kwargs.get("unresolved_availability_player"),
        "unsupported_filters": unsupported_filters,
        "opponent_quality": kwargs.get("opponent_quality"),
        "lineup_members": kwargs.get("lineup_members"),
        "presence_state": kwargs.get("presence_state"),
        "unit_size": kwargs.get("unit_size"),
        "minute_minimum": kwargs.get("minute_minimum"),
        "window_size": kwargs.get("window_size"),
        "stretch_metric": kwargs.get("stretch_metric"),
        "stretch_display_mode": _stretch_display_mode_metadata(
            route,
            player=player,
            dedupe_players=kwargs.get("dedupe_players"),
        ),
        "stat": kwargs.get("stat"),
        "min_value": kwargs.get("min_value"),
        "max_value": kwargs.get("max_value"),
        "conditions": kwargs.get("conditions"),
        "sort_by": kwargs.get("sort_by"),
        "ascending": kwargs.get("ascending"),
        "ranked_intent": kwargs.get("sort_by") == "stat",
        "split_type": kwargs.get("split"),
        "clutch": kwargs.get("clutch"),
        "back_to_back": kwargs.get("back_to_back"),
        "series_situation": kwargs.get("series_situation"),
        "rest_days": kwargs.get("rest_days"),
        "one_possession": kwargs.get("one_possession"),
        "nationally_televised": kwargs.get("nationally_televised"),
        "role": kwargs.get("role"),
        "quarter": kwargs.get("quarter"),
        "half": kwargs.get("half"),
        "position_filter": kwargs.get("position"),
        "head_to_head_used": bool(kwargs.get("head_to_head")),
    }
    if current_through is not None:
        metadata["current_through"] = current_through

    applied_filters = [] if unsupported_filters else _build_applied_filters(kwargs)
    if applied_filters:
        metadata["applied_filters"] = applied_filters

    player_values = [value for value in [player_a, player_b] if value]
    if not player_values and player:
        player_values = [player]
    team_values = [value for value in [team_a, team_b] if value]
    if not team_values and team:
        team_values = [team]
    _add_identity_contexts(
        metadata,
        player_values=player_values,
        team_values=team_values,
        opponent_value=kwargs.get("opponent"),
    )

    query_desc = f"structured:{route}"

    try:
        result = _execute_build_result(route, kwargs)
    except FileNotFoundError:
        result = NoResult(query_class=query_class, reason="no_data")
        return QueryResult(
            result=result,
            metadata=metadata,
            query=query_desc,
            route=route,
        )
    except ValueError as exc:
        result = NoResult(
            query_class=query_class,
            reason="unsupported",
            result_status="no_result",
            notes=[str(exc)],
        )
        return QueryResult(
            result=result,
            metadata=metadata,
            query=query_desc,
            route=route,
        )

    _add_game_summary_answer_metadata(metadata, result)
    _add_team_stretch_answer_metadata(metadata, result)
    _add_player_stretch_answer_metadata(metadata, result)
    _add_playoff_history_answer_metadata(metadata, result)
    _add_titles_leaderboard_answer_metadata(metadata, result)

    if getattr(result, "notes", None):
        _merge_metadata_notes(metadata, list(result.notes))

    return QueryResult(
        result=result,
        metadata=metadata,
        query=query_desc,
        route=route,
    )
