from pathlib import Path

import pandas as pd


def run(season: str, season_type: str) -> None:
    safe = season_type.lower().replace(" ", "_")

    in_path = Path(f"data/raw/team_game_stats/{season}_{safe}.csv")
    out_dir = Path("data/processed/team_game_features")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{season}_{safe}.csv"

    if not in_path.exists():
        raise FileNotFoundError(f"Missing input: {in_path}")

    df = pd.read_csv(in_path)

    df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce")
    df = df.sort_values(["team_id", "game_date", "game_id"]).reset_index(drop=True)

    # --- PREVIOUS GAME VALUES ---
    df["prev_pts"] = df.groupby("team_id")["pts"].shift(1)
    df["prev_fg3m"] = df.groupby("team_id")["fg3m"].shift(1)
    df["prev_fg3a"] = df.groupby("team_id")["fg3a"].shift(1)
    df["prev_fg3_pct"] = df.groupby("team_id")["fg3_pct"].shift(1)
    df["prev_reb"] = df.groupby("team_id")["reb"].shift(1)
    df["prev_tov"] = df.groupby("team_id")["tov"].shift(1)

    # --- REST CALCULATIONS ---
    df["prev_game_date"] = df.groupby("team_id")["game_date"].shift(1)

    df["days_rest"] = (df["game_date"] - df["prev_game_date"]).dt.days

    # If no previous game, set to None
    df["days_rest"] = df["days_rest"].where(df["prev_game_date"].notna(), None)

    df["is_back_to_back"] = (df["days_rest"] == 1).astype(int)

    # --- ROLLING FEATURES ---
    df["pts_last_5"] = df.groupby("team_id")["prev_pts"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )
    df["pts_last_10"] = df.groupby("team_id")["prev_pts"].transform(
        lambda s: s.rolling(10, min_periods=1).mean()
    )

    df["fg3m_last_5"] = df.groupby("team_id")["prev_fg3m"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )
    df["fg3a_last_5"] = df.groupby("team_id")["prev_fg3a"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )
    df["fg3_pct_last_5"] = df.groupby("team_id")["prev_fg3_pct"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )

    df["reb_last_5"] = df.groupby("team_id")["prev_reb"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )
    df["tov_last_5"] = df.groupby("team_id")["prev_tov"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )

    # --- WINDOW COUNTS ---
    prev_games = df.groupby("team_id")["game_id"].shift(1).notna().astype(int)

    df["games_in_window_last_5"] = (
        prev_games.groupby(df["team_id"])
        .transform(lambda s: s.rolling(5, min_periods=1).sum())
        .fillna(0)
        .astype(int)
    )
    df["games_in_window_last_10"] = (
        prev_games.groupby(df["team_id"])
        .transform(lambda s: s.rolling(10, min_periods=1).sum())
        .fillna(0)
        .astype(int)
    )

    df["has_full_last_5_window"] = (df["games_in_window_last_5"] >= 5).astype(int)
    df["has_full_last_10_window"] = (df["games_in_window_last_10"] >= 10).astype(int)

    keep = [
        "team_id",
        "game_id",
        "game_date",
        "season",
        "season_type",
        "opponent_team_id",
        "is_home",
        # NEW
        "days_rest",
        "is_back_to_back",
        # existing
        "pts_last_5",
        "pts_last_10",
        "fg3m_last_5",
        "fg3a_last_5",
        "fg3_pct_last_5",
        "reb_last_5",
        "tov_last_5",
        "games_in_window_last_5",
        "games_in_window_last_10",
        "has_full_last_5_window",
        "has_full_last_10_window",
    ]

    df[keep].to_csv(out_path, index=False)
    print(f"Saved {out_path}")
