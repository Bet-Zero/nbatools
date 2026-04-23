from pathlib import Path

import pandas as pd


def require_columns(df, required, name):
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{name} missing columns: {missing}")


def run(season: str, season_type: str):
    safe = season_type.lower().replace(" ", "_")

    paths = {
        "games": Path(f"data/raw/games/{season}_{safe}.csv"),
        "schedule": Path(f"data/raw/schedule/{season}_{safe}.csv"),
        "team": Path(f"data/raw/team_game_stats/{season}_{safe}.csv"),
        "player": Path(f"data/raw/player_game_stats/{season}_{safe}.csv"),
        "player_roles": Path(f"data/raw/player_game_starter_roles/{season}_{safe}.csv"),
        "rosters": Path(f"data/raw/rosters/{season}.csv"),
        "standings": Path(f"data/raw/standings_snapshots/{season}_{safe}.csv"),
        "team_adv": Path(f"data/raw/team_season_advanced/{season}_{safe}.csv"),
        "player_adv": Path(f"data/raw/player_season_advanced/{season}_{safe}.csv"),
    }

    for name, p in paths.items():
        if name == "standings" and season_type == "Playoffs":
            continue
        if not p.exists():
            raise FileNotFoundError(f"Missing file: {p}")

    games = pd.read_csv(paths["games"])
    schedule = pd.read_csv(paths["schedule"])
    team = pd.read_csv(paths["team"])
    player = pd.read_csv(paths["player"])
    player_roles = pd.read_csv(paths["player_roles"])
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
