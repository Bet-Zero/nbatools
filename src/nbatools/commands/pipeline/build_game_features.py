from pathlib import Path

import pandas as pd


def run(season: str, season_type: str) -> None:
    safe = season_type.lower().replace(" ", "_")

    games_path = Path(f"data/raw/games/{season}_{safe}.csv")
    tf_path = Path(f"data/processed/team_game_features/{season}_{safe}.csv")

    out_dir = Path("data/processed/game_features")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{season}_{safe}.csv"

    if not games_path.exists():
        raise FileNotFoundError(f"Missing: {games_path}")
    if not tf_path.exists():
        raise FileNotFoundError(f"Missing: {tf_path}")

    games = pd.read_csv(games_path)
    tf = pd.read_csv(tf_path)

    home = tf[tf["is_home"] == 1].copy()
    away = tf[tf["is_home"] == 0].copy()

    def prefix(df, p):
        cols = {}
        for c in df.columns:
            if c != "game_id":
                cols[c] = f"{p}_{c}"
        return df.rename(columns=cols)

    home = prefix(home, "home")
    away = prefix(away, "away")

    merged = home.merge(away, on="game_id", how="inner")

    merged = merged.merge(
        games[["game_id", "game_date", "season", "season_type"]], on="game_id", how="left"
    )

    # --- REST FEATURES ---
    merged["rest_diff"] = merged["home_days_rest"] - merged["away_days_rest"]

    def rest_adv(row):
        h = row["home_days_rest"]
        a = row["away_days_rest"]

        if pd.isna(h) or pd.isna(a):
            return None
        if h > a:
            return "home"
        if a > h:
            return "away"
        return "tie"

    merged["rest_advantage"] = merged.apply(rest_adv, axis=1)

    # --- DIFFERENTIALS ---
    merged["pts_last_5_diff"] = merged["home_pts_last_5"] - merged["away_pts_last_5"]
    merged["fg3m_last_5_diff"] = merged["home_fg3m_last_5"] - merged["away_fg3m_last_5"]
    merged["fg3_pct_last_5_diff"] = merged["home_fg3_pct_last_5"] - merged["away_fg3_pct_last_5"]
    merged["reb_last_5_diff"] = merged["home_reb_last_5"] - merged["away_reb_last_5"]
    merged["tov_last_5_diff"] = merged["home_tov_last_5"] - merged["away_tov_last_5"]

    # --- BATTLE WINNERS ---
    def battle(a, b):
        if pd.isna(a) or pd.isna(b):
            return None
        if a > b:
            return "home"
        if b > a:
            return "away"
        return "tie"

    merged["fg3m_battle_winner"] = merged.apply(
        lambda r: battle(r["home_fg3m_last_5"], r["away_fg3m_last_5"]), axis=1
    )

    merged["fg3_pct_battle_winner"] = merged.apply(
        lambda r: battle(r["home_fg3_pct_last_5"], r["away_fg3_pct_last_5"]), axis=1
    )

    merged["reb_battle_winner"] = merged.apply(
        lambda r: battle(r["home_reb_last_5"], r["away_reb_last_5"]), axis=1
    )

    merged["tov_battle_winner"] = merged.apply(
        lambda r: battle(r["home_tov_last_5"], r["away_tov_last_5"]), axis=1
    )

    keep = [
        "game_id",
        "game_date",
        "season",
        "season_type",
        "home_team_id",
        "away_team_id",
        # REST
        "home_days_rest",
        "away_days_rest",
        "home_is_back_to_back",
        "away_is_back_to_back",
        "rest_diff",
        "rest_advantage",
        # SCORING
        "home_pts_last_5",
        "away_pts_last_5",
        "pts_last_5_diff",
        # 3PT
        "home_fg3m_last_5",
        "away_fg3m_last_5",
        "fg3m_last_5_diff",
        "fg3m_battle_winner",
        "home_fg3_pct_last_5",
        "away_fg3_pct_last_5",
        "fg3_pct_last_5_diff",
        "fg3_pct_battle_winner",
        # REB
        "home_reb_last_5",
        "away_reb_last_5",
        "reb_last_5_diff",
        "reb_battle_winner",
        # TOV
        "home_tov_last_5",
        "away_tov_last_5",
        "tov_last_5_diff",
        "tov_battle_winner",
    ]

    merged = merged[keep].copy()

    merged.to_csv(out_path, index=False)
    print(f"Saved {out_path}")
