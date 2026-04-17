import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import LeagueGameFinder

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_SLEEP_SECONDS = 2.0


def fetch_schedule(season: str, season_type: str) -> pd.DataFrame:
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            endpoint = LeagueGameFinder(
                season_nullable=season,
                season_type_nullable=season_type,
                player_or_team_abbreviation="T",
                timeout=REQUEST_TIMEOUT,
            )
            df = endpoint.get_data_frames()[0]
            if df.empty:
                raise ValueError(f"No data returned for season={season}, season_type={season_type}")
            return df
        except Exception as exc:
            last_err = exc
            if attempt < MAX_RETRIES:
                sleep_for = RETRY_SLEEP_SECONDS * attempt
                print(
                    f"Request failed (attempt {attempt}/{MAX_RETRIES}). "
                    f"Retrying in {sleep_for:.1f}s..."
                )
                time.sleep(sleep_for)
            else:
                break

    raise RuntimeError(f"Failed to fetch schedule: {last_err}")


def run(season: str, season_type: str) -> None:
    out_dir = Path("data/raw/schedule")
    out_dir.mkdir(parents=True, exist_ok=True)

    safe = season_type.lower().replace(" ", "_")
    out_path = out_dir / f"{season}_{safe}.csv"

    raw = fetch_schedule(season=season, season_type=season_type).copy()

    rename_map = {
        "GAME_ID": "game_id",
        "GAME_DATE": "game_date",
        "MATCHUP": "matchup",
        "TEAM_ID": "team_id",
        "TEAM_ABBREVIATION": "team_abbr",
        "TEAM_NAME": "team_name",
    }
    raw = raw.rename(columns=rename_map)

    required = ["game_id", "game_date", "matchup", "team_id", "team_abbr", "team_name"]
    missing = [c for c in required if c not in raw.columns]
    if missing:
        raise ValueError(f"Missing required columns after rename: {missing}")

    raw["is_home"] = raw["matchup"].str.contains(" vs. ", na=False).astype(int)
    raw["is_away"] = raw["matchup"].str.contains(" @ ", na=False).astype(int)

    home = raw[raw["is_home"] == 1].copy()
    away = raw[raw["is_away"] == 1].copy()

    home = home.rename(
        columns={
            "team_id": "home_team_id",
            "team_abbr": "home_team_abbr",
            "team_name": "home_team_name",
        }
    )
    away = away.rename(
        columns={
            "team_id": "away_team_id",
            "team_abbr": "away_team_abbr",
            "team_name": "away_team_name",
        }
    )

    schedule = home.merge(
        away[["game_id", "away_team_id", "away_team_abbr", "away_team_name"]],
        on="game_id",
        how="inner",
    )

    schedule["season"] = season
    schedule["season_type"] = season_type
    schedule["game_date"] = pd.to_datetime(schedule["game_date"], errors="coerce").dt.strftime(
        "%Y-%m-%d"
    )

    # This endpoint does not give us a trustworthy future schedule metadata set here.
    # For now keep the schema stable.
    schedule["game_datetime"] = ""
    schedule["status"] = "Final"
    schedule["arena"] = ""
    schedule["city"] = ""
    schedule["national_tv"] = ""

    keep_cols = [
        "game_id",
        "season",
        "season_type",
        "game_date",
        "game_datetime",
        "status",
        "home_team_id",
        "away_team_id",
        "home_team_abbr",
        "away_team_abbr",
        "home_team_name",
        "away_team_name",
        "arena",
        "city",
        "national_tv",
    ]

    schedule = (
        schedule[keep_cols]
        .drop_duplicates(subset=["game_id"])
        .sort_values(["game_date", "game_id"])
        .reset_index(drop=True)
    )

    schedule.to_csv(out_path, index=False)
    print(f"Saved {out_path}")
    print(f"Rows: {len(schedule)}")
