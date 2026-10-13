"""A team's players' single-game lists, and a team owner closing the question (C2).

"Lakers players worst shooting games" and "best scoring games by Lakers
players" listed the Lakers' team games (by date, or by team points); "best
free throw shooting games over 90% by the Celtics" listed Celtics games by
date with no bound.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query


@pytest.mark.parametrize(
    ("query", "stat", "ascending", "limit"),
    [
        ("Lakers players worst shooting games", "fg_pct", True, 10),
        ("worst shooting games by Lakers players", "fg_pct", True, 10),
        ("Lakers players' best shooting games this season", "fg_pct", False, 10),
        ("best scoring games by Lakers players", "pts", False, 10),
        ("Lakers players best scoring performances since 2020", "pts", False, 10),
        ("Lakers players top 5 rebounding games vs the Celtics", "reb", False, 5),
    ],
)
def test_team_players_game_lists(query, stat, ascending, limit):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "player_game_finder"
    assert (kwargs["team"], kwargs["stat"], kwargs["ascending"], kwargs["limit"]) == (
        "LAL",
        stat,
        ascending,
        limit,
    )
    assert kwargs.get("player") is None


def test_a_team_players_list_keeps_its_tail():
    kwargs = parse_query("Lakers players top 5 rebounding games vs the Celtics")["route_kwargs"]
    assert kwargs["opponent"] == "BOS"
    kwargs = parse_query("Lakers players worst shooting games in the clutch")["route_kwargs"]
    assert kwargs["clutch"] is True
    kwargs = parse_query("Lakers players best scoring performances since 2020")["route_kwargs"]
    assert (kwargs["start_season"], kwargs["end_season"]) == ("2020-21", "2025-26")


def test_two_season_windows_refuse_for_a_teams_players():
    parsed = parse_query("Lakers players worst shooting games in 2023-24 and 2024-25")
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == ["two_season_windows"]


@pytest.mark.parametrize(
    ("query", "team", "stat", "condition"),
    [
        (
            "best free throw shooting games over 90% by the Celtics",
            "BOS",
            "ft_pct",
            {"stat": "ft_pct", "min_value": 0.9001, "max_value": None},
        ),
        (
            "worst free throw shooting games under 60% by the Lakers last 3 seasons",
            "LAL",
            "ft_pct",
            {"stat": "ft_pct", "min_value": None, "max_value": 0.5999},
        ),
    ],
)
def test_a_team_owner_closing_the_question(query, team, stat, condition):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "game_finder"
    assert (kwargs["team"], kwargs["stat"]) == (team, stat)
    assert kwargs["conditions"] == [condition]


def test_an_opponent_is_still_not_the_owner():
    kwargs = parse_query("worst shooting games against the Lakers")["route_kwargs"]
    assert kwargs.get("team") is None and kwargs["opponent"] == "LAL"


@pytest.mark.parametrize(
    "query",
    [
        "best scoring games by Lakers players against the Lakers",
        "Lakers players best scoring games against the Lakers",
        "best shooting games by Lakers players vs the Lakers",
    ],
)
def test_a_teams_players_against_that_team_refuse(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert "team_is_opponent" in (kwargs.get("unsupported_filters") or [])


def test_a_shooting_bound_on_a_counting_list_is_not_applied_as_the_count():
    try:
        parsed = parse_query("best scoring games by Lakers players over 50%")
    except ValueError:
        return
    kwargs = parsed["route_kwargs"]
    assert not (parsed["route"] == "player_game_finder" and kwargs.get("stat") == "pts")


@pytest.mark.fixture_data
def test_lakers_players_worst_shooting_games_rank_their_rows():
    rows = execute_natural_query("Lakers players worst shooting games since 2023").result.to_dict()[
        "sections"
    ]["finder"]
    assert rows
    assert {row["team_abbr"] for row in rows} == {"LAL"}
    assert all(row.get("player_name") for row in rows)
    rates = [row["fg_pct"] for row in rows]
    assert rates == sorted(rates)


@pytest.mark.fixture_data
def test_lakers_players_against_the_lakers_is_not_no_games():
    result = execute_natural_query("best scoring games by Lakers players against the Lakers").result
    data = result.to_dict()
    assert data["result_status"] == "no_result"
    assert any("team_is_opponent" in note for note in data.get("notes") or [])
