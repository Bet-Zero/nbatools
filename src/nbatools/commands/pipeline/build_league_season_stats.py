from pathlib import Path

import pandas as pd


def run(season: str, season_type: str) -> None:
    safe = season_type.lower().replace(" ", "_")

    input_path = Path(f"data/raw/team_game_stats/{season}_{safe}.csv")
    output_dir = Path("data/processed/league_season_stats")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{season}_{safe}.csv"

    if not input_path.exists():
        raise FileNotFoundError(f"Missing team_game_stats: {input_path}")

    df = pd.read_csv(input_path)

    # Each game has 2 team rows → divide by 2 for game count
    total_games = df["game_id"].nunique()

    summary = {}

    summary["season"] = season
    summary["season_type"] = season_type
    summary["games"] = total_games

    # Basic totals
    summary["avg_pts"] = df["pts"].mean()
    summary["avg_fg3m"] = df["fg3m"].mean()
    summary["avg_fg3a"] = df["fg3a"].mean()
    summary["avg_fg3_pct"] = df["fg3_pct"].mean()
    summary["avg_reb"] = df["reb"].mean()
    summary["avg_tov"] = df["tov"].mean()

    out_df = pd.DataFrame([summary])

    out_df.to_csv(output_path, index=False)

    print(f"Saved {output_path}")
