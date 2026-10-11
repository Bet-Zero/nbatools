"""Calendar-month buckets shared by the player and team split routes.

"LeBron points per game by month" and "Lakers record by month" divide the
summary sample by the calendar month each game was played in. A bucket is one
month of one year ("March 2026"), so a multi-season span keeps every month
separate instead of pooling every March together. "best month" ranks those
buckets by the requested statistic.
"""

from __future__ import annotations

import pandas as pd

from nbatools.commands.aggregate_metrics import (
    METRIC_DESCRIPTORS,
    AggregationKind,
    aggregate_metric_value,
)

MONTH_KEY_COLUMN = "_month_key"
_COUNT_COLUMNS = {"win_pct", "games", "wins", "losses"}


def assign_month_buckets(df: pd.DataFrame) -> pd.DataFrame:
    """Label each game with its month ("March 2026") and a sortable key."""
    out = df.copy()
    dates = pd.to_datetime(out["game_date"])
    out["bucket"] = dates.dt.month_name() + " " + dates.dt.year.astype(str)
    out[MONTH_KEY_COLUMN] = dates.dt.strftime("%Y-%m")
    return out


def add_requested_stat(row: dict, df: pd.DataFrame, stat: str | None) -> dict:
    """Give a month bucket the stat the question asked about.

    Shooting rates combine the month's totals (makes over attempts); counting
    stats add the month's per-game average and its total.
    """
    if not stat:
        return row
    stat = stat.removesuffix("_sum")
    descriptor = METRIC_DESCRIPTORS.get(stat)
    if descriptor is None or descriptor.kind == AggregationKind.AVERAGE_ONLY:
        # Usage and other team-context rates come from the grouped advanced
        # metrics, which need the team's totals.
        return row
    out = dict(row)
    avg_key = f"{stat}_avg"
    if out.get(avg_key) is None:
        value = aggregate_metric_value(df, stat)
        out[avg_key] = None if value is None else round(value, 3)
    if descriptor.kind == AggregationKind.ADDITIVE and stat in df.columns:
        values = pd.to_numeric(df[stat], errors="coerce")
        out[f"{stat}_sum"] = round(float(values.sum()), 3) if values.notna().any() else None
    return out


def rank_column(rank_stat: str | None, default: str) -> str:
    """The bucket column a "best month" ranks: a count or record column, or
    the stat's per-game average (rates are the month's totals)."""
    if rank_stat is None:
        return default
    if rank_stat in _COUNT_COLUMNS or rank_stat.endswith("_sum"):
        return rank_stat
    return f"{rank_stat}_avg"


def order_month_buckets(
    split_comparison: pd.DataFrame,
    month_keys: dict[str, str],
    *,
    rank_column: str | None = None,
    rank_order: str | None = None,
) -> pd.DataFrame:
    """Months in calendar order, or ranked by ``rank_column`` when asked.

    A ranked table puts months without a value last and keeps calendar order
    among ties; a ranked win percentage breaks ties on wins (best) or losses
    (worst).
    """
    out = split_comparison.copy()
    out["_key"] = out["bucket"].map(month_keys)
    out = out.sort_values("_key", kind="stable")
    if rank_column and rank_column in out.columns and rank_order in ("asc", "desc"):
        ascending = rank_order == "asc"
        sort_cols = [rank_column]
        sort_asc = [ascending]
        if rank_column == "win_pct":
            tie = "losses" if ascending else "wins"
            sort_cols.append(tie)
            sort_asc.append(False)
        out = out.sort_values(sort_cols, ascending=sort_asc, na_position="last", kind="stable")
    return out.drop(columns="_key").reset_index(drop=True)


def sample_stat(stat: str | None, min_value, max_value) -> str | None:
    """The stat that filters the month split's sample: only a bounded one.

    "Lakers 3 point percentage by month" shows a rate the team sample does
    not filter on; passing it would refuse an unfilterable stat.
    """
    if min_value is None and max_value is None:
        # Extra conditions carry their own stats.
        return None
    return stat
