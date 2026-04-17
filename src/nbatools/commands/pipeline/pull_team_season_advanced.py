import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import LeagueDashTeamStats
from nba_api.stats.static import teams

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_SLEEP_SECONDS = 2.0


def fetch_team_advanced(season: str, season_type: str) -> pd.DataFrame:
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            endpoint = LeagueDashTeamStats(
                season=season,
                season_type_all_star=season_type,
                measure_type_detailed_defense="Advanced",
                per_mode_detailed="PerGame",
                timeout=REQUEST_TIMEOUT,
            )
            df = endpoint.get_data_frames()[0]
            if df.empty:
                raise ValueError(
                    f"No team advanced stats returned for "
                    f"season={season}, season_type={season_type}"
                )
            return df
        except Exception as exc:
            last_err = exc
            if attempt < MAX_RETRIES:
                sleep_for = RETRY_SLEEP_SECONDS * attempt
                print(
                    f"Team advanced request failed (attempt {attempt}/{MAX_RETRIES}). "
                    f"Retrying in {sleep_for:.1f}s..."
                )
                time.sleep(sleep_for)
            else:
                break

    raise RuntimeError(f"Failed to fetch team advanced stats: {last_err}")


def normalize(df: pd.DataFrame, season: str, season_type: str, as_of_date: str) -> pd.DataFrame:
    rename_map = {
        "TEAM_ID": "team_id",
        "TEAM_ABBREVIATION": "team_abbr",
        "GP": "games_played",
        "W": "wins",
        "L": "losses",
        "W_PCT": "win_pct",
        "OFF_RATING": "off_rating",
        "DEF_RATING": "def_rating",
        "NET_RATING": "net_rating",
        "PACE": "pace",
    }

    df = df.rename(columns=rename_map).copy()

    # Fill team_abbr from static lookup if missing
    if "team_abbr" not in df.columns:
        team_lookup = pd.DataFrame(teams.get_teams())[["id", "abbreviation"]].rename(
            columns={"id": "team_id", "abbreviation": "team_abbr"}
        )
        df = df.merge(team_lookup, on="team_id", how="left")

    required = [
        "team_id",
        "team_abbr",
        "games_played",
        "wins",
        "losses",
        "win_pct",
        "off_rating",
        "def_rating",
        "net_rating",
        "pace",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing team advanced columns: {missing}")

    df["season"] = season
    df["season_type"] = season_type
    df["as_of_date"] = as_of_date

    keep_cols = [
        "season",
        "season_type",
        "as_of_date",
        "team_id",
        "team_abbr",
        "games_played",
        "wins",
        "losses",
        "win_pct",
        "off_rating",
        "def_rating",
        "net_rating",
        "pace",
    ]

    out = df[keep_cols].copy()

    numeric_cols = [
        "games_played",
        "wins",
        "losses",
        "win_pct",
        "off_rating",
        "def_rating",
        "net_rating",
        "pace",
    ]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    return out


def run(season: str, season_type: str) -> None:
    out_dir = Path("data/raw/team_season_advanced")
    out_dir.mkdir(parents=True, exist_ok=True)

    safe = season_type.lower().replace(" ", "_")
    out_path = out_dir / f"{season}_{safe}.csv"

    games_path = Path(f"data/raw/games/{season}_{safe}.csv")
    if not games_path.exists():
        raise FileNotFoundError("Games file required to derive as_of_date")

    games_df = pd.read_csv(games_path)
    as_of_date = pd.to_datetime(games_df["game_date"]).max().strftime("%Y-%m-%d")

    raw = fetch_team_advanced(season=season, season_type=season_type)
    df = normalize(raw, season=season, season_type=season_type, as_of_date=as_of_date)

    df = (
        df.drop_duplicates(subset=["team_id", "as_of_date"])
        .sort_values(["team_id"])
        .reset_index(drop=True)
    )

    df.to_csv(out_path, index=False)
    print(f"Saved {out_path}")
    print(f"Rows: {len(df)}")
