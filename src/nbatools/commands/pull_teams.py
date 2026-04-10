from pathlib import Path

import pandas as pd


def run() -> None:
    out_dir = Path("data/raw/teams")
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(
        [
            {
                "team_id": 1610612737,
                "team_abbr": "ATL",
                "team_name": "Hawks",
                "city": "Atlanta",
                "conference": "East",
                "division": "Southeast",
                "active_flag": 1,
            },
            {
                "team_id": 1610612738,
                "team_abbr": "BOS",
                "team_name": "Celtics",
                "city": "Boston",
                "conference": "East",
                "division": "Atlantic",
                "active_flag": 1,
            },
        ]
    )

    out_path = out_dir / "teams_reference.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {out_path}")
