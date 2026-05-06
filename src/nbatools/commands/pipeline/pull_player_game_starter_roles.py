import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import BoxScoreTraditionalV3

REQUEST_TIMEOUT = 30
MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 3.0
REQUEST_PAUSE_SECONDS = 0.25
ROLE_SOURCE = "boxscore_traditional_v3.position"
STARTER_ROLE_BASE_COLUMNS = [
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
]


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


def _checkpoint_path(out_path: Path) -> Path:
    return out_path.with_suffix(".partial.csv")


def _load_cached_starter_role_rows(*paths: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for path in paths:
        if not path.exists():
            continue

        df = pd.read_csv(path)
        if df.empty:
            continue

        missing = [col for col in STARTER_ROLE_BASE_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"starter-role cache missing required columns: {missing}")

        frames.append(df[STARTER_ROLE_BASE_COLUMNS].copy())

    if not frames:
        return pd.DataFrame(columns=STARTER_ROLE_BASE_COLUMNS)

    out = pd.concat(frames, ignore_index=True)
    for col in ("game_id", "team_id", "player_id"):
        out[col] = pd.to_numeric(out[col], errors="raise").astype(int)
    out = out.drop_duplicates(subset=["game_id", "player_id"], keep="last")
    return out.reset_index(drop=True)


def _append_checkpoint_rows(path: Path, df: pd.DataFrame) -> None:
    header = not path.exists() or path.stat().st_size == 0
    df.to_csv(path, mode="a", header=header, index=False)


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


def build_starter_role_backfill(
    season: str,
    season_type: str,
    *,
    existing_rows: pd.DataFrame | None = None,
    checkpoint_path: Path | None = None,
) -> pd.DataFrame:
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

    seed = pd.DataFrame(columns=STARTER_ROLE_BASE_COLUMNS)
    if existing_rows is not None and not existing_rows.empty:
        missing = [col for col in STARTER_ROLE_BASE_COLUMNS if col not in existing_rows.columns]
        if missing:
            raise ValueError(f"existing starter-role rows missing required columns: {missing}")
        seed = existing_rows[STARTER_ROLE_BASE_COLUMNS].copy()
        for col in ("game_id", "team_id", "player_id"):
            seed[col] = pd.to_numeric(seed[col], errors="raise").astype(int)

    ordered_game_ids = [int(game_id) for game_id in game_ids]
    if not seed.empty:
        seed = seed[seed["game_id"].isin(ordered_game_ids)].copy()

    cached_game_ids = set(seed["game_id"].drop_duplicates().tolist()) if not seed.empty else set()
    missing_game_ids = [game_id for game_id in ordered_game_ids if game_id not in cached_game_ids]

    if cached_game_ids:
        print(
            "Starter-role backfill resuming with "
            f"{len(cached_game_ids)} cached games; {len(missing_game_ids)} remaining."
        )

    frames: list[pd.DataFrame] = [seed] if not seed.empty else []
    for index, game_id in enumerate(missing_game_ids):
        frame = normalize_boxscore_player_roles(fetch_starter_role_rows_for_game(game_id))
        frame["game_id"] = int(game_id)
        frame["season"] = season
        frame["season_type"] = season_type
        frame = frame[STARTER_ROLE_BASE_COLUMNS].copy()
        frames.append(frame)
        if checkpoint_path is not None:
            _append_checkpoint_rows(checkpoint_path, frame)
        if REQUEST_PAUSE_SECONDS > 0 and index < len(missing_game_ids) - 1:
            time.sleep(REQUEST_PAUSE_SECONDS)

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
    checkpoint_path = _checkpoint_path(out_path)

    cached_rows = _load_cached_starter_role_rows(out_path, checkpoint_path)

    df = build_starter_role_backfill(
        season=season,
        season_type=season_type,
        existing_rows=cached_rows,
        checkpoint_path=checkpoint_path,
    )
    tmp_path = out_path.with_suffix(".tmp.csv")
    df.to_csv(tmp_path, index=False)
    tmp_path.replace(out_path)
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    print(f"Saved {out_path}")
    print(f"Rows: {len(df)}")
