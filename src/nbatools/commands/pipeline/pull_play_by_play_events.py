from __future__ import annotations

import re
import time
from datetime import date
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import PlayByPlayV3

from nbatools.commands.data_utils import PLAY_BY_PLAY_EVENT_REQUIRED_COLUMNS, normalize_season_type
from nbatools.commands.pipeline.validate_raw import validate_play_by_play_events_df
from nbatools.commands.source_invariants import (
    ExpectedGameTerminalState,
    apply_play_by_play_trust_decisions,
    expected_game_terminal_states,
    validate_team_game_pair_invariants,
)

REQUEST_TIMEOUT = 30
MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 3.0
PBP_SOURCE = "playbyplayv3"
PBP_SCHEMA_VERSION = "playbyplayv3.v1"

SOURCE_RENAME_MAP = {
    "gameId": "game_id",
    "actionNumber": "action_number",
    "period": "period",
    "clock": "clock",
    "teamId": "team_id",
    "teamTricode": "team_abbr",
    "personId": "player_id",
    "playerName": "player_name",
    "actionType": "action_type",
    "subType": "sub_type",
    "description": "description",
    "scoreHome": "score_home",
    "scoreAway": "score_away",
}


def parse_clock_seconds_remaining(value: object) -> float:
    text = str(value or "").strip()
    match = re.fullmatch(r"PT(?P<minutes>\d+)M(?P<seconds>\d+(?:\.\d+)?)S", text)
    if match:
        return int(match.group("minutes")) * 60 + float(match.group("seconds"))

    match = re.fullmatch(r"(?P<minutes>\d+):(?P<seconds>\d+(?:\.\d+)?)", text)
    if match:
        return int(match.group("minutes")) * 60 + float(match.group("seconds"))

    raise ValueError(f"Unsupported play-by-play clock value: {value!r}")


def _normalize_score(value: object) -> int:
    text = str(value or "").strip()
    if not text:
        raise ValueError("Play-by-play score values must be present")
    return int(float(text))


def normalize_play_by_play_events(
    raw: pd.DataFrame,
    *,
    season: str,
    season_type: str,
    source_pull_date: str | None = None,
) -> pd.DataFrame:
    out = raw.rename(columns=SOURCE_RENAME_MAP).copy()
    required = list(SOURCE_RENAME_MAP.values())
    missing = [col for col in required if col not in out.columns]
    if missing:
        raise ValueError(f"playbyplayv3 missing columns after rename: {missing}")

    pull_date = source_pull_date or date.today().isoformat()
    out["season"] = season
    out["season_type"] = season_type
    out["pbp_source"] = PBP_SOURCE
    # Row normalization alone cannot prove whole-game completeness. The season
    # backfill stamps trust only after reconciling every terminal state with the
    # paired team final scores.
    out["pbp_source_trusted"] = 0
    out["pbp_validation_reason"] = "expected_final_score_not_validated"
    out["pbp_source_pull_date"] = pull_date
    out["pbp_source_schema_version"] = PBP_SCHEMA_VERSION

    out["clock_seconds_remaining"] = out["clock"].map(parse_clock_seconds_remaining)
    out["score_home"] = out["score_home"].map(_normalize_score)
    out["score_away"] = out["score_away"].map(_normalize_score)

    numeric_cols = ["action_number", "period", "team_id", "player_id"]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0).astype(int)

    for col in (
        "game_id",
        "clock",
        "team_abbr",
        "player_name",
        "action_type",
        "sub_type",
        "description",
    ):
        out[col] = out[col].fillna("").astype(str).str.strip()

    validated = validate_play_by_play_events_df(out[PLAY_BY_PLAY_EVENT_REQUIRED_COLUMNS])
    return validated.sort_values(["game_id", "period", "action_number"]).reset_index(drop=True)


def fetch_play_by_play_events_for_game(game_id: str) -> pd.DataFrame:
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            endpoint = PlayByPlayV3(
                game_id=game_id,
                timeout=REQUEST_TIMEOUT,
            )
            df = endpoint.play_by_play.get_data_frame()
            if df.empty:
                raise ValueError(f"No play-by-play rows returned for game_id={game_id}")
            return df
        except Exception as exc:
            last_err = exc
            sleep_for = RETRY_SLEEP_SECONDS * attempt
            if attempt < MAX_RETRIES:
                print(
                    f"Play-by-play request failed for game {game_id} "
                    f"(attempt {attempt}/{MAX_RETRIES}): {exc}. "
                    f"Retrying in {sleep_for:.1f}s..."
                )
                time.sleep(sleep_for)
            else:
                break

    raise RuntimeError(f"Failed to fetch play-by-play rows for game {game_id}: {last_err}")


def game_ids_for_season(season: str, season_type: str) -> list[str]:
    safe = normalize_season_type(season_type)
    path = Path(f"data/raw/games/{season}_{safe}.csv")
    if not path.exists():
        raise FileNotFoundError(
            f"Missing games file for play-by-play backfill: {path}. "
            "Run the games raw pull before play-by-play backfill."
        )
    games = pd.read_csv(path, dtype={"game_id": str})
    if "game_id" not in games.columns:
        raise ValueError(f"games file missing game_id column: {path}")
    return sorted(games["game_id"].dropna().astype(str).unique().tolist())


def expected_terminal_states_for_season(
    season: str, season_type: str
) -> dict[str, ExpectedGameTerminalState]:
    safe = normalize_season_type(season_type)
    games_path = Path(f"data/raw/games/{season}_{safe}.csv")
    team_path = Path(f"data/raw/team_game_stats/{season}_{safe}.csv")
    if not games_path.exists() or not team_path.exists():
        raise FileNotFoundError(
            "Play-by-play trust requires matching games and team_game_stats files: "
            f"{games_path}, {team_path}"
        )
    games = pd.read_csv(games_path, dtype={"game_id": str})
    team = pd.read_csv(team_path, dtype={"game_id": str})
    validate_team_game_pair_invariants(team, games=games)
    return expected_game_terminal_states(team)


def build_play_by_play_events_backfill(season: str, season_type: str) -> pd.DataFrame:
    pull_date = date.today().isoformat()
    frames: list[pd.DataFrame] = []
    game_ids = game_ids_for_season(season, season_type)
    expected_states = expected_terminal_states_for_season(season, season_type)
    normalized_game_ids = {str(int(game_id)) for game_id in game_ids}
    if normalized_game_ids != set(expected_states):
        raise ValueError(
            "Play-by-play expected-game set does not match paired team final-score coverage"
        )

    for game_id in game_ids:
        raw = fetch_play_by_play_events_for_game(game_id)
        frames.append(
            normalize_play_by_play_events(
                raw,
                season=season,
                season_type=season_type,
                source_pull_date=pull_date,
            )
        )

    if not frames:
        raise ValueError(
            f"No play-by-play rows returned for season={season} season_type={season_type}"
        )

    out = pd.concat(frames, ignore_index=True)
    out, decisions = apply_play_by_play_trust_decisions(out, expected_states)
    failures = [
        f"game_id={game_id}: {';'.join(reasons)}"
        for game_id, reasons in decisions.items()
        if reasons
    ]
    if failures:
        raise ValueError("Play-by-play whole-game trust failed: " + "; ".join(failures))
    return validate_play_by_play_events_df(out).reset_index(drop=True)


def run(season: str, season_type: str) -> None:
    out_dir = Path("data/raw/play_by_play_events")
    out_dir.mkdir(parents=True, exist_ok=True)

    safe = normalize_season_type(season_type)
    out_path = out_dir / f"{season}_{safe}.csv"

    df = build_play_by_play_events_backfill(season=season, season_type=season_type)
    df.to_csv(out_path, index=False)

    print(f"Saved {out_path}")
    print(f"Rows: {len(df)}")
