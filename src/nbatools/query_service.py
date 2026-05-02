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

import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

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
        "opponent_quality": parsed.get("opponent_quality"),
        "lineup_members": parsed.get("lineup_members"),
        "presence_state": parsed.get("presence_state"),
        "unit_size": parsed.get("unit_size"),
        "minute_minimum": parsed.get("minute_minimum"),
        "window_size": parsed.get("window_size"),
        "stretch_metric": parsed.get("stretch_metric"),
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


# ---------------------------------------------------------------------------
# Query envelope
# ---------------------------------------------------------------------------

# Reasons that represent expected/anticipated failures → no_result status.
# All other reasons represent system-level failures → error status.
_EXPECTED_REASONS: frozenset[str] = frozenset({"unsupported", "no_data", "no_match", "ambiguous"})


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
        result = NoResult(
            query_class="unknown",
            reason="ambiguous",
            result_status="no_result",
            result_reason="ambiguous",
            notes=list(notes),
            metadata={"entity_ambiguity": entity_ambiguity},
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
        "opponent_quality": kwargs.get("opponent_quality"),
        "lineup_members": kwargs.get("lineup_members"),
        "presence_state": kwargs.get("presence_state"),
        "unit_size": kwargs.get("unit_size"),
        "minute_minimum": kwargs.get("minute_minimum"),
        "window_size": kwargs.get("window_size"),
        "stretch_metric": kwargs.get("stretch_metric"),
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

    if getattr(result, "notes", None):
        _merge_metadata_notes(metadata, list(result.notes))

    return QueryResult(
        result=result,
        metadata=metadata,
        query=query_desc,
        route=route,
    )
