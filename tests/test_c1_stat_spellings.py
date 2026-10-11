"""C1: stat spellings the readers missed.

"5 3-pointers", "5 three pointers", "5 3pt", "10 free throws", "10 field
goals", "five threes", "ten rebounds" read no bound (every game answered);
"5 3 point games" and "10 3-point attempts" read a 3-point floor; "games with
10 free throw attempts / 10 fta / 20 fga" read the attempts as a leaderboard
qualifier and dropped them. Expected values come from the fixture's rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _player(name: str) -> pd.DataFrame:
    rows = pd.read_csv(RAW / "player_game_stats" / "2025-26_regular_season.csv")
    return rows[rows["player_name"] == name]


def _count(query: str) -> int:
    return execute_natural_query(query).result.to_dict()["sections"]["count"][0]["count"]


@pytest.mark.parametrize(
    ("phrase", "column", "value"),
    [
        ("5 3-pointers", "fg3m", 5),
        ("5 3 pointers", "fg3m", 5),
        ("5 three pointers", "fg3m", 5),
        ("5 three-pointers", "fg3m", 5),
        ("5 3pt", "fg3m", 5),
        ("five threes", "fg3m", 5),
        ("ten rebounds", "reb", 10),
        ("4 free throws", "ftm", 4),
        ("10 field goals", "fgm", 10),
        ("7 free throw attempts", "fta", 7),
        ("7 fta", "fta", 7),
        ("20 fga", "fga", 20),
        ("8 3-point attempts", "fg3a", 8),
        ("8 three point attempts", "fg3a", 8),
        ("8 3pa", "fg3a", 8),
    ],
)
def test_player_game_floors(phrase, column, value):
    games = _player("LeBron James")
    expected = int((games[column] >= value).sum())
    assert 0 < expected < len(games)
    assert _count(f"how many LeBron games with {phrase}") == expected


@pytest.mark.parametrize("query", ["LeBron 5 3 point games", "LeBron 5 three point games"])
def test_three_point_games_are_made_threes(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs.get("stat"), kwargs.get("min_value")) == ("fg3m", 5.0)


def test_word_number_points():
    games = _player("LeBron James")
    assert _count("how many games did LeBron score twenty-five points") == int(
        (games["pts"] >= 25).sum()
    )


@pytest.mark.parametrize(
    ("query", "stat"),
    [
        ("who has the most 3-pointers this season", "fg3m"),
        ("Curry most 3pt attempts", "fg3a"),
        ("who has the most free throws", "ftm"),
    ],
)
def test_rankings_name_the_stat(query, stat):
    from nbatools.commands.natural_query import _build_parse_state

    assert _build_parse_state(query)["stat"] == stat


@pytest.mark.parametrize(
    "query",
    [
        "best three point percentage minimum 100 attempts",
        "best free throw percentage with at least 200 free throw attempts",
        "best 3pt% with 5 3pa per game",
    ],
)
def test_rate_qualifiers_stay_qualifiers(query):
    from nbatools.commands.natural_query import _build_parse_state

    state = _build_parse_state(query)
    assert state["min_attempts"] is not None
    assert state["stat"].endswith("_pct")


def test_team_record_with_a_3_pointer_floor():
    games = pd.read_csv(RAW / "team_game_stats" / "2025-26_regular_season.csv")
    games = games[(games["team_abbr"] == "LAL") & (games["fg3m"] >= 15)]
    summary = execute_natural_query("Lakers record in games with 15 3-pointers").result.to_dict()[
        "sections"
    ]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (
        int((games["wl"] == "W").sum()),
        int((games["wl"] == "L").sum()),
    )


@pytest.mark.parametrize(
    ("query", "limit", "ascending"),
    [
        ("LeBron lowest 3 three point games", 3, True),
        ("Lakers top 3 three point games since 2024", 3, False),
    ],
)
def test_ranked_three_point_games_stay_ranked(query, limit, ascending):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs.get("stat"), kwargs.get("limit"), bool(kwargs.get("ascending"))) == (
        "fg3m",
        limit,
        ascending,
    )
    assert kwargs.get("min_value") is None


def test_three_pointers_made_leaders():
    from nbatools.commands.natural_query import _build_parse_state

    assert _build_parse_state("three pointers made leaders this season")["stat"] == "fg3m"


@pytest.mark.parametrize(
    ("query", "stat"),
    [
        ("Curry 3pt fg%", "fg3_pct"),
        ("Lakers 3pt fg% this season", "fg3_pct"),
        ("Curry 3pt fga per game", "fg3a"),
    ],
)
def test_three_point_rate_and_attempt_spellings(query, stat):
    from nbatools.commands.natural_query import _build_parse_state

    assert _build_parse_state(query)["stat"] == stat


@pytest.mark.parametrize(
    "query",
    ["Curry free throws missed", "Lakers games won by 3pts", "LeBron two point field goals"],
)
def test_not_rewritten_to_makes(query):
    from nbatools.commands.natural_query import _build_parse_state

    assert _build_parse_state(query)["stat"] not in ("ftm", "fg3m", "fgm")


@pytest.mark.parametrize(
    ("query", "own", "opp", "floor_own", "floor_opp"),
    [
        (
            "how many Lakers games with at least 20 free throws and at least 20 opponent free throws",
            "ftm",
            "ftm",
            20,
            20,
        ),
        (
            "how many Lakers games with at least 10 three pointers and at least 15 opponent "
            "three pointers",
            "fg3m",
            "fg3m",
            10,
            15,
        ),
    ],
)
def test_multi_word_own_and_opponent_floors(query, own, opp, floor_own, floor_opp):
    games = pd.read_csv(RAW / "team_game_stats" / "2025-26_regular_season.csv")
    other = games[["game_id", "team_abbr", opp]].rename(columns={"team_abbr": "o", opp: "o_stat"})
    lakers = games[games["team_abbr"] == "LAL"].merge(other, on="game_id")
    lakers = lakers[lakers["o"] != "LAL"]
    expected = int(((lakers[own] >= floor_own) & (lakers["o_stat"] >= floor_opp)).sum())
    assert _count(query) == expected
