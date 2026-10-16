"""Independent raw-team outcome join for played-sample numerical evidence."""

import pandas as pd


def _raw_keys(frame, *, player):
    columns = ["season", "season_type", "game_id", "team_id"]
    if player:
        columns.append("player_id")
    assert set(columns).issubset(frame.columns), "Required raw outcome-join keys are missing"
    assert not frame.empty, "Required raw outcome-join source is empty"
    assert not frame[columns].isna().any().any(), "Null raw outcome-join keys"
    labels = frame[["season", "season_type"]].astype(str)
    assert labels.apply(lambda values: values.str.strip().ne("").all()).all(), (
        "Blank raw outcome-join labels"
    )
    identifiers = {}
    for column in columns[2:]:
        values = pd.to_numeric(frame[column], errors="coerce")
        assert (values.notna() & values.gt(0) & values.mod(1).eq(0)).all(), (
            f"Invalid raw outcome-join identifier: {column}"
        )
        identifiers[column] = values.astype("int64")
    keys = list(
        zip(*(labels[column] if column in labels else identifiers[column] for column in columns))
    )
    assert len(keys) == len(set(keys)), "Duplicate raw outcome-join keys"
    return keys


def attach_raw_team_outcomes(players, teams):
    """Attach W/L with exact many-player-to-one-team-game coverage, never infer it.

    Player CSVs need not contain W/L. Team rows are the independent outcome
    source, even if a synthetic/older player table carries its own W/L column.
    """
    player_keys = _raw_keys(players, player=True)
    team_keys = _raw_keys(teams, player=False)
    assert "wl" in teams.columns, "Required raw team outcome column is missing"
    assert teams["wl"].isin(["W", "L"]).all(), "Invalid or missing raw team outcomes"
    outcomes = dict(zip(team_keys, teams["wl"]))
    game_keys = [key[:-1] for key in player_keys]
    missing = set(game_keys) - outcomes.keys()
    assert not missing, f"Missing raw team outcomes for {len(missing)} player-team-game keys"
    result = players.copy()
    result["wl"] = [outcomes[key] for key in game_keys]
    return result
