from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from nbatools.data_source import data_exists, data_read_csv


def _safe_divide(numer: float, denom: float) -> float | None:
    if denom is None or pd.isna(denom) or denom == 0:
        return None
    value = numer / denom
    if pd.isna(value):
        return None
    return float(value)


def _sum_col(df: pd.DataFrame, col: str) -> float:
    if col not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def _coerce_numeric(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def load_team_games_for_seasons(seasons: list[str], season_type: str) -> pd.DataFrame:
    safe = season_type.lower().replace(" ", "_")
    frames: list[pd.DataFrame] = []

    for season in seasons:
        path = f"data/raw/team_game_stats/{season}_{safe}.csv"
        if not data_exists(path):
            continue

        df = data_read_csv(path).copy()
        df["season"] = season
        df["season_type"] = season_type
        frames.append(df)

    if not frames:
        joined = ", ".join(seasons)
        raise FileNotFoundError(f"No team_game_stats files found for seasons: {joined}")

    out = pd.concat(frames, ignore_index=True)

    required = [
        "game_id",
        "team_id",
        "team_abbr",
        "team_name",
        "opponent_team_id",
        "opponent_team_abbr",
        "minutes",
        "fgm",
        "fga",
        "fta",
        "tov",
        "reb",
        "wl",
        "season",
        "season_type",
    ]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"Missing required team-game columns: {missing}")

    out = _coerce_numeric(
        out,
        ["team_id", "opponent_team_id", "minutes", "fgm", "fga", "fta", "tov", "reb"],
    )

    return out


def build_player_team_context(player_df: pd.DataFrame, team_df: pd.DataFrame) -> pd.DataFrame:
    player = player_df.copy()
    teams = team_df.copy()

    own_cols = [
        "game_id",
        "team_id",
        "season",
        "season_type",
        "minutes",
        "fgm",
        "fga",
        "fta",
        "tov",
        "reb",
    ]
    own = (
        teams[own_cols]
        .drop_duplicates()
        .rename(
            columns={
                "minutes": "team_minutes",
                "fgm": "team_fgm",
                "fga": "team_fga",
                "fta": "team_fta",
                "tov": "team_tov",
                "reb": "team_reb",
            }
        )
    )

    out = player.merge(
        own,
        on=["game_id", "team_id", "season", "season_type"],
        how="left",
        validate="many_to_one",
    )

    opp_cols = [
        "game_id",
        "team_id",
        "season",
        "season_type",
        "minutes",
        "fgm",
        "fga",
        "fta",
        "tov",
        "reb",
    ]
    opp = (
        teams[opp_cols]
        .drop_duplicates()
        .rename(
            columns={
                "team_id": "opponent_team_id",
                "minutes": "opp_minutes",
                "fgm": "opp_fgm",
                "fga": "opp_fga",
                "fta": "opp_fta",
                "tov": "opp_tov",
                "reb": "opp_reb",
            }
        )
    )

    out = out.merge(
        opp,
        on=["game_id", "opponent_team_id", "season", "season_type"],
        how="left",
        validate="many_to_one",
    )

    numeric_cols = [
        "minutes",
        "fgm",
        "fga",
        "fta",
        "tov",
        "reb",
        "ast",
        "team_minutes",
        "team_fgm",
        "team_fga",
        "team_fta",
        "team_tov",
        "team_reb",
        "opp_minutes",
        "opp_fgm",
        "opp_fga",
        "opp_fta",
        "opp_tov",
        "opp_reb",
    ]
    out = _coerce_numeric(out, numeric_cols)

    return out


def compute_sample_usg_pct(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None

    player_fga = _sum_col(df, "fga")
    player_fta = _sum_col(df, "fta")
    player_tov = _sum_col(df, "tov")
    player_minutes = _sum_col(df, "minutes")

    team_fga = _sum_col(df, "team_fga")
    team_fta = _sum_col(df, "team_fta")
    team_tov = _sum_col(df, "team_tov")
    team_minutes = _sum_col(df, "team_minutes")

    player_actions = player_fga + 0.44 * player_fta + player_tov
    team_actions = team_fga + 0.44 * team_fta + team_tov

    numer = player_actions * (team_minutes / 5.0)
    denom = player_minutes * team_actions
    value = _safe_divide(numer, denom)
    return None if value is None else round(100.0 * value, 3)


def compute_sample_ast_pct(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None

    player_ast = _sum_col(df, "ast")
    player_fgm = _sum_col(df, "fgm")
    player_minutes = _sum_col(df, "minutes")

    team_fgm = _sum_col(df, "team_fgm")
    team_minutes = _sum_col(df, "team_minutes")

    team_unit_minutes = team_minutes / 5.0
    minute_share = _safe_divide(player_minutes, team_unit_minutes)
    if minute_share is None:
        return None

    denom = (minute_share * team_fgm) - player_fgm
    value = _safe_divide(player_ast, denom)
    return None if value is None else round(100.0 * value, 3)


def compute_sample_reb_pct(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None

    player_reb = _sum_col(df, "reb")
    player_minutes = _sum_col(df, "minutes")

    team_minutes = _sum_col(df, "team_minutes")
    team_reb = _sum_col(df, "team_reb")
    opp_reb = _sum_col(df, "opp_reb")

    numer = player_reb * (team_minutes / 5.0)
    denom = player_minutes * (team_reb + opp_reb)
    value = _safe_divide(numer, denom)
    return None if value is None else round(100.0 * value, 3)


def compute_sample_tov_pct(df: pd.DataFrame) -> float | None:
    """Compute turnover percentage over a filtered sample.

    TOV% = 100 * TOV / (FGA + 0.44 * FTA + TOV)
    """
    if df.empty:
        return None

    player_fga = _sum_col(df, "fga")
    player_fta = _sum_col(df, "fta")
    player_tov = _sum_col(df, "tov")

    denom = player_fga + 0.44 * player_fta + player_tov
    value = _safe_divide(player_tov, denom)
    return None if value is None else round(100.0 * value, 3)


def compute_sample_advanced_metrics(df: pd.DataFrame) -> dict[str, float | None]:
    return {
        "usg_pct_avg": compute_sample_usg_pct(df),
        "ast_pct_avg": compute_sample_ast_pct(df),
        "reb_pct_avg": compute_sample_reb_pct(df),
        "tov_pct_avg": compute_sample_tov_pct(df),
    }


def add_sample_advanced_metrics_to_summary_row(
    sample_df: pd.DataFrame,
    summary_row: dict,
    include_sum_fields: bool = False,
) -> dict:
    out = dict(summary_row)
    metrics = compute_sample_advanced_metrics(sample_df)
    out.update(metrics)

    if include_sum_fields:
        for key, value in metrics.items():
            sum_key = key.replace("_avg", "_sum")
            out[sum_key] = value

    return out


def compute_grouped_sample_advanced_metrics(
    df: pd.DataFrame,
    group_col: str,
) -> pd.DataFrame:
    if group_col not in df.columns:
        raise ValueError(f"Missing group column: {group_col}")

    rows = []
    for bucket, group in df.groupby(group_col, dropna=False):
        metrics = compute_sample_advanced_metrics(group)
        rows.append(
            {
                group_col: bucket,
                "usg_pct_avg": metrics["usg_pct_avg"],
                "ast_pct_avg": metrics["ast_pct_avg"],
                "reb_pct_avg": metrics["reb_pct_avg"],
                "tov_pct_avg": metrics["tov_pct_avg"],
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[group_col, "usg_pct_avg", "ast_pct_avg", "reb_pct_avg", "tov_pct_avg"]
        )

    return pd.DataFrame(rows)


def compute_season_grouped_sample_advanced_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if "season" not in df.columns:
        raise ValueError("Missing season column")

    rows = []
    for season, group in df.groupby("season", dropna=False):
        metrics = compute_sample_advanced_metrics(group)
        rows.append(
            {
                "season": season,
                "usg_pct_avg": metrics["usg_pct_avg"],
                "ast_pct_avg": metrics["ast_pct_avg"],
                "reb_pct_avg": metrics["reb_pct_avg"],
                "tov_pct_avg": metrics["tov_pct_avg"],
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=["season", "usg_pct_avg", "ast_pct_avg", "reb_pct_avg", "tov_pct_avg"]
        )

    return pd.DataFrame(rows).sort_values("season").reset_index(drop=True)
