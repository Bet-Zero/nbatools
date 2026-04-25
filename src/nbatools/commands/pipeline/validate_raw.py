from pathlib import Path

import pandas as pd

from nbatools.commands.data_utils import (
    LEAGUE_LINEUP_VIZ_REQUIRED_COLUMNS,
    PLAY_BY_PLAY_EVENT_REQUIRED_COLUMNS,
    PLAYER_GAME_CLUTCH_REQUIRED_COLUMNS,
    SCHEDULE_CONTEXT_REQUIRED_COLUMNS,
    TEAM_GAME_CLUTCH_REQUIRED_COLUMNS,
    TEAM_PLAYER_ON_OFF_REQUIRED_COLUMNS,
)

PERIOD_WINDOW_LOOKUP = {
    ("quarter", "1"): (1, 1),
    ("quarter", "2"): (2, 2),
    ("quarter", "3"): (3, 3),
    ("quarter", "4"): (4, 4),
    ("half", "first"): (1, 2),
    ("half", "second"): (3, 4),
    ("overtime", "ot"): (5, 14),
}

PLAYER_PERIOD_REQUIRED_COLUMNS = [
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

TEAM_PERIOD_REQUIRED_COLUMNS = [
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


def require_columns(df, required, name):
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{name} missing columns: {missing}")


def _validate_period_window_columns(df: pd.DataFrame, name: str) -> pd.DataFrame:
    validated = df.copy()
    for col in (
        "game_id",
        "team_id",
        "source_start_period",
        "source_end_period",
    ):
        validated[col] = pd.to_numeric(validated[col], errors="coerce")

    validated["period_family"] = validated["period_family"].fillna("").astype(str).str.lower()
    validated["period_value"] = validated["period_value"].fillna("").astype(str).str.lower()

    keys = list(zip(validated["period_family"], validated["period_value"]))
    if not all(key in PERIOD_WINDOW_LOOKUP for key in keys):
        raise ValueError(f"{name} has unsupported period_family/period_value rows")

    expected = pd.Series(keys).map(PERIOD_WINDOW_LOOKUP)
    expected_start = expected.map(lambda pair: pair[0])
    expected_end = expected.map(lambda pair: pair[1])
    if not validated["source_start_period"].eq(expected_start).all():
        raise ValueError(f"{name} source_start_period mismatch")
    if not validated["source_end_period"].eq(expected_end).all():
        raise ValueError(f"{name} source_end_period mismatch")

    return validated


def validate_player_game_period_stats_df(df: pd.DataFrame) -> pd.DataFrame:
    require_columns(df, PLAYER_PERIOD_REQUIRED_COLUMNS, "player_game_period_stats")
    validated = _validate_period_window_columns(df, "player_game_period_stats")
    validated["player_id"] = pd.to_numeric(validated["player_id"], errors="coerce")

    if validated.duplicated(subset=["game_id", "player_id", "period_family", "period_value"]).any():
        raise ValueError(
            "Duplicate (game_id, player_id, period_family, period_value) "
            "in player_game_period_stats"
        )

    for pct_col in ("usg_pct", "ast_pct", "reb_pct", "tov_pct"):
        values = pd.to_numeric(validated[pct_col], errors="coerce")
        if ((values < 0) | (values > 1)).any():
            raise ValueError(f"player_game_period_stats {pct_col} out of bounds")

    return validated


def validate_team_game_period_stats_df(df: pd.DataFrame) -> pd.DataFrame:
    require_columns(df, TEAM_PERIOD_REQUIRED_COLUMNS, "team_game_period_stats")
    validated = _validate_period_window_columns(df, "team_game_period_stats")

    if validated.duplicated(subset=["game_id", "team_id", "period_family", "period_value"]).any():
        raise ValueError(
            "Duplicate (game_id, team_id, period_family, period_value) in team_game_period_stats"
        )

    wl_expected = validated["plus_minus"].map(
        lambda value: "W" if value > 0 else ("L" if value < 0 else "T")
    )
    if not validated["wl"].fillna("").eq(wl_expected).all():
        raise ValueError("team_game_period_stats wl mismatch")

    return validated


def validate_schedule_context_features_df(df: pd.DataFrame) -> pd.DataFrame:
    require_columns(df, SCHEDULE_CONTEXT_REQUIRED_COLUMNS, "schedule_context_features")
    validated = df.copy()

    if validated.duplicated(subset=["game_id", "team_id"]).any():
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
        validated[col] = pd.to_numeric(validated[col], errors="coerce")

    for flag_col in (
        "back_to_back",
        "one_possession",
        "nationally_televised",
        "national_tv_source_trusted",
        "schedule_context_source_trusted",
    ):
        values = validated[flag_col].dropna()
        if not values.isin([0, 1]).all():
            raise ValueError(f"schedule_context_features {flag_col} must be 0/1")

    valid_rest_states = {"advantage", "disadvantage", "even", "unknown"}
    if not validated["rest_advantage"].fillna("unknown").isin(valid_rest_states).all():
        raise ValueError("schedule_context_features rest_advantage has unsupported values")

    national_source = validated["national_tv_source"].fillna("").astype(str).str.strip()
    trusted = validated["national_tv_source_trusted"].eq(1)
    if trusted.any() and not trusted.all():
        raise ValueError("schedule_context_features national_tv_source_trusted must be file-wide")
    if trusted.all() and national_source.eq("").all():
        raise ValueError(
            "schedule_context_features cannot mark national-TV source trusted with no source tags"
        )

    return validated


def validate_team_player_on_off_summary_df(df: pd.DataFrame) -> pd.DataFrame:
    require_columns(df, TEAM_PLAYER_ON_OFF_REQUIRED_COLUMNS, "team_player_on_off_summary")
    validated = df.copy()

    if validated.duplicated(
        subset=["season", "season_type", "team_id", "player_id", "presence_state"]
    ).any():
        raise ValueError(
            "Duplicate (season, season_type, team_id, player_id, presence_state) "
            "in team_player_on_off_summary"
        )

    validated["presence_state"] = validated["presence_state"].fillna("").astype(str).str.lower()
    if not validated["presence_state"].isin(["on", "off"]).all():
        raise ValueError("team_player_on_off_summary presence_state must be on/off")

    numeric_cols = [
        "team_id",
        "player_id",
        "gp",
        "minutes",
        "plus_minus",
        "off_rating",
        "def_rating",
        "net_rating",
        "coverage_trusted",
    ]
    for col in numeric_cols:
        validated[col] = pd.to_numeric(validated[col], errors="coerce")

    for col in ("team_id", "player_id", "gp", "minutes"):
        if validated[col].isna().any():
            raise ValueError(f"team_player_on_off_summary {col} has invalid numeric values")

    if not validated["coverage_trusted"].dropna().isin([0, 1]).all():
        raise ValueError("team_player_on_off_summary coverage_trusted must be 0/1")

    state_counts = (
        validated.groupby(["season", "season_type", "team_id", "player_id"])["presence_state"]
        .nunique()
        .rename("_presence_state_count")
    )
    checked = validated.merge(
        state_counts,
        on=["season", "season_type", "team_id", "player_id"],
        how="left",
        validate="many_to_one",
    )
    trusted_expected = checked["_presence_state_count"].eq(2).astype(int)
    if not checked["coverage_trusted"].eq(trusted_expected).all():
        raise ValueError("team_player_on_off_summary coverage_trusted mismatch")

    trusted = checked["coverage_trusted"].eq(1)
    if not checked.loc[trusted, "coverage_validation_reason"].fillna("").eq("").all():
        raise ValueError("Trusted on/off rows must have blank coverage_validation_reason")
    if not checked.loc[~trusted, "coverage_validation_reason"].fillna("").ne("").all():
        raise ValueError("Untrusted on/off rows must explain coverage_validation_reason")

    return validated


def _split_members(value: object) -> list[str]:
    return [part for part in str(value or "").split("|") if part]


def validate_league_lineup_viz_df(df: pd.DataFrame) -> pd.DataFrame:
    require_columns(df, LEAGUE_LINEUP_VIZ_REQUIRED_COLUMNS, "league_lineup_viz")
    validated = df.copy()

    if validated.duplicated(
        subset=["season", "season_type", "team_id", "unit_size", "lineup_id", "minute_minimum"]
    ).any():
        raise ValueError(
            "Duplicate (season, season_type, team_id, unit_size, lineup_id, "
            "minute_minimum) in league_lineup_viz"
        )

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
        "coverage_trusted",
    ]
    for col in numeric_cols:
        validated[col] = pd.to_numeric(validated[col], errors="coerce")

    for col in ("team_id", "unit_size", "minute_minimum", "minutes"):
        if validated[col].isna().any():
            raise ValueError(f"league_lineup_viz {col} has invalid numeric values")

    if not validated["coverage_trusted"].dropna().isin([0, 1]).all():
        raise ValueError("league_lineup_viz coverage_trusted must be 0/1")

    id_counts = validated["player_ids"].map(lambda value: len(_split_members(value)))
    name_counts = validated["player_names"].map(lambda value: len(_split_members(value)))
    expected_trusted = (
        id_counts.eq(validated["unit_size"])
        & (name_counts.eq(0) | name_counts.eq(validated["unit_size"]))
    ).astype(int)
    if not validated["coverage_trusted"].eq(expected_trusted).all():
        raise ValueError("league_lineup_viz coverage_trusted mismatch")

    trusted = validated["coverage_trusted"].eq(1)
    if not validated.loc[trusted, "coverage_validation_reason"].fillna("").eq("").all():
        raise ValueError("Trusted lineup rows must have blank coverage_validation_reason")
    if not validated.loc[~trusted, "coverage_validation_reason"].fillna("").ne("").all():
        raise ValueError("Untrusted lineup rows must explain coverage_validation_reason")

    return validated


def validate_play_by_play_events_df(df: pd.DataFrame) -> pd.DataFrame:
    require_columns(df, PLAY_BY_PLAY_EVENT_REQUIRED_COLUMNS, "play_by_play_events")
    validated = df.copy()

    event_key = ["season", "season_type", "game_id", "action_number"]
    if validated.duplicated(subset=event_key).any():
        raise ValueError(
            "Duplicate (season, season_type, game_id, action_number) in play_by_play_events"
        )

    numeric_cols = [
        "action_number",
        "period",
        "clock_seconds_remaining",
        "score_home",
        "score_away",
        "pbp_source_trusted",
    ]
    for col in numeric_cols:
        validated[col] = pd.to_numeric(validated[col], errors="coerce")

    for col in (
        "action_number",
        "period",
        "clock_seconds_remaining",
        "score_home",
        "score_away",
    ):
        if validated[col].isna().any():
            raise ValueError(f"play_by_play_events {col} has invalid numeric values")

    if (validated["period"] < 1).any():
        raise ValueError("play_by_play_events period must be positive")
    if (validated["clock_seconds_remaining"] < 0).any():
        raise ValueError("play_by_play_events clock_seconds_remaining must be non-negative")
    if not validated["pbp_source_trusted"].dropna().isin([0, 1]).all():
        raise ValueError("play_by_play_events pbp_source_trusted must be 0/1")

    trusted = validated["pbp_source_trusted"].eq(1)
    if not validated.loc[trusted, "pbp_validation_reason"].fillna("").eq("").all():
        raise ValueError("Trusted play-by-play rows must have blank pbp_validation_reason")
    if not validated.loc[~trusted, "pbp_validation_reason"].fillna("").ne("").all():
        raise ValueError("Untrusted play-by-play rows must explain pbp_validation_reason")

    for game_id, group in validated.groupby("game_id", sort=False):
        actions = group["action_number"]
        if not actions.is_monotonic_increasing:
            raise ValueError(
                f"play_by_play_events action_number order invalid for game_id={game_id}"
            )

    return validated


def _validate_clutch_stats_df(
    df: pd.DataFrame,
    *,
    dataset: str,
    required_columns: list[str],
    key_columns: list[str],
) -> pd.DataFrame:
    require_columns(df, required_columns, dataset)
    validated = df.copy()

    if validated.duplicated(subset=key_columns).any():
        raise ValueError(f"Duplicate {tuple(key_columns)} in {dataset}")

    numeric_cols = [
        "team_id",
        "clutch_window",
        "clutch_time_remaining_start",
        "clutch_score_margin_max",
        "clutch_events",
        "clutch_seconds",
        "pts",
        "clutch_source_trusted",
    ]
    if "player_id" in validated.columns:
        numeric_cols.append("player_id")
    for col in numeric_cols:
        validated[col] = pd.to_numeric(validated[col], errors="coerce")
        if validated[col].isna().any():
            raise ValueError(f"{dataset} {col} has invalid numeric values")

    if not validated["clutch_window"].isin([1]).all():
        raise ValueError(f"{dataset} clutch_window must be 1")
    if not validated["clutch_source_trusted"].dropna().isin([0, 1]).all():
        raise ValueError(f"{dataset} clutch_source_trusted must be 0/1")
    if (validated["clutch_events"] < 1).any():
        raise ValueError(f"{dataset} clutch_events must be positive")
    if (validated["clutch_seconds"] < 0).any():
        raise ValueError(f"{dataset} clutch_seconds must be non-negative")

    trusted = validated["clutch_source_trusted"].eq(1)
    if not validated.loc[trusted, "clutch_validation_reason"].fillna("").eq("").all():
        raise ValueError(f"Trusted {dataset} rows must have blank clutch_validation_reason")
    if not validated.loc[~trusted, "clutch_validation_reason"].fillna("").ne("").all():
        raise ValueError(f"Untrusted {dataset} rows must explain clutch_validation_reason")

    return validated


def validate_player_game_clutch_stats_df(df: pd.DataFrame) -> pd.DataFrame:
    return _validate_clutch_stats_df(
        df,
        dataset="player_game_clutch_stats",
        required_columns=PLAYER_GAME_CLUTCH_REQUIRED_COLUMNS,
        key_columns=["season", "season_type", "game_id", "team_id", "player_id"],
    )


def validate_team_game_clutch_stats_df(df: pd.DataFrame) -> pd.DataFrame:
    return _validate_clutch_stats_df(
        df,
        dataset="team_game_clutch_stats",
        required_columns=TEAM_GAME_CLUTCH_REQUIRED_COLUMNS,
        key_columns=["season", "season_type", "game_id", "team_id"],
    )


def run(season: str, season_type: str):
    safe = season_type.lower().replace(" ", "_")

    paths = {
        "games": Path(f"data/raw/games/{season}_{safe}.csv"),
        "schedule": Path(f"data/raw/schedule/{season}_{safe}.csv"),
        "team": Path(f"data/raw/team_game_stats/{season}_{safe}.csv"),
        "player": Path(f"data/raw/player_game_stats/{season}_{safe}.csv"),
        "player_roles": Path(f"data/raw/player_game_starter_roles/{season}_{safe}.csv"),
        "player_period": Path(f"data/raw/player_game_period_stats/{season}_{safe}.csv"),
        "team_period": Path(f"data/raw/team_game_period_stats/{season}_{safe}.csv"),
        "schedule_context": Path(f"data/processed/schedule_context_features/{season}_{safe}.csv"),
        "rosters": Path(f"data/raw/rosters/{season}.csv"),
        "standings": Path(f"data/raw/standings_snapshots/{season}_{safe}.csv"),
        "team_adv": Path(f"data/raw/team_season_advanced/{season}_{safe}.csv"),
        "player_adv": Path(f"data/raw/player_season_advanced/{season}_{safe}.csv"),
    }

    for name, p in paths.items():
        if name == "schedule_context" and not p.exists():
            continue
        if name == "standings" and season_type == "Playoffs":
            continue
        if not p.exists():
            raise FileNotFoundError(f"Missing file: {p}")

    games = pd.read_csv(paths["games"])
    schedule = pd.read_csv(paths["schedule"])
    team = pd.read_csv(paths["team"])
    player = pd.read_csv(paths["player"])
    player_roles = pd.read_csv(paths["player_roles"])
    player_period = pd.read_csv(paths["player_period"])
    team_period = pd.read_csv(paths["team_period"])
    schedule_context = (
        pd.read_csv(paths["schedule_context"]) if paths["schedule_context"].exists() else None
    )
    rosters = pd.read_csv(paths["rosters"])
    standings = None
    if paths["standings"].exists():
        standings = pd.read_csv(paths["standings"])
    team_adv = pd.read_csv(paths["team_adv"])
    player_adv = pd.read_csv(paths["player_adv"])

    # --- GAMES ---
    require_columns(games, ["game_id", "game_date", "home_team_id"], "games")
    if games["game_id"].duplicated().any():
        raise ValueError("Duplicate game_id in games")

    # --- SCHEDULE ---
    require_columns(schedule, ["game_id", "game_date"], "schedule")
    if schedule["game_id"].duplicated().any():
        raise ValueError("Duplicate game_id in schedule")

    if set(schedule["game_id"]) != set(games["game_id"]):
        raise ValueError("Mismatch between schedule and games game_id sets")

    # --- TEAM GAME ---
    require_columns(team, ["game_id", "team_id", "pts", "fgm", "fga"], "team_game_stats")
    if team.duplicated(subset=["game_id", "team_id"]).any():
        raise ValueError("Duplicate (game_id, team_id) in team_game_stats")

    counts = team.groupby("game_id").size()
    if not (counts == 2).all():
        raise ValueError("Each game must have exactly 2 team rows")

    if (team["fgm"] > team["fga"]).any():
        raise ValueError("team_game_stats invalid fgm > fga")
    if (team["fg3m"] > team["fg3a"]).any():
        raise ValueError("team_game_stats invalid fg3m > fg3a")
    if (team["ftm"] > team["fta"]).any():
        raise ValueError("team_game_stats invalid ftm > fta")

    # --- PLAYER GAME ---
    require_columns(player, ["game_id", "player_id", "fgm", "fga"], "player_game_stats")
    if player.duplicated(subset=["game_id", "player_id"]).any():
        raise ValueError("Duplicate (game_id, player_id) in player_game_stats")

    if (player["fgm"] > player["fga"]).any():
        raise ValueError("player_game_stats invalid fgm > fga")
    if (player["fg3m"] > player["fg3a"]).any():
        raise ValueError("player_game_stats invalid fg3m > fg3a")
    if (player["ftm"] > player["fta"]).any():
        raise ValueError("player_game_stats invalid ftm > fta")

    # --- PLAYER GAME STARTER ROLES ---
    require_columns(
        player_roles,
        [
            "game_id",
            "team_id",
            "player_id",
            "starter_position_raw",
            "starter_flag",
            "role_source",
            "role_source_trusted",
            "starter_count_for_team_game",
            "role_validation_reason",
        ],
        "player_game_starter_roles",
    )
    if player_roles.duplicated(subset=["game_id", "player_id"]).any():
        raise ValueError("Duplicate (game_id, player_id) in player_game_starter_roles")

    starter_counts = (
        player_roles.groupby(["game_id", "team_id"], as_index=False)["starter_flag"]
        .sum()
        .rename(columns={"starter_flag": "_starter_count"})
    )
    validated = player_roles.merge(
        starter_counts,
        on=["game_id", "team_id"],
        how="left",
        validate="many_to_one",
    )
    if not validated["starter_count_for_team_game"].eq(validated["_starter_count"]).all():
        raise ValueError("player_game_starter_roles starter_count_for_team_game mismatch")

    trusted_expected = validated["_starter_count"].eq(5).astype(int)
    if not validated["role_source_trusted"].eq(trusted_expected).all():
        raise ValueError("player_game_starter_roles role_source_trusted mismatch")

    trusted = validated["role_source_trusted"].eq(1)
    if not validated.loc[trusted, "role_validation_reason"].fillna("").eq("").all():
        raise ValueError("Trusted starter-role rows must have blank role_validation_reason")
    if not validated.loc[~trusted, "role_validation_reason"].fillna("").ne("").all():
        raise ValueError("Untrusted starter-role rows must explain role_validation_reason")

    # --- PLAYER / TEAM GAME PERIOD STATS ---
    player_period = validate_player_game_period_stats_df(player_period)
    team_period = validate_team_game_period_stats_df(team_period)

    if not set(player_period["game_id"]).issubset(set(player["game_id"])):
        raise ValueError("player_game_period_stats contains unknown game_id values")
    if not set(team_period["game_id"]).issubset(set(team["game_id"])):
        raise ValueError("team_game_period_stats contains unknown game_id values")

    if schedule_context is not None:
        schedule_context = validate_schedule_context_features_df(schedule_context)
        if not set(schedule_context["game_id"]).issubset(set(team["game_id"])):
            raise ValueError("schedule_context_features contains unknown game_id values")

    # --- ROSTERS ---
    require_columns(rosters, ["player_id", "team_id", "season", "stint"], "rosters")
    if rosters.duplicated(subset=["player_id", "team_id", "season", "stint"]).any():
        raise ValueError("Duplicate roster entries")

    # --- STANDINGS (regular season only) ---
    if season_type != "Playoffs":
        require_columns(standings, ["team_id", "wins", "losses", "win_pct"], "standings")

        if standings.duplicated(subset=["team_id", "snapshot_date"]).any():
            raise ValueError("Duplicate standings snapshot")

        if ((standings["win_pct"] < 0) | (standings["win_pct"] > 1)).any():
            raise ValueError("Invalid win_pct values")

    # --- TEAM ADVANCED ---
    require_columns(
        team_adv,
        ["team_id", "off_rating", "def_rating", "net_rating"],
        "team_season_advanced",
    )
    if team_adv.duplicated(subset=["team_id", "as_of_date"]).any():
        raise ValueError("Duplicate team advanced rows")

    if not (
        (team_adv["off_rating"] - team_adv["def_rating"] - team_adv["net_rating"]).abs() < 0.5
    ).all():
        raise ValueError("Net rating mismatch")

    # --- PLAYER ADVANCED ---
    require_columns(
        player_adv,
        ["player_id", "usage_rate", "ts_pct"],
        "player_season_advanced",
    )
    if player_adv.duplicated(subset=["player_id", "as_of_date"]).any():
        raise ValueError("Duplicate player advanced rows")

    if ((player_adv["usage_rate"] < 0) | (player_adv["usage_rate"] > 1)).any():
        raise ValueError("usage_rate out of bounds")

    if ((player_adv["ts_pct"] < 0) | (player_adv["ts_pct"] > 2)).any():
        raise ValueError("ts_pct out of bounds")

    print("FULL VALIDATION PASSED")
