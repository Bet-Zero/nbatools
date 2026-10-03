"""Consecutive-game runs shared by the player and team streak finders.

A streak is a run of an entity's consecutive games in the filtered sample
(a player's appearances, a team's games) in which the condition held. A game
that fails the condition, or a missing stat, ends the run.
"""

from __future__ import annotations

import pandas as pd


def compound_condition_mask(df: pd.DataFrame, conditions: list[dict]) -> pd.Series:
    """Rows meeting every ``{stat, min_value, max_value}`` condition.

    A missing value meets no bound, so an unrecorded stat never extends a
    streak of "0 turnover" games.
    """
    mask = pd.Series(True, index=df.index)
    for cond in conditions:
        stat = str(cond["stat"]).lower()
        if stat not in df.columns:
            raise ValueError(f"Column '{stat}' not available for streak queries")
        values = pd.to_numeric(df[stat], errors="coerce")
        if cond.get("min_value") is not None:
            mask &= values >= cond["min_value"]
        if cond.get("max_value") is not None:
            mask &= values <= cond["max_value"]
        mask &= values.notna()
    return mask


def compound_condition_label(conditions: list[dict]) -> str:
    parts = []
    for cond in conditions:
        stat, low, high = cond["stat"], cond.get("min_value"), cond.get("max_value")
        if low is not None and high is not None:
            parts.append(f"{stat}:{_fmt(low)}-{_fmt(high)}")
        elif low is not None:
            parts.append(f"{stat}>={_fmt(low)}")
        elif high is not None:
            parts.append(f"{stat}<={_fmt(high)}")
    return " and ".join(parts)


def _fmt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def best_runs_per_entity(
    df: pd.DataFrame,
    mask: pd.Series,
    entity_col: str,
    *,
    current: bool = False,
    limit: int | None = None,
) -> list[tuple[pd.DataFrame, bool]]:
    """Each entity's best run, longest first (most recent breaks ties).

    ``current`` keeps only runs still alive at the entity's last game in the
    sample. Returns ``(games_of_the_run, is_active)`` pairs.
    """
    if df.empty:
        return []
    work = df.copy()
    work["_ok"] = pd.Series(mask, index=df.index).fillna(False).astype(bool).values
    work["game_date"] = pd.to_datetime(work["game_date"])
    work = work.sort_values([entity_col, "game_date", "game_id"]).reset_index(drop=True)

    entity = work[entity_col]
    new_run = work["_ok"].ne(work["_ok"].shift()) | entity.ne(entity.shift())
    work["_run"] = new_run.cumsum()
    work["_entity_last"] = False
    work.loc[work.groupby(entity_col).tail(1).index, "_entity_last"] = True

    hits = work[work["_ok"]]
    if hits.empty:
        return []
    runs = hits.groupby("_run").agg(
        entity=(entity_col, "first"),
        length=("_ok", "size"),
        end_date=("game_date", "last"),
        active=("_entity_last", "any"),
    )
    if current:
        runs = runs[runs["active"]]
    runs = runs.sort_values(["length", "end_date"], ascending=[False, False])
    best = runs.groupby("entity", sort=False).head(1)
    if limit is not None:
        best = best.head(limit)

    helper = ["_ok", "_run", "_entity_last"]
    return [
        (work[work["_run"] == run_id].drop(columns=helper), bool(active))
        for run_id, active in best["active"].items()
    ]
