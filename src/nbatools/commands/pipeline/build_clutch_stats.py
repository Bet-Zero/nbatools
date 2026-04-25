from __future__ import annotations

from pathlib import Path

import pandas as pd

from nbatools.commands.data_utils import (
    PLAYER_GAME_CLUTCH_REQUIRED_COLUMNS,
    TEAM_GAME_CLUTCH_REQUIRED_COLUMNS,
    load_play_by_play_events_for_seasons,
    normalize_season_type,
    select_trusted_play_by_play_events,
)
from nbatools.commands.pipeline.validate_raw import (
    validate_player_game_clutch_stats_df,
    validate_team_game_clutch_stats_df,
)

CLUTCH_SOURCE = "play_by_play_events"
CLUTCH_TIME_REMAINING_START = 300
CLUTCH_SCORE_MARGIN_MAX = 5


def add_event_points(events: pd.DataFrame) -> pd.DataFrame:
    out = events.sort_values(["game_id", "action_number"]).copy()
    for score_col in ("score_home", "score_away"):
        out[score_col] = pd.to_numeric(out[score_col], errors="coerce")
        out[f"_{score_col}_previous"] = (
            out.groupby("game_id")[score_col].shift(1).fillna(out[score_col])
        )
        out[f"_{score_col}_delta"] = (out[score_col] - out[f"_{score_col}_previous"]).clip(lower=0)

    out["pts"] = out[["_score_home_delta", "_score_away_delta"]].max(axis=1).fillna(0)
    return out.drop(
        columns=[
            "_score_home_previous",
            "_score_home_delta",
            "_score_away_previous",
            "_score_away_delta",
        ]
    )


def filter_clutch_events(events: pd.DataFrame) -> pd.DataFrame:
    work = add_event_points(events)
    score_margin = (work["score_home"] - work["score_away"]).abs()
    mask = (
        pd.to_numeric(work["period"], errors="coerce").ge(4)
        & pd.to_numeric(work["clock_seconds_remaining"], errors="coerce").le(
            CLUTCH_TIME_REMAINING_START
        )
        & score_margin.le(CLUTCH_SCORE_MARGIN_MAX)
    )
    return work.loc[mask].copy()


def _clutch_seconds(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return 0.0
    return float(numeric.max() - numeric.min())


def derive_player_game_clutch_stats(events: pd.DataFrame) -> pd.DataFrame:
    clutch = filter_clutch_events(events)
    clutch = clutch[
        pd.to_numeric(clutch["player_id"], errors="coerce").fillna(0).astype(int).gt(0)
        & pd.to_numeric(clutch["team_id"], errors="coerce").fillna(0).astype(int).gt(0)
    ].copy()
    if clutch.empty:
        return pd.DataFrame(columns=PLAYER_GAME_CLUTCH_REQUIRED_COLUMNS)

    grouped = clutch.groupby(
        [
            "season",
            "season_type",
            "game_id",
            "team_id",
            "team_abbr",
            "player_id",
            "player_name",
        ],
        as_index=False,
    ).agg(
        clutch_events=("action_number", "count"),
        clutch_seconds=("clock_seconds_remaining", _clutch_seconds),
        pts=("pts", "sum"),
    )
    grouped["clutch_window"] = 1
    grouped["clutch_time_remaining_start"] = CLUTCH_TIME_REMAINING_START
    grouped["clutch_score_margin_max"] = CLUTCH_SCORE_MARGIN_MAX
    grouped["clutch_source"] = CLUTCH_SOURCE
    grouped["clutch_source_trusted"] = 1
    grouped["clutch_validation_reason"] = ""
    out = grouped[PLAYER_GAME_CLUTCH_REQUIRED_COLUMNS].sort_values(
        ["game_id", "team_id", "player_id"]
    )
    return validate_player_game_clutch_stats_df(out).reset_index(drop=True)


def derive_team_game_clutch_stats(events: pd.DataFrame) -> pd.DataFrame:
    clutch = filter_clutch_events(events)
    clutch = clutch[
        pd.to_numeric(clutch["team_id"], errors="coerce").fillna(0).astype(int).gt(0)
    ].copy()
    if clutch.empty:
        return pd.DataFrame(columns=TEAM_GAME_CLUTCH_REQUIRED_COLUMNS)

    grouped = clutch.groupby(
        ["season", "season_type", "game_id", "team_id", "team_abbr"],
        as_index=False,
    ).agg(
        clutch_events=("action_number", "count"),
        clutch_seconds=("clock_seconds_remaining", _clutch_seconds),
        pts=("pts", "sum"),
    )
    grouped["clutch_window"] = 1
    grouped["clutch_time_remaining_start"] = CLUTCH_TIME_REMAINING_START
    grouped["clutch_score_margin_max"] = CLUTCH_SCORE_MARGIN_MAX
    grouped["clutch_source"] = CLUTCH_SOURCE
    grouped["clutch_source_trusted"] = 1
    grouped["clutch_validation_reason"] = ""
    out = grouped[TEAM_GAME_CLUTCH_REQUIRED_COLUMNS].sort_values(["game_id", "team_id"])
    return validate_team_game_clutch_stats_df(out).reset_index(drop=True)


def build_clutch_stats_for_season(
    season: str, season_type: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    events = load_play_by_play_events_for_seasons([season], season_type)
    trusted_events, failures = select_trusted_play_by_play_events(events)
    if trusted_events.empty:
        reason = "; ".join(failures) if failures else "trusted play-by-play coverage is missing"
        raise ValueError(f"Cannot derive clutch stats: {reason}")
    return (
        derive_player_game_clutch_stats(trusted_events),
        derive_team_game_clutch_stats(trusted_events),
    )


def run(season: str, season_type: str) -> None:
    safe = normalize_season_type(season_type)
    player_out_dir = Path("data/processed/player_game_clutch_stats")
    team_out_dir = Path("data/processed/team_game_clutch_stats")
    player_out_dir.mkdir(parents=True, exist_ok=True)
    team_out_dir.mkdir(parents=True, exist_ok=True)

    player_df, team_df = build_clutch_stats_for_season(season, season_type)
    player_path = player_out_dir / f"{season}_{safe}.csv"
    team_path = team_out_dir / f"{season}_{safe}.csv"
    player_df.to_csv(player_path, index=False)
    team_df.to_csv(team_path, index=False)

    print(f"Saved {player_path}")
    print(f"Player rows: {len(player_df)}")
    print(f"Saved {team_path}")
    print(f"Team rows: {len(team_df)}")
