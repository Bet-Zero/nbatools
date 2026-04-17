from __future__ import annotations

import pandas as pd

REQUIRED_PLAYER_COLUMNS = {
    "game_id",
    "team_abbr",
    "minutes",
    "fga",
    "fta",
    "tov",
}

REQUIRED_TEAM_COLUMNS = {
    "game_id",
    "team_abbr",
    "minutes",
    "fga",
    "fta",
    "tov",
}


def _coerce_minutes_to_float(series: pd.Series) -> pd.Series:
    """
    Convert minutes values to numeric minutes.

    Supports:
    - numeric values already in minutes
    - strings like '36:24'
    - strings like '38'
    """
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    def parse_one(value):
        if pd.isna(value):
            return None

        text = str(value).strip()
        if not text:
            return None

        if ":" in text:
            try:
                mins, secs = text.split(":", 1)
                return float(mins) + (float(secs) / 60.0)
            except Exception:
                return None

        try:
            return float(text)
        except Exception:
            return None

    return series.apply(parse_one)


def _validate_columns(df: pd.DataFrame, required: set[str], label: str) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {', '.join(missing)}")


def add_usage_rate(
    player_df: pd.DataFrame,
    team_df: pd.DataFrame,
    *,
    player_game_id_col: str = "game_id",
    team_game_id_col: str = "game_id",
    player_team_col: str = "team_abbr",
    team_team_col: str = "team_abbr",
    player_minutes_col: str = "minutes",
    team_minutes_col: str = "minutes",
    player_fga_col: str = "fga",
    team_fga_col: str = "fga",
    player_fta_col: str = "fta",
    team_fta_col: str = "fta",
    player_tov_col: str = "tov",
    team_tov_col: str = "tov",
    output_col: str = "usg_pct",
) -> pd.DataFrame:
    """
    Add per-game usage rate (USG%) to a player game log DataFrame.

    Formula:
        USG% = 100 * ((FGA + 0.44*FTA + TOV) * (Team Minutes / 5))
                    / (Minutes * (Team FGA + 0.44*Team FTA + Team TOV))

    Assumptions:
    - player_df contains one row per player game
    - team_df contains one row per team game for the player's team
    - both can be joined on (game_id, team_abbr)

    Returns a copy of player_df with:
    - team_fga
    - team_fta
    - team_tov
    - team_minutes
    - usg_pct
    """
    player = player_df.copy()
    team = team_df.copy()

    player = player.rename(
        columns={
            player_game_id_col: "game_id",
            player_team_col: "team_abbr",
            player_minutes_col: "minutes",
            player_fga_col: "fga",
            player_fta_col: "fta",
            player_tov_col: "tov",
        }
    )

    team = team.rename(
        columns={
            team_game_id_col: "game_id",
            team_team_col: "team_abbr",
            team_minutes_col: "team_minutes",
            team_fga_col: "team_fga",
            team_fta_col: "team_fta",
            team_tov_col: "team_tov",
        }
    )

    _validate_columns(player, REQUIRED_PLAYER_COLUMNS, "player_df")
    _validate_columns(
        team.rename(
            columns={
                "team_minutes": "minutes",
                "team_fga": "fga",
                "team_fta": "fta",
                "team_tov": "tov",
            }
        ),
        REQUIRED_TEAM_COLUMNS,
        "team_df",
    )

    player["minutes"] = _coerce_minutes_to_float(player["minutes"])
    team["team_minutes"] = _coerce_minutes_to_float(team["team_minutes"])

    merge_cols = ["game_id", "team_abbr", "team_minutes", "team_fga", "team_fta", "team_tov"]
    merged = player.merge(
        team[merge_cols],
        on=["game_id", "team_abbr"],
        how="left",
        validate="many_to_one",
    )

    player_actions = (
        pd.to_numeric(merged["fga"], errors="coerce").fillna(0)
        + 0.44 * pd.to_numeric(merged["fta"], errors="coerce").fillna(0)
        + pd.to_numeric(merged["tov"], errors="coerce").fillna(0)
    )

    team_actions = (
        pd.to_numeric(merged["team_fga"], errors="coerce").fillna(0)
        + 0.44 * pd.to_numeric(merged["team_fta"], errors="coerce").fillna(0)
        + pd.to_numeric(merged["team_tov"], errors="coerce").fillna(0)
    )

    numerator = player_actions * (pd.to_numeric(merged["team_minutes"], errors="coerce") / 5.0)
    denominator = pd.to_numeric(merged["minutes"], errors="coerce") * team_actions

    merged[output_col] = (100.0 * numerator / denominator).where(denominator > 0)

    return merged


def summarize_usage_rate(
    player_with_usage_df: pd.DataFrame,
    *,
    usage_col: str = "usg_pct",
) -> dict[str, float | None]:
    """
    Return simple summary stats for usage rate over a filtered sample.
    """
    if usage_col not in player_with_usage_df.columns:
        return {
            "usg_pct_avg": None,
            "usg_pct_sum": None,
        }

    values = pd.to_numeric(player_with_usage_df[usage_col], errors="coerce")
    if values.notna().sum() == 0:
        return {
            "usg_pct_avg": None,
            "usg_pct_sum": None,
        }

    return {
        "usg_pct_avg": float(values.mean()),
        "usg_pct_sum": float(values.sum()),
    }


def add_usage_to_grouped_summary(
    grouped_df: pd.DataFrame,
    *,
    usage_col: str = "usg_pct",
    output_avg_col: str = "usg_pct_avg",
) -> pd.DataFrame:
    """
    Normalize grouped summary naming so downstream code can treat usage like
    the other averaged advanced metrics.
    """
    df = grouped_df.copy()
    if usage_col in df.columns and output_avg_col not in df.columns:
        df[output_avg_col] = pd.to_numeric(df[usage_col], errors="coerce")
    return df
