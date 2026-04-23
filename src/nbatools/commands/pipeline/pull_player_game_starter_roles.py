import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import BoxScoreTraditionalV3

REQUEST_TIMEOUT = 30
MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 3.0
ROLE_SOURCE = "boxscore_traditional_v3.position"


def _api_game_id(game_id: int | str) -> str:
    return str(int(game_id)).zfill(10)


def normalize_boxscore_player_roles(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "gameId": "game_id",
        "teamId": "team_id",
        "teamTricode": "team_abbr",
        "personId": "player_id",
        "firstName": "first_name",
        "familyName": "family_name",
        "position": "starter_position_raw",
    }
    out = df.rename(columns=rename_map).copy()

    required = [
        "game_id",
        "team_id",
        "team_abbr",
        "player_id",
        "first_name",
        "family_name",
        "starter_position_raw",
    ]
    missing = [col for col in required if col not in out.columns]
    if missing:
        raise ValueError(f"Missing required box score columns after rename: {missing}")

    out["player_name"] = (
        out["first_name"].fillna("").astype(str).str.strip()
        + " "
        + out["family_name"].fillna("").astype(str).str.strip()
    ).str.strip()
    out["starter_position_raw"] = out["starter_position_raw"].fillna("").astype(str).str.strip()
    out["starter_flag"] = out["starter_position_raw"].ne("").astype(int)
    out["role_source"] = ROLE_SOURCE

    keep_cols = [
        "game_id",
        "team_id",
        "team_abbr",
        "player_id",
        "player_name",
        "starter_position_raw",
        "starter_flag",
        "role_source",
    ]
    return out[keep_cols].copy()


def add_trust_validation(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if out.duplicated(subset=["game_id", "player_id"]).any():
        raise ValueError("Duplicate (game_id, player_id) in starter-role backfill")

    counts = (
        out.groupby(["game_id", "team_id"], as_index=False)["starter_flag"]
        .sum()
        .rename(columns={"starter_flag": "starter_count_for_team_game"})
    )
    out = out.merge(counts, on=["game_id", "team_id"], how="left", validate="many_to_one")
    out["role_source_trusted"] = out["starter_count_for_team_game"].eq(5).astype(int)
    out["role_validation_reason"] = out["role_source_trusted"].map(
        {1: "", 0: "starter_count_not_five"}
    )

    keep_cols = [
        "game_id",
        "season",
        "season_type",
        "team_id",
        "team_abbr",
        "player_id",
        "player_name",
        "starter_position_raw",
        "starter_flag",
        "role_source",
        "role_source_trusted",
        "starter_count_for_team_game",
        "role_validation_reason",
    ]
    return out[keep_cols].copy()


def fetch_starter_role_rows_for_game(game_id: int | str) -> pd.DataFrame:
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            endpoint = BoxScoreTraditionalV3(
                game_id=_api_game_id(game_id),
                timeout=REQUEST_TIMEOUT,
            )
            frames = endpoint.get_data_frames()
            if not frames:
                raise ValueError(f"No tables returned for game_id={game_id}")

            df = frames[0]
            if df.empty:
                raise ValueError(f"No player rows returned for game_id={game_id}")

            return df
        except Exception as exc:
            last_err = exc
            sleep_for = RETRY_SLEEP_SECONDS * attempt
            if attempt < MAX_RETRIES:
                print(
                    f"Starter-role request failed for game {game_id} "
                    f"(attempt {attempt}/{MAX_RETRIES}): {exc}. "
                    f"Retrying in {sleep_for:.1f}s..."
                )
                time.sleep(sleep_for)
            else:
                break

    raise RuntimeError(f"Failed to fetch starter-role rows for game {game_id}: {last_err}")


def build_starter_role_backfill(season: str, season_type: str) -> pd.DataFrame:
    safe = season_type.lower().replace(" ", "_")
    games_path = Path(f"data/raw/games/{season}_{safe}.csv")
    if not games_path.exists():
        raise FileNotFoundError(f"Missing games file: {games_path}")

    games = pd.read_csv(games_path)
    if "game_id" not in games.columns:
        raise ValueError("games missing required column: ['game_id']")

    game_ids = games["game_id"].dropna().drop_duplicates().tolist()
    if not game_ids:
        raise ValueError(f"No game_id values found in {games_path}")

    frames: list[pd.DataFrame] = []
    for game_id in game_ids:
        frame = normalize_boxscore_player_roles(fetch_starter_role_rows_for_game(game_id))
        frame["game_id"] = int(game_id)
        frame["season"] = season
        frame["season_type"] = season_type
        frames.append(frame)

    out = pd.concat(frames, ignore_index=True)
    out["game_id"] = pd.to_numeric(out["game_id"], errors="raise").astype(int)
    out["team_id"] = pd.to_numeric(out["team_id"], errors="raise").astype(int)
    out["player_id"] = pd.to_numeric(out["player_id"], errors="raise").astype(int)
    out = add_trust_validation(out)
    out = out.sort_values(["game_id", "team_id", "player_id"]).reset_index(drop=True)
    return out


def run(season: str, season_type: str) -> None:
    out_dir = Path("data/raw/player_game_starter_roles")
    out_dir.mkdir(parents=True, exist_ok=True)

    safe = season_type.lower().replace(" ", "_")
    out_path = out_dir / f"{season}_{safe}.csv"

    df = build_starter_role_backfill(season=season, season_type=season_type)
    df.to_csv(out_path, index=False)

    print(f"Saved {out_path}")
    print(f"Rows: {len(df)}")
