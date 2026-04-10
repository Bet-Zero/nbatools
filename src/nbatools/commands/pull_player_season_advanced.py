import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import LeagueDashPlayerStats

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_SLEEP_SECONDS = 2.0


def fetch_player_advanced(season: str, season_type: str) -> pd.DataFrame:
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            endpoint = LeagueDashPlayerStats(
                season=season,
                season_type_all_star=season_type,
                measure_type_detailed_defense="Advanced",
                per_mode_detailed="PerGame",
                timeout=REQUEST_TIMEOUT,
            )
            df = endpoint.get_data_frames()[0]
            if df.empty:
                raise ValueError(
                    f"No player advanced stats returned for "
                    f"season={season}, season_type={season_type}"
                )
            return df
        except Exception as exc:
            last_err = exc
            if attempt < MAX_RETRIES:
                sleep_for = RETRY_SLEEP_SECONDS * attempt
                print(
                    f"Player advanced request failed (attempt {attempt}/{MAX_RETRIES}). "
                    f"Retrying in {sleep_for:.1f}s..."
                )
                time.sleep(sleep_for)
            else:
                break

    raise RuntimeError(f"Failed to fetch player advanced stats: {last_err}")


def normalize(raw: pd.DataFrame, season: str, season_type: str, as_of_date: str) -> pd.DataFrame:
    df = raw.copy()

    rename_map = {
        "PLAYER_ID": "player_id",
        "PLAYER_NAME": "player_name",
        "TEAM_ID": "team_id",
        "GP": "games_played",
        "MIN": "minutes_per_game",
        "OFF_RATING": "off_rating",
        "DEF_RATING": "def_rating",
        "NET_RATING": "net_rating",
        "USG_PCT": "usage_rate",
        "TS_PCT": "ts_pct",
        "AST_PCT": "ast_pct",
        "REB_PCT": "reb_pct",
        "OREB_PCT": "oreb_pct",
        "DREB_PCT": "dreb_pct",
        "PIE": "pie",
    }

    df = df.rename(columns=rename_map).copy()

    required = [
        "player_id",
        "player_name",
        "team_id",
        "games_played",
        "minutes_per_game",
        "usage_rate",
        "ts_pct",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing player advanced columns: {missing}")

    # Optional advanced columns: create if missing
    optional_cols = [
        "off_rating",
        "def_rating",
        "net_rating",
        "ast_pct",
        "reb_pct",
        "oreb_pct",
        "dreb_pct",
        "pie",
    ]
    for col in optional_cols:
        if col not in df.columns:
            df[col] = pd.NA

    df["season"] = season
    df["season_type"] = season_type
    df["as_of_date"] = as_of_date

    keep_cols = [
        "season",
        "season_type",
        "as_of_date",
        "player_id",
        "player_name",
        "team_id",
        "games_played",
        "minutes_per_game",
        "off_rating",
        "def_rating",
        "net_rating",
        "usage_rate",
        "ts_pct",
        "ast_pct",
        "reb_pct",
        "oreb_pct",
        "dreb_pct",
        "pie",
    ]

    out = df[keep_cols].copy()

    numeric_cols = [
        "games_played",
        "minutes_per_game",
        "off_rating",
        "def_rating",
        "net_rating",
        "usage_rate",
        "ts_pct",
        "ast_pct",
        "reb_pct",
        "oreb_pct",
        "dreb_pct",
        "pie",
    ]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    return out


def run(season: str, season_type: str) -> None:
    out_dir = Path("data/raw/player_season_advanced")
    out_dir.mkdir(parents=True, exist_ok=True)

    safe = season_type.lower().replace(" ", "_")
    out_path = out_dir / f"{season}_{safe}.csv"

    games_path = Path(f"data/raw/games/{season}_{safe}.csv")
    if not games_path.exists():
        raise FileNotFoundError("Games file required to derive as_of_date")

    games_df = pd.read_csv(games_path)
    as_of_date = pd.to_datetime(games_df["game_date"]).max().strftime("%Y-%m-%d")

    raw = fetch_player_advanced(season=season, season_type=season_type)
    df = normalize(raw, season=season, season_type=season_type, as_of_date=as_of_date)

    df = (
        df.drop_duplicates(subset=["player_id", "as_of_date"])
        .sort_values(["player_id"])
        .reset_index(drop=True)
    )

    df.to_csv(out_path, index=False)
    print(f"Saved {out_path}")
    print(f"Rows: {len(df)}")
