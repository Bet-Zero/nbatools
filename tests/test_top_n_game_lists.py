""" "LeBron top 5 scoring games" asks for his five best scoring games.

The 5 was read as a points floor ("5+ point games"), and game lists kept a
fixed 25-row limit, so the request returned every game of 5+ points. A count
next to a ranking word ("top 5", "best 5", "5 highest") sizes the list; a
ranked opponent ("vs top 10 defenses") does not.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands._parse_helpers import extract_top_n_games
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


@pytest.mark.parametrize(
    ("query", "route", "limit"),
    [
        ("LeBron top 5 scoring games", "player_game_finder", 5),
        ("LeBron best 5 scoring games", "player_game_finder", 5),
        ("LeBron 5 highest scoring games", "player_game_finder", 5),
        ("Jokic top 3 rebounding games", "player_game_finder", 3),
        ("Lakers top 5 scoring games", "game_finder", 5),
        ("Lakers 5 highest scoring games", "game_finder", 5),
        ("top 10 scoring games this season", "top_player_games", 10),
        ("top 3 team scoring games this season", "top_team_games", 3),
        ("LeBron best 5 rebounding games", "player_game_finder", 5),
    ],
)
def test_ranked_count_sizes_the_game_list(query, route, limit):
    parsed = parse_query(query)
    assert parsed["route"] == route
    kwargs = parsed["route_kwargs"]
    assert kwargs["limit"] == limit
    assert kwargs.get("min_value") is None


@pytest.mark.parametrize(
    ("query", "limit"),
    [
        ("LeBron 30 point games against top 10 teams", 25),
        ("Lakers games vs top 5 defenses", 25),
        ("list LeBron games vs top 10 teams", 25),
        ("LeBron best games vs top 10 teams", 5),
        ("Lakers top 5 scoring games vs top 10 defenses", 5),
    ],
)
def test_ranked_opponents_do_not_size_the_game_list(query, limit):
    assert parse_query(query)["route_kwargs"]["limit"] == limit


@pytest.mark.parametrize(
    ("query", "floor"),
    [
        ("LeBron 30 point games", 30.0),
        ("Curry best 50 point games", 50.0),
        ("LeBron greatest 40 point games", 40.0),
        ("Jokic highest 20 rebound games", 20.0),
        ("LeBron biggest 30 point games", 30.0),
    ],
)
def test_threshold_games_keep_their_threshold(query, floor):
    # A unit noun after the number ("50 point games") is a floor, not a count.
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs["min_value"], kwargs["limit"]) == (floor, 25)


@pytest.mark.parametrize("query", ["LeBron 2024 highest scoring games", "Lakers 2024 best wins"])
def test_a_year_is_not_a_list_size(query):
    assert parse_query(query)["route_kwargs"]["limit"] in (5, 25)


@pytest.mark.parametrize(
    ("text", "count"),
    [
        ("top 5 scoring games vs top 10 defenses", 5),
        ("games vs top 10 teams", None),
        ("top 3 team scoring games", 3),
    ],
)
def test_extract_top_n_games(text, count):
    assert extract_top_n_games(text) == count


def test_lebron_top_five_scoring_games_are_his_five_best():
    assert parse_query("LeBron top 5 scoring games")["route_kwargs"]["season"] == "2025-26"
    rows = pd.read_csv(RAW / "player_game_stats" / "2025-26_regular_season.csv")
    lebron = rows[rows["player_name"] == "LeBron James"]
    expected = sorted(lebron["pts"], reverse=True)[:5]

    result = execute_natural_query("LeBron top 5 scoring games")
    assert result.result_status == "ok", result.result_reason
    games = result.result.to_dict()["sections"]["finder"]
    assert [row["pts"] for row in games] == expected


def test_team_top_scoring_games_are_its_highest():
    result = execute_natural_query("Lakers top 2 scoring games")
    assert result.result_status == "ok", result.result_reason
    games = result.result.to_dict()["sections"]["finder"]
    assert len(games) == 2
    assert games[0]["pts"] >= games[1]["pts"]
