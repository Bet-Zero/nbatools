"""C2: game lists keep their bounds; "season with the most X" ranks seasons.

Fixture: three regular seasons, 2023-24 to 2025-26.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query]


@pytest.mark.parametrize(
    ("query", "stat", "min_value", "max_value", "ascending"),
    [
        ("LeBron best shooting games over 50%", "fg_pct", 0.5001, None, False),
        ("LeBron best shooting games at least 50%", "fg_pct", 0.5, None, False),
        ("LeBron worst shooting games under 40%", "fg_pct", None, 0.3999, True),
        ("Curry best 3 point shooting games over 40%", "fg3_pct", 0.4001, None, False),
        ("LeBron best shooting games shooting over 50% from three", "fg3_pct", 0.5001, None, False),
    ],
)
def test_shooting_game_list_keeps_percent_bound(query, stat, min_value, max_value, ascending):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "player_game_finder"
    assert (kwargs["stat"], kwargs["sort_by"], kwargs["ascending"]) == (stat, "stat", ascending)
    # The bound is a condition, so the attempt floor still applies.
    assert kwargs.get("min_value") is None and kwargs.get("max_value") is None
    [condition] = kwargs["conditions"]
    assert condition["stat"] == stat
    assert condition["min_value"] == (pytest.approx(min_value) if min_value else None)
    assert condition["max_value"] == (pytest.approx(max_value) if max_value else None)


@pytest.mark.parametrize(
    ("query", "condition", "ascending"),
    [
        (
            "LeBron worst shooting games under 15 points",
            {"stat": "pts", "min_value": None, "max_value": 14.9999},
            True,
        ),
        (
            "LeBron best shooting games over 25 points",
            {"stat": "pts", "min_value": 25.0001, "max_value": None},
            False,
        ),
    ],
)
def test_shooting_game_list_keeps_other_stat_bound(query, condition, ascending):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "player_game_finder"
    assert (kwargs["stat"], kwargs["ascending"]) == ("fg_pct", ascending)
    assert kwargs["conditions"] == [condition]
    assert kwargs.get("min_value") is None and kwargs.get("max_value") is None


@pytest.mark.parametrize(
    ("query", "route", "stat", "ascending"),
    [
        ("Lakers season with the most turnovers", "season_team_leaders", "tov", False),
        ("Lakers seasons with the fewest turnovers", "season_team_leaders", "tov", True),
        ("Lakers season with the most points", "season_team_leaders", "pts", False),
        ("Lakers season with the best record", "team_record_leaderboard", "win_pct", False),
        ("Lakers season with the worst record", "team_record_leaderboard", "win_pct", True),
        ("LeBron season with the most assists", "season_leaders", "ast", False),
    ],
)
def test_season_with_the_most_ranks_seasons(query, route, stat, ascending):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == route
    assert (kwargs["stat"], kwargs["ascending"], kwargs["per_season"]) == (stat, ascending, True)
    assert not kwargs.get("unsupported_filters")


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record in seasons with the worst bench",
        "LeBron season with the highest scoring teammate",
        "Lakers seasons with the best point guard",
    ],
)
def test_season_with_a_person_is_not_a_stat_board(query):
    parsed = parse_query(query)
    assert parsed["route"] not in (
        "season_leaders",
        "season_team_leaders",
        "team_record_leaderboard",
    )


@pytest.mark.fixture_data
def test_percent_bound_keeps_the_attempt_floor():
    result = execute_natural_query("Curry best 3 point shooting games over 40%")
    assert result.result_status == "ok"
    rows = result.result.to_dict()["sections"]["finder"]
    assert rows and all(row["fg3a"] >= 5 and row["fg3_pct"] > 0.4 for row in rows)


@pytest.mark.fixture_data
def test_worst_shooting_games_under_15_points_answer():
    result = execute_natural_query("LeBron worst shooting games under 15 points")
    assert result.result_status == "ok"
    rows = result.result.to_dict()["sections"]["finder"]
    assert rows and all(row["pts"] < 15 for row in rows)
    pcts = [row["fg_pct"] for row in rows]
    assert pcts == sorted(pcts)


@pytest.mark.fixture_data
def test_season_with_the_most_turnovers_answers():
    result = execute_natural_query("Lakers season with the most turnovers")
    assert result.result_status == "ok"
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert {row["season"] for row in rows} == {"2023-24", "2024-25", "2025-26"}


@pytest.mark.parametrize(
    ("query", "stat", "min_value", "max_value"),
    [
        ("LeBron best shooting games over 80% from the line", "ft_pct", 0.8001, None),
        ("LeBron worst shooting games under 30% from three", "fg3_pct", None, 0.2999),
        ("Curry best shooting games over 50% from deep", "fg3_pct", 0.5001, None),
        ("LeBron best shooting games over 40% from 3", "fg3_pct", 0.4001, None),
        ("LeBron best shooting games with at least 40% from three", "fg3_pct", 0.4, None),
    ],
)
def test_percent_from_three_or_the_line_names_its_rate(query, stat, min_value, max_value):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["stat"] == stat
    [condition] = kwargs["conditions"]
    assert condition["stat"] == stat
    assert condition["min_value"] == (pytest.approx(min_value) if min_value else None)
    assert condition["max_value"] == (pytest.approx(max_value) if max_value else None)


@pytest.mark.fixture_data
@pytest.mark.parametrize(
    "query",
    [
        "Lakers season with the best home record",
        "Lakers seasons with the best road record",
        "Lakers season with the most home wins",
    ],
)
def test_home_road_season_records_do_not_answer_one_season(query):
    result = execute_natural_query(query)
    assert result.result_status != "ok"


@pytest.mark.parametrize(
    ("query", "stat", "conditions"),
    [
        (
            "Curry best 3 point shooting games over 80% from the line",
            "fg3_pct",
            [("ft_pct", 0.8001, None)],
        ),
        (
            "LeBron best free throw shooting games over 50% from three",
            "ft_pct",
            [("fg3_pct", 0.5001, None)],
        ),
        ("LeBron best shooting games over 70% at the line", "ft_pct", [("ft_pct", 0.7001, None)]),
        (
            "LeBron best shooting games over 50% from the field and over 40% from three",
            "fg_pct",
            [("fg_pct", 0.5001, None), ("fg3_pct", 0.4001, None)],
        ),
    ],
)
def test_two_rates_rank_one_and_bound_the_other(query, stat, conditions):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["stat"] == stat
    assert [
        (c["stat"], pytest.approx(c["min_value"]) if c["min_value"] else None, c["max_value"])
        for c in kwargs["conditions"]
    ] == [(s, pytest.approx(lo) if lo else None, hi) for s, lo, hi in conditions]
