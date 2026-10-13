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


@pytest.mark.parametrize(
    "query",
    [
        "best scoring games by rookie of the year",
        "best scoring games by the rookie of the year in 2024",
        "best scoring games vs the Celtics by Lakers centers",
        "best scoring games vs the Celtics by Lakers rookie guards",
        "best scoring games vs the Celtics by the Lakers' centers",
        "best scoring games vs the Celtics by Lakers starters",
        "best shooting games vs the Celtics by Lakers centers",
        "best scoring games vs the Celtics allowed by the Lakers",
        "best scoring games by the Lakers vs Celtics centers",
        "best scoring games allowed by the Lakers vs the Celtics",
        "best scoring games vs the Celtics and Knicks rookies",
        "best scoring games vs the Celtics and Knicks' rookies",
        "best scoring games vs the Celtics and Knicks starters",
        "best scoring games vs the Celtics and Knicks bench",
        "best scoring games by the Lakers vs the Celtics and vs the Knicks",
        "best scoring games by the Lakers vs the Celtics compared to the Knicks",
    ],
)
def test_words_these_lists_do_not_read_are_not_answered(query):
    try:
        parsed = parse_query(query)
    except ValueError:
        return
    kwargs = parsed["route_kwargs"]
    if kwargs.get("unsupported_filters"):
        return
    # Not one of the new lists answering without the group, award, "allowed"
    # or second opponent.
    assert parsed["route"] not in ("player_game_finder", "game_finder")


@pytest.mark.parametrize(
    "query",
    [
        "best scoring games by the Lakers vs the Celtics and the Lakers",
        "best scoring games vs the Celtics and Knicks rookies",
    ],
)
def test_a_team_against_itself_or_the_opponents_players_refuse(query):
    parsed = parse_query(query)
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"]


@pytest.mark.parametrize(
    ("query", "route", "team"),
    [
        ("best scoring games by Lakers players vs the Celtics ever", "player_game_finder", "LAL"),
        (
            "best scoring games by Lakers players vs the Celtics all time",
            "player_game_finder",
            "LAL",
        ),
        (
            "best scoring games vs the Celtics by Lakers players in 2024",
            "player_game_finder",
            "LAL",
        ),
        ("best scoring games by the Lakers vs the Celtics of all time", "game_finder", "LAL"),
        ("best scoring games vs the Celtics by the Lakers please", "game_finder", "LAL"),
        (
            "best scoring games vs the Celtics and Knicks so far this season",
            "player_game_finder",
            None,
        ),
    ],
)
def test_time_words_after_an_owner_or_opponent_keep_the_list(query, route, team):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == route
    assert kwargs.get("team") == team
    assert kwargs.get("opponent")
    assert not kwargs.get("unsupported_filters")


@pytest.mark.parametrize(
    ("query", "key"),
    [
        ("best scoring games by Lakers players just at home", "home_only"),
        ("best scoring games by the Lakers they lost", "losses_only"),
        ("best scoring games by rookies vs the Celtics just at home", "home_only"),
        ("best scoring games by the Lakers yesterday", "start_date"),
    ],
)
def test_a_filter_after_a_team_is_applied_not_refused(query, key):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs.get(key)
    assert not kwargs.get("unsupported_filters")


def test_a_team_shooting_list_keeps_its_rate_before_more_words():
    kwargs = parse_query("worst shooting games by the Lakers so far this season")["route_kwargs"]
    assert (kwargs["team"], kwargs["stat"], kwargs["ascending"]) == ("LAL", "fg_pct", True)


@pytest.mark.parametrize(
    "query",
    [
        "best scoring games by Lakers centers",
        "best scoring games by the Lakers rookies vs the Celtics",
    ],
)
def test_a_group_of_a_teams_players_refuses(query):
    parsed = parse_query(query)
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == ["team_players_group"]


@pytest.mark.parametrize(
    "group",
    [
        "shooting guards",
        "at center",
        "in the frontcourt",
        "with rookies",
        "just rookies",
        "plus their starters",
        "- rookies only",
        "led by rookies",
    ],
)
@pytest.mark.parametrize(
    "frame",
    [
        "best scoring games vs the Celtics by the Lakers {}",
        "best scoring games by the Lakers vs the Celtics {}",
        "best scoring games by the Lakers {}",
    ],
)
def test_a_group_after_an_opening_word_refuses(frame, group):
    # The team's totals would answer with the group gone.
    parsed = parse_query(frame.format(group))
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == ["team_players_group"]


@pytest.mark.parametrize(
    "tail",
    [
        "winning players",
        "going big",
        "under 25",
        "since the 2020 season",
        "show stoppers",
        "in the fourth",
        "in league history",
        "in the fourth game of the season",
        "in the second and third quarter",
    ],
)
def test_an_unread_word_after_the_opponent_refuses(tail):
    parsed = parse_query(f"best scoring games vs the Celtics by the Lakers {tail}")
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == ["team_game_list_words"]


@pytest.mark.parametrize(
    ("tail", "key", "value"),
    [
        ("since 2020", "start_season", "2020-21"),
        ("in 2023-24", "season", "2023-24"),
        ("this season", "stat", "pts"),
        ("top 25", "limit", 25),
        ("they lost", "losses_only", True),
        ("that they won", "wins_only", True),
        ("in the 4th quarter", "quarter", "4"),
        ("in the second half", "half", "second"),
        ("in NBA history", "start_season", "1996-97"),
        ("on 0 days rest", "rest_days", 0),
        ("in the clutch", "clutch", True),
        ("on the second night of a back to back", "back_to_back", True),
        ("in game 7s", "series_situation", "game_7"),
        ("in the last 5 meetings", "last_n", 5),
        (
            "in wins by 20 or more",
            "conditions",
            [{"stat": "win_margin", "min_value": 20.0, "max_value": None}],
        ),
    ],
)
def test_read_words_after_the_opponent_still_answer(tail, key, value):
    kwargs = parse_query(f"best scoring games vs the Celtics by the Lakers {tail}")["route_kwargs"]
    assert (kwargs["team"], kwargs["opponent"], kwargs[key]) == ("LAL", "BOS", value)


@pytest.mark.parametrize(
    "query",
    [
        "best scoring games by Lakers players vs the Celtics starters",
        "Lakers players worst shooting games vs the Celtics' starters",
        "best scoring games by Lakers players vs the Celtics and Knicks rookies",
        "best scoring games by the Lakers vs the Celtics sixth man",
        "best scoring games vs the Celtics and Knicks best players",
        "best rookie scoring games vs the Celtics top players",
    ],
)
def test_a_group_of_the_opponents_players_refuses(query):
    parsed = parse_query(query)
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == ["opponent_players_group"]


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


@pytest.mark.fixture_data
def test_a_player_missing_from_the_roster_is_reported_not_silently_dropped():
    import pandas as pd

    from nbatools.commands.player_game_finder import _apply_roster_filter

    roster = _roster("2025-26")
    rookie = int(roster.loc[roster["experience_years"] == 0, "player_id"].iloc[0])
    games = pd.DataFrame({"season": ["2025-26", "2025-26"], "player_id": [rookie, 999999999]})
    caveats: list[str] = []
    kept, note = _apply_roster_filter(games, None, True, caveats)
    assert note is None
    assert kept["player_id"].tolist() == [rookie]
    assert caveats == [
        "1 games by players missing from that season's roster could not be classified "
        "and are left out"
    ]


def test_the_all_star_break_is_a_date_not_a_group():
    for query in (
        "best scoring games by the Lakers after the all-star break",
        "best scoring games vs the Celtics by the Lakers after the all-star break",
    ):
        kwargs = parse_query(query)["route_kwargs"]
        assert kwargs["team"] == "LAL"
        assert kwargs["start_date"]
