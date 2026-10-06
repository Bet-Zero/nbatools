"""C2: league-wide team-season boards and wins thresholds.

"seasons with at least 40 wins ranked by losses" refused (wins_only and
losses_only together), "teams with 50 wins ranked by point differential" and
"best defensive seasons by opponent points" were unclear, "50 win teams" did
not parse, and "seasons with the most wins" ranked one season.

Fixture: three regular seasons, 2023-24 to 2025-26.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

CAREER = ("1996-97", "2025-26")


@pytest.mark.parametrize(
    ("query", "route", "stat", "ascending", "min_wins", "max_wins"),
    [
        (
            "seasons with at least 40 wins ranked by losses",
            "team_record_leaderboard",
            "losses",
            False,
            40,
            None,
        ),
        (
            "teams with 50 wins ranked by point differential",
            "season_team_leaders",
            "plus_minus_per_game",
            False,
            50,
            None,
        ),
        (
            "teams with at least 50 wins ranked by net rating",
            "season_team_leaders",
            "net_rating",
            False,
            50,
            None,
        ),
        (
            "teams with 50+ wins ranked by defensive rating",
            "season_team_leaders",
            "def_rating",
            True,
            50,
            None,
        ),
        ("50 win teams", "team_record_leaderboard", "wins", False, 50, None),
        ("teams that won 60 games", "team_record_leaderboard", "wins", False, 60, None),
        ("teams with more than 60 wins", "team_record_leaderboard", "wins", False, 61, None),
        ("teams with fewer than 20 wins", "team_record_leaderboard", "wins", True, None, 19),
        ("teams with 20 wins or fewer", "team_record_leaderboard", "wins", True, None, 20),
        ("teams with at most 25 wins", "team_record_leaderboard", "wins", True, None, 25),
        ("teams with between 40 and 50 wins", "team_record_leaderboard", "wins", False, 40, 50),
        (
            "best defensive seasons by opponent points",
            "season_team_leaders",
            "opponent_pts_per_game",
            True,
            None,
            None,
        ),
        ("best defensive seasons", "season_team_leaders", "def_rating", True, None, None),
        (
            "best point differential seasons ever",
            "season_team_leaders",
            "plus_minus_per_game",
            False,
            None,
            None,
        ),
        ("seasons with the most wins", "team_record_leaderboard", "wins", False, None, None),
        ("worst seasons by net rating", "season_team_leaders", "net_rating", True, None, None),
    ],
)
def test_league_team_season_boards(query, route, stat, ascending, min_wins, max_wins):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == route
    assert (kwargs["start_season"], kwargs["end_season"]) == CAREER
    assert kwargs["per_season"] is True
    assert kwargs["stat"] == stat
    assert kwargs["ascending"] is ascending
    assert (kwargs["min_wins"], kwargs["max_wins"]) == (min_wins, max_wins)
    assert not kwargs.get("wins_only") and not kwargs.get("losses_only")


def test_a_named_season_ranks_that_season():
    kwargs = parse_query("teams with 50 wins in 2016")["route_kwargs"]
    assert kwargs["season"] == "2015-16"
    assert kwargs["per_season"] is False
    assert kwargs["min_wins"] == 50


def test_a_span_ranks_each_season_in_it():
    kwargs = parse_query("teams with at least 50 wins ranked by net rating since 2015")[
        "route_kwargs"
    ]
    assert (kwargs["start_season"], kwargs["per_season"]) == ("2015-16", True)


@pytest.mark.parametrize(
    "query",
    [
        # Games played, not wins.
        "most points per game in the 2020s with at least 50 games",
        # Player seasons and spans keep their boards.
        "best scoring seasons",
        "best shooting seasons",
        "most points over the last 3 seasons",
        "teams with the most wins since 2010",
        "LeBron seasons with the most wins",
    ],
)
def test_other_boards_are_left_alone(query):
    parsed = parse_query(query)
    assert parsed["route_kwargs"].get("min_wins") is None
    assert "single_season: each team season ranked on its own" not in (parsed.get("notes") or [])


@pytest.mark.parametrize(
    "query",
    [
        "teams with 50 wins at home",
        "teams with 50 wins vs the Celtics",
        "players with 50 wins",
        "teams with 50 wins in back to back seasons",
        "teams with 50 wins ranked by net rating in the playoffs",
    ],
)
def test_win_bounds_never_drop_a_filter(query):
    try:
        parsed = parse_query(query)
    except ValueError:
        return
    assert parsed["route_kwargs"].get("min_wins") is None


@pytest.mark.fixture_data
def test_win_floor_keeps_only_those_team_seasons():
    data = execute_natural_query(
        "teams with at least 40 wins ranked by net rating since 2023"
    ).result.to_dict()
    rows = data["sections"]["leaderboard"]
    assert rows and all(row["wins"] >= 40 for row in rows)
    assert len({row["season"] for row in rows}) > 1
    ratings = [row["net_rating"] for row in rows]
    assert ratings == sorted(ratings, reverse=True)
    assert "teams with at least 40 wins" in data["caveats"]


@pytest.mark.fixture_data
def test_losses_board_with_a_win_floor():
    rows = execute_natural_query(
        "seasons with at least 20 wins ranked by losses since 2023"
    ).result.to_dict()["sections"]["leaderboard"]
    assert rows and all(row["wins"] >= 20 for row in rows)
    losses = [row["losses"] for row in rows]
    assert losses == sorted(losses, reverse=True)


@pytest.mark.fixture_data
def test_best_defensive_seasons_by_opponent_points():
    rows = execute_natural_query(
        "best defensive seasons by opponent points since 2023"
    ).result.to_dict()["sections"]["leaderboard"]
    allowed = [row["opponent_pts_per_game"] for row in rows]
    assert allowed == sorted(allowed)
    assert len({row["season"] for row in rows}) > 1
