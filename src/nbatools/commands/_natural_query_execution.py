"""Execution, runtime, and orchestration helpers for natural query processing.

Extracted from natural_query.py to separate execution/result-manipulation
concerns from parsing and route selection.

This module contains:
- build_result map management
- result DataFrame accessors (get/set primary df)
- extra-condition post-filtering
- single-route execution
- OR-query execution and result combination
- grouped-boolean execution
- grouped-base-DataFrame loaders
- grouped-condition-text extraction
- CLI rendering/export wrapper
"""

from __future__ import annotations

import copy
import re
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from nbatools.commands._constants import normalize_text
from nbatools.commands._parse_helpers import (
    build_game_context_filter_notes,
    build_period_filter_note,
    build_role_filter_note,
)
from nbatools.commands.entity_resolution import PLAYER_ALIASES, TEAM_ALIASES
from nbatools.commands.format_output import (
    build_error_output,
    build_no_result_output,
    format_pretty_from_result,
    route_to_query_class,
    wrap_result_with_metadata,
    write_csv_from_result,
    write_json_from_result,
)
from nbatools.commands.game_finder import build_result as game_finder_build_result
from nbatools.commands.game_summary import (
    _apply_filters as apply_team_summary_filters,
)
from nbatools.commands.game_summary import (
    build_result as game_summary_build_result,
)
from nbatools.commands.game_summary import (
    load_team_games_for_seasons as load_team_summary_games,
)
from nbatools.commands.game_summary import (
    resolve_seasons as resolve_team_summary_seasons,
)
from nbatools.commands.player_compare import (
    build_result as player_compare_build_result,
)
from nbatools.commands.player_game_finder import (
    build_result as player_game_finder_build_result,
)
from nbatools.commands.player_game_summary import (
    _apply_filters as apply_player_summary_filters,
)
from nbatools.commands.player_game_summary import (
    build_result as player_game_summary_build_result,
)
from nbatools.commands.player_game_summary import (
    load_player_games_for_seasons as load_player_summary_games,
)
from nbatools.commands.player_game_summary import (
    resolve_seasons as resolve_player_summary_seasons,
)
from nbatools.commands.player_occurrence_leaders import (
    build_result as player_occurrence_leaders_build_result,
)
from nbatools.commands.player_split_summary import (
    build_result as player_split_summary_build_result,
)
from nbatools.commands.player_streak_finder import (
    build_result as player_streak_finder_build_result,
)
from nbatools.commands.playoff_history import (
    build_matchup_by_decade_result,
    build_playoff_appearances_result,
    build_playoff_history_result,
    build_playoff_matchup_history_result,
    build_playoff_round_record_result,
    build_record_by_decade_leaderboard_result,
    build_record_by_decade_result,
)
from nbatools.commands.query_boolean_parser import (
    evaluate_condition_tree,
    expression_contains_boolean_ops,
    parse_condition_text,
)
from nbatools.commands.season_leaders import (
    build_result as season_leaders_build_result,
)
from nbatools.commands.season_team_leaders import (
    build_result as season_team_leaders_build_result,
)
from nbatools.commands.structured_results import (
    FinderResult,
    LeaderboardResult,
    NoResult,
    StreakResult,
)
from nbatools.commands.team_compare import (
    build_result as team_compare_build_result,
)
from nbatools.commands.team_occurrence_leaders import (
    build_result as team_occurrence_leaders_build_result,
)
from nbatools.commands.team_record import (
    build_matchup_record_result,
    build_record_leaderboard_result,
    build_team_record_result,
)
from nbatools.commands.team_split_summary import (
    build_result as team_split_summary_build_result,
)
from nbatools.commands.team_streak_finder import (
    build_result as team_streak_finder_build_result,
)
from nbatools.commands.top_player_games import (
    build_result as top_player_games_build_result,
)
from nbatools.commands.top_team_games import (
    build_result as top_team_games_build_result,
)

# ---------------------------------------------------------------------------
# build_result map
# ---------------------------------------------------------------------------
# Maps route name → build_result callable, used by the orchestration layer.

_BUILD_RESULT_MAP: dict[str, Callable] = {}

# ---------------------------------------------------------------------------
# Precomputed alias sequences (length-descending) for condition text extraction
# ---------------------------------------------------------------------------
# Sorted once at import time so _extract_grouped_condition_text doesn't re-sort
# on every call.

_SORTED_PLAYER_ALIAS_NAMES: list[str] = sorted(PLAYER_ALIASES.keys(), key=len, reverse=True)
_SORTED_TEAM_ALIAS_NAMES: list[str] = sorted(TEAM_ALIASES.keys(), key=len, reverse=True)


def _get_build_result_map() -> dict[str, Callable]:
    if not _BUILD_RESULT_MAP:
        _BUILD_RESULT_MAP.update(
            {
                "top_player_games": top_player_games_build_result,
                "top_team_games": top_team_games_build_result,
                "season_leaders": season_leaders_build_result,
                "season_team_leaders": season_team_leaders_build_result,
                "player_game_summary": player_game_summary_build_result,
                "game_summary": game_summary_build_result,
                "player_game_finder": player_game_finder_build_result,
                "game_finder": game_finder_build_result,
                "player_compare": player_compare_build_result,
                "team_compare": team_compare_build_result,
                "team_record": build_team_record_result,
                "team_matchup_record": build_matchup_record_result,
                "team_record_leaderboard": build_record_leaderboard_result,
                "player_split_summary": player_split_summary_build_result,
                "team_split_summary": team_split_summary_build_result,
                "player_streak_finder": player_streak_finder_build_result,
                "team_streak_finder": team_streak_finder_build_result,
                "player_occurrence_leaders": player_occurrence_leaders_build_result,
                "team_occurrence_leaders": team_occurrence_leaders_build_result,
                "playoff_history": build_playoff_history_result,
                "playoff_appearances": build_playoff_appearances_result,
                "playoff_matchup_history": build_playoff_matchup_history_result,
                "playoff_round_record": build_playoff_round_record_result,
                "record_by_decade": build_record_by_decade_result,
                "record_by_decade_leaderboard": build_record_by_decade_leaderboard_result,
                "matchup_by_decade": build_matchup_by_decade_result,
            }
        )
    return _BUILD_RESULT_MAP


# ---------------------------------------------------------------------------
# Helpers: work on result objects, not text
# ---------------------------------------------------------------------------


def _get_result_primary_df(result):
    """Extract the primary DataFrame from a structured result object."""
    if isinstance(result, FinderResult):
        return result.games
    if isinstance(result, LeaderboardResult):
        return result.leaders
    if isinstance(result, StreakResult):
        return result.streaks
    if isinstance(result, NoResult):
        return None
    # For summary/comparison/split: not applicable for tabular post-processing
    return None


def _set_result_primary_df(result, df):
    """Return a modified copy of a single-table result with a new DataFrame.

    Only applicable to FinderResult / LeaderboardResult / StreakResult.
    """
    new_result = copy.copy(result)
    if isinstance(result, FinderResult):
        new_result.games = df
    elif isinstance(result, LeaderboardResult):
        new_result.leaders = df
    elif isinstance(result, StreakResult):
        new_result.streaks = df
    return new_result


def _append_result_notes(result, notes: list[str]):
    """Append notes to a structured result without mutating the original."""
    if not notes:
        return result

    new_result = copy.copy(result)
    existing = list(getattr(new_result, "notes", []) or [])
    for note in notes:
        if note not in existing:
            existing.append(note)
    new_result.notes = existing
    return new_result


def _sanitize_unavailable_context_filters(kwargs: dict) -> tuple[dict, list[str]]:
    """Drop context-filter kwargs until the relevant data joins exist."""
    sanitized = dict(kwargs)
    quarter = sanitized.pop("quarter", None)
    half = sanitized.pop("half", None)
    back_to_back = sanitized.pop("back_to_back", False)
    rest_days = sanitized.pop("rest_days", None)
    one_possession = sanitized.pop("one_possession", False)
    nationally_televised = sanitized.pop("nationally_televised", False)
    role = sanitized.pop("role", None)

    notes: list[str] = []
    if period_note := build_period_filter_note(quarter=quarter, half=half):
        notes.append(period_note)
    notes.extend(
        build_game_context_filter_notes(
            back_to_back=back_to_back,
            rest_days=rest_days,
            one_possession=one_possession,
            nationally_televised=nationally_televised,
        )
    )
    if role_note := build_role_filter_note(role=role):
        notes.append(role_note)

    return sanitized, notes


def _apply_extra_conditions_to_result(result, extra_conditions: list[dict]):
    """Apply stat-threshold extra conditions directly to the result's DataFrame.

    Returns a modified result (or NoResult if the filtered DataFrame is empty).
    """
    if not extra_conditions:
        return result

    if isinstance(result, NoResult):
        return result

    df = _get_result_primary_df(result)
    if df is None:
        # Summary/comparison/split types don't support tabular post-filtering
        return result

    for cond in extra_conditions:
        stat = cond.get("stat")
        if not stat:
            return NoResult(query_class=getattr(result, "query_class", "finder"))
        if stat not in df.columns:
            return NoResult(query_class=getattr(result, "query_class", "finder"))
        if cond.get("min_value") is not None:
            df = df[df[stat] >= cond["min_value"]]
        if cond.get("max_value") is not None:
            df = df[df[stat] <= cond["max_value"]]

    if df.empty:
        return NoResult(query_class=getattr(result, "query_class", "finder"))

    return _set_result_primary_df(result, df)


def _execute_build_result(
    route: str,
    kwargs: dict,
    extra_conditions: list[dict] | None = None,
):
    """Build a structured result directly from a command's build_result()."""
    if extra_conditions is None:
        extra_conditions = []

    build_fn = _get_build_result_map()[route]
    sanitized_kwargs, notes = _sanitize_unavailable_context_filters(kwargs)
    result = build_fn(**sanitized_kwargs)
    result = _append_result_notes(result, notes)

    if extra_conditions:
        result = _apply_extra_conditions_to_result(result, extra_conditions)

    return result


def _combine_or_results(results: list):
    """Combine multiple finder-style results (for OR queries) into one FinderResult."""
    frames = []
    first_columns: list[str] | None = None
    query_class = "finder"

    for result in results:
        if isinstance(result, NoResult):
            continue
        df = _get_result_primary_df(result)
        if df is None or df.empty:
            continue
        query_class = getattr(result, "query_class", "finder")
        if first_columns is None:
            first_columns = list(df.columns)
        frames.append(df)

    if not frames:
        return NoResult(query_class=query_class)

    combined = pd.concat(frames, ignore_index=True)

    dedupe_keys = [c for c in ["game_id", "player_id", "team_id"] if c in combined.columns]
    if dedupe_keys:
        combined = combined.drop_duplicates(subset=dedupe_keys)
    else:
        combined = combined.drop_duplicates()

    if "game_date" in combined.columns:
        try:
            combined["_game_date_sort"] = pd.to_datetime(combined["game_date"], errors="coerce")
            sort_cols = ["_game_date_sort"]
            ascending = [False]
            if "game_id" in combined.columns:
                sort_cols.append("game_id")
                ascending.append(False)
            combined = combined.sort_values(sort_cols, ascending=ascending)
            combined = combined.drop(columns="_game_date_sort")
        except Exception:
            pass  # sorting is best-effort; failure here is cosmetic only

    if "rank" in combined.columns:
        combined = combined.drop(columns="rank")
        combined.insert(0, "rank", range(1, len(combined) + 1))

    if first_columns:
        ordered = [c for c in first_columns if c in combined.columns]
        extras = [c for c in combined.columns if c not in ordered]
        combined = combined[ordered + extras]

    return FinderResult(games=combined)


# ---------------------------------------------------------------------------
# OR-clause splitter (no natural_query dependency)
# ---------------------------------------------------------------------------


def _split_or_clauses(text: str) -> list[str]:
    text = normalize_text(text)
    if " or " not in text:
        return [text]

    raw_parts = re.split(r"\s+or\s+", text, flags=re.IGNORECASE)
    parts = [normalize_text(p) for p in raw_parts if normalize_text(p)]
    return parts if parts else [text]


def _execute_or_query_build_result(query: str) -> tuple:
    """Build a structured result for OR queries.

    Returns ``(result, parsed)`` so the caller can use the parsed state
    directly without re-parsing the query.

    ``_build_parse_state``, ``_merge_inherited_context``, and ``parse_query``
    are still imported lazily here because they depend on ``_finalize_route``
    and all of the parse-helper functions that live in ``natural_query.py``.
    Moving them cleanly requires extracting the full parsing layer into a
    dedicated module (a separate, larger cleanup pass).
    """
    # Lazy imports to avoid circular dependency with natural_query.py
    from nbatools.commands.natural_query import (
        _build_parse_state,
        _merge_inherited_context,
        parse_query,
    )

    clauses = _split_or_clauses(query)
    if len(clauses) <= 1:
        parsed = parse_query(query)
        result = _execute_build_result(
            parsed["route"], parsed["route_kwargs"], parsed.get("extra_conditions", [])
        )
        return result, parsed

    base = _build_parse_state(query)
    clause_parsed = [
        _merge_inherited_context(base, _build_parse_state(clause)) for clause in clauses
    ]

    allowed_routes = {"player_game_finder", "game_finder"}
    routes = {item["route"] for item in clause_parsed}
    if len(routes) != 1 or list(routes)[0] not in allowed_routes:
        raise ValueError(
            "Top-level OR is currently supported for finder-style queries, for example: "
            "'Jokic over 25 points or over 10 rebounds' or "
            "'Celtics over 120 points or over 15 threes'."
        )

    results = []
    for item in clause_parsed:
        results.append(
            _execute_build_result(
                item["route"], item["route_kwargs"], item.get("extra_conditions", [])
            )
        )

    return _combine_or_results(results), clause_parsed[0] if clause_parsed else base


def _execute_grouped_boolean_build_result(condition_text: str, parsed: dict):
    """Build a structured result for grouped boolean queries.

    ``parsed`` must be the result of ``parse_query(query)`` and is accepted as
    a parameter so the caller can supply it directly, avoiding a second
    ``parse_query`` call inside this function.

    ``condition_text`` must be the result of
    ``_extract_grouped_condition_text(query)`` and is accepted as a parameter
    so the caller controls all text pre-processing, keeping this function free
    of raw query string access.
    """
    route = parsed["route"]

    if route in {"player_game_summary", "player_split_summary"}:
        if not expression_contains_boolean_ops(condition_text):
            raise ValueError("No grouped boolean expression detected.")

        tree = parse_condition_text(condition_text)
        base_df = _load_grouped_player_base_df(parsed)

        if base_df.empty:
            qc = "summary" if route == "player_game_summary" else "split_summary"
            return NoResult(query_class=qc)

        filtered_df = evaluate_condition_tree(tree, base_df)

        if filtered_df.empty:
            qc = "summary" if route == "player_game_summary" else "split_summary"
            return NoResult(query_class=qc)

        build_fn = _get_build_result_map()[route]
        if route == "player_game_summary":
            return build_fn(
                season=parsed["season"],
                start_season=parsed["start_season"],
                end_season=parsed["end_season"],
                season_type=parsed["season_type"],
                player=parsed["player"],
                team=parsed["team"],
                opponent=parsed["opponent"],
                home_only=parsed["home_only"],
                away_only=parsed["away_only"],
                wins_only=parsed["wins_only"],
                losses_only=parsed["losses_only"],
                stat=None,
                min_value=None,
                max_value=None,
                last_n=None,
                df=filtered_df,
            )
        else:
            return build_fn(
                split=parsed["split_type"],
                season=parsed["season"],
                start_season=parsed["start_season"],
                end_season=parsed["end_season"],
                season_type=parsed["season_type"],
                player=parsed["player"],
                team=parsed["team"],
                opponent=parsed["opponent"],
                stat=None,
                min_value=None,
                max_value=None,
                last_n=None,
                df=filtered_df,
            )

    if route in {"game_summary", "team_split_summary"}:
        if not expression_contains_boolean_ops(condition_text):
            raise ValueError("No grouped boolean expression detected.")

        tree = parse_condition_text(condition_text)
        base_df = _load_grouped_team_base_df(parsed)

        if base_df.empty:
            return NoResult(query_class="summary" if route == "game_summary" else "split_summary")

        filtered_df = evaluate_condition_tree(tree, base_df)

        if filtered_df.empty:
            return NoResult(query_class="summary" if route == "game_summary" else "split_summary")

        build_fn = _get_build_result_map()[route]
        if route == "game_summary":
            return build_fn(
                season=parsed["season"],
                start_season=parsed["start_season"],
                end_season=parsed["end_season"],
                season_type=parsed["season_type"],
                team=parsed["team"],
                opponent=parsed["opponent"],
                home_only=parsed["home_only"],
                away_only=parsed["away_only"],
                wins_only=parsed["wins_only"],
                losses_only=parsed["losses_only"],
                stat=None,
                min_value=None,
                max_value=None,
                last_n=None,
                df=filtered_df,
            )
        else:
            return build_fn(
                split=parsed["split_type"],
                season=parsed["season"],
                start_season=parsed["start_season"],
                end_season=parsed["end_season"],
                season_type=parsed["season_type"],
                team=parsed["team"],
                opponent=parsed["opponent"],
                stat=None,
                min_value=None,
                max_value=None,
                last_n=None,
                df=filtered_df,
            )

    if route not in {"player_game_finder", "game_finder"}:
        raise ValueError(
            "Grouped boolean logic is currently supported for finder, player summary/split, "
            "and team summary/split natural queries."
        )

    if not expression_contains_boolean_ops(condition_text):
        raise ValueError("No grouped boolean expression detected.")

    tree = parse_condition_text(condition_text)

    # Build a base result without stat filters to get all matching games
    base_kwargs = dict(parsed["route_kwargs"])
    base_kwargs["stat"] = None
    base_kwargs["min_value"] = None
    base_kwargs["max_value"] = None
    base_kwargs["sort_by"] = "game_date"
    base_kwargs["ascending"] = False

    base_result = _execute_build_result(route, base_kwargs)

    df = _get_result_primary_df(base_result)
    if df is None or df.empty:
        return NoResult(query_class="finder")

    df = evaluate_condition_tree(tree, df)

    if df.empty:
        return NoResult(query_class="finder")

    if "game_date" in df.columns:
        try:
            df["_game_date_sort"] = pd.to_datetime(df["game_date"], errors="coerce")
            sort_cols = ["_game_date_sort"]
            ascending_list = [False]
            if "game_id" in df.columns:
                sort_cols.append("game_id")
                ascending_list.append(False)
            df = df.sort_values(sort_cols, ascending=ascending_list)
            df = df.drop(columns="_game_date_sort")
        except Exception:
            pass  # sorting is best-effort; failure here is cosmetic only

    if "rank" in df.columns:
        df = df.drop(columns="rank")
        df.insert(0, "rank", range(1, len(df) + 1))

    return FinderResult(games=df)


# ---------------------------------------------------------------------------
# Grouped-boolean helpers
# ---------------------------------------------------------------------------


def _extract_grouped_condition_text(query: str) -> str:
    normalized = normalize_text(query)
    condition_text = normalized

    for name in _SORTED_PLAYER_ALIAS_NAMES:
        condition_text = re.sub(rf"\b{re.escape(name)}\b", "", condition_text)

    for name in _SORTED_TEAM_ALIAS_NAMES:
        condition_text = re.sub(rf"\b{re.escape(name)}\b", "", condition_text)

    condition_text = re.sub(r"\b(?:19|20)\d{2}-\d{2}\b", "", condition_text)
    condition_text = re.sub(
        r"\bfrom\s+(?:19|20)\d{2}-\d{2}\s+to\s+(?:19|20)\d{2}-\d{2}\b", "", condition_text
    )
    condition_text = re.sub(r"\b(last|past|recent)\s+\d+\s+games?\b", "", condition_text)
    condition_text = re.sub(r"\b(last|past|recent)\s+\d+\b", "", condition_text)
    condition_text = re.sub(r"\b(playoff|playoffs|postseason)\b", "", condition_text)
    condition_text = re.sub(r"\bhome\s+vs\.?\s+away\b", "", condition_text)
    condition_text = re.sub(r"\bwins?\s+vs\.?\s+loss(?:es)?\b", "", condition_text)
    condition_text = re.sub(
        r"\b(summary|summarize|average|averages|avg|record|split|form|where|games|game"
        r"|show\s+me|list|find|give\s+me|how\s+many|count|number\s+of)\b",
        "",
        condition_text,
    )
    condition_text = re.sub(r"\b(home|away|road|wins?|loss(?:es)?|won|lost)\b", "", condition_text)
    condition_text = re.sub(r"\b(vs\.?|versus|against)\s+[a-z0-9 .&'\-]+\b", "", condition_text)
    condition_text = re.sub(r"^(vs\.?|versus)\s+", "", condition_text)

    return normalize_text(condition_text)


def _load_grouped_player_base_df(parsed: dict) -> pd.DataFrame:
    seasons = resolve_player_summary_seasons(
        parsed["season"],
        parsed["start_season"],
        parsed["end_season"],
    )
    df = load_player_summary_games(seasons, parsed["season_type"])

    home_only = parsed["home_only"]
    away_only = parsed["away_only"]
    wins_only = parsed["wins_only"]
    losses_only = parsed["losses_only"]

    if parsed["route"] == "player_split_summary":
        home_only = False
        away_only = False
        wins_only = False
        losses_only = False

    df = apply_player_summary_filters(
        df=df,
        player=parsed["player"],
        team=parsed["team"],
        opponent=parsed["opponent"],
        home_only=home_only,
        away_only=away_only,
        wins_only=wins_only,
        losses_only=losses_only,
        stat=None,
        min_value=None,
        max_value=None,
        last_n=parsed["last_n"],
    )
    return df


def _load_grouped_team_base_df(parsed: dict) -> pd.DataFrame:
    seasons = resolve_team_summary_seasons(
        parsed["season"],
        parsed["start_season"],
        parsed["end_season"],
    )
    df = load_team_summary_games(seasons, parsed["season_type"])

    home_only = parsed["home_only"]
    away_only = parsed["away_only"]
    wins_only = parsed["wins_only"]
    losses_only = parsed["losses_only"]

    if parsed["route"] == "team_split_summary":
        home_only = False
        away_only = False
        wins_only = False
        losses_only = False

    df = apply_team_summary_filters(
        df=df,
        team=parsed["team"],
        opponent=parsed["opponent"],
        home_only=home_only,
        away_only=away_only,
        wins_only=wins_only,
        losses_only=losses_only,
        stat=None,
        min_value=None,
        max_value=None,
        last_n=parsed["last_n"],
    )
    return df


# ---------------------------------------------------------------------------
# CLI rendering / export
# ---------------------------------------------------------------------------


def render_query_result(
    query_result,
    query: str,
    pretty: bool = True,
    export_csv_path: str | None = None,
    export_txt_path: str | None = None,
    export_json_path: str | None = None,
) -> None:
    """Render a QueryResult to console and/or export files.

    This is the CLI rendering layer.  It takes a ``QueryResult`` from the
    query service and handles pretty/raw display and CSV/TXT/JSON exports.
    """
    result = query_result.result
    metadata = dict(query_result.metadata)
    query_class = route_to_query_class(query_result.route)

    # Build the wrapped raw output text
    if isinstance(result, NoResult):
        reason = result.result_reason or result.reason or "no_match"
        if result.result_status == "error":
            wrapped = build_error_output(metadata, reason=reason)
        else:
            wrapped = build_no_result_output(metadata, reason=reason)
    else:
        wrapped = wrap_result_with_metadata(result, metadata, query_class)

    # Export directly from structured result
    if export_csv_path:
        write_csv_from_result(result, export_csv_path)

    if export_json_path:
        write_json_from_result(result, export_json_path, metadata)

    if export_txt_path:
        if pretty:
            text_to_save = format_pretty_from_result(result, query)
        else:
            text_to_save = wrapped
        _p = Path(export_txt_path)
        if _p.parent != Path("."):
            _p.parent.mkdir(parents=True, exist_ok=True)
        _p.write_text(
            text_to_save + ("" if text_to_save.endswith("\n") else "\n"),
            encoding="utf-8",
        )

    # Console output
    if not pretty:
        print(wrapped, end="" if wrapped.endswith("\n") else "\n")
        return

    pretty_text = format_pretty_from_result(result, query)
    print(pretty_text)
