import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import LeagueGameFinder

REQUEST_TIMEOUT = 30
MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 3.0


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "GAME_ID": "game_id",
        "GAME_DATE": "game_date",
        "TEAM_ID": "team_id",
        "TEAM_ABBREVIATION": "team_abbr",
        "TEAM_NAME": "team_name",
        "MATCHUP": "matchup",
        "WL": "wl",
        "PLAYER_ID": "player_id",
        "PLAYER_NAME": "player_name",
        "START_POSITION": "start_position",
        "MIN": "minutes",
        "PTS": "pts",
        "FGM": "fgm",
        "FGA": "fga",
        "FG_PCT": "fg_pct",
        "FG3M": "fg3m",
        "FG3A": "fg3a",
        "FG3_PCT": "fg3_pct",
        "FTM": "ftm",
        "FTA": "fta",
        "FT_PCT": "ft_pct",
        "OREB": "oreb",
        "DREB": "dreb",
        "REB": "reb",
        "AST": "ast",
        "STL": "stl",
        "BLK": "blk",
        "TOV": "tov",
        "PF": "pf",
        "PLUS_MINUS": "plus_minus",
        "COMMENT": "comment",
    }

    df = df.rename(columns=rename_map)

    required = [
        "game_id",
        "game_date",
        "team_id",
        "team_abbr",
        "team_name",
        "matchup",
        "wl",
        "player_id",
        "player_name",
        "minutes",
        "pts",
        "fgm",
        "fga",
        "fg_pct",
        "fg3m",
        "fg3a",
        "fg3_pct",
        "ftm",
        "fta",
        "ft_pct",
        "oreb",
        "dreb",
        "reb",
        "ast",
        "stl",
        "blk",
        "tov",
        "pf",
        "plus_minus",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns after rename: {missing}")

    if "start_position" not in df.columns:
        df["start_position"] = ""
    if "comment" not in df.columns:
        df["comment"] = ""

    df["is_home"] = df["matchup"].str.contains(" vs. ", na=False).astype(int)
    df["is_away"] = df["matchup"].str.contains(" @ ", na=False).astype(int)

    return df


def add_opponent_info(df: pd.DataFrame) -> pd.DataFrame:
    team_lookup = (
        df[["game_id", "team_id", "team_abbr", "team_name"]]
        .drop_duplicates()
        .rename(
            columns={
                "team_id": "opponent_team_id",
                "team_abbr": "opponent_team_abbr",
                "team_name": "opponent_team_name",
            }
        )
    )

    merged = df.merge(team_lookup, on="game_id", how="left")
    merged = merged[merged["team_id"] != merged["opponent_team_id"]].copy()
    merged = merged.drop_duplicates(subset=["game_id", "player_id"]).copy()

    return merged


def add_starter_flag(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["starter_flag"] = df["start_position"].fillna("").astype(str).str.strip().ne("").astype(int)
    return df


def fetch_player_game_logs(season: str, season_type: str) -> pd.DataFrame:
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            endpoint = LeagueGameFinder(
                season_nullable=season,
                season_type_nullable=season_type,
                player_or_team_abbreviation="P",
                timeout=REQUEST_TIMEOUT,
            )

            data_frames = endpoint.get_data_frames()
            if not data_frames:
                raise ValueError("No tables returned from LeagueGameFinder")

            df = data_frames[0]
            if df.empty:
                raise ValueError(f"No data returned for season={season}, season_type={season_type}")

            return df

        except Exception as exc:
            last_err = exc
            sleep_for = RETRY_SLEEP_SECONDS * attempt

            if attempt < MAX_RETRIES:
                print(
                    f"Request failed (attempt {attempt}/{MAX_RETRIES}): {exc}. "
                    f"Retrying in {sleep_for:.1f}s..."
                )
                time.sleep(sleep_for)
            else:
                break

    raise RuntimeError(f"Failed to fetch player game logs: {last_err}")


def run(season: str, season_type: str) -> None:
    out_dir = Path("data/raw/player_game_stats")
    out_dir.mkdir(parents=True, exist_ok=True)

    safe = season_type.lower().replace(" ", "_")
    out_path = out_dir / f"{season}_{safe}.csv"

    raw = fetch_player_game_logs(season=season, season_type=season_type)
    df = normalize_columns(raw)
    df = add_opponent_info(df)
    df = add_starter_flag(df)

    df["season"] = season
    df["season_type"] = season_type

    keep_cols = [
        "game_id",
        "season",
        "season_type",
        "game_date",
        "team_id",
        "team_abbr",
        "team_name",
        "opponent_team_id",
        "opponent_team_abbr",
        "opponent_team_name",
        "is_home",
        "is_away",
        "player_id",
        "player_name",
        "starter_flag",
        "start_position",
        "minutes",
        "pts",
        "fgm",
        "fga",
        "fg_pct",
        "fg3m",
        "fg3a",
        "fg3_pct",
        "ftm",
        "fta",
        "ft_pct",
        "oreb",
        "dreb",
        "reb",
        "ast",
        "stl",
        "blk",
        "tov",
        "pf",
        "plus_minus",
        "comment",
    ]

    df = df[keep_cols].copy()
    df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.sort_values(["game_date", "game_id", "team_id", "player_id"]).reset_index(drop=True)

    df.to_csv(out_path, index=False)
    print(f"Saved {out_path}")
    print(f"Rows: {len(df)}")
