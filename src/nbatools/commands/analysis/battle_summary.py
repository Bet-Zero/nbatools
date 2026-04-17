from pathlib import Path

import pandas as pd

BATTLE_CONFIG = {
    "fg3m": {
        "winner_col": "fg3m_battle_winner",
        "diff_col": "fg3m_last_5_diff",
        "higher_is_better": True,
    },
    "fg3_pct": {
        "winner_col": "fg3_pct_battle_winner",
        "diff_col": "fg3_pct_last_5_diff",
        "higher_is_better": True,
    },
    "reb": {
        "winner_col": "reb_battle_winner",
        "diff_col": "reb_last_5_diff",
        "higher_is_better": True,
    },
    "tov": {
        "winner_col": "tov_battle_winner",
        "diff_col": "tov_last_5_diff",
        "higher_is_better": False,
    },
    "rest": {
        "winner_col": "rest_advantage",
        "diff_col": "rest_diff",
        "higher_is_better": True,
    },
}


def winner_result(row: pd.Series) -> str | None:
    if pd.isna(row.get("winner_col_value")) or pd.isna(row.get("home_team_won")):
        return None

    winner = row["winner_col_value"]
    home_team_won = int(row["home_team_won"])

    if winner == "tie":
        return "tie"
    if winner == "home":
        return "win" if home_team_won == 1 else "loss"
    if winner == "away":
        return "win" if home_team_won == 0 else "loss"
    return None


def run(
    season: str,
    battle: str,
    season_type: str = "Regular Season",
    exclude_ties: bool = False,
) -> None:
    safe = season_type.lower().replace(" ", "_")
    path = Path(f"data/processed/game_features/{season}_{safe}.csv")

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    battle = battle.lower().strip()
    if battle not in BATTLE_CONFIG:
        allowed = ", ".join(sorted(BATTLE_CONFIG.keys()))
        raise ValueError(f"Unsupported battle '{battle}'. Allowed battles: {allowed}")

    cfg = BATTLE_CONFIG[battle]
    df = pd.read_csv(path)

    winner_col = cfg["winner_col"]
    diff_col = cfg["diff_col"]

    required = [winner_col, diff_col, "game_id", "game_date", "home_team_id", "away_team_id"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in game_features: {missing}")

    games_path = Path(f"data/raw/games/{season}_{safe}.csv")
    if not games_path.exists():
        raise FileNotFoundError(f"Missing games file: {games_path}")

    games = pd.read_csv(games_path)
    if (
        "game_id" not in games.columns
        or "home_team_id" not in games.columns
        or "away_team_id" not in games.columns
    ):
        raise ValueError("games file is missing required columns")
    if "home_team_name" not in games.columns or "away_team_name" not in games.columns:
        raise ValueError("games file is missing home/away team names")

    team_stats_path = Path(f"data/raw/team_game_stats/{season}_{safe}.csv")
    if not team_stats_path.exists():
        raise FileNotFoundError(f"Missing team_game_stats file: {team_stats_path}")

    team_stats = pd.read_csv(team_stats_path)
    if (
        "game_id" not in team_stats.columns
        or "team_id" not in team_stats.columns
        or "wl" not in team_stats.columns
    ):
        raise ValueError("team_game_stats file is missing required columns")

    home_results = (
        team_stats[["game_id", "team_id", "wl"]]
        .rename(columns={"team_id": "home_team_id", "wl": "home_wl"})
        .copy()
    )

    merged = df.merge(
        games[["game_id", "home_team_name", "away_team_name"]],
        on="game_id",
        how="left",
    ).merge(
        home_results,
        on=["game_id", "home_team_id"],
        how="left",
    )

    merged["home_team_won"] = merged["home_wl"].eq("W").astype(int)
    merged["winner_col_value"] = merged[winner_col]
    merged["battle_result"] = merged.apply(winner_result, axis=1)

    if exclude_ties:
        merged = merged[merged["winner_col_value"] != "tie"].copy()

    considered = merged[merged["battle_result"].isin(["win", "loss", "tie"])].copy()

    total_games = int(len(merged))
    considered_games = int(len(considered))
    wins = int((considered["battle_result"] == "win").sum())
    losses = int((considered["battle_result"] == "loss").sum())
    ties = int((considered["battle_result"] == "tie").sum())

    win_pct = (wins / (wins + losses)) if (wins + losses) > 0 else None

    summary = pd.DataFrame(
        [
            {
                "season": season,
                "season_type": season_type,
                "battle": battle,
                "total_games": total_games,
                "considered_games": considered_games,
                "wins_when_battle_winner_identified": wins,
                "losses_when_battle_winner_identified": losses,
                "ties": ties,
                "win_pct_when_battle_winner_identified": win_pct,
                "exclude_ties": int(exclude_ties),
            }
        ]
    )

    print("SUMMARY")
    print(summary.to_csv(index=False))

    detail_cols = [
        "game_date",
        "game_id",
        "home_team_name",
        "away_team_name",
        diff_col,
        "winner_col_value",
        "battle_result",
    ]
    detail_cols = [c for c in detail_cols if c in considered.columns]

    details = (
        considered[detail_cols].copy().sort_values(["game_date", "game_id"]).reset_index(drop=True)
    )

    print("DETAILS")
    print(details.to_csv(index=False))
