from __future__ import annotations

import re
import time
from datetime import date
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import LeagueLineupViz

from nbatools.commands.data_utils import LEAGUE_LINEUP_VIZ_REQUIRED_COLUMNS, normalize_season_type
from nbatools.commands.pipeline.validate_raw import validate_league_lineup_viz_df

REQUEST_TIMEOUT = 30
MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 3.0
LINEUP_SOURCE_ENDPOINT = "leaguelineupviz"
LINEUP_SCHEMA_VERSION = "leaguelineupviz.v1"

SOURCE_RENAME_MAP = {
    "GROUP_ID": "lineup_id",
    "GROUP_NAME": "lineup_name",
    "TEAM_ID": "team_id",
    "TEAM_ABBREVIATION": "team_abbr",
    "MIN": "minutes",
    "OFF_RATING": "off_rating",
    "DEF_RATING": "def_rating",
    "NET_RATING": "net_rating",
    "PACE": "pace",
    "TS_PCT": "ts_pct",
}


def _parse_player_ids(lineup_id: object) -> list[str]:
    return re.findall(r"\d+", str(lineup_id or ""))


def _parse_player_names(lineup_name: object) -> list[str]:
    text = str(lineup_name or "").strip()
    if not text:
        return []
    parts = re.split(r"\s+-\s+|\s*,\s*", text)
    return [part.strip() for part in parts if part.strip()]


def _membership_reason(player_ids: list[str], player_names: list[str], unit_size: int) -> str:
    if len(player_ids) != unit_size:
        return "player_id_count_mismatch"
    if player_names and len(player_names) != unit_size:
        return "player_name_count_mismatch"
    return ""


def normalize_league_lineup_viz(
    raw: pd.DataFrame,
    *,
    season: str,
    season_type: str,
    unit_size: int,
    minute_minimum: int,
    source_pull_date: str | None = None,
) -> pd.DataFrame:
    out = raw.rename(columns=SOURCE_RENAME_MAP).copy()
    required = list(SOURCE_RENAME_MAP.values())
    missing = [col for col in required if col not in out.columns]
    if missing:
        raise ValueError(f"leaguelineupviz missing columns after rename: {missing}")

    pull_date = source_pull_date or date.today().isoformat()
    out["season"] = season
    out["season_type"] = season_type
    out["unit_size"] = int(unit_size)
    out["minute_minimum"] = int(minute_minimum)
    out["source_endpoint"] = LINEUP_SOURCE_ENDPOINT
    out["source_pull_date"] = pull_date
    out["source_schema_version"] = LINEUP_SCHEMA_VERSION

    out["lineup_id"] = out["lineup_id"].fillna("").astype(str).str.strip()
    out["lineup_name"] = out["lineup_name"].fillna("").astype(str).str.strip()
    out["player_ids"] = out["lineup_id"].map(lambda value: "|".join(_parse_player_ids(value)))
    out["player_names"] = out["lineup_name"].map(lambda value: "|".join(_parse_player_names(value)))

    reasons = [
        _membership_reason(
            ids.split("|") if ids else [], names.split("|") if names else [], unit_size
        )
        for ids, names in zip(out["player_ids"], out["player_names"], strict=False)
    ]
    out["coverage_validation_reason"] = reasons
    out["coverage_trusted"] = out["coverage_validation_reason"].eq("").astype(int)

    numeric_cols = [
        "team_id",
        "unit_size",
        "minute_minimum",
        "minutes",
        "off_rating",
        "def_rating",
        "net_rating",
        "pace",
        "ts_pct",
    ]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="raise")

    out["team_abbr"] = out["team_abbr"].fillna("").astype(str).str.strip()

    return (
        out[LEAGUE_LINEUP_VIZ_REQUIRED_COLUMNS]
        .sort_values(["unit_size", "minute_minimum", "team_id", "lineup_id"])
        .reset_index(drop=True)
    )


def fetch_league_lineup_viz(
    *,
    season: str,
    season_type: str,
    unit_size: int,
    minute_minimum: int,
) -> pd.DataFrame:
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            endpoint = LeagueLineupViz(
                minutes_min=minute_minimum,
                group_quantity=str(unit_size),
                season=season,
                season_type_all_star=season_type,
                timeout=REQUEST_TIMEOUT,
            )
            df = endpoint.league_lineup_viz.get_data_frame()
            if df.empty:
                raise ValueError(
                    "No lineup rows returned for "
                    f"season={season} season_type={season_type} "
                    f"unit_size={unit_size} minute_minimum={minute_minimum}"
                )
            return df
        except Exception as exc:
            last_err = exc
            sleep_for = RETRY_SLEEP_SECONDS * attempt
            if attempt < MAX_RETRIES:
                print(
                    f"Lineup-viz request failed for unit_size={unit_size}, "
                    f"minute_minimum={minute_minimum} "
                    f"(attempt {attempt}/{MAX_RETRIES}): {exc}. "
                    f"Retrying in {sleep_for:.1f}s..."
                )
                time.sleep(sleep_for)
            else:
                break

    raise RuntimeError(f"Failed to fetch lineup-viz rows: {last_err}")


def build_league_lineup_viz_backfill(
    season: str,
    season_type: str,
    *,
    unit_sizes: list[int] | tuple[int, ...] = (5,),
    minute_minimums: list[int] | tuple[int, ...] = (0,),
) -> pd.DataFrame:
    pull_date = date.today().isoformat()
    frames: list[pd.DataFrame] = []

    for unit_size in unit_sizes:
        for minute_minimum in minute_minimums:
            raw = fetch_league_lineup_viz(
                season=season,
                season_type=season_type,
                unit_size=int(unit_size),
                minute_minimum=int(minute_minimum),
            )
            frames.append(
                normalize_league_lineup_viz(
                    raw,
                    season=season,
                    season_type=season_type,
                    unit_size=int(unit_size),
                    minute_minimum=int(minute_minimum),
                    source_pull_date=pull_date,
                )
            )

    if not frames:
        raise ValueError(f"No lineup rows returned for season={season} season_type={season_type}")

    out = pd.concat(frames, ignore_index=True)
    return validate_league_lineup_viz_df(out).reset_index(drop=True)


def run(
    season: str,
    season_type: str,
    unit_size: int = 5,
    minute_minimum: int = 0,
) -> None:
    out_dir = Path("data/raw/league_lineup_viz")
    out_dir.mkdir(parents=True, exist_ok=True)

    safe = normalize_season_type(season_type)
    out_path = out_dir / f"{season}_{safe}.csv"

    df = build_league_lineup_viz_backfill(
        season=season,
        season_type=season_type,
        unit_sizes=(unit_size,),
        minute_minimums=(minute_minimum,),
    )
    df.to_csv(out_path, index=False)

    print(f"Saved {out_path}")
    print(f"Rows: {len(df)}")
