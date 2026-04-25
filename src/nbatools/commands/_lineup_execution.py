from __future__ import annotations

import pandas as pd

from nbatools.commands._parse_helpers import build_lineup_note
from nbatools.commands._seasons import default_end_season, resolve_seasons
from nbatools.commands.data_utils import (
    load_league_lineup_viz_for_seasons,
    select_trusted_league_lineup_viz_rows,
)
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.structured_results import NoResult

SUPPORTED_UNIT_SIZES = {2, 3, 4, 5}

RESULT_COLUMNS = [
    "season",
    "season_type",
    "team_abbr",
    "unit_size",
    "lineup_id",
    "lineup_name",
    "player_ids",
    "player_names",
    "minute_minimum",
    "minutes",
    "off_rating",
    "def_rating",
    "net_rating",
    "pace",
    "ts_pct",
]

LINEUP_METRICS = {
    "minutes",
    "off_rating",
    "def_rating",
    "net_rating",
    "pace",
    "ts_pct",
}


def placeholder_result(
    *,
    query_class: str,
    lineup_members: list[str] | None,
    unit_size: int | None,
    minute_minimum: int | None,
    current_through: str | None = None,
) -> NoResult:
    notes: list[str] = []
    if lineup_note := build_lineup_note(
        lineup_members=lineup_members,
        unit_size=unit_size,
        minute_minimum=minute_minimum,
    ):
        notes.append(lineup_note)

    return NoResult(
        query_class=query_class,
        reason="unsupported",
        current_through=current_through,
        notes=notes,
    )


def coverage_unavailable(
    query_class: str,
    reason: str,
    *,
    current_through: str | None = None,
) -> NoResult:
    return NoResult(
        query_class=query_class,
        reason="unsupported",
        current_through=current_through,
        notes=[f"lineup: trustworthy lineup coverage is unavailable ({reason})"],
    )


def resolve_requested_unit_size(
    *,
    lineup_members: list[str] | None,
    unit_size: int | None,
    default: int,
) -> int:
    if unit_size is not None:
        return int(unit_size)
    if lineup_members:
        return len(lineup_members)
    return default


def sort_metric(stat: str | None) -> str:
    if stat is None:
        return "net_rating"
    metric = str(stat).strip().lower()
    if metric in LINEUP_METRICS:
        return metric
    raise ValueError(f"Unsupported lineup leaderboard metric: {stat}")


def trusted_lineup_rows(
    *,
    query_class: str,
    season: str | None,
    start_season: str | None,
    end_season: str | None,
    season_type: str,
    team: str | None,
    lineup_members: list[str] | None,
    unit_size: int,
    minute_minimum: int,
    sort_by: str,
    limit: int | None = None,
) -> tuple[pd.DataFrame | NoResult, str | None]:
    if season is None and start_season is None and end_season is None:
        season = default_end_season(season_type)
    seasons = resolve_seasons(season, start_season, end_season)
    current_through = compute_current_through_for_seasons(seasons, season_type)

    if unit_size not in SUPPORTED_UNIT_SIZES:
        return (
            coverage_unavailable(
                query_class,
                f"unit_size={unit_size} is outside the approved 2-5 player lineup contract",
                current_through=current_through,
            ),
            current_through,
        )

    try:
        df = load_league_lineup_viz_for_seasons(seasons, season_type)
    except FileNotFoundError:
        return (
            placeholder_result(
                query_class=query_class,
                lineup_members=lineup_members,
                unit_size=unit_size,
                minute_minimum=minute_minimum,
                current_through=current_through,
            ),
            current_through,
        )

    if team:
        target = str(team).strip().upper()
        df = df.loc[
            df["team_abbr"].astype(str).str.upper().eq(target)
            | df["team_id"].astype(str).eq(str(team).strip())
        ].copy()

    rows, failures = select_trusted_league_lineup_viz_rows(
        df,
        unit_size=unit_size,
        minute_minimum=minute_minimum,
        lineup_members=lineup_members,
        limit=limit,
        sort_by=sort_by,
    )
    if rows.empty:
        if failures:
            return (
                coverage_unavailable(
                    query_class,
                    "; ".join(failures),
                    current_through=current_through,
                ),
                current_through,
            )
        return (
            NoResult(
                query_class=query_class,
                reason="no_match",
                current_through=current_through,
            ),
            current_through,
        )

    return rows[RESULT_COLUMNS].reset_index(drop=True), current_through
