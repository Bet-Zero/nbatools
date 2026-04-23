"""Shared data-loading and DataFrame utilities used across command modules."""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path

import pandas as pd

PLAYER_GAME_STARTER_ROLE_REQUIRED_COLUMNS = [
    "game_id",
    "season",
    "season_type",
    "team_id",
    "player_id",
    "starter_position_raw",
    "starter_flag",
    "role_source",
    "role_source_trusted",
    "starter_count_for_team_game",
    "role_validation_reason",
]

PLAYER_GAME_STARTER_ROLE_OPTIONAL_COLUMNS = [
    "team_abbr",
    "player_name",
]

PLAYER_GAME_PERIOD_REQUIRED_COLUMNS = [
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
    "usg_pct",
    "ast_pct",
    "reb_pct",
    "tov_pct",
]

PLAYER_GAME_PERIOD_OPTIONAL_COLUMNS = [
    "fg_pct",
    "fg3_pct",
    "ft_pct",
    "efg_pct",
    "ts_pct",
    "comment",
]

TEAM_GAME_PERIOD_REQUIRED_COLUMNS = [
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

TEAM_GAME_PERIOD_OPTIONAL_COLUMNS = [
    "fg_pct",
    "fg3_pct",
    "ft_pct",
    "efg_pct",
    "ts_pct",
]

SCHEDULE_CONTEXT_REQUIRED_COLUMNS = [
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
    "rest_days",
    "opponent_rest_days",
    "back_to_back",
    "rest_advantage",
    "score_margin",
    "one_possession",
    "nationally_televised",
    "national_tv_source",
    "national_tv_source_trusted",
    "schedule_context_source",
    "schedule_context_source_trusted",
]

PERIOD_DESCRIPTOR_LOOKUP = {
    ("quarter", "1"): (1, 1),
    ("quarter", "2"): (2, 2),
    ("quarter", "3"): (3, 3),
    ("quarter", "4"): (4, 4),
    ("half", "first"): (1, 2),
    ("half", "second"): (3, 4),
    ("overtime", "ot"): (5, 14),
}


def safe_divide(numer: pd.Series, denom: pd.Series, fill: float | None = 0.0) -> pd.Series:
    """Element-wise division that returns *fill* where *denom* is zero.

    Pass ``fill=None`` to leave divide-by-zero cells as NaN instead of filling.
    """
    numer = pd.Series(numer)
    denom = pd.Series(denom)
    out = numer / denom.replace(0, pd.NA)
    if fill is None:
        return out
    return out.fillna(fill)


def add_advanced_pct_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add shooting pct and efficiency columns computed from box-score totals."""
    out = df.copy()

    if {"fgm", "fga"}.issubset(out.columns) and "fg_pct" not in out.columns:
        out["fg_pct"] = safe_divide(out["fgm"], out["fga"])

    if {"fg3m", "fg3a"}.issubset(out.columns) and "fg3_pct" not in out.columns:
        out["fg3_pct"] = safe_divide(out["fg3m"], out["fg3a"])

    if {"ftm", "fta"}.issubset(out.columns) and "ft_pct" not in out.columns:
        out["ft_pct"] = safe_divide(out["ftm"], out["fta"])

    if {"fgm", "fg3m", "fga"}.issubset(out.columns):
        out["efg_pct"] = safe_divide(out["fgm"] + 0.5 * out["fg3m"], out["fga"])

    if {"pts", "fga", "fta"}.issubset(out.columns):
        out["ts_pct"] = safe_divide(out["pts"], 2 * (out["fga"] + 0.44 * out["fta"]))

    if {"tov", "fga", "fta"}.issubset(out.columns) and "tov_pct" not in out.columns:
        out["tov_pct"] = (
            safe_divide(out["tov"], out["fga"] + 0.44 * out["fta"] + out["tov"]) * 100.0
        )

    return out


def normalize_season_type(season_type: str) -> str:
    """'Regular Season' -> 'regular_season'"""
    return season_type.lower().replace(" ", "_")


def _normalize_period_request(
    quarter: str | None = None,
    half: str | None = None,
) -> tuple[str, str] | None:
    if quarter and half:
        raise ValueError("quarter and half cannot both be set")
    if quarter is not None:
        quarter_value = str(quarter).strip().upper()
        if quarter_value == "OT":
            return ("overtime", "ot")
        if quarter_value in {"1", "2", "3", "4"}:
            return ("quarter", quarter_value)
        raise ValueError(f"Unsupported quarter value: {quarter}")
    if half is not None:
        half_value = str(half).strip().lower()
        if half_value in {"first", "second"}:
            return ("half", half_value)
        raise ValueError(f"Unsupported half value: {half}")
    return None


def filter_period_rows(
    df: pd.DataFrame,
    *,
    quarter: str | None = None,
    half: str | None = None,
) -> pd.DataFrame:
    descriptor = _normalize_period_request(quarter=quarter, half=half)
    if descriptor is None:
        return df.copy()

    period_family, period_value = descriptor
    work = df.copy()
    family = work["period_family"].fillna("").astype(str).str.lower()
    value = work["period_value"].fillna("").astype(str).str.lower()
    return work.loc[family.eq(period_family) & value.eq(period_value)].copy()


def build_period_filter_coverage_note(
    quarter: str | None = None,
    half: str | None = None,
) -> str | None:
    if quarter is not None:
        return (
            "quarter: filter detected but trustworthy period-window coverage is unavailable "
            "for the requested slice; results are unfiltered"
        )
    if half is not None:
        return (
            "half: filter detected but trustworthy period-window coverage is unavailable "
            "for the requested slice; results are unfiltered"
        )
    return None


def _normalize_opponent_values(
    opponent: str | list[str] | tuple[str, ...] | set[str] | None,
) -> set[str]:
    if opponent is None:
        return set()
    if isinstance(opponent, (list, tuple, set, frozenset)):
        values = opponent
    else:
        values = [opponent]
    return {str(value).upper() for value in values if value}


def build_opponent_mask(
    df: pd.DataFrame,
    opponent: str | list[str] | tuple[str, ...] | set[str] | None,
) -> pd.Series:
    values = _normalize_opponent_values(opponent)
    mask = pd.Series(False, index=df.index)
    if not values:
        return mask
    if "opponent_team_abbr" in df.columns:
        mask = mask | df["opponent_team_abbr"].astype(str).str.upper().isin(values)
    if "opponent_team_name" in df.columns:
        mask = mask | df["opponent_team_name"].astype(str).str.upper().isin(values)
    return mask


def describe_opponent_filter(
    opponent: str | list[str] | tuple[str, ...] | set[str] | None,
) -> str:
    values = sorted(_normalize_opponent_values(opponent))
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) <= 3:
        return ", ".join(values)
    preview = ", ".join(values[:3])
    return f"{len(values)} opponents ({preview}, ...)"


@cache
def _load_latest_standings_snapshot_cached(season: str, data_root: str) -> pd.DataFrame:
    path = Path(data_root) / f"data/raw/standings_snapshots/{season}_regular_season.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing standings snapshot file: {path}")
    df = pd.read_csv(path)
    if "snapshot_date" in df.columns:
        df["_snapshot_date"] = pd.to_datetime(df["snapshot_date"], errors="coerce")
        latest = df["_snapshot_date"].max()
        if pd.notna(latest):
            df = df[df["_snapshot_date"] == latest].copy()
        df = df.drop(columns=["_snapshot_date"])
    return df


def load_latest_standings_snapshot(season: str) -> pd.DataFrame:
    return _load_latest_standings_snapshot_cached(season, os.getcwd()).copy()


@cache
def _load_latest_team_advanced_cached(season: str, data_root: str) -> pd.DataFrame:
    path = Path(data_root) / f"data/raw/team_season_advanced/{season}_regular_season.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing team season advanced file: {path}")
    df = pd.read_csv(path)
    if "as_of_date" in df.columns:
        df["_as_of_date"] = pd.to_datetime(df["as_of_date"], errors="coerce")
        latest = df["_as_of_date"].max()
        if pd.notna(latest):
            df = df[df["_as_of_date"] == latest].copy()
        df = df.drop(columns=["_as_of_date"])
    return df


def load_latest_team_advanced(season: str) -> pd.DataFrame:
    return _load_latest_team_advanced_cached(season, os.getcwd()).copy()


def resolve_opponent_quality_teams(
    opponent_quality: dict,
    seasons: list[str],
    season_type: str,
) -> list[str]:
    del season_type  # policy currently resolves via regular-season standings/ratings only

    definition = opponent_quality.get("definition") or {}
    metric = definition.get("metric")
    operator = definition.get("operator")
    value = definition.get("value")

    resolved: set[str] = set()

    for season in seasons:
        if metric in {"conference_rank", "win_pct"}:
            df = load_latest_standings_snapshot(season)
        elif metric in {"def_rating_rank", "off_rating_rank"}:
            df = load_latest_team_advanced(season)
        else:
            raise ValueError(f"Unsupported opponent_quality metric: {metric}")

        if metric == "conference_rank":
            ranks = pd.to_numeric(df.get("conference_rank"), errors="coerce")
            mask = ranks <= float(value)
            teams = df.loc[mask, "team_abbr"]
        elif metric == "win_pct":
            win_pct = pd.to_numeric(df.get("win_pct"), errors="coerce")
            if operator == ">=":
                mask = win_pct >= float(value)
            elif operator == ">":
                mask = win_pct > float(value)
            elif operator == "<":
                mask = win_pct < float(value)
            else:
                raise ValueError(f"Unsupported win_pct operator: {operator}")
            teams = df.loc[mask, "team_abbr"]
        elif metric == "def_rating_rank":
            work = df.copy()
            work["def_rating"] = pd.to_numeric(work.get("def_rating"), errors="coerce")
            teams = work.sort_values(["def_rating", "team_abbr"], ascending=[True, True]).head(
                int(value)
            )["team_abbr"]
        elif metric == "off_rating_rank":
            work = df.copy()
            work["off_rating"] = pd.to_numeric(work.get("off_rating"), errors="coerce")
            teams = work.sort_values(["off_rating", "team_abbr"], ascending=[False, True]).head(
                int(value)
            )["team_abbr"]
        else:
            raise ValueError(f"Unsupported opponent_quality metric: {metric}")

        resolved.update(teams.astype(str).str.upper())

    return sorted(resolved)


@cache
def _load_team_games_cached(
    seasons: tuple[str, ...], season_type: str, data_root: str
) -> pd.DataFrame:
    safe = normalize_season_type(season_type)
    frames: list[pd.DataFrame] = []

    for season in seasons:
        path = Path(data_root) / f"data/raw/team_game_stats/{season}_{safe}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        df = add_advanced_pct_columns(df)
        frames.append(df)

    if not frames:
        joined = ", ".join(seasons)
        raise FileNotFoundError(f"No team_game_stats files found for seasons: {joined}")

    return pd.concat(frames, ignore_index=True)


def load_team_games_for_seasons(seasons: list[str], season_type: str) -> pd.DataFrame:
    """Load and concatenate team_game_stats CSVs for the given seasons."""
    return _load_team_games_cached(tuple(seasons), season_type, os.getcwd()).copy()


@cache
def _load_player_games_cached(
    seasons: tuple[str, ...], season_type: str, data_root: str
) -> pd.DataFrame:
    safe = normalize_season_type(season_type)
    frames: list[pd.DataFrame] = []
    root = Path(data_root)

    for season in seasons:
        path = root / f"data/raw/player_game_stats/{season}_{safe}.csv"
        if not path.exists():
            continue

        df = pd.read_csv(path)

        team_stats_path = root / f"data/raw/team_game_stats/{season}_{safe}.csv"
        if not team_stats_path.exists():
            raise FileNotFoundError(f"Missing team stats file: {team_stats_path}")

        team_stats = pd.read_csv(team_stats_path)[["game_id", "team_id", "wl"]].drop_duplicates()
        df = df.merge(team_stats, on=["game_id", "team_id"], how="left", suffixes=("", "_team"))

        if "wl_team" in df.columns:
            if "wl" in df.columns:
                df["wl"] = df["wl"].combine_first(df["wl_team"])
            else:
                df["wl"] = df["wl_team"]
            df = df.drop(columns=["wl_team"])

        df = add_advanced_pct_columns(df)
        frames.append(df)

    if not frames:
        joined = ", ".join(seasons)
        raise FileNotFoundError(f"No player_game_stats files found for seasons: {joined}")

    out = pd.concat(frames, ignore_index=True)
    out = add_usage_ast_reb_rate_columns(
        out, seasons=seasons, season_type=season_type, data_root=data_root
    )
    return out


def load_player_games_for_seasons(seasons: list[str], season_type: str) -> pd.DataFrame:
    """Load player_game_stats CSVs, merge win/loss from team stats, add pct columns."""
    return _load_player_games_cached(tuple(seasons), season_type, os.getcwd()).copy()


def _empty_player_game_period_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            *PLAYER_GAME_PERIOD_REQUIRED_COLUMNS,
            *PLAYER_GAME_PERIOD_OPTIONAL_COLUMNS,
        ]
    )


@cache
def _load_player_game_period_stats_cached(
    seasons: tuple[str, ...], season_type: str, data_root: str
) -> pd.DataFrame:
    safe = normalize_season_type(season_type)
    frames: list[pd.DataFrame] = []
    root = Path(data_root)
    missing_paths: list[str] = []

    for season in seasons:
        path = root / f"data/raw/player_game_period_stats/{season}_{safe}.csv"
        if not path.exists():
            missing_paths.append(str(path))
            continue

        df = pd.read_csv(path)
        missing = [col for col in PLAYER_GAME_PERIOD_REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"player_game_period_stats missing required columns: {missing}")
        if df.duplicated(subset=["game_id", "player_id", "period_family", "period_value"]).any():
            raise ValueError(
                "Duplicate (game_id, player_id, period_family, period_value) "
                "in player_game_period_stats"
            )

        numeric_cols = [
            "game_id",
            "team_id",
            "opponent_team_id",
            "player_id",
            "source_start_period",
            "source_end_period",
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
            "usg_pct",
            "ast_pct",
            "reb_pct",
            "tov_pct",
        ]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        period_keys = list(
            zip(
                df["period_family"].fillna("").astype(str).str.lower(),
                df["period_value"].fillna("").astype(str).str.lower(),
            )
        )
        if not all(key in PERIOD_DESCRIPTOR_LOOKUP for key in period_keys):
            raise ValueError(
                "player_game_period_stats has unsupported period_family/period_value rows"
            )
        expected_windows = pd.Series(period_keys).map(PERIOD_DESCRIPTOR_LOOKUP)
        expected_start = expected_windows.map(lambda pair: pair[0])
        expected_end = expected_windows.map(lambda pair: pair[1])
        if not df["source_start_period"].eq(expected_start).all():
            raise ValueError("player_game_period_stats source_start_period mismatch")
        if not df["source_end_period"].eq(expected_end).all():
            raise ValueError("player_game_period_stats source_end_period mismatch")

        df = add_advanced_pct_columns(df)
        frames.append(df)

    if missing_paths:
        raise FileNotFoundError(
            "Missing player_game_period_stats files for requested slice: "
            + ", ".join(missing_paths)
        )
    if not frames:
        return _empty_player_game_period_df()
    return pd.concat(frames, ignore_index=True)


def load_player_game_period_stats_for_seasons(seasons: list[str], season_type: str) -> pd.DataFrame:
    return _load_player_game_period_stats_cached(tuple(seasons), season_type, os.getcwd()).copy()


def _empty_team_game_period_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            *TEAM_GAME_PERIOD_REQUIRED_COLUMNS,
            *TEAM_GAME_PERIOD_OPTIONAL_COLUMNS,
        ]
    )


@cache
def _load_team_game_period_stats_cached(
    seasons: tuple[str, ...], season_type: str, data_root: str
) -> pd.DataFrame:
    safe = normalize_season_type(season_type)
    frames: list[pd.DataFrame] = []
    root = Path(data_root)
    missing_paths: list[str] = []

    for season in seasons:
        path = root / f"data/raw/team_game_period_stats/{season}_{safe}.csv"
        if not path.exists():
            missing_paths.append(str(path))
            continue

        df = pd.read_csv(path)
        missing = [col for col in TEAM_GAME_PERIOD_REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"team_game_period_stats missing required columns: {missing}")
        if df.duplicated(subset=["game_id", "team_id", "period_family", "period_value"]).any():
            raise ValueError(
                "Duplicate (game_id, team_id, period_family, period_value) "
                "in team_game_period_stats"
            )

        numeric_cols = [
            "game_id",
            "team_id",
            "opponent_team_id",
            "source_start_period",
            "source_end_period",
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
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        period_keys = list(
            zip(
                df["period_family"].fillna("").astype(str).str.lower(),
                df["period_value"].fillna("").astype(str).str.lower(),
            )
        )
        if not all(key in PERIOD_DESCRIPTOR_LOOKUP for key in period_keys):
            raise ValueError(
                "team_game_period_stats has unsupported period_family/period_value rows"
            )
        expected_windows = pd.Series(period_keys).map(PERIOD_DESCRIPTOR_LOOKUP)
        expected_start = expected_windows.map(lambda pair: pair[0])
        expected_end = expected_windows.map(lambda pair: pair[1])
        if not df["source_start_period"].eq(expected_start).all():
            raise ValueError("team_game_period_stats source_start_period mismatch")
        if not df["source_end_period"].eq(expected_end).all():
            raise ValueError("team_game_period_stats source_end_period mismatch")

        df = add_advanced_pct_columns(df)
        frames.append(df)

    if missing_paths:
        raise FileNotFoundError(
            "Missing team_game_period_stats files for requested slice: " + ", ".join(missing_paths)
        )
    if not frames:
        return _empty_team_game_period_df()
    return pd.concat(frames, ignore_index=True)


def load_team_game_period_stats_for_seasons(seasons: list[str], season_type: str) -> pd.DataFrame:
    return _load_team_game_period_stats_cached(tuple(seasons), season_type, os.getcwd()).copy()


def _empty_schedule_context_features_df() -> pd.DataFrame:
    return pd.DataFrame(columns=SCHEDULE_CONTEXT_REQUIRED_COLUMNS)


@cache
def _load_schedule_context_features_cached(
    seasons: tuple[str, ...], season_type: str, data_root: str
) -> pd.DataFrame:
    safe = normalize_season_type(season_type)
    frames: list[pd.DataFrame] = []
    root = Path(data_root)
    missing_paths: list[str] = []

    for season in seasons:
        path = root / f"data/processed/schedule_context_features/{season}_{safe}.csv"
        if not path.exists():
            missing_paths.append(str(path))
            continue

        df = pd.read_csv(path)
        missing = [col for col in SCHEDULE_CONTEXT_REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"schedule_context_features missing required columns: {missing}")
        if df.duplicated(subset=["game_id", "team_id"]).any():
            raise ValueError("Duplicate (game_id, team_id) in schedule_context_features")

        for col in (
            "game_id",
            "team_id",
            "opponent_team_id",
            "is_home",
            "is_away",
            "rest_days",
            "opponent_rest_days",
            "back_to_back",
            "score_margin",
            "one_possession",
            "nationally_televised",
            "national_tv_source_trusted",
            "schedule_context_source_trusted",
        ):
            df[col] = pd.to_numeric(df[col], errors="coerce")

        for flag_col in (
            "back_to_back",
            "one_possession",
            "nationally_televised",
            "national_tv_source_trusted",
            "schedule_context_source_trusted",
        ):
            values = df[flag_col].dropna()
            if not values.isin([0, 1]).all():
                raise ValueError(f"schedule_context_features {flag_col} must be 0/1")

        rest_states = {"advantage", "disadvantage", "even", "unknown"}
        if not df["rest_advantage"].fillna("unknown").isin(rest_states).all():
            raise ValueError("schedule_context_features rest_advantage has unsupported values")

        frames.append(df)

    if missing_paths:
        raise FileNotFoundError(
            "Missing schedule_context_features files for requested slice: "
            + ", ".join(missing_paths)
        )
    if not frames:
        return _empty_schedule_context_features_df()
    return pd.concat(frames, ignore_index=True)


def load_schedule_context_features_for_seasons(
    seasons: list[str], season_type: str
) -> pd.DataFrame:
    """Load validated team-game schedule-context features for the given seasons."""
    return _load_schedule_context_features_cached(tuple(seasons), season_type, os.getcwd()).copy()


def build_schedule_context_filter_coverage_notes(
    *,
    back_to_back: bool = False,
    rest_days: str | int | None = None,
    one_possession: bool = False,
    nationally_televised: bool = False,
) -> list[str]:
    notes: list[str] = []
    if back_to_back:
        notes.append(
            "back_to_back: filter detected but trustworthy schedule-context coverage is "
            "unavailable for the requested slice; results are unfiltered for this filter"
        )
    if rest_days is not None:
        notes.append(
            "rest: filter detected but trustworthy schedule-context coverage is unavailable "
            "for the requested slice; results are unfiltered for this filter"
        )
    if one_possession:
        notes.append(
            "one_possession: filter detected but trustworthy schedule-context coverage is "
            "unavailable for the requested slice; results are unfiltered for this filter"
        )
    if nationally_televised:
        notes.append(
            "national_tv: filter detected but trustworthy national-TV coverage is unavailable "
            "for the requested slice; results are unfiltered for this filter"
        )
    return notes


def _drop_schedule_context_helper_columns(df: pd.DataFrame) -> pd.DataFrame:
    helper_cols = [
        col
        for col in df.columns
        if col.startswith("_schedule_context_") or col.startswith("_national_tv_")
    ]
    return df.drop(columns=helper_cols) if helper_cols else df


def apply_schedule_context_filters(
    df: pd.DataFrame,
    seasons: list[str],
    season_type: str,
    *,
    back_to_back: bool = False,
    rest_days: str | int | None = None,
    one_possession: bool = False,
    nationally_televised: bool = False,
) -> tuple[pd.DataFrame, list[str]]:
    requested = any(
        [
            back_to_back,
            rest_days is not None,
            one_possession,
            nationally_televised,
        ]
    )
    if not requested or df.empty:
        return df.copy(), []

    join_cols = ["game_id", "team_id"]
    missing = [col for col in join_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns for schedule-context filters: {missing}")

    try:
        features = load_schedule_context_features_for_seasons(seasons, season_type)
    except FileNotFoundError:
        return df.copy(), build_schedule_context_filter_coverage_notes(
            back_to_back=back_to_back,
            rest_days=rest_days,
            one_possession=one_possession,
            nationally_televised=nationally_televised,
        )

    if features.empty:
        return df.copy(), build_schedule_context_filter_coverage_notes(
            back_to_back=back_to_back,
            rest_days=rest_days,
            one_possession=one_possession,
            nationally_televised=nationally_televised,
        )

    feature_cols = [
        "game_id",
        "team_id",
        "rest_days",
        "back_to_back",
        "rest_advantage",
        "one_possession",
        "nationally_televised",
        "national_tv_source_trusted",
        "schedule_context_source_trusted",
    ]
    lookup = features[feature_cols].drop_duplicates(subset=join_cols)
    work = df.merge(
        lookup.rename(
            columns={
                "rest_days": "_schedule_context_rest_days",
                "back_to_back": "_schedule_context_back_to_back",
                "rest_advantage": "_schedule_context_rest_advantage",
                "one_possession": "_schedule_context_one_possession",
                "nationally_televised": "_schedule_context_nationally_televised",
                "national_tv_source_trusted": "_national_tv_source_trusted",
                "schedule_context_source_trusted": "_schedule_context_source_trusted",
            }
        ),
        on=join_cols,
        how="left",
        validate="many_to_one",
    )

    context_trusted = (
        pd.to_numeric(work["_schedule_context_source_trusted"], errors="coerce").fillna(0).eq(1)
    )
    if not context_trusted.all():
        return df.copy(), build_schedule_context_filter_coverage_notes(
            back_to_back=back_to_back,
            rest_days=rest_days,
            one_possession=one_possession,
            nationally_televised=nationally_televised,
        )

    notes: list[str] = []
    filtered = work

    if back_to_back:
        filtered = filtered[
            pd.to_numeric(filtered["_schedule_context_back_to_back"], errors="coerce")
            .fillna(0)
            .eq(1)
        ].copy()

    if rest_days is not None:
        if isinstance(rest_days, str) and rest_days in {"advantage", "disadvantage"}:
            filtered = filtered[
                filtered["_schedule_context_rest_advantage"]
                .fillna("unknown")
                .astype(str)
                .str.lower()
                .eq(rest_days)
            ].copy()
        else:
            requested_rest = int(rest_days)
            filtered = filtered[
                pd.to_numeric(filtered["_schedule_context_rest_days"], errors="coerce").eq(
                    requested_rest
                )
            ].copy()

    if one_possession:
        filtered = filtered[
            pd.to_numeric(filtered["_schedule_context_one_possession"], errors="coerce")
            .fillna(0)
            .eq(1)
        ].copy()

    if nationally_televised:
        national_tv_trusted = (
            pd.to_numeric(work["_national_tv_source_trusted"], errors="coerce").fillna(0).eq(1)
        )
        if national_tv_trusted.all():
            filtered = filtered[
                pd.to_numeric(filtered["_schedule_context_nationally_televised"], errors="coerce")
                .fillna(0)
                .eq(1)
            ].copy()
        else:
            notes.extend(build_schedule_context_filter_coverage_notes(nationally_televised=True))

    return _drop_schedule_context_helper_columns(filtered), notes


def build_role_filter_coverage_note(role: str | None = None) -> str | None:
    if role is None:
        return None
    return (
        f"role: {role} filter detected but trustworthy starter-role coverage is unavailable "
        "for the requested slice; results are unfiltered"
    )


def _empty_player_game_starter_roles_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            *PLAYER_GAME_STARTER_ROLE_REQUIRED_COLUMNS,
            *PLAYER_GAME_STARTER_ROLE_OPTIONAL_COLUMNS,
        ]
    )


@cache
def _load_player_game_starter_roles_cached(
    seasons: tuple[str, ...], season_type: str, data_root: str
) -> pd.DataFrame:
    safe = normalize_season_type(season_type)
    frames: list[pd.DataFrame] = []
    root = Path(data_root)

    for season in seasons:
        path = root / f"data/raw/player_game_starter_roles/{season}_{safe}.csv"
        if not path.exists():
            continue

        df = pd.read_csv(path)
        missing = [
            col for col in PLAYER_GAME_STARTER_ROLE_REQUIRED_COLUMNS if col not in df.columns
        ]
        if missing:
            raise ValueError(f"player_game_starter_roles missing required columns: {missing}")
        if df.duplicated(subset=["game_id", "player_id"]).any():
            raise ValueError("Duplicate (game_id, player_id) in player_game_starter_roles")

        for col in (
            "game_id",
            "team_id",
            "player_id",
            "starter_flag",
            "role_source_trusted",
            "starter_count_for_team_game",
        ):
            df[col] = pd.to_numeric(df[col], errors="coerce")

        frames.append(df)

    if not frames:
        return _empty_player_game_starter_roles_df()

    return pd.concat(frames, ignore_index=True)


def load_player_game_starter_roles_for_seasons(
    seasons: list[str], season_type: str
) -> pd.DataFrame:
    """Load the optional starter-role dataset for the given seasons."""
    return _load_player_game_starter_roles_cached(tuple(seasons), season_type, os.getcwd()).copy()


def apply_player_role_filter(
    df: pd.DataFrame,
    seasons: list[str],
    season_type: str,
    role: str | None,
) -> tuple[pd.DataFrame, str | None]:
    if role is None or df.empty:
        return df.copy(), None

    role_normalized = str(role).strip().lower()
    if role_normalized not in {"starter", "bench"}:
        raise ValueError(f"Unsupported role: {role}")

    required_join_cols = ["game_id", "team_id", "player_id"]
    missing = [col for col in required_join_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns for role filter: {missing}")

    roles = load_player_game_starter_roles_for_seasons(seasons, season_type)
    if roles.empty:
        return df.copy(), build_role_filter_coverage_note(role_normalized)

    join_cols = required_join_cols
    role_cols = join_cols + ["starter_flag", "role_source_trusted"]
    role_lookup = roles[role_cols].drop_duplicates(subset=join_cols)
    work = df.merge(
        role_lookup.rename(
            columns={
                "starter_flag": "_role_starter_flag",
                "role_source_trusted": "_role_source_trusted",
            }
        ),
        on=join_cols,
        how="left",
        validate="one_to_one",
    )

    trusted_mask = pd.to_numeric(work["_role_source_trusted"], errors="coerce").fillna(0).eq(1)
    if not trusted_mask.all():
        return df.copy(), build_role_filter_coverage_note(role_normalized)

    expected_flag = 1 if role_normalized == "starter" else 0
    filtered = work.loc[
        pd.to_numeric(work["_role_starter_flag"], errors="coerce").fillna(-1).eq(expected_flag)
    ].copy()
    filtered = filtered.drop(columns=["_role_starter_flag", "_role_source_trusted"])
    return filtered, None


def get_game_ids_for_player(player_name: str, seasons: list[str], season_type: str) -> set:
    """Return the set of game_ids where a given player appears in box scores."""
    df = load_player_games_for_seasons(seasons, season_type)
    mask = df["player_name"].astype(str).str.upper() == player_name.upper()
    return set(df.loc[mask, "game_id"].unique())


def filter_by_opponent_player(
    df: pd.DataFrame,
    opponent_player: str,
    seasons: list[str],
    season_type: str,
) -> pd.DataFrame:
    """Filter df to games where opponent_player was on the opposing team.

    For player game logs: keep rows where the game_id appears in
    opponent_player's game logs AND opponent_player was on a different team.
    """
    opp_df = load_player_games_for_seasons(seasons, season_type)
    opp_mask = opp_df["player_name"].astype(str).str.upper() == opponent_player.upper()
    opp_rows = opp_df.loc[opp_mask, ["game_id", "team_abbr"]].drop_duplicates()

    if opp_rows.empty:
        return df.iloc[0:0].copy()

    # Build set of (game_id, opponent_team_abbr) pairs so we only include
    # games where the opponent player was actually on the OTHER team
    if "opponent_team_abbr" in df.columns:
        merged = df.merge(
            opp_rows.rename(columns={"team_abbr": "_opp_player_team"}),
            on="game_id",
            how="inner",
        )
        result = merged[
            merged["opponent_team_abbr"].str.upper() == merged["_opp_player_team"].str.upper()
        ].drop(columns=["_opp_player_team"])
        return result.copy()
    else:
        # Fallback: just filter by game_id presence
        game_ids = set(opp_rows["game_id"])
        return df[df["game_id"].isin(game_ids)].copy()


def filter_without_player(
    df: pd.DataFrame,
    without_player: str,
    seasons: list[str],
    season_type: str,
    team: str | None = None,
    strict_team_match: bool = False,
) -> pd.DataFrame:
    """Filter df to games where without_player did NOT play.

    Specifically: exclude game_ids where without_player appeared for the
    same team (or at all, if no team context).
    """
    player_df = load_player_games_for_seasons(seasons, season_type)
    p_mask = player_df["player_name"].astype(str).str.upper() == without_player.upper()
    p_rows = player_df.loc[p_mask, ["game_id", "team_abbr"]].drop_duplicates()

    if p_rows.empty:
        return df.iloc[0:0].copy() if strict_team_match else df.copy()

    if team:
        # Only exclude games where the player was on the same team
        team_games = set(p_rows.loc[p_rows["team_abbr"].str.upper() == team.upper(), "game_id"])
        if strict_team_match and not team_games:
            return df.iloc[0:0].copy()
    else:
        team_games = set(p_rows["game_id"])

    return df[~df["game_id"].isin(team_games)].copy()


def add_usage_ast_reb_rate_columns(
    df: pd.DataFrame, seasons: list[str] | tuple[str, ...], season_type: str, data_root: str = ""
) -> pd.DataFrame:
    """Merge usage/ast/reb rate columns from player_season_advanced files."""
    out = df.copy()
    safe = normalize_season_type(season_type)
    root = Path(data_root) if data_root else Path()
    frames: list[pd.DataFrame] = []

    for season in seasons:
        adv_path = root / f"data/raw/player_season_advanced/{season}_{safe}.csv"
        if not adv_path.exists():
            continue

        adv = pd.read_csv(adv_path)

        rename_map: dict[str, str] = {}
        if "usage_rate" in adv.columns:
            rename_map["usage_rate"] = "usg_pct"
        if "ast_pct" in adv.columns:
            rename_map["ast_pct"] = "ast_pct"
        elif "assist_percentage" in adv.columns:
            rename_map["assist_percentage"] = "ast_pct"
        if "reb_pct" in adv.columns:
            rename_map["reb_pct"] = "reb_pct"
        elif "rebound_percentage" in adv.columns:
            rename_map["rebound_percentage"] = "reb_pct"

        if not rename_map:
            continue

        keep_cols = [
            c for c in ["season", "player_id", "team_id", *rename_map.keys()] if c in adv.columns
        ]
        adv = adv[keep_cols].rename(columns=rename_map).drop_duplicates()

        if {"season", "player_id", "team_id"}.issubset(adv.columns):
            frames.append(adv)

    if not frames:
        return out

    adv_all = pd.concat(frames, ignore_index=True).drop_duplicates()
    out = out.merge(
        adv_all,
        on=["season", "player_id", "team_id"],
        how="left",
    )
    return out
