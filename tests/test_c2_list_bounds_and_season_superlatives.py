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
    ],
)
def test_shooting_game_list_keeps_percent_bound(query, stat, min_value, max_value, ascending):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "player_game_finder"
    assert (kwargs["stat"], kwargs["sort_by"], kwargs["ascending"]) == (stat, "stat", ascending)
    assert (
        kwargs.get("min_value") == pytest.approx(min_value)
        if min_value
        else not kwargs.get("min_value")
    )
    assert (
        kwargs.get("max_value") == pytest.approx(max_value)
        if max_value
        else not kwargs.get("max_value")
    )


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
