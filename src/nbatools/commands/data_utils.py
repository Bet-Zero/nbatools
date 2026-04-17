"""Shared data-loading and DataFrame utilities used across command modules."""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path

import pandas as pd


def safe_divide(numer: pd.Series, denom: pd.Series, fill: float | None = 0.0) -> pd.Series:
    """Element-wise division that returns *fill* where *denom* is zero.

    Pass ``fill=None`` to leave divide-by-zero cells as NaN instead of filling.
    """
    numer = pd.Series(numer)
    denom = pd.Series(denom)
    out = numer / denom.replace(0, pd.NA)
    if fill is None:
        return out
    return out.fillna(fill)


def add_advanced_pct_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add shooting pct and efficiency columns computed from box-score totals."""
    out = df.copy()

    if {"fgm", "fga"}.issubset(out.columns) and "fg_pct" not in out.columns:
        out["fg_pct"] = safe_divide(out["fgm"], out["fga"])

    if {"fg3m", "fg3a"}.issubset(out.columns) and "fg3_pct" not in out.columns:
        out["fg3_pct"] = safe_divide(out["fg3m"], out["fg3a"])

    if {"ftm", "fta"}.issubset(out.columns) and "ft_pct" not in out.columns:
        out["ft_pct"] = safe_divide(out["ftm"], out["fta"])

    if {"fgm", "fg3m", "fga"}.issubset(out.columns):
        out["efg_pct"] = safe_divide(out["fgm"] + 0.5 * out["fg3m"], out["fga"])

    if {"pts", "fga", "fta"}.issubset(out.columns):
        out["ts_pct"] = safe_divide(out["pts"], 2 * (out["fga"] + 0.44 * out["fta"]))

    if {"tov", "fga", "fta"}.issubset(out.columns):
        out["tov_pct"] = (
            safe_divide(out["tov"], out["fga"] + 0.44 * out["fta"] + out["tov"]) * 100.0
        )

    return out


def normalize_season_type(season_type: str) -> str:
    """'Regular Season' -> 'regular_season'"""
    return season_type.lower().replace(" ", "_")


@cache
def _load_team_games_cached(
    seasons: tuple[str, ...], season_type: str, data_root: str
) -> pd.DataFrame:
    safe = normalize_season_type(season_type)
    frames: list[pd.DataFrame] = []

    for season in seasons:
        path = Path(data_root) / f"data/raw/team_game_stats/{season}_{safe}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        df = add_advanced_pct_columns(df)
        frames.append(df)

    if not frames:
        joined = ", ".join(seasons)
        raise FileNotFoundError(f"No team_game_stats files found for seasons: {joined}")

    return pd.concat(frames, ignore_index=True)


def load_team_games_for_seasons(seasons: list[str], season_type: str) -> pd.DataFrame:
    """Load and concatenate team_game_stats CSVs for the given seasons."""
    return _load_team_games_cached(tuple(seasons), season_type, os.getcwd()).copy()


@cache
def _load_player_games_cached(
    seasons: tuple[str, ...], season_type: str, data_root: str
) -> pd.DataFrame:
    safe = normalize_season_type(season_type)
    frames: list[pd.DataFrame] = []
    root = Path(data_root)

    for season in seasons:
        path = root / f"data/raw/player_game_stats/{season}_{safe}.csv"
        if not path.exists():
            continue

        df = pd.read_csv(path)

        team_stats_path = root / f"data/raw/team_game_stats/{season}_{safe}.csv"
        if not team_stats_path.exists():
            raise FileNotFoundError(f"Missing team stats file: {team_stats_path}")

        team_stats = pd.read_csv(team_stats_path)[["game_id", "team_id", "wl"]].drop_duplicates()
        df = df.merge(team_stats, on=["game_id", "team_id"], how="left", suffixes=("", "_team"))

        if "wl_team" in df.columns:
            if "wl" in df.columns:
                df["wl"] = df["wl"].combine_first(df["wl_team"])
            else:
                df["wl"] = df["wl_team"]
            df = df.drop(columns=["wl_team"])

        df = add_advanced_pct_columns(df)
        frames.append(df)

    if not frames:
        joined = ", ".join(seasons)
        raise FileNotFoundError(f"No player_game_stats files found for seasons: {joined}")

    out = pd.concat(frames, ignore_index=True)
    out = add_usage_ast_reb_rate_columns(
        out, seasons=seasons, season_type=season_type, data_root=data_root
    )
    return out


def load_player_games_for_seasons(seasons: list[str], season_type: str) -> pd.DataFrame:
    """Load player_game_stats CSVs, merge win/loss from team stats, add pct columns."""
    return _load_player_games_cached(tuple(seasons), season_type, os.getcwd()).copy()


def get_game_ids_for_player(player_name: str, seasons: list[str], season_type: str) -> set:
    """Return the set of game_ids where a given player appears in box scores."""
    df = load_player_games_for_seasons(seasons, season_type)
    mask = df["player_name"].astype(str).str.upper() == player_name.upper()
    return set(df.loc[mask, "game_id"].unique())


def filter_by_opponent_player(
    df: pd.DataFrame,
    opponent_player: str,
    seasons: list[str],
    season_type: str,
) -> pd.DataFrame:
    """Filter df to games where opponent_player was on the opposing team.

    For player game logs: keep rows where the game_id appears in
    opponent_player's game logs AND opponent_player was on a different team.
    """
    opp_df = load_player_games_for_seasons(seasons, season_type)
    opp_mask = opp_df["player_name"].astype(str).str.upper() == opponent_player.upper()
    opp_rows = opp_df.loc[opp_mask, ["game_id", "team_abbr"]].drop_duplicates()

    if opp_rows.empty:
        return df.iloc[0:0].copy()

    # Build set of (game_id, opponent_team_abbr) pairs so we only include
    # games where the opponent player was actually on the OTHER team
    if "opponent_team_abbr" in df.columns:
        merged = df.merge(
            opp_rows.rename(columns={"team_abbr": "_opp_player_team"}),
            on="game_id",
            how="inner",
        )
        result = merged[
            merged["opponent_team_abbr"].str.upper() == merged["_opp_player_team"].str.upper()
        ].drop(columns=["_opp_player_team"])
        return result.copy()
    else:
        # Fallback: just filter by game_id presence
        game_ids = set(opp_rows["game_id"])
        return df[df["game_id"].isin(game_ids)].copy()


def filter_without_player(
    df: pd.DataFrame,
    without_player: str,
    seasons: list[str],
    season_type: str,
    team: str | None = None,
) -> pd.DataFrame:
    """Filter df to games where without_player did NOT play.

    Specifically: exclude game_ids where without_player appeared for the
    same team (or at all, if no team context).
    """
    player_df = load_player_games_for_seasons(seasons, season_type)
    p_mask = player_df["player_name"].astype(str).str.upper() == without_player.upper()
    p_rows = player_df.loc[p_mask, ["game_id", "team_abbr"]].drop_duplicates()

    if p_rows.empty:
        return df.copy()

    if team and "team_abbr" in df.columns:
        # Only exclude games where the player was on the same team
        team_games = set(p_rows.loc[p_rows["team_abbr"].str.upper() == team.upper(), "game_id"])
    else:
        team_games = set(p_rows["game_id"])

    return df[~df["game_id"].isin(team_games)].copy()


def add_usage_ast_reb_rate_columns(
    df: pd.DataFrame, seasons: list[str] | tuple[str, ...], season_type: str, data_root: str = ""
) -> pd.DataFrame:
    """Merge usage/ast/reb rate columns from player_season_advanced files."""
    out = df.copy()
    safe = normalize_season_type(season_type)
    root = Path(data_root) if data_root else Path()
    frames: list[pd.DataFrame] = []

    for season in seasons:
        adv_path = root / f"data/raw/player_season_advanced/{season}_{safe}.csv"
        if not adv_path.exists():
            continue

        adv = pd.read_csv(adv_path)

        rename_map: dict[str, str] = {}
        if "usage_rate" in adv.columns:
            rename_map["usage_rate"] = "usg_pct"
        if "ast_pct" in adv.columns:
            rename_map["ast_pct"] = "ast_pct"
        elif "assist_percentage" in adv.columns:
            rename_map["assist_percentage"] = "ast_pct"
        if "reb_pct" in adv.columns:
            rename_map["reb_pct"] = "reb_pct"
        elif "rebound_percentage" in adv.columns:
            rename_map["rebound_percentage"] = "reb_pct"

        if not rename_map:
            continue

        keep_cols = [
            c for c in ["season", "player_id", "team_id", *rename_map.keys()] if c in adv.columns
        ]
        adv = adv[keep_cols].rename(columns=rename_map).drop_duplicates()

        if {"season", "player_id", "team_id"}.issubset(adv.columns):
            frames.append(adv)

    if not frames:
        return out

    adv_all = pd.concat(frames, ignore_index=True).drop_duplicates()
    out = out.merge(
        adv_all,
        on=["season", "player_id", "team_id"],
        how="left",
    )
    return out
