from __future__ import annotations

import time
from datetime import date
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import TeamPlayerOnOffSummary
from nba_api.stats.static import teams

from nbatools.commands.data_utils import TEAM_PLAYER_ON_OFF_REQUIRED_COLUMNS, normalize_season_type
from nbatools.commands.pipeline.validate_raw import validate_team_player_on_off_summary_df

REQUEST_TIMEOUT = 30
MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 3.0
ON_OFF_SOURCE_ENDPOINT = "teamplayeronoffsummary"
ON_OFF_SCHEMA_VERSION = "teamplayeronoffsummary.v1"

SOURCE_RENAME_MAP = {
    "TEAM_ID": "team_id",
    "TEAM_ABBREVIATION": "team_abbr",
    "TEAM_NAME": "team_name",
    "VS_PLAYER_ID": "player_id",
    "VS_PLAYER_NAME": "player_name",
    "COURT_STATUS": "court_status_raw",
    "GP": "gp",
    "MIN": "minutes",
    "PLUS_MINUS": "plus_minus",
    "OFF_RATING": "off_rating",
    "DEF_RATING": "def_rating",
    "NET_RATING": "net_rating",
}


def team_ids() -> list[int]:
    return sorted(int(team["id"]) for team in teams.get_teams())


def _normalize_presence_state(value: object) -> str:
    text = str(value or "").strip().lower()
    if text == "on":
        return "on"
    if text == "off":
        return "off"
    raise ValueError(f"Unsupported COURT_STATUS value: {value!r}")


def _normalize_source_rows(
    df: pd.DataFrame,
    *,
    season: str,
    season_type: str,
    presence_state: str,
    source_pull_date: str,
) -> pd.DataFrame:
    out = df.rename(columns=SOURCE_RENAME_MAP).copy()
    required = list(SOURCE_RENAME_MAP.values())
    missing = [col for col in required if col not in out.columns]
    if missing:
        raise ValueError(f"teamplayeronoffsummary missing columns after rename: {missing}")

    out["season"] = season
    out["season_type"] = season_type
    out["presence_state"] = presence_state
    out["source_endpoint"] = ON_OFF_SOURCE_ENDPOINT
    out["source_pull_date"] = source_pull_date
    out["source_schema_version"] = ON_OFF_SCHEMA_VERSION

    if "court_status_raw" not in out.columns:
        out["court_status_raw"] = presence_state
    out["court_status_raw"] = out["court_status_raw"].fillna(presence_state).astype(str).str.strip()
    out["presence_state"] = out["court_status_raw"].map(_normalize_presence_state)

    numeric_cols = [
        "team_id",
        "player_id",
        "gp",
        "minutes",
        "plus_minus",
        "off_rating",
        "def_rating",
        "net_rating",
    ]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="raise")

    for col in ("team_abbr", "team_name", "player_name"):
        out[col] = out[col].fillna("").astype(str).str.strip()

    return out[
        [
            "season",
            "season_type",
            "team_id",
            "team_abbr",
            "team_name",
            "player_id",
            "player_name",
            "presence_state",
            "court_status_raw",
            "gp",
            "minutes",
            "plus_minus",
            "off_rating",
            "def_rating",
            "net_rating",
            "source_endpoint",
            "source_pull_date",
            "source_schema_version",
        ]
    ].copy()


def add_coverage_validation(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.duplicated(
        subset=["season", "season_type", "team_id", "player_id", "presence_state"]
    ).any():
        raise ValueError(
            "Duplicate (season, season_type, team_id, player_id, presence_state) "
            "in team_player_on_off_summary"
        )

    state_counts = (
        out.groupby(["season", "season_type", "team_id", "player_id"])["presence_state"]
        .nunique()
        .rename("_presence_state_count")
    )
    out = out.merge(
        state_counts,
        on=["season", "season_type", "team_id", "player_id"],
        how="left",
        validate="many_to_one",
    )
    out["coverage_trusted"] = out["_presence_state_count"].eq(2).astype(int)
    out["coverage_validation_reason"] = out["coverage_trusted"].map(
        {1: "", 0: "missing_presence_state"}
    )
    out = out.drop(columns=["_presence_state_count"])
    return out[TEAM_PLAYER_ON_OFF_REQUIRED_COLUMNS].copy()


def normalize_team_player_on_off_summary(
    on_court: pd.DataFrame,
    off_court: pd.DataFrame,
    *,
    season: str,
    season_type: str,
    source_pull_date: str | None = None,
) -> pd.DataFrame:
    pull_date = source_pull_date or date.today().isoformat()
    frames = [
        _normalize_source_rows(
            on_court,
            season=season,
            season_type=season_type,
            presence_state="on",
            source_pull_date=pull_date,
        ),
        _normalize_source_rows(
            off_court,
            season=season,
            season_type=season_type,
            presence_state="off",
            source_pull_date=pull_date,
        ),
    ]
    out = pd.concat(frames, ignore_index=True)
    out = add_coverage_validation(out)
    return out.sort_values(["team_id", "player_id", "presence_state"]).reset_index(drop=True)


def fetch_team_player_on_off_summary_for_team(
    team_id: int,
    *,
    season: str,
    season_type: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            endpoint = TeamPlayerOnOffSummary(
                team_id=team_id,
                season=season,
                season_type_all_star=season_type,
                timeout=REQUEST_TIMEOUT,
            )
            return (
                endpoint.players_on_court_team_player_on_off_summary.get_data_frame(),
                endpoint.players_off_court_team_player_on_off_summary.get_data_frame(),
            )
        except Exception as exc:
            last_err = exc
            sleep_for = RETRY_SLEEP_SECONDS * attempt
            if attempt < MAX_RETRIES:
                print(
                    f"On/off summary request failed for team {team_id} "
                    f"(attempt {attempt}/{MAX_RETRIES}): {exc}. "
                    f"Retrying in {sleep_for:.1f}s..."
                )
                time.sleep(sleep_for)
            else:
                break

    raise RuntimeError(f"Failed to fetch on/off summary rows for team {team_id}: {last_err}")


def build_team_player_on_off_summary_backfill(season: str, season_type: str) -> pd.DataFrame:
    pull_date = date.today().isoformat()
    frames: list[pd.DataFrame] = []
    for team_id in team_ids():
        on_court, off_court = fetch_team_player_on_off_summary_for_team(
            team_id,
            season=season,
            season_type=season_type,
        )
        if on_court.empty and off_court.empty:
            continue
        frames.append(
            normalize_team_player_on_off_summary(
                on_court,
                off_court,
                season=season,
                season_type=season_type,
                source_pull_date=pull_date,
            )
        )

    if not frames:
        raise ValueError(f"No on/off rows returned for season={season} season_type={season_type}")

    out = pd.concat(frames, ignore_index=True)
    return validate_team_player_on_off_summary_df(out).reset_index(drop=True)


def run(season: str, season_type: str) -> None:
    out_dir = Path("data/raw/team_player_on_off_summary")
    out_dir.mkdir(parents=True, exist_ok=True)

    safe = normalize_season_type(season_type)
    out_path = out_dir / f"{season}_{safe}.csv"

    df = build_team_player_on_off_summary_backfill(season=season, season_type=season_type)
    df.to_csv(out_path, index=False)

    print(f"Saved {out_path}")
    print(f"Rows: {len(df)}")
