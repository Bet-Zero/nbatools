"""Controlled raw-row join checks, not real NBA or feature-acceptance evidence."""

import pandas as pd
import pytest

from tests.played_sample_oracle import attach_raw_team_outcomes


def _sources():
    # Same game id deliberately recurs across seasons, types and opponent teams.
    contexts = [
        ("2023-24", "Regular Season", 11, "W"),
        ("2025-26", "Regular Season", 11, "L"),
        ("2023-24", "Regular Season", 22, "L"),
        ("2023-24", "Playoffs", 11, "L"),
    ]
    teams = pd.DataFrame(
        [
            dict(season=s, season_type=t, game_id=700, team_id=team, wl=wl)
            for s, t, team, wl in contexts
        ]
    )
    players = teams.drop(columns="wl").copy()
    players["player_id"] = [41, 41, 42, 41]
    players["pts"] = [18, 35, 24, 27]
    # Another player on the first team/game demonstrates the many-to-one join.
    teammate = players.iloc[[0]].copy()
    teammate["player_id"] = 43
    teammate["pts"] = 12
    players = pd.concat([players, teammate], ignore_index=True)
    players.index = [9, 4, 2, 8, 1]
    return players, teams


def test_outcomes_use_all_source_keys_and_preserve_every_player_row():
    players, teams = _sources()
    joined = attach_raw_team_outcomes(players, teams.iloc[::-1])
    assert joined.wl.tolist() == ["W", "L", "L", "L", "W"]
    pd.testing.assert_frame_equal(joined.drop(columns="wl"), players)
    assert joined.pts.tolist() == [18, 35, 24, 27, 12]
    assert joined.pts.mean() == pytest.approx(23.2)
    assert joined.wl.eq("W").sum() == 2
    assert joined.wl.eq("L").sum() == 3
    assert "wl" not in players


def test_team_outcomes_replace_stale_player_outcomes_without_suffix_ambiguity():
    players, teams = _sources()
    players["wl"] = "W"
    joined = attach_raw_team_outcomes(players, teams)
    assert joined.wl.tolist() == ["W", "L", "L", "L", "W"]
    assert joined.columns.tolist() == players.columns.tolist()
    assert players.wl.eq("W").all()


@pytest.mark.parametrize("side", ["players", "teams"])
@pytest.mark.parametrize("column", ["season", "season_type", "game_id", "team_id"])
def test_missing_join_key_columns_fail(side, column):
    players, teams = _sources()
    if side == "players":
        players = players.drop(columns=column)
    else:
        teams = teams.drop(columns=column)
    with pytest.raises(AssertionError, match="keys are missing"):
        attach_raw_team_outcomes(players, teams)


@pytest.mark.parametrize("side", ["players", "teams"])
@pytest.mark.parametrize("column", ["season", "season_type", "game_id", "team_id"])
def test_null_join_keys_fail(side, column):
    players, teams = _sources()
    frame = players if side == "players" else teams
    frame[column] = frame[column].astype(object)
    frame.iloc[0, frame.columns.get_loc(column)] = None
    with pytest.raises(AssertionError, match="Null raw"):
        attach_raw_team_outcomes(players, teams)


@pytest.mark.parametrize("bad", ["not-an-id", 700.5, 0, -1])
def test_malformed_numeric_key_cannot_match_by_coercion(bad):
    players, teams = _sources()
    players["game_id"] = players.game_id.astype(object)
    players.loc[9, "game_id"] = bad
    with pytest.raises(AssertionError, match="Invalid raw.*identifier"):
        attach_raw_team_outcomes(players, teams)


@pytest.mark.parametrize("side", ["players", "teams"])
def test_duplicate_grain_keys_fail_instead_of_inflating_or_overwriting_rows(side):
    players, teams = _sources()
    if side == "players":
        players = pd.concat([players, players.iloc[[0]]])
    else:
        duplicate = teams.iloc[[0]].copy()
        duplicate["wl"] = "L"
        teams = pd.concat([teams, duplicate])
    with pytest.raises(AssertionError, match="Duplicate raw"):
        attach_raw_team_outcomes(players, teams)


@pytest.mark.parametrize("bad", [None, "", "T", "win", " W"])
def test_missing_or_invalid_team_outcomes_fail(bad):
    players, teams = _sources()
    teams.loc[0, "wl"] = bad
    with pytest.raises(AssertionError, match="Invalid or missing raw team outcomes"):
        attach_raw_team_outcomes(players, teams)


def test_missing_outcome_column_fails():
    players, teams = _sources()
    with pytest.raises(AssertionError, match="outcome column is missing"):
        attach_raw_team_outcomes(players, teams.drop(columns="wl"))


@pytest.mark.parametrize("removed", [0, 1, 2, 3])
def test_every_player_key_requires_its_exact_team_outcome(removed):
    players, teams = _sources()
    with pytest.raises(AssertionError, match="Missing raw team outcomes for 1"):
        attach_raw_team_outcomes(players, teams.drop(index=removed))


@pytest.mark.parametrize("side", ["players", "teams"])
def test_empty_required_sources_are_not_successful_joins(side):
    players, teams = _sources()
    if side == "players":
        players = players.iloc[:0]
    else:
        teams = teams.iloc[:0]
    with pytest.raises(AssertionError, match="source is empty"):
        attach_raw_team_outcomes(players, teams)


def test_required_player_witness_joins_outcomes_without_changing_teammate_samples(monkeypatch):
    from tests import test_played_season_splits_real_data as required

    def source(path):
        season = path.name[:7]
        common = dict(
            season=season,
            season_type="Regular Season",
            team_id=11,
            team_abbr="BOS",
            opponent_team_abbr="ATL",
        )
        if "team_game_stats" in str(path):
            return pd.DataFrame(
                [
                    dict(common, game_id=game, wl=outcome)
                    for game, outcome in [(10, "W"), (20, "L"), (30, "W")]
                ]
            )
        return pd.DataFrame(
            [
                dict(common, game_id=game, player_id=player, player_name=name, pts=points)
                for game, player, name, points in [
                    (10, 41, "Jaylen Brown", 18),
                    (20, 41, "Jaylen Brown", 35),
                    (30, 41, "Jaylen Brown", 24),
                    (10, 42, "Jayson Tatum", 40),
                    (20, 42, "Jayson Tatum", 25),
                    (20, 43, "Derrick White", 20),
                ]
            ]
        )

    monkeypatch.setattr(required, "data_read_csv", source)
    opponent, stages = required._qualified_sample("player")
    assert opponent == "ATL"
    assert list(stages) == required.SEASONS
    for base, one_teammate, both_teammates in stages.values():
        assert base.game_id.tolist() == [10, 20, 30]
        assert base.wl.tolist() == ["W", "L", "W"]
        assert one_teammate.game_id.tolist() == [10, 20]
        assert one_teammate.pts.mean() == 26.5
        assert both_teammates.game_id.tolist() == [20]
        assert both_teammates.wl.tolist() == ["L"]
        assert both_teammates.pts.mean() == 35
