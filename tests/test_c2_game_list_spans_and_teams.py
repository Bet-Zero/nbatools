"""Game lists over season spans, with rate bounds, and for a named team (C2).

"best shooting games in the last 3 seasons" ranked season percentages; "best
free throw shooting games over 90%" could not be mapped; "Lakers worst
shooting games" listed the Lakers' games by date with no stat; "in the last 10
games" on a league list answered season percentages.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query


@pytest.mark.parametrize(
    ("query", "stat", "start", "season_type"),
    [
        ("best shooting games in the last 3 seasons", "fg_pct", "2023-24", "Regular Season"),
        ("worst free throw shooting games in the last 2 seasons", "ft_pct", "2024-25", None),
        ("top 5 shooting performances in the last 3 seasons", "fg_pct", "2023-24", None),
        ("best shooting games in the last 3 playoffs", "fg_pct", "2023-24", "Playoffs"),
    ],
)
def test_last_n_seasons_is_a_span(query, stat, start, season_type):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "player_game_finder"
    assert (kwargs["stat"], kwargs["start_season"]) == (stat, start)
    assert kwargs.get("player") is None
    if season_type:
        assert kwargs["season_type"] == season_type


def test_a_players_list_over_the_last_seasons_ranks_games():
    parsed = parse_query("Curry best shooting games in the last 3 seasons")
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "player_game_finder"
    assert (kwargs["stat"], kwargs["start_season"]) == ("fg_pct", "2023-24")


@pytest.mark.parametrize(
    "query",
    [
        "best shooting games in the last 10 games",
        "best shooting games last 5 games",
    ],
)
def test_recent_games_on_a_league_list_refuse(query):
    parsed = parse_query(query)
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == ["league_game_list_unread"]


@pytest.mark.parametrize(
    ("query", "stat", "bound"),
    [
        ("best free throw shooting games over 90%", "ft_pct", (0.9001, None)),
        ("best free throw shooting games at least 90%", "ft_pct", (0.9, None)),
        ("best true shooting games over 70%", "ts_pct", (0.7001, None)),
    ],
)
def test_an_unnamed_rate_bound_is_on_the_ranked_rate(query, stat, bound):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["stat"] == stat
    assert [(c["stat"], c["min_value"], c["max_value"]) for c in kwargs["conditions"]] == [
        (stat, *bound)
    ]


def test_a_lower_rate_bound_is_on_the_ranked_rate():
    kwargs = parse_query("worst 3 point shooting games under 20%")["route_kwargs"]
    assert kwargs["stat"] == "fg3_pct" and kwargs["ascending"] is True
    [condition] = kwargs["conditions"]
    assert condition["stat"] == "fg3_pct"
    assert condition["max_value"] == pytest.approx(0.1999)


@pytest.mark.parametrize(
    ("query", "team", "stat", "ascending", "limit"),
    [
        ("Lakers worst shooting games", "LAL", "fg_pct", True, 10),
        ("Lakers best shooting games", "LAL", "fg_pct", False, 10),
        ("worst shooting games by the Lakers", "LAL", "fg_pct", True, 10),
        ("best shooting games for the Celtics", "BOS", "fg_pct", False, 10),
        ("Lakers best 3 point shooting games", "LAL", "fg3_pct", False, 10),
        ("Lakers top 5 free throw shooting games this season", "LAL", "ft_pct", False, 5),
        ("the Lakers' worst shooting games since 2020", "LAL", "fg_pct", True, 10),
    ],
)
def test_named_team_shooting_game_lists(query, team, stat, ascending, limit):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "game_finder"
    assert (kwargs["team"], kwargs["stat"], kwargs["ascending"], kwargs["limit"]) == (
        team,
        stat,
        ascending,
        limit,
    )


def test_a_named_team_list_keeps_its_tail():
    kwargs = parse_query("Lakers worst shooting games vs the Celtics")["route_kwargs"]
    assert (kwargs["team"], kwargs["opponent"]) == ("LAL", "BOS")
    kwargs = parse_query("Lakers best shooting games in the last 3 seasons")["route_kwargs"]
    assert (kwargs["start_season"], kwargs["end_season"]) == ("2023-24", "2025-26")
    kwargs = parse_query("Lakers best shooting games over 55%")["route_kwargs"]
    assert kwargs["conditions"] == [{"stat": "fg_pct", "min_value": 0.5501, "max_value": None}]


@pytest.mark.parametrize(
    ("query", "label"),
    [
        ("Lakers worst shooting games in the clutch", "team_game_list_filter"),
        ("Lakers worst shooting games in 2023-24 and 2024-25", "two_season_windows"),
    ],
)
def test_a_named_team_list_refuses_what_it_cannot_apply(query, label):
    parsed = parse_query(query)
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == [label]


def test_an_opponent_team_is_not_the_owner():
    kwargs = parse_query("worst shooting games against the Lakers")["route_kwargs"]
    assert kwargs.get("team") is None and kwargs["opponent"] == "LAL"


@pytest.mark.fixture_data
def test_a_named_team_list_ranks_that_teams_games():
    data = execute_natural_query("Lakers worst shooting games since 2023").result.to_dict()
    rows = data["sections"]["finder"]
    assert rows
    rates = [row["fg_pct"] for row in rows]
    assert rates == sorted(rates)
    assert {row.get("team_abbr") for row in rows} == {"LAL"}
