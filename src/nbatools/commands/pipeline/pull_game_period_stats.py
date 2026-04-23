from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import BoxScoreAdvancedV3, BoxScoreTraditionalV3

from nbatools.commands.data_utils import add_advanced_pct_columns, normalize_season_type

REQUEST_TIMEOUT = 30
MAX_RETRIES = 5
RETRY_SLEEP_SECONDS = 3.0
OT_END_PERIOD = 14


@dataclass(frozen=True)
class PeriodWindow:
    period_family: str
    period_value: str
    start_period: int
    end_period: int


PERIOD_WINDOWS = (
    PeriodWindow("quarter", "1", 1, 1),
    PeriodWindow("quarter", "2", 2, 2),
    PeriodWindow("quarter", "3", 3, 3),
    PeriodWindow("quarter", "4", 4, 4),
    PeriodWindow("half", "first", 1, 2),
    PeriodWindow("half", "second", 3, 4),
    PeriodWindow("overtime", "OT", 5, OT_END_PERIOD),
)

PLAYER_RATE_COLUMNS = ("usg_pct", "ast_pct", "reb_pct", "tov_pct")


def _api_game_id(game_id: int | str) -> str:
    return str(int(game_id)).zfill(10)


def _parse_minutes_value(value) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return 0.0

    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return float(text)

    if ":" in text:
        minutes_text, seconds_text = text.split(":", 1)
        try:
            return float(minutes_text) + (float(seconds_text) / 60.0)
        except ValueError:
            return 0.0

    iso_match = re.fullmatch(r"PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", text)
    if iso_match:
        minutes = float(iso_match.group(1) or 0.0)
        seconds = float(iso_match.group(2) or 0.0)
        return minutes + (seconds / 60.0)

    return 0.0


def _normalize_fraction_series(series: pd.Series) -> pd.Series:
    out = pd.to_numeric(series, errors="coerce")
    if out.dropna().gt(1.0).any():
        out = out / 100.0
    return out


def _fetch_with_retries(endpoint_cls, game_id: int | str, start_period: int, end_period: int):
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return endpoint_cls(
                game_id=_api_game_id(game_id),
                start_period=start_period,
                end_period=end_period,
                start_range=0,
                end_range=0,
                range_type=0,
                timeout=REQUEST_TIMEOUT,
            )
        except Exception as exc:
            last_err = exc
            sleep_for = RETRY_SLEEP_SECONDS * attempt
            if attempt < MAX_RETRIES:
                print(
                    f"Period-window request failed for game {game_id} "
                    f"({endpoint_cls.__name__}, periods {start_period}-{end_period}, "
                    f"attempt {attempt}/{MAX_RETRIES}): {exc}. "
                    f"Retrying in {sleep_for:.1f}s..."
                )
                time.sleep(sleep_for)
            else:
                break

    raise RuntimeError(
        "Failed to fetch period-window rows for game "
        f"{game_id} ({endpoint_cls.__name__}, periods {start_period}-{end_period}): {last_err}"
    )


def fetch_traditional_period_rows_for_game(
    game_id: int | str,
    *,
    start_period: int,
    end_period: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    endpoint = _fetch_with_retries(
        BoxScoreTraditionalV3,
        game_id=game_id,
        start_period=start_period,
        end_period=end_period,
    )
    return (
        endpoint.player_stats.get_data_frame(),
        endpoint.team_stats.get_data_frame(),
    )


def fetch_advanced_period_rows_for_game(
    game_id: int | str,
    *,
    start_period: int,
    end_period: int,
) -> pd.DataFrame:
    endpoint = _fetch_with_retries(
        BoxScoreAdvancedV3,
        game_id=game_id,
        start_period=start_period,
        end_period=end_period,
    )
    return endpoint.player_stats.get_data_frame()


def normalize_boxscore_player_period_rows(
    df: pd.DataFrame,
    *,
    season: str,
    season_type: str,
    period_window: PeriodWindow,
    player_context: pd.DataFrame,
) -> pd.DataFrame:
    rename_map = {
        "gameId": "game_id",
        "teamId": "team_id",
        "personId": "player_id",
        "comment": "comment",
        "minutes": "minutes",
        "points": "pts",
        "fieldGoalsMade": "fgm",
        "fieldGoalsAttempted": "fga",
        "fieldGoalsPercentage": "fg_pct",
        "threePointersMade": "fg3m",
        "threePointersAttempted": "fg3a",
        "threePointersPercentage": "fg3_pct",
        "freeThrowsMade": "ftm",
        "freeThrowsAttempted": "fta",
        "freeThrowsPercentage": "ft_pct",
        "reboundsOffensive": "oreb",
        "reboundsDefensive": "dreb",
        "reboundsTotal": "reb",
        "assists": "ast",
        "steals": "stl",
        "blocks": "blk",
        "turnovers": "tov",
        "foulsPersonal": "pf",
        "plusMinusPoints": "plus_minus",
    }

    out = df.rename(columns=rename_map).copy()
    required = [
        "game_id",
        "team_id",
        "player_id",
        "minutes",
        "pts",
        "fgm",
        "fga",
        "fg3m",
        "fg3a",
        "ftm",
        "fta",
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
    missing = [col for col in required if col not in out.columns]
    if missing:
        raise ValueError(f"Missing required traditional player box score columns: {missing}")

    for col in ("game_id", "team_id", "player_id"):
        out[col] = pd.to_numeric(out[col], errors="raise").astype(int)

    out["minutes"] = out["minutes"].map(_parse_minutes_value)
    if "comment" not in out.columns:
        out["comment"] = ""
    out["comment"] = out["comment"].fillna("").astype(str)

    numeric_cols = [
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
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    context_cols = [
        "game_id",
        "team_id",
        "player_id",
        "game_date",
        "team_abbr",
        "team_name",
        "opponent_team_id",
        "opponent_team_abbr",
        "opponent_team_name",
        "is_home",
        "is_away",
        "wl",
        "player_name",
    ]
    context = player_context[context_cols].drop_duplicates(
        subset=["game_id", "team_id", "player_id"]
    )
    out = out.merge(
        context, on=["game_id", "team_id", "player_id"], how="left", validate="one_to_one"
    )
    if out[["game_date", "player_name"]].isna().any().any():
        raise ValueError("Player period rows could not be joined back to player_game_stats context")

    out["season"] = season
    out["season_type"] = season_type
    out["period_family"] = period_window.period_family
    out["period_value"] = period_window.period_value
    out["source_start_period"] = period_window.start_period
    out["source_end_period"] = period_window.end_period

    keep_cols = [
        "game_id",
        "season",
        "season_type",
        "game_date",
        "period_family",
        "period_value",
        "source_start_period",
        "source_end_period",
        "team_id",
        "team_abbr",
        "team_name",
        "opponent_team_id",
        "opponent_team_abbr",
        "opponent_team_name",
        "is_home",
        "is_away",
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
        "comment",
    ]
    return out[keep_cols].copy()


def normalize_boxscore_player_advanced_rows(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "gameId": "game_id",
        "teamId": "team_id",
        "personId": "player_id",
        "usagePercentage": "usg_pct",
        "assistPercentage": "ast_pct",
        "reboundPercentage": "reb_pct",
        "turnoverRatio": "tov_pct",
    }
    out = df.rename(columns=rename_map).copy()
    required = ["game_id", "team_id", "player_id", *PLAYER_RATE_COLUMNS]
    missing = [col for col in required if col not in out.columns]
    if missing:
        raise ValueError(f"Missing required advanced player box score columns: {missing}")

    for col in ("game_id", "team_id", "player_id"):
        out[col] = pd.to_numeric(out[col], errors="raise").astype(int)

    for col in PLAYER_RATE_COLUMNS:
        out[col] = _normalize_fraction_series(out[col]).fillna(0.0)

    return out[["game_id", "team_id", "player_id", *PLAYER_RATE_COLUMNS]].copy()


def normalize_boxscore_team_period_rows(
    df: pd.DataFrame,
    *,
    season: str,
    season_type: str,
    period_window: PeriodWindow,
    team_context: pd.DataFrame,
) -> pd.DataFrame:
    rename_map = {
        "gameId": "game_id",
        "teamId": "team_id",
        "minutes": "minutes",
        "points": "pts",
        "fieldGoalsMade": "fgm",
        "fieldGoalsAttempted": "fga",
        "fieldGoalsPercentage": "fg_pct",
        "threePointersMade": "fg3m",
        "threePointersAttempted": "fg3a",
        "threePointersPercentage": "fg3_pct",
        "freeThrowsMade": "ftm",
        "freeThrowsAttempted": "fta",
        "freeThrowsPercentage": "ft_pct",
        "reboundsOffensive": "oreb",
        "reboundsDefensive": "dreb",
        "reboundsTotal": "reb",
        "assists": "ast",
        "steals": "stl",
        "blocks": "blk",
        "turnovers": "tov",
        "foulsPersonal": "pf",
        "plusMinusPoints": "plus_minus",
    }

    out = df.rename(columns=rename_map).copy()
    required = [
        "game_id",
        "team_id",
        "minutes",
        "pts",
        "fgm",
        "fga",
        "fg3m",
        "fg3a",
        "ftm",
        "fta",
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
    missing = [col for col in required if col not in out.columns]
    if missing:
        raise ValueError(f"Missing required traditional team box score columns: {missing}")

    for col in ("game_id", "team_id"):
        out[col] = pd.to_numeric(out[col], errors="raise").astype(int)

    out["minutes"] = out["minutes"].map(_parse_minutes_value)
    numeric_cols = [
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
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    context_cols = [
        "game_id",
        "team_id",
        "game_date",
        "team_abbr",
        "team_name",
        "opponent_team_id",
        "opponent_team_abbr",
        "opponent_team_name",
        "is_home",
        "is_away",
    ]
    context = team_context[context_cols].drop_duplicates(subset=["game_id", "team_id"])
    out = out.merge(context, on=["game_id", "team_id"], how="left", validate="one_to_one")
    if out[["game_date", "team_abbr"]].isna().any().any():
        raise ValueError("Team period rows could not be joined back to team_game_stats context")

    out["season"] = season
    out["season_type"] = season_type
    out["period_family"] = period_window.period_family
    out["period_value"] = period_window.period_value
    out["source_start_period"] = period_window.start_period
    out["source_end_period"] = period_window.end_period
    out["wl"] = out["plus_minus"].map(
        lambda value: "W" if value > 0 else ("L" if value < 0 else "T")
    )

    keep_cols = [
        "game_id",
        "season",
        "season_type",
        "game_date",
        "period_family",
        "period_value",
        "source_start_period",
        "source_end_period",
        "team_id",
        "team_abbr",
        "team_name",
        "opponent_team_id",
        "opponent_team_abbr",
        "opponent_team_name",
        "is_home",
        "is_away",
        "wl",
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
    return out[keep_cols].copy()


def _period_window_has_activity(team_df: pd.DataFrame) -> bool:
    if team_df.empty:
        return False
    if pd.to_numeric(team_df.get("minutes"), errors="coerce").fillna(0.0).gt(0).any():
        return True
    activity_cols = ("pts", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "reb", "ast", "plus_minus")
    return any(
        pd.to_numeric(team_df.get(col), errors="coerce").fillna(0.0).abs().sum() > 0
        for col in activity_cols
        if col in team_df.columns
    )


def _load_context_frames(
    season: str,
    season_type: str,
) -> tuple[list[int], pd.DataFrame, pd.DataFrame]:
    safe = normalize_season_type(season_type)

    games_path = Path(f"data/raw/games/{season}_{safe}.csv")
    player_context_path = Path(f"data/raw/player_game_stats/{season}_{safe}.csv")
    team_context_path = Path(f"data/raw/team_game_stats/{season}_{safe}.csv")

    if not games_path.exists():
        raise FileNotFoundError(f"Missing games file: {games_path}")
    if not player_context_path.exists():
        raise FileNotFoundError(f"Missing player_game_stats file: {player_context_path}")
    if not team_context_path.exists():
        raise FileNotFoundError(f"Missing team_game_stats file: {team_context_path}")

    games = pd.read_csv(games_path)
    player_context = pd.read_csv(player_context_path)
    team_context = pd.read_csv(team_context_path)

    if "game_id" not in games.columns:
        raise ValueError("games missing required column: ['game_id']")

    for frame in (player_context, team_context):
        for col in ("game_id", "team_id"):
            frame[col] = pd.to_numeric(frame[col], errors="raise").astype(int)
    player_context["player_id"] = pd.to_numeric(player_context["player_id"], errors="raise").astype(
        int
    )

    game_ids = [
        int(game_id)
        for game_id in pd.to_numeric(games["game_id"], errors="raise").drop_duplicates()
    ]
    if not game_ids:
        raise ValueError(f"No game_id values found in {games_path}")

    return game_ids, player_context, team_context


def build_period_backfill(season: str, season_type: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    game_ids, player_context, team_context = _load_context_frames(season, season_type)

    player_frames: list[pd.DataFrame] = []
    team_frames: list[pd.DataFrame] = []

    for game_id in game_ids:
        for period_window in PERIOD_WINDOWS:
            player_raw, team_raw = fetch_traditional_period_rows_for_game(
                game_id,
                start_period=period_window.start_period,
                end_period=period_window.end_period,
            )

            team_period = normalize_boxscore_team_period_rows(
                team_raw,
                season=season,
                season_type=season_type,
                period_window=period_window,
                team_context=team_context,
            )
            team_period = add_advanced_pct_columns(team_period)

            if period_window.period_family == "overtime" and not _period_window_has_activity(
                team_period
            ):
                continue

            player_period = normalize_boxscore_player_period_rows(
                player_raw,
                season=season,
                season_type=season_type,
                period_window=period_window,
                player_context=player_context,
            )

            player_advanced_raw = fetch_advanced_period_rows_for_game(
                game_id,
                start_period=period_window.start_period,
                end_period=period_window.end_period,
            )
            player_advanced = normalize_boxscore_player_advanced_rows(player_advanced_raw)
            player_period = player_period.merge(
                player_advanced,
                on=["game_id", "team_id", "player_id"],
                how="left",
                validate="one_to_one",
            )
            for col in PLAYER_RATE_COLUMNS:
                player_period[col] = pd.to_numeric(player_period[col], errors="coerce").fillna(0.0)
            player_period = add_advanced_pct_columns(player_period)

            player_frames.append(player_period)
            team_frames.append(team_period)

    if not player_frames or not team_frames:
        raise ValueError(f"No period-window rows were built for {season} {season_type}")

    player_out = pd.concat(player_frames, ignore_index=True)
    team_out = pd.concat(team_frames, ignore_index=True)

    player_out = player_out.sort_values(
        ["game_date", "game_id", "period_family", "period_value", "team_id", "player_id"]
    ).reset_index(drop=True)
    team_out = team_out.sort_values(
        ["game_date", "game_id", "period_family", "period_value", "team_id"]
    ).reset_index(drop=True)
    return player_out, team_out


def run(season: str, season_type: str) -> None:
    player_out_dir = Path("data/raw/player_game_period_stats")
    team_out_dir = Path("data/raw/team_game_period_stats")
    player_out_dir.mkdir(parents=True, exist_ok=True)
    team_out_dir.mkdir(parents=True, exist_ok=True)

    safe = normalize_season_type(season_type)
    player_out_path = player_out_dir / f"{season}_{safe}.csv"
    team_out_path = team_out_dir / f"{season}_{safe}.csv"

    player_df, team_df = build_period_backfill(season=season, season_type=season_type)
    player_df.to_csv(player_out_path, index=False)
    team_df.to_csv(team_out_path, index=False)

    print(f"Saved {player_out_path}")
    print(f"Rows: {len(player_df)}")
    print(f"Saved {team_out_path}")
    print(f"Rows: {len(team_df)}")
