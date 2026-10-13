"""Game lists by rookies or a position group, two owners, opponent lists (C2).

"best scoring games by rookies" and "worst shooting games by centers" were
refused; "best scoring games vs the Celtics by the Lakers" ranked every
player's games against Boston (the Lakers were dropped); "best scoring games
by the Lakers vs the Celtics" compared the two teams; "by the Lakers and
Knicks" answered for one team; "best shooting games vs the Celtics and
Knicks" read New York as the owner.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query


@pytest.mark.parametrize(
    ("query", "stat", "ascending", "limit", "position", "rookies"),
    [
        ("best scoring games by rookies", "pts", False, 10, None, True),
        ("best scoring games by a rookie", "pts", False, 10, None, True),
        ("best rookie scoring games", "pts", False, 10, None, True),
        ("rookies best scoring games this season", "pts", False, 10, None, True),
        ("rookies' worst shooting games", "fg_pct", True, 10, None, True),
        ("best scoring performances by rookies", "pts", False, 10, None, True),
        ("most points in a game by a rookie", "pts", False, 10, None, True),
        ("best scoring games by centers", "pts", False, 10, "centers", False),
        ("worst shooting games by guards", "fg_pct", True, 10, "guards", False),
        ("best shooting performances among guards", "fg_pct", False, 10, "guards", False),
        ("top 5 center rebounding games since 2020", "reb", False, 5, "centers", False),
        ("most rebounds in a game by a center", "reb", False, 10, "centers", False),
        ("best free throw shooting games by guards", "ft_pct", False, 10, "guards", False),
        ("best scoring games by rookie guards", "pts", False, 10, "guards", True),
    ],
)
def test_group_game_lists(query, stat, ascending, limit, position, rookies):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "player_game_finder"
    assert (kwargs["stat"], bool(kwargs.get("ascending")), kwargs["limit"]) == (
        stat,
        ascending,
        limit,
    )
    assert kwargs.get("position") == position
    assert bool(kwargs.get("rookies_only")) is rookies
    assert kwargs.get("team") is None and kwargs.get("player") is None
    assert not kwargs.get("unsupported_filters")


def test_a_group_list_keeps_its_tail():
    kwargs = parse_query("best scoring games among centers vs the Celtics")["route_kwargs"]
    assert (kwargs["position"], kwargs["opponent"]) == ("centers", "BOS")
    kwargs = parse_query("most points in a single game by a rookie since 2010")["route_kwargs"]
    assert (kwargs["start_season"], kwargs["rookies_only"]) == ("2010-11", True)
    kwargs = parse_query("best scoring games by centers off the bench")["route_kwargs"]
    assert (kwargs["position"], kwargs["role"]) == ("centers", "bench")
    kwargs = parse_query("best shooting games over 50% from three for guards")["route_kwargs"]
    assert kwargs["conditions"] == [{"stat": "fg3_pct", "min_value": 0.5001, "max_value": None}]


@pytest.mark.parametrize(
    "query",
    [
        "best scoring games by point guards",
        "best shooting games by a point guard",
        "best scoring games against centers",
    ],
)
def test_a_group_the_lists_do_not_read_is_not_answered_for_everyone(query):
    try:
        parsed = parse_query(query)
    except ValueError:
        return
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] != "player_game_finder" or kwargs.get("unsupported_filters")


@pytest.mark.parametrize(
    ("query", "stat", "ascending", "opponent"),
    [
        ("best scoring games vs the Celtics by the Lakers", "pts", False, "BOS"),
        ("worst rebounding games against the Celtics by the Lakers", "reb", True, "BOS"),
        ("best scoring games by the Lakers vs the Celtics", "pts", False, "BOS"),
        ("best shooting games by the Lakers vs the Celtics", "fg_pct", False, "BOS"),
        (
            "best shooting games by the Lakers vs the Celtics and Knicks",
            "fg_pct",
            False,
            ["BOS", "NYK"],
        ),
    ],
)
def test_a_team_owner_beside_an_opponent_is_kept(query, stat, ascending, opponent):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "game_finder"
    assert (kwargs["team"], kwargs["opponent"], kwargs["stat"]) == ("LAL", opponent, stat)
    assert bool(kwargs.get("ascending")) is ascending
    assert kwargs["sort_by"] == "stat"
    assert not kwargs.get("unsupported_filters")


def test_a_team_owner_beside_its_own_name_refuses():
    kwargs = parse_query("best scoring games by the Lakers vs the Lakers")["route_kwargs"]
    assert "team_is_opponent" in kwargs["unsupported_filters"]


@pytest.mark.parametrize(
    "query",
    [
        "best scoring games by the Lakers and Knicks",
        "best scoring games by Lakers and Knicks players",
        "Lakers and Knicks players worst shooting games",
        "best shooting games by the Lakers and the Knicks",
        "best scoring games vs the Celtics by the Lakers and Knicks",
        "most points in a game by Lakers and Knicks players",
    ],
)
def test_two_team_owners_refuse(query):
    parsed = parse_query(query)
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == ["two_team_game_lists"]


@pytest.mark.parametrize(
    ("query", "team", "extra"),
    [
        ("best shooting games vs the Celtics and Knicks", None, {}),
        ("best scoring games vs Celtics or Knicks", None, {}),
        ("Lakers players best scoring games vs Celtics and Knicks", "LAL", {}),
        ("best scoring games by centers vs the Celtics and Knicks", None, {"position": "centers"}),
        ("rookies best scoring games vs the Celtics and Knicks", None, {"rookies_only": True}),
    ],
)
def test_an_opponent_list_is_every_team_in_it(query, team, extra):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "player_game_finder"
    assert kwargs["opponent"] == ["BOS", "NYK"]
    assert kwargs.get("team") == team
    for key, value in extra.items():
        assert kwargs[key] == value
    assert not kwargs.get("unsupported_filters")


def test_three_opponents_and_a_team_in_its_own_list():
    kwargs = parse_query("worst shooting games against the Celtics, Knicks and Heat")[
        "route_kwargs"
    ]
    assert kwargs["opponent"] == ["BOS", "NYK", "MIA"]
    kwargs = parse_query("Lakers players best scoring games vs Celtics and Lakers")["route_kwargs"]
    assert "team_is_opponent" in kwargs["unsupported_filters"]


def test_most_points_in_a_game_by_a_teams_players_is_their_games():
    parsed = parse_query("most points in a game by Lakers players")
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "player_game_finder"
    assert (kwargs["team"], kwargs["stat"]) == ("LAL", "pts")
    # No owner: the league game board, as before.
    assert parse_query("most points in a game this season")["route"] == "top_player_games"


def _roster(season):
    from pathlib import Path

    from nbatools.data_source import data_read_csv

    return data_read_csv(Path(f"data/raw/rosters/{season}.csv"))


@pytest.mark.fixture_data
def test_rookie_scoring_games_are_rookies_games():
    executed = execute_natural_query("best scoring games by rookies in 2025-26")
    rows = executed.result.to_dict()["sections"]["finder"]
    assert rows
    roster = _roster("2025-26")
    rookies = set(roster.loc[roster["experience_years"] == 0, "player_id"])
    assert {row["player_id"] for row in rows} <= rookies
    points = [row["pts"] for row in rows]
    assert points == sorted(points, reverse=True)
    assert {"label": "Experience", "value": "Rookies", "kind": "position"} in (
        executed.metadata["applied_filters"]
    )


@pytest.mark.fixture_data
def test_center_rebounding_games_are_centers_games():
    result = execute_natural_query("best rebounding games by centers in 2025-26")
    rows = result.result.to_dict()["sections"]["finder"]
    assert rows
    roster = _roster("2025-26")
    centers = set(roster.loc[roster["position"].isin(["C", "C-F"]), "player_id"])
    assert {row["player_id"] for row in rows} <= centers
    rebounds = [row["reb"] for row in rows]
    assert rebounds == sorted(rebounds, reverse=True)


@pytest.mark.fixture_data
def test_lakers_scoring_games_vs_the_celtics_are_lakers_games():
    rows = execute_natural_query(
        "best scoring games vs the Celtics by the Lakers since 2023"
    ).result.to_dict()["sections"]["finder"]
    for row in rows:
        assert (row["team_abbr"], row["opponent_team_abbr"]) == ("LAL", "BOS")
    points = [row["pts"] for row in rows]
    assert points == sorted(points, reverse=True)


@pytest.mark.fixture_data
def test_an_opponent_list_keeps_games_against_each_team():
    rows = execute_natural_query(
        "best scoring games vs the Celtics and Knicks in 2025-26"
    ).result.to_dict()["sections"]["finder"]
    assert rows
    assert {row["opponent_team_abbr"] for row in rows} <= {"BOS", "NYK"}
