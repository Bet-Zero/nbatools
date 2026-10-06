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
    seen: set[tuple[str, Any, Any]] = set()
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
        signature = stat_condition_signature(cond)
        if signature in seen:
            continue
        seen.add(signature)
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


def combined_stat_conditions(
    stat: str | None,
    min_value: float | None,
    max_value: float | None,
    conditions: Any,
) -> list[dict[str, Any]]:
    """The scalar threshold plus any condition set, as one AND list."""
    primary = primary_condition_from_kwargs(
        {"stat": stat, "min_value": min_value, "max_value": max_value}
    )
    return normalize_stat_conditions(([primary] if primary else []) + list(conditions or []))


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
    out = attach_margin_stats(df, {c["stat"] for c in normalize_stat_conditions(conditions)})
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


#: Team box-score stats an opponent filter can name ("opponents made 15+
#: threes"): read from the other team's row of the same game.
OPPONENT_STAT_BASES = (
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
)
OPPONENT_STATS = {f"opponent_{base}": f"opponent_{base}" for base in OPPONENT_STAT_BASES}
#: Final-margin stats from the team plus-minus: ``margin`` is either team's
#: ("decided by 3 or fewer"); ``win_margin`` and ``loss_margin`` exist only on
#: wins or losses ("won by 10+", "lost by 20+"), so no bound matches the other.
MARGIN_STATS = {"margin": "margin", "win_margin": "win_margin", "loss_margin": "loss_margin"}
#: A player's game context ("LeBron games when the Lakers score 120", "when
#: opponents make 15 threes"): his team's and the opponent's box score, read
#: from team rows of the same game.
PLAYER_GAME_CONTEXT_BASES = ("pts", *OPPONENT_STAT_BASES)
PLAYER_GAME_CONTEXT_STATS = {
    f"{side}_{base}": f"{side}_{base}"
    for side in ("team", "opponent")
    for base in PLAYER_GAME_CONTEXT_BASES
}
#: Stats read from a team game row beyond its own box score.
TEAM_GAME_EXTRA_STATS = {**OPPONENT_STATS, **MARGIN_STATS}


def attach_margin_stats(df: pd.DataFrame, wanted: Any) -> pd.DataFrame:
    """Add the margin columns named in *wanted* from the team plus-minus.

    Player rows carry their team's as ``team_plus_minus``; their own
    ``plus_minus`` is on-court only and never a final margin.
    """
    names = [n for n in MARGIN_STATS if n in set(wanted) and n not in df.columns]
    if "team_plus_minus" in df.columns:
        source = "team_plus_minus"
    elif "plus_minus" in df.columns and "player_id" not in df.columns:
        source = "plus_minus"
    else:
        return df
    if not names:
        return df
    df = df.copy()
    pm = pd.to_numeric(df[source], errors="coerce")
    columns = {
        "margin": pm.abs(),
        "win_margin": pm.where(pm > 0),
        "loss_margin": (-pm).where(pm < 0),
    }
    for name in names:
        df[name] = columns[name]
    return df


def attach_opponent_stats(
    df: pd.DataFrame, stat: str | None, conditions: Any = None
) -> pd.DataFrame:
    """Add ``opponent_<stat>`` columns named by *stat* or *conditions*.

    Runs on the whole league frame, before team filters, so each game's other
    row is still present to join on ``(game_id, opponent_team_id)``.
    """
    wanted = {stat} | {c["stat"] for c in normalize_stat_conditions(conditions)}
    df = attach_margin_stats(df, wanted)
    columns = [
        name
        for name in sorted(s for s in wanted if s in OPPONENT_STATS)
        if name not in df.columns and name[len("opponent_") :] in df.columns
    ]
    if not columns or not {"game_id", "team_id", "opponent_team_id"}.issubset(df.columns):
        return df
    bases = [name[len("opponent_") :] for name in columns]
    other = df[["game_id", "team_id", *bases]].rename(
        columns={"team_id": "opponent_team_id", **dict(zip(bases, columns, strict=True))}
    )
    other = other.drop_duplicates(subset=["game_id", "opponent_team_id"])
    out = df.merge(other, on=["game_id", "opponent_team_id"], how="left")
    out.index = df.index
    return out
