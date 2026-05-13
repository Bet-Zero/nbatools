"""Shared stat-threshold condition helpers.

These helpers keep compound threshold handling consistent across natural-query
routing, finder execution, and metadata construction.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd


def normalize_stat_conditions(conditions: Any) -> list[dict[str, Any]]:
    """Return canonical stat-threshold condition dictionaries.

    The canonical representation is:
    ``{"stat": str, "min_value": float|None, "max_value": float|None}``.
    Extra descriptive keys such as ``text`` are preserved for metadata, but
    execution only depends on the three canonical keys.
    """
    if not conditions:
        return []

    normalized: list[dict[str, Any]] = []
    for raw in conditions:
        if hasattr(raw, "to_dict"):
            raw = raw.to_dict()
        if not isinstance(raw, Mapping):
            continue

        stat = raw.get("stat")
        if not stat:
            continue

        cond: dict[str, Any] = {
            "stat": str(stat).lower(),
            "min_value": raw.get("min_value"),
            "max_value": raw.get("max_value"),
        }
        if "text" in raw:
            cond["text"] = raw.get("text")
        normalized.append(cond)

    return normalized


def primary_condition_from_kwargs(kwargs: Mapping[str, Any]) -> dict[str, Any] | None:
    """Build a condition from scalar ``stat``/``min_value``/``max_value`` kwargs."""
    stat = kwargs.get("stat")
    min_value = kwargs.get("min_value")
    max_value = kwargs.get("max_value")

    if not stat or (min_value is None and max_value is None):
        return None

    return {
        "stat": str(stat).lower(),
        "min_value": min_value,
        "max_value": max_value,
    }


def stat_condition_signature(condition: Mapping[str, Any]) -> tuple[str, Any, Any]:
    """Return a comparable key for a stat-threshold condition."""
    stat = str(condition.get("stat") or "").lower()
    return (stat, condition.get("min_value"), condition.get("max_value"))


def stat_conditions_cover(conditions: Any, expected: Any) -> bool:
    """Return whether ``conditions`` contains every condition in ``expected``."""
    expected_conditions = normalize_stat_conditions(expected)
    if not expected_conditions:
        return True

    condition_keys = {
        stat_condition_signature(cond) for cond in normalize_stat_conditions(conditions)
    }
    expected_keys = {stat_condition_signature(cond) for cond in expected_conditions}
    return expected_keys.issubset(condition_keys)


def apply_stat_conditions(
    df: pd.DataFrame,
    conditions: Any,
    allowed_stats: Mapping[str, str],
    *,
    prepare_stat_column=None,
) -> pd.DataFrame:
    """Apply an AND condition set to a DataFrame before result limiting.

    Parameters
    ----------
    df:
        DataFrame to filter.
    conditions:
        Iterable of canonical or canonical-like condition dictionaries.
    allowed_stats:
        Mapping from public stat ids to DataFrame column names.
    prepare_stat_column:
        Optional callback ``(df, stat_col) -> df`` used by callers that derive
        columns on demand, such as ``opponent_pts``.
    """
    out = df
    for cond in normalize_stat_conditions(conditions):
        stat = cond["stat"]
        if stat not in allowed_stats:
            raise ValueError(f"Unsupported stat: {stat}")

        stat_col = allowed_stats[stat]
        if prepare_stat_column is not None:
            out = prepare_stat_column(out, stat_col)

        if stat_col not in out.columns:
            raise ValueError(f"Missing required stat column: {stat_col}")

        values = pd.to_numeric(out[stat_col], errors="coerce")
        if cond.get("min_value") is not None:
            out = out[values >= cond["min_value"]].copy()
            values = pd.to_numeric(out[stat_col], errors="coerce")
        if cond.get("max_value") is not None:
            out = out[values <= cond["max_value"]].copy()

    return out
