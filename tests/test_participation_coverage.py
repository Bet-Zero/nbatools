"""Contain missing absence evidence; these checks do not accept positive absence."""

import pandas as pd
import pytest

from nbatools.commands.data_utils import filter_without_player
from nbatools.query_service import execute_natural_query, execute_structured_query


@pytest.mark.engine
@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("opponent", [None, "BOS", ["BOS", "NYK"]])
def test_appearances_do_not_qualify_absence(monkeypatch, strict, opponent):
    sample = pd.DataFrame(
        {"game_id": ["before", "played", "missed", "unknown", "after"], "team_id": [1] * 5}
    )
    appearances = pd.DataFrame(
        {"game_id": ["played"], "team_id": [1], "player_id": [42], "player_name": ["A Player"]}
    )
    monkeypatch.setattr(
        "nbatools.commands.data_utils.load_player_games_for_seasons", lambda *_: appearances
    )
    # Even 'missed' is only a stipulated fact in this test: the engine has no
    # machine-readable qualification that can separate it from unknown/before.
    with pytest.raises(ValueError, match="game-date team membership.*complete participation"):
        filter_without_player(
            sample,
            "A Player",
            ["2025-26"],
            "regular_season",
            team="LAL",
            strict_team_match=strict,
            opponent=opponent,
        )


@pytest.mark.query
@pytest.mark.fixture_data
@pytest.mark.parametrize(
    "query",
    [
        "Celtics record without Tatum",
        "Lakers record vs Celtics and Knicks without Tatum",
        "Jaylen Brown stats without Tatum",
        "Jaylen Brown games with 27 points without Tatum and Holiday",
    ],
)
def test_natural_absence_reports_missing_qualification(query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert not result.to_dict()["sections"]
    assert "Missing player-game rows are not verified absences" in " ".join(result.result.notes)


@pytest.mark.query
@pytest.mark.fixture_data
@pytest.mark.parametrize(
    ("route", "kwargs"),
    [
        ("team_record", {"team": "BOS"}),
        ("game_finder", {"team": "BOS", "stat": "pts", "min_value": 100}),
        ("game_summary", {"team": "BOS"}),
        ("player_game_finder", {"player": "Jaylen Brown", "stat": "pts", "min_value": 27}),
        ("player_game_summary", {"player": "Jaylen Brown"}),
    ],
)
def test_structured_consumers_report_missing_qualification(route, kwargs):
    result = execute_structured_query(
        route, season="2025-26", without_player="Jayson Tatum", **kwargs
    )
    assert result.result_status == "no_result"
    assert not result.to_dict()["sections"]
    assert "game-date team membership" in " ".join(result.result.notes)


@pytest.mark.query
@pytest.mark.fixture_data
def test_played_control_retains_exact_ids():
    players = pd.read_csv(
        "qa/fixtures/query_engine_sample/data/raw/player_game_stats/2025-26_regular_season.csv"
    )
    brown = players[players["player_name"].eq("Jaylen Brown") & players["pts"].ge(27)]
    tatum = players[players["player_name"].eq("Jayson Tatum")]
    keys = set(zip(tatum["game_id"], tatum["team_id"]))
    expected = {row.game_id for row in brown.itertuples() if (row.game_id, row.team_id) in keys}
    assert expected
    result = execute_natural_query("Jaylen Brown games with 27 points with Tatum")
    assert result.result_status == "ok"
    assert {row["game_id"] for row in result.to_dict()["sections"]["finder"]} == expected
