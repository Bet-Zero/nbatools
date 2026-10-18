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
    An optional ``opponent_team`` qualifies the bound's owner without changing
    the base game sample (in particular, before a last-N window is selected).
    """
    if not conditions:
        return []

    normalized: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
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
        if "opponent_team" in raw:
            cond["opponent_team"] = str(raw.get("opponent_team") or "").upper()
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


def stat_condition_signature(condition: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return a comparable key for a stat-threshold condition."""
    stat = str(condition.get("stat") or "").lower()
    key = (stat, condition.get("min_value"), condition.get("max_value"))
    if "opponent_team" in condition:
        return (*key, str(condition.get("opponent_team") or "").upper())
    return key


def condition_owner_mask(df: pd.DataFrame, condition: Mapping[str, Any]) -> pd.Series:
    """Match a bound's named opponent at condition time; unknown identity fails closed."""
    if "opponent_team" not in condition:
        return pd.Series(True, index=df.index)
    if not str(condition.get("stat") or "").startswith("opponent_"):
        raise ValueError("Only opponent stats can name an opponent owner")
    from nbatools.commands.data_utils import build_opponent_mask

    return build_opponent_mask(df, condition.get("opponent_team"))


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
        out = out[condition_owner_mask(out, cond)].copy()
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
#: Shooting rates a team game list can rank or bound the opponent by
#: ("highest opponent field goal percentage"); team rows carry them.
OPPONENT_RATE_BASES = ("fg_pct", "fg3_pct", "ft_pct", "efg_pct", "ts_pct")
OPPONENT_STATS = {
    f"opponent_{base}": f"opponent_{base}" for base in (*OPPONENT_STAT_BASES, *OPPONENT_RATE_BASES)
}
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
#: The team's best single-player line in the game ("Lakers record when a
#: player scores 40"): the most any one of its players had, from player rows
#: of the same game.
TOP_PLAYER_BASES = ("pts", "reb", "ast", "stl", "blk", "fg3m", "fgm", "ftm", "tov")
TOP_PLAYER_STATS = {f"top_player_{base}": f"top_player_{base}" for base in TOP_PLAYER_BASES}
#: Stats read from a team game row beyond its own box score.
TEAM_GAME_EXTRA_STATS = {**OPPONENT_STATS, **MARGIN_STATS, **TOP_PLAYER_STATS}


def attach_top_player_stats(df: pd.DataFrame, wanted: Any) -> pd.DataFrame:
    """Add the ``top_player_<stat>`` columns named in *wanted* to team rows."""
    names = [n for n in TOP_PLAYER_STATS if n in set(wanted) and n not in df.columns]
    needed = {"game_id", "team_id", "season", "season_type"}
    if not names or df.empty or not needed.issubset(df.columns):
        return df
    from nbatools.commands.data_utils import (
        data_exists,
        load_player_games_for_seasons,
        normalize_season_type,
    )

    bases = [n[len("top_player_") :] for n in names]
    frames = []
    for season_type, part in df.groupby("season_type"):
        seasons = sorted(str(s) for s in part["season"].dropna().unique())
        safe = normalize_season_type(str(season_type))
        missing = [
            s for s in seasons if not data_exists(f"data/raw/player_game_stats/{s}_{safe}.csv")
        ]
        if missing:
            # A season without player rows would silently drop its games.
            raise FileNotFoundError(f"No player_game_stats for {', '.join(missing)}")
        players = load_player_games_for_seasons(seasons, str(season_type))
        frames.append(players[["game_id", "team_id", *bases]])
    out = df.copy()
    players = pd.concat(frames, ignore_index=True)
    for base in bases:
        players[base] = pd.to_numeric(players[base], errors="coerce")
    top = players.groupby(["game_id", "team_id"], as_index=False)[bases].max()
    top = top.rename(columns={b: f"top_player_{b}" for b in bases})
    key_types = {k: out[k].dtype for k in ("game_id", "team_id")}
    for key, dtype in key_types.items():
        top[key] = top[key].astype(dtype)
    merged = out.merge(top, on=["game_id", "team_id"], how="left")
    merged.index = out.index
    return merged


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
    df = attach_top_player_stats(df, wanted)
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
