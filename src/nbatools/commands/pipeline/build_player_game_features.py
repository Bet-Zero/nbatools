from pathlib import Path

import pandas as pd


def run(season: str, season_type: str) -> None:
    safe_season_type = season_type.lower().replace(" ", "_")

    in_path = Path(f"data/raw/player_game_stats/{season}_{safe_season_type}.csv")
    out_dir = Path("data/processed/player_game_features")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{season}_{safe_season_type}.csv"

    if not in_path.exists():
        raise FileNotFoundError(f"Missing required input file: {in_path}")

    df = pd.read_csv(in_path)

    required = [
        "game_id",
        "season",
        "season_type",
        "game_date",
        "player_id",
        "team_id",
        "minutes",
        "pts",
        "reb",
        "ast",
        "fga",
        "fg3a",
        "fta",
        "fg_pct",
        "fg3_pct",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce")
    df = df.sort_values(["player_id", "game_date", "game_id"]).reset_index(drop=True)

    # Prior-game values only
    df["prev_minutes"] = df.groupby("player_id")["minutes"].shift(1)
    df["prev_pts"] = df.groupby("player_id")["pts"].shift(1)
    df["prev_reb"] = df.groupby("player_id")["reb"].shift(1)
    df["prev_ast"] = df.groupby("player_id")["ast"].shift(1)
    df["prev_fga"] = df.groupby("player_id")["fga"].shift(1)
    df["prev_fg3a"] = df.groupby("player_id")["fg3a"].shift(1)
    df["prev_fta"] = df.groupby("player_id")["fta"].shift(1)
    df["prev_fg_pct"] = df.groupby("player_id")["fg_pct"].shift(1)
    df["prev_fg3_pct"] = df.groupby("player_id")["fg3_pct"].shift(1)
    df["prev_game_flag"] = df.groupby("player_id")["game_id"].shift(1).notna().astype(int)

    # Rolling windows
    df["minutes_last_5"] = df.groupby("player_id")["prev_minutes"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )
    df["minutes_last_10"] = df.groupby("player_id")["prev_minutes"].transform(
        lambda s: s.rolling(10, min_periods=1).mean()
    )

    df["pts_last_5"] = df.groupby("player_id")["prev_pts"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )
    df["pts_last_10"] = df.groupby("player_id")["prev_pts"].transform(
        lambda s: s.rolling(10, min_periods=1).mean()
    )

    df["reb_last_5"] = df.groupby("player_id")["prev_reb"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )
    df["ast_last_5"] = df.groupby("player_id")["prev_ast"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )

    df["fga_last_5"] = df.groupby("player_id")["prev_fga"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )
    df["fg3a_last_5"] = df.groupby("player_id")["prev_fg3a"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )
    df["fta_last_5"] = df.groupby("player_id")["prev_fta"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )

    df["fg_pct_last_5"] = df.groupby("player_id")["prev_fg_pct"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )
    df["fg3_pct_last_5"] = df.groupby("player_id")["prev_fg3_pct"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )

    # Window completeness
    df["games_in_window_last_5"] = (
        df.groupby("player_id")["prev_game_flag"]
        .transform(lambda s: s.rolling(5, min_periods=1).sum())
        .fillna(0)
        .astype(int)
    )
    df["games_in_window_last_10"] = (
        df.groupby("player_id")["prev_game_flag"]
        .transform(lambda s: s.rolling(10, min_periods=1).sum())
        .fillna(0)
        .astype(int)
    )

    df["has_full_last_5_window"] = (df["games_in_window_last_5"] >= 5).astype(int)
    df["has_full_last_10_window"] = (df["games_in_window_last_10"] >= 10).astype(int)

    keep_cols = [
        "player_id",
        "game_id",
        "team_id",
        "game_date",
        "season",
        "season_type",
        "minutes_last_5",
        "minutes_last_10",
        "pts_last_5",
        "pts_last_10",
        "reb_last_5",
        "ast_last_5",
        "fga_last_5",
        "fg3a_last_5",
        "fta_last_5",
        "fg_pct_last_5",
        "fg3_pct_last_5",
        "games_in_window_last_5",
        "games_in_window_last_10",
        "has_full_last_5_window",
        "has_full_last_10_window",
    ]

    features = df[keep_cols].copy()
    features.to_csv(out_path, index=False)
    print(f"Saved {out_path}")
