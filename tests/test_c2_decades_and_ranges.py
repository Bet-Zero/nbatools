"""C2: decades, year ranges and a player's plain "best season".

"most points in a season in the 2010s" ranked team wins by decade, "most points
in a season from 2010 to 2019" refused, "this decade" was not read, and "LeBron
best season" gave a current-season summary.

Fixture: three regular seasons, 2023-24 to 2025-26.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query]


@pytest.mark.parametrize(
    ("query", "route", "stat", "start", "per_season", "ascending"),
    [
        ("most points in a season in the 2010s", "season_leaders", "pts", "2010-11", True, False),
        ("most threes in a season in the 2010s", "season_leaders", "fg3m", "2010-11", True, False),
        (
            "most points by a team in a season in the 2010s",
            "season_team_leaders",
            "pts",
            "2010-11",
            True,
            False,
        ),
        (
            "most wins in a season in the 2010s",
            "team_record_leaderboard",
            "wins",
            "2010-11",
            True,
            False,
        ),
        (
            "fewest wins in a single season in the 2000s",
            "team_record_leaderboard",
            "wins",
            "2000-01",
            True,
            True,
        ),
        ("most points in the 2010s", "season_leaders", "pts", "2010-11", None, False),
    ],
)
def test_named_decade_stat_questions(query, route, stat, start, per_season, ascending):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == route
    assert (kwargs["stat"], kwargs["start_season"], kwargs["ascending"]) == (stat, start, ascending)
    assert kwargs.get("per_season") == per_season


@pytest.mark.parametrize(
    "query", ["best record in the 2010s", "most wins in the 2010s", "best record by decade"]
)
def test_decade_record_boards_stay(query):
    assert parse_query(query)["route"] == "record_by_decade_leaderboard"


@pytest.mark.parametrize(
    ("query", "start", "end"),
    [
        ("most points in a season from 2010 to 2019", "2010-11", "2019-20"),
        ("most points in a season between 2010 and 2019", "2010-11", "2019-20"),
        ("most assists between 2015 and 2020", "2015-16", "2020-21"),
    ],
)
def test_year_ranges_pass_the_leaderboard_check(query, start, end):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "season_leaders"
    assert not kwargs.get("unsupported_filters")
    assert (kwargs["start_season"], kwargs["end_season"]) == (start, end)


@pytest.mark.parametrize(
    ("query", "route", "stat"),
    [
        ("most points in a season this decade", "season_leaders", "pts"),
        ("Lakers best offensive season this decade", "season_team_leaders", "off_rating"),
        ("Lakers best seasons this decade", "team_record_leaderboard", "win_pct"),
    ],
)
def test_this_decade_is_the_current_decade(query, route, stat):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == route
    assert (kwargs["stat"], kwargs["start_season"], kwargs["per_season"]) == (
        stat,
        "2020-21",
        True,
    )


def test_team_decade_record_stays():
    assert parse_query("Lakers record this decade")["route"] == "record_by_decade"


@pytest.mark.parametrize(
    ("query", "ascending", "limit", "season_type"),
    [
        ("LeBron best season", False, 10, "Regular Season"),
        ("LeBron worst season", True, 10, "Regular Season"),
        ("LeBron top 3 seasons", False, 3, "Regular Season"),
        ("LeBron best playoff season", False, 10, "Playoffs"),
    ],
)
def test_plain_player_best_season_ranks_scoring(query, ascending, limit, season_type):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "season_leaders"
    assert (kwargs["stat"], kwargs["ascending"], kwargs["limit"]) == ("pts", ascending, limit)
    assert (kwargs["per_season"], kwargs["season_type"]) == (True, season_type)
    assert "default: best season ranked by points per game" in parsed["notes"]


def test_player_best_season_in_a_named_year_stays_that_season():
    assert parse_query("LeBron best season in 2016")["route"] == "player_game_summary"


@pytest.mark.fixture_data
def test_this_decade_board_answers():
    result = execute_natural_query("most points in a season this decade")
    assert result.result_status == "ok"
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert {row["season"] for row in rows} <= {"2023-24", "2024-25", "2025-26"}
