"""League single-game lists in wordings the base parse missed (C2).

"worst shooting games", "top 5 shooting performances this season", "best free
throw shooting games since 2020" could not be mapped; "best shooting games by
a team" ranked team season percentages and "best scoring performances" was
unclear. Each is answered as the canonical "best shooting games ..." (or the
team game board) with the same tail, then given the rate, direction and row
count asked for.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query


@pytest.mark.parametrize(
    ("query", "stat", "ascending", "limit"),
    [
        ("worst shooting games", "fg_pct", True, 10),
        ("lowest shooting games this season", "fg_pct", True, 10),
        ("top 5 shooting performances this season", "fg_pct", False, 5),
        ("top 3 shooting games", "fg_pct", False, 3),
        ("top 3 point shooting games", "fg3_pct", False, 10),
        ("best free throw shooting games since 2020", "ft_pct", False, 10),
        ("worst free throw shooting games", "ft_pct", True, 10),
        ("best true shooting games", "ts_pct", False, 10),
        ("worst shooting games in the clutch", "fg_pct", True, 10),
    ],
)
def test_league_player_game_lists(query, stat, ascending, limit):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "player_game_finder"
    assert (kwargs["stat"], kwargs["ascending"], kwargs["limit"]) == (stat, ascending, limit)
    assert kwargs.get("player") is None
    assert kwargs.get("season") or kwargs.get("start_season")
    assert parsed["normalized_query"] == query


@pytest.mark.parametrize(
    ("query", "season"),
    [
        ("best shooting games in 2023-24", "2023-24"),
        ("worst free throw shooting games in 2023-24", "2023-24"),
        ("best shooting games on 2024-01-05", "2023-24"),
    ],
)
def test_a_season_or_date_is_not_an_unread_number(query, season):
    parsed = parse_query(query)
    assert parsed["route"] == "player_game_finder"
    assert parsed["route_kwargs"]["season"] == season


@pytest.mark.parametrize(
    ("query", "situation"),
    [
        ("best shooting games in game 7", "game_7"),
        ("best shooting games when up 3-1", "score_3_1"),
        ("best shooting games when down 2-0", "score_0_2"),
    ],
)
def test_a_series_situation_is_not_an_unread_number(query, situation):
    parsed = parse_query(query)
    assert parsed["route"] == "player_game_finder"
    assert parsed["route_kwargs"]["series_situation"] == situation


def test_a_margin_is_not_an_unread_number():
    kwargs = parse_query("best shooting games in games decided by 10")["route_kwargs"]
    assert {"stat": "margin", "min_value": 10.0, "max_value": None} in kwargs["conditions"]


def test_an_attempt_count_the_list_does_not_read_refuses():
    kwargs = parse_query("best shooting games with 20 shots")["route_kwargs"]
    assert kwargs["unsupported_filters"] == ["league_game_list_unread"]


@pytest.mark.parametrize(
    "query",
    [
        "best scoring performances in wins by 20 or more",
        "best rebounding performances in blowouts",
        "highest scoring games by a team in blowouts",
        "highest scoring games by a team in wins by 20 or more",
    ],
)
def test_a_margin_never_replaces_the_counted_stat(query):
    parsed = parse_query(query)
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"]


@pytest.mark.parametrize(
    "query",
    [
        "best rebounding performances with at least 20 points",
        "best scoring performances over 40 points",
        "highest scoring games by a team over 130 points",
    ],
)
def test_a_bound_the_game_board_cannot_apply_refuses(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["unsupported_filters"] == ["game_list_bound_unapplied"]


def test_the_tail_keeps_its_filters():
    kwargs = parse_query("best free throw shooting games since 2020")["route_kwargs"]
    assert (kwargs["start_season"], kwargs["end_season"]) == ("2020-21", "2025-26")
    assert parse_query("worst shooting games in the clutch")["route_kwargs"]["clutch"] is True
    assert (
        parse_query("top 5 shooting games in the playoffs")["route_kwargs"]["season_type"]
        == "Playoffs"
    )


@pytest.mark.parametrize(
    ("query", "stat", "ascending"),
    [
        ("best shooting games by a team", "fg_pct", False),
        ("best team shooting games since 2020", "fg_pct", False),
        ("best team 3 point shooting games", "fg3_pct", False),
        ("worst team shooting games vs the lakers", "fg_pct", True),
    ],
)
def test_league_team_shooting_game_lists(query, stat, ascending):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "game_finder"
    assert (kwargs["stat"], kwargs["ascending"], kwargs.get("team")) == (stat, ascending, None)


@pytest.mark.parametrize(
    ("query", "stat"),
    [
        ("highest scoring games by a team", "pts"),
        ("top 5 rebounding games by a team since 2020", "reb"),
        ("best passing games by a team", "ast"),
    ],
)
def test_team_counting_game_lists_use_the_team_game_board(query, stat):
    parsed = parse_query(query)
    assert parsed["route"] == "top_team_games"
    assert parsed["route_kwargs"]["stat"] == stat


@pytest.mark.parametrize(
    ("query", "stat"),
    [
        ("best scoring performances", "pts"),
        ("top scoring performances this season", "pts"),
        ("best rebounding performances", "reb"),
    ],
)
def test_performances_are_games(query, stat):
    parsed = parse_query(query)
    assert parsed["route"] == "top_player_games"
    assert parsed["route_kwargs"]["stat"] == stat
    assert not parsed["route_kwargs"].get("unsupported_filters")


def test_a_team_list_filter_team_games_cannot_apply_refuses():
    kwargs = parse_query("best shooting games by a team in the clutch")["route_kwargs"]
    assert kwargs["unsupported_filters"] == ["team_game_list_filter"]


@pytest.mark.parametrize(
    "query",
    [
        "best shooting games by a guard",
        "worst shooting games by rookies",
        "worst shooting games for the top 10 scorers",
    ],
)
def test_a_subject_the_list_cannot_filter_is_not_dropped(query):
    try:
        parsed = parse_query(query)
    except ValueError:
        return
    assert parsed["route"] != "player_game_finder" or parsed["route_kwargs"].get(
        "unsupported_filters"
    )


@pytest.mark.parametrize(
    "query",
    [
        "worst shooting games for the top 10 scorers",
        "best shooting games for the top 10 scorers",
        "best shooting games among all-stars",
    ],
)
def test_a_player_group_refuses(query):
    # The group is refused, never dropped from a list of every player's games.
    assert parse_query(query)["route_kwargs"]["unsupported_filters"]


def test_a_rate_bound_read_as_field_goals_does_not_rank_free_throws():
    try:
        parsed = parse_query("best free throw shooting games over 90%")
    except ValueError:
        return
    conditions = parsed["route_kwargs"].get("conditions") or []
    assert not any(c["stat"] == "fg_pct" for c in conditions)


@pytest.mark.fixture_data
def test_worst_free_throw_games_keep_the_attempt_floor():
    data = execute_natural_query("worst free throw shooting games since 2023").result.to_dict()
    rows = data["sections"]["finder"]
    assert rows and all(row["fta"] >= 5 for row in rows)
    rates = [row["ft_pct"] for row in rows]
    assert rates == sorted(rates)
    assert "games with fewer than 5 free throw attempts left out" in data["caveats"]


@pytest.mark.fixture_data
def test_team_shooting_games_rank_team_rows():
    rows = execute_natural_query("best shooting games by a team since 2023").result.to_dict()[
        "sections"
    ]["finder"]
    assert rows and all("player_name" not in row for row in rows)
    rates = [row["fg_pct"] for row in rows]
    assert rates == sorted(rates, reverse=True)
