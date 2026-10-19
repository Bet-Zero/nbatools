"""Frozen independent reciprocal-source oracle for named-opponent OR."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_path
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ORACLE = json.loads((Path(__file__).parent / "fixtures/owned_opponent_or/primary.json").read_text())


def _qualify():
    for path, digest in ORACLE["sources"].items():
        assert hashlib.sha256(data_path(path).read_bytes()).hexdigest() == digest
    teams = pd.read_csv(data_path("raw/team_game_stats/2023-24_regular_season.csv"))
    games = pd.read_csv(data_path("raw/games/2023-24_regular_season.csv"))
    assert not teams.duplicated(["game_id", "team_id"]).any()
    assert not games.game_id.duplicated().any()
    observed = teams.loc[teams.team_abbr.eq("LAL") & teams.opponent_team_abbr.isin(["BOS", "WAS"])]
    assert set(observed.game_id) == {row["game_id"] for row in ORACLE["candidate_rows"]}
    for truth in ORACLE["candidate_rows"]:
        own = observed.loc[observed.game_id.eq(truth["game_id"])].iloc[0]
        other = teams.loc[
            teams.game_id.eq(truth["game_id"]) & teams.team_id.eq(truth["opponent_team_id"])
        ]
        game = games.loc[games.game_id.eq(truth["game_id"])].iloc[0]
        assert len(other) == 1 and other.iloc[0].opponent_team_id == truth["team_id"]
        assert {int(game.home_team_id), int(game.away_team_id)} == {
            truth["team_id"],
            truth["opponent_team_id"],
        }
        assert str(game.is_final).lower() in {"true", "1"}
        assert str(game.game_date) == truth["game_date"] and game.season == "2023-24"
        for key, value in truth.items():
            if key == "opponent_pts":
                assert other.iloc[0].pts == value
            elif key != "matching_branches":
                assert own[key] == value


@pytest.mark.parametrize(
    "query",
    [
        ORACLE["query"],
        ORACLE["query"].replace("Celtics", "BOS").replace("Wizards", "WAS"),
        "Lakers games against Celtics and Wizards in 2023-24 when Celtics score at least 110 or Wizards score at least 125",
        "Lakers games against Celtics and Wizards when Wizards score at least 125 or Celtics score at least 110 in 2023-24",
    ],
)
def test_owned_or_uses_each_opponents_bound_and_keeps_lakers_rows(query):
    _qualify()
    result = execute_natural_query(query)
    assert result.result_status == "ok", result.metadata
    rows = result.result.to_dict()["sections"]["finder"]
    expected = ORACLE["expected"]
    assert sorted([int(row["game_id"]) for row in rows]) == [key[0] for key in expected["keys"]]
    assert all(row["team_abbr"] == "LAL" for row in rows)
    assert sum(row["wl"] == "W" for row in rows) == expected["wins"]
    for stat, total in expected["sums"].items():
        assert sum(row[stat] for row in rows) == total
    assert result.metadata["team_context"]["team_id"] == ORACLE["subject"]["team_id"]
    assert {
        b["conditions"][0]["opponent_team"] for b in result.metadata["boolean_filter_branches"]
    } == {"BOS", "WAS"}


def test_qualified_empty_branch_is_a_valid_or_member():
    _qualify()
    result = execute_natural_query(
        ORACLE["query"].replace("Celtics score at least 110", "Celtics score at least 200")
    )
    assert result.result_status == "ok", result.metadata
    rows = result.result.to_dict()["sections"]["finder"]
    assert [int(row["game_id"]) for row in rows] == [22300856]
    assert (rows[0]["pts"], rows[0]["reb"], rows[0]["ast"]) == (134, 45, 30)
