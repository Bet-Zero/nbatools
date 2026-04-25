"""Coverage-gated route for specific lineup summary queries."""

from __future__ import annotations

import pandas as pd

from nbatools.commands._lineup_execution import (
    resolve_requested_unit_size,
    sort_metric,
    trusted_lineup_rows,
)
from nbatools.commands.structured_results import NoResult, SummaryResult


def build_result(
    *,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    team: str | None = None,
    lineup_members: list[str] | None = None,
    unit_size: int | None = None,
    minute_minimum: int | None = None,
    stat: str | None = None,
    **_: object,
) -> SummaryResult | NoResult:
    """Return trusted lineup-unit rows when source coverage exists."""
    if not lineup_members:
        raise ValueError("lineup_summary requires lineup_members")

    requested_unit_size = resolve_requested_unit_size(
        lineup_members=lineup_members,
        unit_size=unit_size,
        default=len(lineup_members),
    )
    requested_minimum = int(minute_minimum or 0)
    rows, current_through = trusted_lineup_rows(
        query_class="summary",
        season=season,
        start_season=start_season,
        end_season=end_season,
        season_type=season_type,
        team=team,
        lineup_members=lineup_members,
        unit_size=requested_unit_size,
        minute_minimum=requested_minimum,
        sort_by=sort_metric(stat),
    )
    if isinstance(rows, NoResult):
        return rows

    summary = rows.copy()
    for col in ("minutes", "off_rating", "def_rating", "net_rating", "pace", "ts_pct"):
        summary[col] = pd.to_numeric(summary[col], errors="coerce")

    return SummaryResult(
        summary=summary,
        current_through=current_through,
    )
