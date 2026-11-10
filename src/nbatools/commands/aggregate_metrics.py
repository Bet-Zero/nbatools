"""Shared descriptors and formulas for game-sample aggregation."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

import pandas as pd

from nbatools.development_data import DevelopmentDataUnavailable, selected_snapshot


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


def fractional_source_rate_bounds(value):
    """Copy natural percent-point bounds into canonical period fractions.

    Only the four existing source-rate metrics use these units. Counts and
    already fractional shooting bounds retain their existing meaning.
    """
    if isinstance(value, list):
        return [fractional_source_rate_bounds(item) for item in value]
    if not isinstance(value, dict):
        return value
    out = {key: fractional_source_rate_bounds(item) for key, item in value.items()}
    descriptor = METRIC_DESCRIPTORS.get(str(out.get("stat")).lower())
    if descriptor and descriptor.kind == AggregationKind.AVERAGE_ONLY:
        for field in ("min_value", "max_value"):
            if out.get(field) is not None:
                out[field] = float(Decimal(str(out[field])) / 100)
    return out


def require_known_metric_inputs(
    df: pd.DataFrame, metrics: Iterable[str], *, operation: str, row_rates: bool = False
) -> None:
    """Check all dependency leaves before a predicate or sample-changing operation.

    The existing descriptor supplies ratio numerators/denominators. A source
    average-only rate remains a source input: it is never rebuilt from counts.
    """
    if selected_snapshot() is None:
        return
    metrics = {str(m).lower() for m in metrics if m}
    required = set()
    for metric in metrics:
        if not metric:
            continue
        metric = str(metric).lower()
        descriptor = METRIC_DESCRIPTORS.get(metric)
        required.update(
            descriptor.required_columns if descriptor and descriptor.required_columns else (metric,)
        )
    for field in sorted(required):
        if (
            field not in df
            or pd.to_numeric(df[field], errors="coerce").isna().any()
            or pd.to_numeric(df[field], errors="coerce").isin([float("inf"), float("-inf")]).any()
        ):
            raise DevelopmentDataUnavailable(
                f"Unknown {field} input prevents complete {operation}; no rows were discarded"
            )
    if row_rates:
        for metric in metrics:
            denominator = {
                "fg_pct": "fga",
                "fg3_pct": "fg3a",
                "ft_pct": "fta",
                "efg_pct": "fga",
            }.get(metric)
            values = pd.to_numeric(df[denominator]) if denominator else None
            if metric == "ts_pct":
                values = pd.to_numeric(df["fga"]) + 0.44 * pd.to_numeric(df["fta"])
            if values is not None and values.le(0).any():
                raise DevelopmentDataUnavailable(
                    f"Undefined {metric}: zero-attempt denominator prevents complete {operation}"
                )


def _numeric_sum(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns:
        return None
    values = pd.to_numeric(df[column], errors="coerce")
    if selected_snapshot() is not None and values.isna().any():
        return None
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
    if selected_snapshot() is not None and values.isna().any():
        return None
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
