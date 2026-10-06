"""C2: league-wide shooting game lists and filters on player record boards.

"best shooting games this season" ranked season percentages, "worst shooting
games under 15 points" ranked season scoring from the bottom, and "players
with the best record against the Celtics" or "guards with the best record"
ranked teams.

Fixture: three regular seasons, 2023-24 to 2025-26.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query]


@pytest.mark.parametrize(
    ("query", "stat", "ascending"),
    [
        ("best shooting games this season", "fg_pct", False),
        ("best 3 point shooting games this season", "fg3_pct", False),
        ("worst 3 point shooting games in the playoffs", "fg3_pct", True),
        ("best shooting games at home", "fg_pct", False),
    ],
)
def test_league_shooting_game_lists_rank_games(query, stat, ascending):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "player_game_finder"
    assert (kwargs["stat"], kwargs["ascending"], kwargs["sort_by"]) == (stat, ascending, "stat")
    assert not kwargs.get("player")


@pytest.mark.parametrize(
    ("query", "condition"),
    [
        ("worst shooting games under 15 points", {"stat": "pts", "max_value": 14.9999}),
        ("best shooting games over 30 points", {"stat": "pts", "min_value": 30.0001}),
        ("best shooting games over 50%", {"stat": "fg_pct", "min_value": 0.5001}),
    ],
)
def test_league_game_list_bounds_are_conditions(query, condition):
    conditions = parse_query(query)["route_kwargs"]["conditions"]
    assert any(all(c.get(k) == v for k, v in condition.items()) for c in conditions)


@pytest.mark.parametrize(
    ("query", "route"),
    [
        ("highest scoring games by a player this season", "top_player_games"),
        ("best shooting seasons", "season_leaders"),
        ("best shooting teams", "season_team_leaders"),
    ],
)
def test_other_boards_keep_their_route(query, route):
    assert parse_query(query)["route"] == route


@pytest.mark.parametrize(
    ("query", "key", "value"),
    [
        ("players with the best record against the Celtics", "opponent", "BOS"),
        ("players with the best record in March", "start_date", "2026-03-01"),
        ("guards with the best record", "position", "guards"),
        ("centers with the most wins", "position", "centers"),
        ("most wins by guards since 2015", "position", "guards"),
        ("players with the best record since 2020 with at least 200 games", "min_games", 200),
    ],
)
def test_player_record_boards_keep_filters(query, key, value):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "season_leaders"
    assert kwargs[key] == value
    assert not kwargs.get("unsupported_filters")


def test_team_record_against_guards_stays_a_team_board():
    assert parse_query("teams with the best record against guards")["route"] == (
        "team_record_leaderboard"
    )


@pytest.mark.fixture_data
def test_league_shooting_games_keep_the_attempt_floor():
    result = execute_natural_query("best shooting games since 2023")
    data = result.result.to_dict()
    rows = data["sections"]["finder"]
    assert len({row["player_name"] for row in rows}) > 1
    assert all(row["fga"] >= 10 for row in rows)
    assert [row["fg_pct"] for row in rows] == sorted((row["fg_pct"] for row in rows), reverse=True)
    assert "games with fewer than 10 field goal attempts left out" in data["caveats"]


@pytest.mark.fixture_data
def test_worst_shooting_games_under_15_points():
    rows = execute_natural_query(
        "worst shooting games under 15 points since 2023"
    ).result.to_dict()["sections"]["finder"]
    assert all(row["pts"] < 15 for row in rows)
    assert [row["fg_pct"] for row in rows] == sorted(row["fg_pct"] for row in rows)


@pytest.mark.fixture_data
def test_player_record_against_one_opponent():
    result = execute_natural_query("players with the best record against the Celtics since 2023")
    data = result.result.to_dict()
    assert "filtered to games vs BOS" in data["caveats"]
    rows = data["sections"]["leaderboard"]
    assert all(row["wins"] + row["losses"] <= row["games_played"] for row in rows)
