"""A lone "from 2019", open-ended spans, and a game-list owner after an opponent (C2).

"best scoring games from 2019" ranked 2025-26 games (the year was dropped);
"from 2019 on" / "2019 onwards" / "from 2019 to now" were dropped or refused;
"best scoring games vs the Celtics by Lakers players" ranked every player's
games against Boston (the Lakers were dropped).
"""

from __future__ import annotations

import pytest

from nbatools.commands._parse_helpers import extract_bare_year_season, extract_since_season
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query


@pytest.mark.parametrize(
    ("query", "route", "season"),
    [
        ("best scoring games from 2019", "top_player_games", "2018-19"),
        ("best shooting games from 2019", "player_game_finder", "2018-19"),
        ("lakers record from 2019", "team_record", "2018-19"),
        ("lakers record from 2019 on the road", "team_record", "2018-19"),
        ("best scoring games from 2019 by Lakers players", "player_game_finder", "2018-19"),
        ("best shooting games by the Lakers from 2019", "game_finder", "2018-19"),
    ],
)
def test_from_a_year_names_that_season(query, route, season):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == route
    assert kwargs["season"] == season
    assert not kwargs.get("start_season")


@pytest.mark.parametrize(
    ("query", "start"),
    [
        ("best scoring games from 2019 on", "2019-20"),
        ("lakers record from 2019 on", "2019-20"),
        ("lakers record from 2019, on", "2019-20"),
        ("lebron ppg from 2019 to now", "2019-20"),
        ("lebron ppg from 2019-20 to present", "2019-20"),
    ],
)
def test_open_ended_spans_read_as_since(query, start):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["start_season"] == start
    assert kwargs["end_season"] > start


@pytest.mark.parametrize(
    ("text", "since"),
    [
        ("best scoring games from 2019 onward", "2019-20"),
        ("best scoring games 2019 onwards", "2019-20"),
        ("from the 2015-16 season onward", "2015-16"),
        ("lakers record 2019 on the road", None),
        ("best scoring games from 2019", None),
    ],
)
def test_since_reads_open_ended_wording(text, since):
    assert extract_since_season(text) == since


def test_from_a_year_that_opens_a_range_is_not_one_season():
    assert (
        extract_bare_year_season("best scoring games from 2016 playoffs to 2019 playoffs") is None
    )
    kwargs = parse_query("best scoring games from 2019 to 2021")["route_kwargs"]
    assert (kwargs["start_season"], kwargs["end_season"]) == ("2019-20", "2021-22")


@pytest.mark.parametrize(
    ("query", "route", "stat", "ascending"),
    [
        ("best scoring games vs the Celtics by Lakers players", "player_game_finder", "pts", False),
        (
            "worst shooting games against the Celtics by Lakers players",
            "player_game_finder",
            "fg_pct",
            True,
        ),
        ("best shooting games vs the Celtics by the Lakers", "game_finder", "fg_pct", False),
    ],
)
def test_an_owner_after_the_opponent_is_kept(query, route, stat, ascending):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == route
    assert (kwargs["team"], kwargs["opponent"]) == ("LAL", "BOS")
    assert kwargs["stat"] == stat
    assert bool(kwargs.get("ascending")) is ascending
    assert not kwargs.get("unsupported_filters")


@pytest.mark.parametrize(
    "query",
    [
        "best scoring games against the Lakers by Lakers players",
        "best shooting games against the lakers by the lakers",
    ],
)
def test_an_owner_who_is_also_the_opponent_refuses(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert "team_is_opponent" in (kwargs.get("unsupported_filters") or [])


def test_opponents_of_a_team_are_not_its_players():
    kwargs = parse_query("best scoring games vs the Celtics by former Lakers players")[
        "route_kwargs"
    ]
    assert kwargs.get("team") != "LAL" or kwargs.get("unsupported_filters")


@pytest.mark.fixture_data
def test_lakers_players_vs_the_celtics_rank_their_rows():
    rows = (
        execute_natural_query("best scoring games vs the Celtics by Lakers players since 2023")
        .result.to_dict()["sections"]
        .get("finder")
        or []
    )
    for row in rows:
        assert row["team_abbr"] == "LAL"
        assert row["opponent_team_abbr"] == "BOS"
    points = [row["pts"] for row in rows]
    assert points == sorted(points, reverse=True)


@pytest.mark.parametrize(
    ("query", "start", "season_type"),
    [
        ("LeBron stats for 2019 on", "2019-20", "Regular Season"),
        ("LeBron stats in 2019, on", "2019-20", "Regular Season"),
        ("Lakers record in 2019 on", "2019-20", "Regular Season"),
        ("LeBron stats from 2019 on vs Celtics", "2019-20", "Regular Season"),
        ("LeBron stats from 2019 on in wins", "2019-20", "Regular Season"),
        ("from 2019 on LeBron stats", "2019-20", "Regular Season"),
        ("LeBron stats from 2019 on in the playoffs", "2019-20", "Playoffs"),
        ("Lakers record from the 2019 playoffs on", "2018-19", "Playoffs"),
        ("LeBron stats from 2019 up to now", "2019-20", "Regular Season"),
        ("LeBron stats from 2019 to this season", "2019-20", "Regular Season"),
    ],
)
def test_an_open_end_followed_by_more_question_is_still_a_span(query, start, season_type):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["start_season"] == start
    assert kwargs["end_season"] > start
    assert kwargs["season_type"] == season_type


@pytest.mark.parametrize(
    "query",
    [
        "lakers record from 2019 on the road",
        "lakers record from 2019 on back to backs",
    ],
)
def test_an_on_filter_after_the_year_keeps_one_season(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["season"] == "2018-19"
    assert not kwargs.get("start_season")


@pytest.mark.parametrize(
    "query", ["lebron ppg from 2019 to today", "lebron ppg from 2019 until today"]
)
def test_to_today_ends_a_season_span_without_a_one_day_filter(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["start_season"] == "2019-20"
    assert not kwargs.get("start_date") and not kwargs.get("end_date")


@pytest.mark.parametrize(
    ("query", "season"),
    [
        ("LeBron stats in 2019 on the Lakers", "2018-19"),
        ("Lakers in 2019 on offense", "2018-19"),
        ("Lakers record in 2024 on a back to back", "2023-24"),
        ("LeBron in 2024 on rest", "2023-24"),
        ("Lakers record in 2025 up to March", "2024-25"),
        ("LeBron stats from 2023-24 on the Lakers", "2023-24"),
    ],
)
def test_on_that_is_not_an_open_end_keeps_the_season(query, season):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["season"] == season
    assert not kwargs.get("start_season")


def test_to_tonight_closes_a_season_span():
    kwargs = parse_query("LeBron stats from 2024 to tonight")["route_kwargs"]
    assert kwargs["start_season"] == "2024-25"
    assert kwargs["end_season"] > "2024-25"
    assert not kwargs.get("start_date")


@pytest.mark.parametrize(
    ("query", "season"),
    [
        ("LeBron stats in 2024 on at least 2 days rest", "2023-24"),
        ("Lakers record in 2024 on at least 1 day rest", "2023-24"),
        ("LeBron stats in 2024 on at most 1 day rest", "2023-24"),
        ("LeBron stats in 2024 on in-season tournament games", "2023-24"),
    ],
)
def test_at_least_and_in_season_after_on_are_not_open_ends(query, season):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs.get("season") == season
    assert not kwargs.get("start_season")


def test_in_a_year_to_tonight_has_no_one_day_filter():
    kwargs = parse_query("LeBron stats in 2024 to tonight")["route_kwargs"]
    assert not kwargs.get("start_date") and not kwargs.get("end_date")


@pytest.mark.parametrize(
    ("query", "season"),
    [
        ("Jokic in the 2024-25 season on vs off court", "2024-25"),
        ("LeBron in 2024 on vs off court", "2023-24"),
        ("LeBron in 2024 on versus off court", "2023-24"),
        ("LeBron in 2024 on vs. off court", "2023-24"),
        ("LeBron stats in 2024 on for 30+ minutes", "2023-24"),
    ],
)
def test_on_court_wording_after_a_year_keeps_the_season(query, season):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs.get("season") == season
    assert not kwargs.get("start_season")


@pytest.mark.parametrize(
    ("query", "season"),
    [
        ("Tatum stats in 2024 on with Brown off", "2023-24"),
        ("Tatum stats in 2024 on without Brown", "2023-24"),
        ("Nuggets in 2024 on vs bench", "2023-24"),
        ("Jokic net rating in 2024 on vs sitting", "2023-24"),
        ("Celtics record in 2024 on with Tatum", "2023-24"),
    ],
)
def test_in_a_year_on_followed_by_more_is_on_court_wording(query, season):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs.get("season") == season
    assert not kwargs.get("start_season")


@pytest.mark.parametrize(
    ("query", "season"),
    [
        ("In 2019 on the Lakers, how many points did LeBron average", "2018-19"),
        ("in 2019 on the road Celtics record", "2018-19"),
        ("during 2024 on the road Celtics record", "2023-24"),
        ("In 2023-24 on the road Celtics record", "2023-24"),
    ],
)
def test_a_leading_in_a_year_on_filter_keeps_the_season(query, season):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs.get("season") == season
    assert not kwargs.get("start_season")


@pytest.mark.parametrize(
    "query",
    ["from 2019 on LeBron stats", "from 2019 on, LeBron stats", "In 2019 onward LeBron stats"],
)
def test_a_leading_open_end_is_a_span(query):
    assert parse_query(query)["route_kwargs"]["start_season"] == "2019-20"
