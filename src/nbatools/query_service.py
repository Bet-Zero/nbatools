"""Query service / engine facade for nbatools.

This module is the primary entry point for executing NBA queries
programmatically.  Both natural-language and structured (route-based)
queries are supported and return structured result objects directly.

A future UI or API layer should call the functions here instead of
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
``StreakResult``, ``SplitSummaryResult``, ``NoResult``).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from nbatools.commands._constants import contains_boolean_or
from nbatools.commands._natural_query_execution import (
    _execute_build_result,
    _execute_grouped_boolean_build_result,
    _execute_or_query_build_result,
    _extract_grouped_condition_text,
)
from nbatools.commands.entity_resolution import resolve_team
from nbatools.commands.format_output import route_to_query_class
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.natural_query import (
    _build_parse_state,
    normalize_text,
    parse_query,
)
from nbatools.commands.query_boolean_parser import expression_contains_boolean_ops

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
from nbatools.data_source import data_glob, data_read_csv_dicts

_COUNT_THRESHOLD_EPSILON = 0.0001

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
def _player_identity_lookup() -> dict[str, dict[str, Any]]:
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
def _team_identity_lookup() -> dict[str, dict[str, Any]]:
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
    context = _player_identity_lookup().get(key)
    return dict(context) if context else None


def _resolve_team_context(team_value: Any) -> dict[str, Any] | None:
    text = _clean_text(team_value)
    if text is None:
        return None

    lookup = _team_identity_lookup()
    resolved = resolve_team(text)
    candidates: list[str] = []
    if resolved.is_confident and resolved.resolved:
        candidates.append(resolved.resolved)
    candidates.append(text)

    for candidate in candidates:
        context = lookup.get(_identity_key(candidate))
        if context:
            return dict(context)
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


def _build_applied_filters(
    source: dict[str, Any],
    *,
    route_kwargs: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    route_kwargs = route_kwargs or {}
    applied_filters: list[dict[str, str]] = []

    if source.get("opponent"):
        applied_filters.append({"label": "Opponent", "value": source["opponent"], "kind": "team"})
    if source.get("without_player"):
        applied_filters.append(
            {"label": "Without player", "value": source["without_player"], "kind": "player"}
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
        label = "OPP PTS min" if stat == "opponent_pts" else f"{stat} min"
        applied_filters.append({"label": label, "value": str(min_value), "kind": "threshold"})
    if stat and max_value is not None:
        label = "OPP PTS max" if stat == "opponent_pts" else f"{stat} max"
        applied_filters.append({"label": label, "value": str(max_value), "kind": "threshold"})
    if source.get("start_season") and source.get("end_season"):
        applied_filters.append(
            {
                "label": "Season range",
                "value": f"{source['start_season']} – {source['end_season']}",
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

    This mirrors ``_build_metadata_dict`` in natural_query.py but is
    decoupled from CLI-specific concerns.
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
        "season_type": parsed.get("season_type"),
        "start_date": parsed.get("start_date"),
        "end_date": parsed.get("end_date"),
        "player": player,
        "team": team,
        "opponent": parsed.get("opponent"),
        "without_player": parsed.get("without_player"),
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
        "stat": parsed.get("stat") or route_kwargs.get("stat"),
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
        "ranked_intent": bool(
            parsed.get("leaderboard_intent")
            or parsed.get("season_high_intent")
            or parsed.get("top_n")
        ),
        "threshold_conditions": parsed.get("threshold_conditions"),
        "extra_conditions": parsed.get("extra_conditions"),
        "occurrence_event": parsed.get("occurrence_event"),
        "split_type": parsed.get("split_type"),
        "clutch": parsed.get("clutch"),
        "back_to_back": parsed.get("back_to_back"),
        "rest_days": parsed.get("rest_days"),
        "one_possession": parsed.get("one_possession"),
        "nationally_televised": parsed.get("nationally_televised"),
        "role": parsed.get("role"),
        "quarter": parsed.get("quarter"),
        "half": parsed.get("half"),
        "position_filter": parsed.get("position_filter"),
        "grouped_boolean_used": grouped_boolean_used,
        "head_to_head_used": bool(parsed.get("head_to_head")),
    }

    if current_through is not None:
        meta["current_through"] = current_through

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
    applied_filters = _build_applied_filters(parsed, route_kwargs=route_kwargs)
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
    if metadata.get("stat") == "opponent_pts" and team:
        threshold = _count_threshold_text(metadata.get("max_value"))
        entity = _team_subject(metadata)
        context = _count_context(metadata, player=bool(player))
        times = "time" if count == 1 else "times"
        record = _record_suffix(games)
        return (
            f"{entity} have held opponents under {threshold} points "
            f"{count} {times} {context}{record}."
        )

    entity = player or _team_subject(metadata) or "Result"
    occurrence = _occurrence_label(parsed.get("occurrence_event") or parsed.get("stat"))
    count_noun = occurrence if count == 1 else pluralize_occurrence(occurrence)
    context = _count_context(metadata, player=bool(player))
    verb = "has had" if count_noun.startswith("games with ") else "has recorded"
    return f"{entity} {verb} {count} {count_noun} {context}."


def _team_subject(metadata: dict) -> str | None:
    team_context = metadata.get("team_context")
    if isinstance(team_context, dict):
        team_name = _clean_text(team_context.get("team_name"))
        if team_name:
            return f"The {team_name}"
    team = _clean_text(metadata.get("team"))
    return f"The {team}" if team else None


def _count_context(metadata: dict, *, player: bool) -> str:
    query_text = (_clean_text(metadata.get("query_text")) or "").lower()
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
            if isinstance(min_value, (int, float)):
                return f"games with {compact_number(min_value)}+ {stat_name}"
            if isinstance(max_value, (int, float)):
                return f"games with <= {compact_number(max_value)} {stat_name}"
            return f"games with {stat_name}"

    if isinstance(occurrence, str) and occurrence:
        return occurrence.replace("_", "-")
    return "game"


def pluralize_occurrence(label: str) -> str:
    if label.startswith("games with "):
        return label
    if label.endswith("s"):
        return label
    return f"{label}s"


def stat_phrase_label(stat: str) -> str:
    labels = {
        "ast": "assists",
        "blk": "blocks",
        "fg3m": "threes",
        "pts": "points",
        "reb": "rebounds",
        "stl": "steals",
        "tov": "turnovers",
    }
    return labels.get(stat.lower(), stat.replace("_", " "))


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
    {"unsupported", "no_data", "no_match", "ambiguous", "filter_not_supported"}
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


# ---------------------------------------------------------------------------
# Natural query entry point
# ---------------------------------------------------------------------------


def execute_natural_query(query: str) -> QueryResult:
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
        metadata = _build_query_metadata(parsed, query, grouped_boolean_used=grouped_boolean_used)
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
        return QueryResult(
            result=result,
            metadata=metadata,
            query=query,
            route=route,
        )

    # -- Grouped boolean path --
    if grouped_boolean_used:
        # Guarantee parsed is always assigned before the execution try block.
        parsed = _build_parse_state(query)
        try:
            parsed = parse_query(query)
        except ValueError:
            pass  # keep _build_parse_state result
        condition_text = _extract_grouped_condition_text(query)
        try:
            result = _execute_grouped_boolean_build_result(condition_text, parsed)
        except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
            return _build_special_path_error_result(exc, parsed, grouped_boolean_used=True)

        metadata = _build_query_metadata(parsed, query, grouped_boolean_used=True)
        return QueryResult(
            result=result,
            metadata=metadata,
            query=query,
            route=parsed.get("route"),
        )

    # -- OR query path --
    if contains_boolean_or(normalized):
        try:
            result, parsed = _execute_or_query_build_result(query)
        except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
            try:
                parsed = parse_query(query)
            except ValueError:
                parsed = _build_parse_state(query)
            return _build_special_path_error_result(exc, parsed, grouped_boolean_used=False)

        metadata = _build_query_metadata(parsed, query, grouped_boolean_used=False)
        return QueryResult(
            result=result,
            metadata=metadata,
            query=query,
            route=parsed.get("route"),
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
    count_intent = parsed.get("count_intent", False)

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
        metadata = _build_query_metadata(parsed, query, grouped_boolean_used=False)
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
        return QueryResult(
            result=result,
            metadata=metadata,
            query=query,
            route=route,
        )

    # Post-process: convert FinderResult → CountResult when count intent detected
    if count_intent and isinstance(result, FinderResult):
        result = CountResult(
            count=len(result.games),
            games=result.games,
            result_status=result.result_status,
            result_reason=result.result_reason,
            current_through=result.current_through,
            metadata=result.metadata,
            notes=result.notes,
            caveats=result.caveats,
        )
    elif count_intent and isinstance(result, LeaderboardResult):
        # Occurrence count for a specific player or team routed through
        # player_occurrence_leaders or team_occurrence_leaders.
        # Extract the entity's row and return the occurrence count.
        player_name = parsed.get("player")
        team_name = kwargs.get("team")  # Team filter passed to occurrence_leaders
        entity_count = 0

        if not result.leaders.empty:
            if parsed.get("distinct_player_count") or parsed.get("distinct_team_count"):
                entity_count = len(result.leaders)
            # Try player first
            elif player_name and "player_name" in result.leaders.columns:
                match = result.leaders[
                    result.leaders["player_name"].str.upper() == player_name.upper()
                ]
                if not match.empty:
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
                    event_cols = [c for c in match.columns if c not in skip_cols]
                    if event_cols:
                        entity_count = int(match.iloc[0][event_cols[0]])
            # Try team (for team occurrence counts)
            elif team_name:
                team_upper = team_name.upper()
                team_match = None
                for col in ["team_abbr", "team_name"]:
                    if col in result.leaders.columns:
                        team_match = result.leaders[
                            result.leaders[col].astype(str).str.upper() == team_upper
                        ]
                        if not team_match.empty:
                            break
                if team_match is not None and not team_match.empty:
                    skip_cols = {
                        "rank",
                        "team_abbr",
                        "team_name",
                        "games_played",
                        "season",
                        "seasons",
                        "season_type",
                    }
                    event_cols = [c for c in team_match.columns if c not in skip_cols]
                    if event_cols:
                        entity_count = int(team_match.iloc[0][event_cols[0]])
            # Fallback: if there's exactly one row, use it (single entity filter worked)
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
                event_cols = [c for c in result.leaders.columns if c not in skip_cols]
                if event_cols:
                    entity_count = int(result.leaders.iloc[0][event_cols[0]])

        result = CountResult(
            count=entity_count,
            result_status=result.result_status,
            result_reason=result.result_reason,
            current_through=result.current_through,
            metadata=result.metadata,
            notes=result.notes,
            caveats=result.caveats,
        )
    elif count_intent and isinstance(result, NoResult):
        result = CountResult(
            count=0,
            result_status="ok",
            notes=result.notes,
            caveats=result.caveats,
        )

    metadata = _build_query_metadata(parsed, query, grouped_boolean_used=False)
    # Override query_class in metadata when count intent is active
    if count_intent:
        metadata["query_class"] = "count"
    # Pattern 3: expose primary_count and count_phrase for count-flavored queries.
    if count_intent and isinstance(result, CountResult):
        metadata["primary_count"] = result.count
        metadata["count_phrase"] = _build_count_phrase(
            result.count,
            parsed,
            metadata,
            result.games,
        )
    _add_game_summary_answer_metadata(metadata, result)
    if getattr(result, "notes", None):
        _merge_metadata_notes(metadata, list(result.notes))
    return QueryResult(
        result=result,
        metadata=metadata,
        query=query,
        route=route,
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
        "playoff_history",
        "playoff_appearances",
        "playoff_matchup_history",
        "playoff_round_record",
        "record_by_decade",
        "record_by_decade_leaderboard",
        "matchup_by_decade",
    ]
)


def execute_structured_query(route: str, **kwargs: Any) -> QueryResult:
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
        "without_player": kwargs.get("without_player"),
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
        "sort_by": kwargs.get("sort_by"),
        "ranked_intent": kwargs.get("sort_by") == "stat",
        "split_type": kwargs.get("split"),
        "clutch": kwargs.get("clutch"),
        "back_to_back": kwargs.get("back_to_back"),
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

    applied_filters = _build_applied_filters(kwargs)
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

    if getattr(result, "notes", None):
        _merge_metadata_notes(metadata, list(result.notes))

    return QueryResult(
        result=result,
        metadata=metadata,
        query=query_desc,
        route=route,
    )
