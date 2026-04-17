import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import CommonTeamRoster
from nba_api.stats.static import teams

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_SLEEP_SECONDS = 2.0


def fetch_team_roster(team_id: int, season: str) -> pd.DataFrame:
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            endpoint = CommonTeamRoster(
                team_id=team_id,
                season=season,
                timeout=REQUEST_TIMEOUT,
            )
            df = endpoint.get_data_frames()[0]
            return df
        except Exception as exc:
            last_err = exc
            if attempt < MAX_RETRIES:
                sleep_for = RETRY_SLEEP_SECONDS * attempt
                print(
                    f"Roster request failed for team {team_id} "
                    f"(attempt {attempt}/{MAX_RETRIES}). Retrying in {sleep_for:.1f}s..."
                )
                time.sleep(sleep_for)
            else:
                break

    raise RuntimeError(f"Failed to fetch roster for team_id={team_id}: {last_err}")


def normalize_columns(df: pd.DataFrame, season: str, team_id: int, team_abbr: str) -> pd.DataFrame:
    rename_map = {
        "PLAYER_ID": "player_id",
        "PLAYER": "player_name",
        "NUM": "jersey_number",
        "POSITION": "position",
        "HEIGHT": "height",
        "WEIGHT": "weight",
        "BIRTH_DATE": "birth_date",
        "EXP": "experience_years",
        "SCHOOL": "school",
    }

    df = df.rename(columns=rename_map).copy()

    required = [
        "player_id",
        "player_name",
        "jersey_number",
        "position",
        "height",
        "weight",
        "birth_date",
        "experience_years",
        "school",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing roster columns after rename: {missing}")

    df["season"] = season
    df["team_id"] = team_id
    df["team_abbr"] = team_abbr
    df["stint"] = 1

    keep_cols = [
        "season",
        "team_id",
        "team_abbr",
        "player_id",
        "player_name",
        "jersey_number",
        "position",
        "height",
        "weight",
        "birth_date",
        "experience_years",
        "school",
        "stint",
    ]

    return df[keep_cols].copy()


def run(season: str) -> None:
    out_dir = Path("data/raw/rosters")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{season}.csv"

    nba_teams = teams.get_teams()
    all_rows = []

    for t in nba_teams:
        team_id = t["id"]
        team_abbr = t["abbreviation"]

        print(f"Fetching roster for {team_abbr} ({team_id})...")
        raw = fetch_team_roster(team_id=team_id, season=season)

        if raw.empty:
            continue

        norm = normalize_columns(raw, season=season, team_id=team_id, team_abbr=team_abbr)
        all_rows.append(norm)

        time.sleep(0.6)

    if not all_rows:
        raise RuntimeError(f"No roster data fetched for season={season}")

    df = pd.concat(all_rows, ignore_index=True)

    # Normalize a few fields
    df["birth_date"] = pd.to_datetime(df["birth_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["experience_years"] = df["experience_years"].replace("R", "0")
    df["experience_years"] = pd.to_numeric(df["experience_years"], errors="coerce")
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")

    df = df.drop_duplicates(subset=["season", "team_id", "player_id", "stint"]).copy()
    df = df.sort_values(["team_id", "player_name"]).reset_index(drop=True)

    df.to_csv(out_path, index=False)
    print(f"Saved {out_path}")
    print(f"Rows: {len(df)}")
