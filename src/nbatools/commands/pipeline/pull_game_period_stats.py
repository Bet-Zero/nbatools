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
MAX_WINDOW_PASSES = 3
WINDOW_PASS_SLEEP_SECONDS = 20.0
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
PLAYER_PERIOD_KEY_COLUMNS = ("game_id", "period_family", "period_value", "team_id", "player_id")
TEAM_PERIOD_KEY_COLUMNS = ("game_id", "period_family", "period_value", "team_id")
WINDOW_PROGRESS_COLUMNS = ("game_id", "period_family", "period_value", "has_activity")
PLAYER_PERIOD_OUTPUT_COLUMNS = (
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
    "usg_pct",
    "ast_pct",
    "reb_pct",
    "tov_pct",
    "efg_pct",
    "ts_pct",
)
TEAM_PERIOD_OUTPUT_COLUMNS = (
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
    "efg_pct",
    "ts_pct",
)


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


def _checkpoint_path(out_path: Path) -> Path:
    return out_path.with_suffix(".partial.csv")


def _progress_checkpoint_path(player_out_path: Path) -> Path:
    return player_out_path.with_suffix(".windows.partial.csv")


def _load_cached_period_rows(
    *paths: Path,
    required_columns: tuple[str, ...],
    dedupe_subset: tuple[str, ...],
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for path in paths:
        if not path.exists():
            continue

        df = pd.read_csv(path)
        if df.empty:
            continue

        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            raise ValueError(f"period-stats cache missing required columns: {missing}")

        frames.append(df[list(required_columns)].copy())

    if not frames:
        return pd.DataFrame(columns=list(required_columns))

    out = pd.concat(frames, ignore_index=True)
    for col in ("game_id", "team_id", "player_id"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="raise").astype(int)

    out = out.drop_duplicates(subset=list(dedupe_subset), keep="last")
    return out.reset_index(drop=True)


def _load_window_progress(*paths: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for path in paths:
        if not path.exists():
            continue

        df = pd.read_csv(path)
        if df.empty:
            continue

        missing = [col for col in WINDOW_PROGRESS_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"period-window checkpoint missing required columns: {missing}")

        frames.append(df[list(WINDOW_PROGRESS_COLUMNS)].copy())

    if not frames:
        return pd.DataFrame(columns=list(WINDOW_PROGRESS_COLUMNS))

    out = pd.concat(frames, ignore_index=True)
    out["game_id"] = pd.to_numeric(out["game_id"], errors="raise").astype(int)
    out["has_activity"] = out["has_activity"].fillna(False).astype(bool)
    out = out.drop_duplicates(subset=["game_id", "period_family", "period_value"], keep="last")
    return out.reset_index(drop=True)


def _append_checkpoint_rows(path: Path, df: pd.DataFrame) -> None:
    header = not path.exists() or path.stat().st_size == 0
    df.to_csv(path, mode="a", header=header, index=False)


def _append_window_progress(
    path: Path,
    game_id: int,
    period_window: PeriodWindow,
    *,
    has_activity: bool,
) -> None:
    _append_checkpoint_rows(
        path,
        pd.DataFrame(
            [
                {
                    "game_id": int(game_id),
                    "period_family": period_window.period_family,
                    "period_value": period_window.period_value,
                    "has_activity": bool(has_activity),
                }
            ]
        ),
    )


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
    missing_context = out[["game_date", "player_name"]].isna().any(axis=1)
    if missing_context.any():
        unmatched = out.loc[missing_context].copy()
        non_participant = unmatched["comment"].fillna("").astype(str).str.strip().ne(
            ""
        ) & unmatched["minutes"].eq(0.0)
        if not non_participant.all():
            raise ValueError(
                "Player period rows could not be joined back to player_game_stats context"
            )
        out = out.loc[~missing_context].copy()

    out["season"] = season
    out["season_type"] = season_type
    out["period_family"] = period_window.period_family
    out["period_value"] = period_window.period_value
    out["source_start_period"] = period_window.start_period
    out["source_end_period"] = period_window.end_period

    return out[list(PLAYER_PERIOD_OUTPUT_COLUMNS[:-6])].copy()


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

    return out[list(TEAM_PERIOD_OUTPUT_COLUMNS[:-2])].copy()


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

    if "wl" not in team_context.columns:
        raise ValueError("team_game_stats missing required column: ['wl']")

    team_wl = team_context[["game_id", "team_id", "wl"]].drop_duplicates()
    player_context = player_context.merge(
        team_wl,
        on=["game_id", "team_id"],
        how="left",
        suffixes=("", "_team"),
        validate="many_to_one",
    )
    if "wl_team" in player_context.columns:
        if "wl" in player_context.columns:
            player_context["wl"] = player_context["wl"].combine_first(player_context["wl_team"])
        else:
            player_context["wl"] = player_context["wl_team"]
        player_context = player_context.drop(columns=["wl_team"])

    game_ids = [
        int(game_id)
        for game_id in pd.to_numeric(games["game_id"], errors="raise").drop_duplicates()
    ]
    if not game_ids:
        raise ValueError(f"No game_id values found in {games_path}")

    return game_ids, player_context, team_context


def build_period_backfill(
    season: str,
    season_type: str,
    *,
    existing_player_rows: pd.DataFrame | None = None,
    existing_team_rows: pd.DataFrame | None = None,
    fully_cached_game_ids: set[int] | None = None,
    completed_window_keys: set[tuple[int, str, str]] | None = None,
    player_checkpoint_path: Path | None = None,
    team_checkpoint_path: Path | None = None,
    progress_checkpoint_path: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    game_ids, player_context, team_context = _load_context_frames(season, season_type)

    game_id_set = set(game_ids)

    seeded_player_rows = pd.DataFrame(columns=list(PLAYER_PERIOD_OUTPUT_COLUMNS))
    if existing_player_rows is not None and not existing_player_rows.empty:
        missing = [
            col for col in PLAYER_PERIOD_OUTPUT_COLUMNS if col not in existing_player_rows.columns
        ]
        if missing:
            raise ValueError(f"existing player period rows missing required columns: {missing}")
        seeded_player_rows = existing_player_rows[list(PLAYER_PERIOD_OUTPUT_COLUMNS)].copy()
        seeded_player_rows["game_id"] = pd.to_numeric(
            seeded_player_rows["game_id"], errors="raise"
        ).astype(int)
        seeded_player_rows["team_id"] = pd.to_numeric(
            seeded_player_rows["team_id"], errors="raise"
        ).astype(int)
        seeded_player_rows["player_id"] = pd.to_numeric(
            seeded_player_rows["player_id"], errors="raise"
        ).astype(int)
        seeded_player_rows = seeded_player_rows[
            seeded_player_rows["game_id"].isin(game_id_set)
        ].drop_duplicates(subset=list(PLAYER_PERIOD_KEY_COLUMNS), keep="last")

    seeded_team_rows = pd.DataFrame(columns=list(TEAM_PERIOD_OUTPUT_COLUMNS))
    if existing_team_rows is not None and not existing_team_rows.empty:
        missing = [
            col for col in TEAM_PERIOD_OUTPUT_COLUMNS if col not in existing_team_rows.columns
        ]
        if missing:
            raise ValueError(f"existing team period rows missing required columns: {missing}")
        seeded_team_rows = existing_team_rows[list(TEAM_PERIOD_OUTPUT_COLUMNS)].copy()
        seeded_team_rows["game_id"] = pd.to_numeric(
            seeded_team_rows["game_id"], errors="raise"
        ).astype(int)
        seeded_team_rows["team_id"] = pd.to_numeric(
            seeded_team_rows["team_id"], errors="raise"
        ).astype(int)
        seeded_team_rows = seeded_team_rows[
            seeded_team_rows["game_id"].isin(game_id_set)
        ].drop_duplicates(subset=list(TEAM_PERIOD_KEY_COLUMNS), keep="last")

    cached_games = {
        int(game_id) for game_id in (fully_cached_game_ids or set()) if int(game_id) in game_id_set
    }
    cached_windows = {
        (int(game_id), str(period_family), str(period_value))
        for game_id, period_family, period_value in (completed_window_keys or set())
        if int(game_id) in game_id_set and int(game_id) not in cached_games
    }

    remaining_game_ids = [game_id for game_id in game_ids if game_id not in cached_games]
    if cached_games or cached_windows:
        print(
            "Period backfill resuming with "
            f"{len(cached_games)} cached games and {len(cached_windows)} cached windows; "
            f"{len(remaining_game_ids)} games remaining."
        )

    player_frames: list[pd.DataFrame] = [seeded_player_rows] if not seeded_player_rows.empty else []
    team_frames: list[pd.DataFrame] = [seeded_team_rows] if not seeded_team_rows.empty else []

    pending_windows: list[tuple[int, PeriodWindow]] = [
        (game_id, period_window)
        for game_id in remaining_game_ids
        for period_window in PERIOD_WINDOWS
        if (game_id, period_window.period_family, period_window.period_value) not in cached_windows
    ]

    for pass_index in range(1, MAX_WINDOW_PASSES + 1):
        if not pending_windows:
            break

        if pass_index > 1:
            print(
                f"Period backfill retry pass {pass_index}/{MAX_WINDOW_PASSES} for "
                f"{len(pending_windows)} deferred windows."
            )

        pass_game_ids = list(dict.fromkeys(game_id for game_id, _ in pending_windows))
        total_pass_games = len(pass_game_ids)
        seen_game_ids: set[int] = set()
        next_pending_windows: list[tuple[int, PeriodWindow]] = []

        for game_id, period_window in pending_windows:
            if game_id not in seen_game_ids:
                seen_game_ids.add(game_id)
                game_index = len(seen_game_ids)
                if (
                    total_pass_games == 1
                    or game_index == 1
                    or game_index == total_pass_games
                    or game_index % 25 == 0
                ):
                    if pass_index == 1:
                        print(
                            "Period backfill fetching game "
                            f"{game_index}/{total_pass_games} ({game_id})..."
                        )
                    else:
                        print(
                            f"Period backfill retry pass {pass_index}/{MAX_WINDOW_PASSES} "
                            f"game {game_index}/{total_pass_games} ({game_id})..."
                        )

            window_key = (game_id, period_window.period_family, period_window.period_value)
            if window_key in cached_windows:
                continue

            try:
                player_raw, team_raw = fetch_traditional_period_rows_for_game(
                    game_id,
                    start_period=period_window.start_period,
                    end_period=period_window.end_period,
                )
            except Exception as exc:
                next_pending_windows.append((game_id, period_window))
                print(
                    f"Deferring period window for game {game_id} "
                    f"({period_window.period_family} {period_window.period_value}) "
                    f"in pass {pass_index}/{MAX_WINDOW_PASSES}: {exc}"
                )
                continue

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
                if progress_checkpoint_path is not None:
                    _append_window_progress(
                        progress_checkpoint_path,
                        game_id,
                        period_window,
                        has_activity=False,
                    )
                cached_windows.add(window_key)
                continue

            player_period = normalize_boxscore_player_period_rows(
                player_raw,
                season=season,
                season_type=season_type,
                period_window=period_window,
                player_context=player_context,
            )

            try:
                player_advanced_raw = fetch_advanced_period_rows_for_game(
                    game_id,
                    start_period=period_window.start_period,
                    end_period=period_window.end_period,
                )
            except Exception as exc:
                next_pending_windows.append((game_id, period_window))
                print(
                    f"Deferring period window for game {game_id} "
                    f"({period_window.period_family} {period_window.period_value}) "
                    f"in pass {pass_index}/{MAX_WINDOW_PASSES}: {exc}"
                )
                continue

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

            player_period = player_period[list(PLAYER_PERIOD_OUTPUT_COLUMNS)].copy()
            team_period = team_period[list(TEAM_PERIOD_OUTPUT_COLUMNS)].copy()

            player_frames.append(player_period)
            team_frames.append(team_period)
            if player_checkpoint_path is not None:
                _append_checkpoint_rows(player_checkpoint_path, player_period)
            if team_checkpoint_path is not None:
                _append_checkpoint_rows(team_checkpoint_path, team_period)
            if progress_checkpoint_path is not None:
                _append_window_progress(
                    progress_checkpoint_path,
                    game_id,
                    period_window,
                    has_activity=True,
                )
            cached_windows.add(window_key)

        pending_windows = next_pending_windows
        if pending_windows and pass_index < MAX_WINDOW_PASSES:
            sleep_for = WINDOW_PASS_SLEEP_SECONDS * pass_index
            print(f"Retrying {len(pending_windows)} deferred period windows in {sleep_for:.1f}s...")
            time.sleep(sleep_for)

    if pending_windows:
        failed_game_id, failed_window = pending_windows[0]
        raise RuntimeError(
            "Failed to fetch period-window rows after "
            f"{MAX_WINDOW_PASSES} passes; first remaining window: game {failed_game_id} "
            f"({failed_window.period_family} {failed_window.period_value})"
        )

    if not player_frames or not team_frames:
        raise ValueError(f"No period-window rows were built for {season} {season_type}")

    player_out = pd.concat(player_frames, ignore_index=True)
    team_out = pd.concat(team_frames, ignore_index=True)

    player_out = player_out.drop_duplicates(subset=list(PLAYER_PERIOD_KEY_COLUMNS), keep="last")
    team_out = team_out.drop_duplicates(subset=list(TEAM_PERIOD_KEY_COLUMNS), keep="last")

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
    player_checkpoint_path = _checkpoint_path(player_out_path)
    team_checkpoint_path = _checkpoint_path(team_out_path)
    progress_checkpoint_path = _progress_checkpoint_path(player_out_path)

    final_player_rows = _load_cached_period_rows(
        player_out_path,
        required_columns=PLAYER_PERIOD_OUTPUT_COLUMNS,
        dedupe_subset=PLAYER_PERIOD_KEY_COLUMNS,
    )
    final_team_rows = _load_cached_period_rows(
        team_out_path,
        required_columns=TEAM_PERIOD_OUTPUT_COLUMNS,
        dedupe_subset=TEAM_PERIOD_KEY_COLUMNS,
    )
    cached_player_rows = _load_cached_period_rows(
        player_out_path,
        player_checkpoint_path,
        required_columns=PLAYER_PERIOD_OUTPUT_COLUMNS,
        dedupe_subset=PLAYER_PERIOD_KEY_COLUMNS,
    )
    cached_team_rows = _load_cached_period_rows(
        team_out_path,
        team_checkpoint_path,
        required_columns=TEAM_PERIOD_OUTPUT_COLUMNS,
        dedupe_subset=TEAM_PERIOD_KEY_COLUMNS,
    )
    progress_rows = _load_window_progress(progress_checkpoint_path)

    fully_cached_game_ids: set[int] = set()
    if not final_player_rows.empty and not final_team_rows.empty:
        fully_cached_game_ids = set(final_team_rows["game_id"].drop_duplicates().tolist())

    completed_window_keys = {
        (int(row.game_id), str(row.period_family), str(row.period_value))
        for row in progress_rows.itertuples(index=False)
    }
    if team_checkpoint_path.exists() and not cached_team_rows.empty:
        completed_window_keys.update(
            {
                (int(row.game_id), str(row.period_family), str(row.period_value))
                for row in cached_team_rows.itertuples(index=False)
                if int(row.game_id) not in fully_cached_game_ids
            }
        )

    player_df, team_df = build_period_backfill(
        season=season,
        season_type=season_type,
        existing_player_rows=cached_player_rows,
        existing_team_rows=cached_team_rows,
        fully_cached_game_ids=fully_cached_game_ids,
        completed_window_keys=completed_window_keys,
        player_checkpoint_path=player_checkpoint_path,
        team_checkpoint_path=team_checkpoint_path,
        progress_checkpoint_path=progress_checkpoint_path,
    )

    player_tmp_path = player_out_path.with_suffix(".tmp.csv")
    team_tmp_path = team_out_path.with_suffix(".tmp.csv")
    player_df.to_csv(player_tmp_path, index=False)
    team_df.to_csv(team_tmp_path, index=False)
    player_tmp_path.replace(player_out_path)
    team_tmp_path.replace(team_out_path)

    for path in (player_checkpoint_path, team_checkpoint_path, progress_checkpoint_path):
        if path.exists():
            path.unlink()

    print(f"Saved {player_out_path}")
    print(f"Rows: {len(player_df)}")
    print(f"Saved {team_out_path}")
    print(f"Rows: {len(team_df)}")
