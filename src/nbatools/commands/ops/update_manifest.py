from datetime import datetime
from pathlib import Path

import pandas as pd

RAW_REQUIRED = [
    "games",
    "schedule",
    "team_game_stats",
    "player_game_stats",
    "team_season_advanced",
    "player_season_advanced",
]

PROCESSED_REQUIRED = [
    "team_game_features",
    "game_features",
    "player_game_features",
    "league_season_stats",
]


def raw_paths(season: str, season_type: str) -> list[Path]:
    safe = season_type.lower().replace(" ", "_")
    paths = [
        Path(f"data/raw/games/{season}_{safe}.csv"),
        Path(f"data/raw/schedule/{season}_{safe}.csv"),
        Path(f"data/raw/team_game_stats/{season}_{safe}.csv"),
        Path(f"data/raw/player_game_stats/{season}_{safe}.csv"),
        Path(f"data/raw/team_season_advanced/{season}_{safe}.csv"),
        Path(f"data/raw/player_season_advanced/{season}_{safe}.csv"),
        Path(f"data/raw/rosters/{season}.csv"),
    ]

    if season_type != "Playoffs":
        paths.append(Path(f"data/raw/standings_snapshots/{season}_{safe}.csv"))

    return paths


def processed_paths(season: str, season_type: str) -> list[Path]:
    safe = season_type.lower().replace(" ", "_")
    return [
        Path(f"data/processed/team_game_features/{season}_{safe}.csv"),
        Path(f"data/processed/game_features/{season}_{safe}.csv"),
        Path(f"data/processed/player_game_features/{season}_{safe}.csv"),
        Path(f"data/processed/league_season_stats/{season}_{safe}.csv"),
    ]


def run(season: str, season_type: str) -> None:
    metadata_dir = Path("data/metadata")
    metadata_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = metadata_dir / "backfill_manifest.csv"

    raw_complete = all(p.exists() for p in raw_paths(season, season_type))
    processed_complete = all(p.exists() for p in processed_paths(season, season_type))

    new_row = pd.DataFrame(
        [
            {
                "season": season,
                "season_type": season_type,
                "raw_complete": int(raw_complete),
                "processed_complete": int(processed_complete),
                "loaded_at": datetime.now().isoformat(timespec="seconds"),
            }
        ]
    )

    if manifest_path.exists():
        df = pd.read_csv(manifest_path)
        df = df[~((df["season"] == season) & (df["season_type"] == season_type))].copy()
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = new_row

    df = df.sort_values(["season", "season_type"]).reset_index(drop=True)
    df.to_csv(manifest_path, index=False)

    print(f"Updated {manifest_path}")
