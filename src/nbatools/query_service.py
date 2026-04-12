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

from dataclasses import dataclass, field
from typing import Any

from nbatools.commands.format_output import route_to_query_class
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.natural_query import (
    _build_parse_state,
    _execute_build_result,
    _execute_grouped_boolean_build_result,
    _execute_or_query_build_result,
    _get_build_result_map,
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

# ---------------------------------------------------------------------------
# Metadata helper
# ---------------------------------------------------------------------------


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

    player = parsed.get("player")
    if not player:
        player_a = parsed.get("player_a")
        player_b = parsed.get("player_b")
        if player_a and player_b:
            player = f"{player_a}, {player_b}"
        else:
            player = player_a or player_b

    team = parsed.get("team")
    if not team:
        team_a = parsed.get("team_a")
        team_b = parsed.get("team_b")
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
        "split_type": parsed.get("split_type"),
        "position_filter": parsed.get("position_filter"),
        "grouped_boolean_used": grouped_boolean_used,
        "head_to_head_used": bool(parsed.get("head_to_head")),
    }

    if current_through is not None:
        meta["current_through"] = current_through

    if notes:
        meta["notes"] = notes

    return meta


# ---------------------------------------------------------------------------
# Query envelope
# ---------------------------------------------------------------------------


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

    # -- Grouped boolean path --
    if grouped_boolean_used:
        try:
            result = _execute_grouped_boolean_build_result(query)
        except Exception:
            result = NoResult(query_class="finder", reason="error")

        try:
            parsed = parse_query(query)
        except Exception:
            parsed = _build_parse_state(query)

        metadata = _build_query_metadata(parsed, query, grouped_boolean_used=True)
        return QueryResult(
            result=result,
            metadata=metadata,
            query=query,
            route=parsed.get("route"),
        )

    # -- OR query path --
    if " or " in normalized:
        try:
            result = _execute_or_query_build_result(query)
        except Exception:
            result = NoResult(query_class="finder", reason="error")

        try:
            parsed = parse_query(query)
        except Exception:
            parsed = _build_parse_state(query)

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
    except (FileNotFoundError, KeyError, TypeError) as exc:
        metadata = _build_query_metadata(parsed, query, grouped_boolean_used=False)
        if isinstance(exc, FileNotFoundError):
            reason = "no_data"
        elif route is None:
            reason = "unrouted"
        else:
            reason = "error"
        result = NoResult(query_class=route_to_query_class(route), reason=reason)
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
        # Occurrence count for a specific player routed through
        # player_occurrence_leaders — extract the player's row.
        player_name = parsed.get("player")
        player_count = 0
        if player_name and not result.leaders.empty:
            # Find this player in the leaderboard
            if "player_name" in result.leaders.columns:
                match = result.leaders[
                    result.leaders["player_name"].str.upper() == player_name.upper()
                ]
                if not match.empty:
                    # The event-count column is the one that's not rank/player_name/team_abbr/etc.
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
                        player_count = int(match.iloc[0][event_cols[0]])
        result = CountResult(
            count=player_count,
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
        "player_split_summary",
        "team_split_summary",
        "player_streak_finder",
        "team_streak_finder",
        "player_occurrence_leaders",
        "team_occurrence_leaders",
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
        raise ValueError(f"Unknown route {route!r}. Valid routes: {sorted(VALID_ROUTES)}")

    build_map = _get_build_result_map()
    build_fn = build_map[route]

    query_class = route_to_query_class(route)

    # Build metadata from kwargs
    player = kwargs.get("player")
    player_a = kwargs.get("player_a")
    player_b = kwargs.get("player_b")
    if not player and player_a and player_b:
        player = f"{player_a}, {player_b}"
    elif not player:
        player = player_a or player_b

    team = kwargs.get("team")
    team_a = kwargs.get("team_a")
    team_b = kwargs.get("team_b")
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
        "split_type": kwargs.get("split"),
        "position_filter": kwargs.get("position"),
        "head_to_head_used": bool(kwargs.get("head_to_head")),
    }
    if current_through is not None:
        metadata["current_through"] = current_through

    query_desc = f"structured:{route}"

    try:
        result = build_fn(**kwargs)
    except FileNotFoundError:
        result = NoResult(query_class=query_class, reason="no_data")
        return QueryResult(
            result=result,
            metadata=metadata,
            query=query_desc,
            route=route,
        )

    return QueryResult(
        result=result,
        metadata=metadata,
        query=query_desc,
        route=route,
    )
