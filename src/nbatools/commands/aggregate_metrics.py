"""Shared descriptors and formulas for game-sample aggregation."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum

import pandas as pd


class AggregationKind(StrEnum):
    """How a metric must be combined across game rows."""

    ADDITIVE = "additive"
    AVERAGE_ONLY = "average_only"
    RATE_OF_TOTALS = "rate_of_totals"


@dataclass(frozen=True)
class MetricDescriptor:
    kind: AggregationKind
    required_columns: tuple[str, ...] = ()


_ADDITIVE_METRICS = (
    "minutes",
    "pts",
    "fgm",
    "fga",
    "fg3m",
    "fg3a",
    "ftm",
    "fta",
    "oreb",
    "dreb",
    "reb",
    "ast",
    "stl",
    "blk",
    "tov",
    "pf",
    "plus_minus",
    "clutch_events",
    "clutch_seconds",
)

_AVERAGE_ONLY_METRICS = (
    "usg_pct",
    "ast_pct",
    "reb_pct",
    "tov_pct",
)

METRIC_DESCRIPTORS: dict[str, MetricDescriptor] = {
    **{metric: MetricDescriptor(AggregationKind.ADDITIVE) for metric in _ADDITIVE_METRICS},
    **{metric: MetricDescriptor(AggregationKind.AVERAGE_ONLY) for metric in _AVERAGE_ONLY_METRICS},
    "fg_pct": MetricDescriptor(AggregationKind.RATE_OF_TOTALS, ("fgm", "fga")),
    "fg3_pct": MetricDescriptor(AggregationKind.RATE_OF_TOTALS, ("fg3m", "fg3a")),
    "ft_pct": MetricDescriptor(AggregationKind.RATE_OF_TOTALS, ("ftm", "fta")),
    "efg_pct": MetricDescriptor(
        AggregationKind.RATE_OF_TOTALS,
        ("fgm", "fg3m", "fga"),
    ),
    "ts_pct": MetricDescriptor(
        AggregationKind.RATE_OF_TOTALS,
        ("pts", "fga", "fta"),
    ),
}


def _numeric_sum(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns:
        return None
    values = pd.to_numeric(df[column], errors="coerce")
    if not values.notna().any():
        return None
    return float(values.sum())


def _safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    value = numerator / denominator
    return None if pd.isna(value) else float(value)


def _fg_pct(df: pd.DataFrame) -> float | None:
    return _safe_ratio(_numeric_sum(df, "fgm"), _numeric_sum(df, "fga"))


def _fg3_pct(df: pd.DataFrame) -> float | None:
    return _safe_ratio(_numeric_sum(df, "fg3m"), _numeric_sum(df, "fg3a"))


def _ft_pct(df: pd.DataFrame) -> float | None:
    return _safe_ratio(_numeric_sum(df, "ftm"), _numeric_sum(df, "fta"))


def _efg_pct(df: pd.DataFrame) -> float | None:
    fgm = _numeric_sum(df, "fgm")
    fg3m = _numeric_sum(df, "fg3m")
    fga = _numeric_sum(df, "fga")
    if fgm is None or fg3m is None:
        return None
    return _safe_ratio(fgm + 0.5 * fg3m, fga)


def _ts_pct(df: pd.DataFrame) -> float | None:
    pts = _numeric_sum(df, "pts")
    fga = _numeric_sum(df, "fga")
    fta = _numeric_sum(df, "fta")
    if fga is None or fta is None:
        return None
    return _safe_ratio(pts, 2.0 * (fga + 0.44 * fta))


_RATE_FORMULAS: dict[str, Callable[[pd.DataFrame], float | None]] = {
    "fg_pct": _fg_pct,
    "fg3_pct": _fg3_pct,
    "ft_pct": _ft_pct,
    "efg_pct": _efg_pct,
    "ts_pct": _ts_pct,
}


def aggregate_metric_value(df: pd.DataFrame, metric: str) -> float | None:
    """Return a sample average or totals-based rate for one metric."""
    descriptor = METRIC_DESCRIPTORS.get(metric)
    if descriptor is None:
        raise ValueError(f"Missing aggregate metric descriptor: {metric}")
    if not set(descriptor.required_columns).issubset(df.columns):
        return None
    if descriptor.kind == AggregationKind.RATE_OF_TOTALS:
        return _RATE_FORMULAS[metric](df)
    if metric not in df.columns:
        return None
    values = pd.to_numeric(df[metric], errors="coerce")
    if not values.notna().any():
        return None
    return float(values.mean())


def add_aggregate_metric_fields(
    row: dict,
    df: pd.DataFrame,
    metrics: Iterable[str],
    *,
    sum_metrics: Iterable[str] = (),
) -> dict:
    """Add stable ``*_avg`` fields and allowed additive ``*_sum`` fields."""
    out = dict(row)
    requested_sums = set(sum_metrics)

    for metric in metrics:
        descriptor = METRIC_DESCRIPTORS.get(metric)
        if descriptor is None:
            raise ValueError(f"Missing aggregate metric descriptor: {metric}")
        value = aggregate_metric_value(df, metric)
        out[f"{metric}_avg"] = None if value is None else round(value, 3)
        if metric not in requested_sums:
            continue
        if descriptor.kind != AggregationKind.ADDITIVE:
            raise ValueError(f"Rate and average-only metrics cannot be summed: {metric}")
        total = _numeric_sum(df, metric)
        out[f"{metric}_sum"] = None if total is None else round(total, 3)

    return out


def additive_metric_names(metrics: Iterable[str]) -> list[str]:
    """Return the requested metrics whose descriptors permit sum fields."""
    additive: list[str] = []
    for metric in metrics:
        descriptor = METRIC_DESCRIPTORS.get(metric)
        if descriptor is None:
            raise ValueError(f"Missing aggregate metric descriptor: {metric}")
        if descriptor.kind == AggregationKind.ADDITIVE:
            additive.append(metric)
    return additive


def compute_grouped_rate_metrics(
    df: pd.DataFrame,
    group_column: str,
    metrics: Iterable[str],
) -> pd.DataFrame:
    """Compute totals-based rate fields for each group in a game sample."""
    if group_column not in df.columns:
        raise ValueError(f"Missing group column: {group_column}")

    metric_list = list(metrics)
    for metric in metric_list:
        descriptor = METRIC_DESCRIPTORS.get(metric)
        if descriptor is None or descriptor.kind != AggregationKind.RATE_OF_TOTALS:
            raise ValueError(f"Grouped rate metric is not rate-of-totals: {metric}")

    rows: list[dict] = []
    for group, sample in df.groupby(group_column, dropna=False):
        row = {group_column: group}
        for metric in metric_list:
            value = aggregate_metric_value(sample, metric)
            row[f"{metric}_avg"] = None if value is None else round(value, 3)
        rows.append(row)

    return pd.DataFrame(rows, columns=[group_column, *[f"{metric}_avg" for metric in metric_list]])
