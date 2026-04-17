from pathlib import Path

import pandas as pd


def run(team_id: int | None = None, season: int | None = None) -> None:
    path = Path("data/raw/teams/team_history_reference.csv")
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    df = pd.read_csv(path)

    if team_id is not None:
        df = df[df["team_id"] == team_id].copy()

    if season is not None:
        df = df[(df["season_start"] <= season) & (df["season_end"] >= season)].copy()

    if df.empty:
        print("No matching rows found.")
        return

    print(df.to_csv(index=False))
