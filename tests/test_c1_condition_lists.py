"""Distinct player counts with condition lists, roles and a player headline.

"how many players had 25 points, 5 rebounds, 5 assists" keeps every
condition (a comma list used to drop all but one, counting 5-rebound games),
"off the bench" counts bench games only, and the headline counts players,
not games. Expected values are counted from the fixture.
"""

from __future__ import annotations

import pytest

from nbatools.commands._occurrence_route_utils import extract_compound_occurrence_event

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def _count(result) -> int:
    return result.result.to_dict()["sections"]["count"][0]["count"]


@pytest.mark.parametrize(
    "text",
    [
        "30 points, 10 rebounds and 5 assists",
        "30 points and 10 rebounds and 5 assists",
        "30 points, 10 rebounds, 5 assists",
    ],
)
def test_every_condition_in_a_list_is_kept(text):
    assert extract_compound_occurrence_event(text) == [
        {"stat": "pts", "min_value": 30.0},
        {"stat": "reb", "min_value": 10.0},
        {"stat": "ast", "min_value": 5.0},
    ]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("how many players had 25 points, 5 rebounds, 5 assists this season", 18),
        ("how many players had 30 points, 10 rebounds and 5 assists this season", 6),
        ("how many players had 30 points and 10 rebounds and 5 assists this season", 6),
    ],
)
def test_condition_list_counts(query, expected):
    result = _run(query)
    assert result.route == "player_occurrence_leaders"
    assert _count(result) == expected


def test_off_the_bench_counts_bench_games_only():
    result = _run("how many players had 15 points off the bench")
    assert _count(result) == 6
    assert result.metadata["count_phrase"] == (
        "6 players have had a game with 15+ points off the bench in the 2025-26 regular season."
    )


def test_as_a_starter_counts_starts_only():
    assert _count(_run("how many players scored 30 as a starter")) == 18


def test_count_headline_counts_players_not_games():
    result = _run("how many players had 30 points and 10 rebounds this season")
    assert result.metadata["count_phrase"] == (
        "9 players have had a game with 30+ points and 10+ rebounds this season."
    )


def test_occurrence_leaderboard_keeps_off_the_bench():
    # Robert Williams has five bench games with 15+ points and 5+ rebounds in
    # 2024-25 on the fixture; ignoring the role ranked every game.
    result = _run("most games with 15 points and 5 rebounds off the bench in 2024-25")
    assert result.route == "player_occurrence_leaders"
    top = result.result.to_dict()["sections"]["leaderboard"][0]
    assert (top["player_name"], top["games_pts_15+_reb_5+"]) == ("Robert Williams", 5)


def test_between_range_is_one_condition_in_a_list():
    assert extract_compound_occurrence_event("between 20 and 30 points and 10 rebounds") == [
        {"stat": "pts", "min_value": 20.0, "max_value": 30.0},
        {"stat": "reb", "min_value": 10.0},
    ]
    result = _run(
        "how many games did Jokic have between 20 and 30 points and 10 rebounds in 2024-25"
    )
    assert result.metadata["count_phrase"] == (
        "Nikola Jokić has had 32 games with 20-30 points and 10+ rebounds "
        "in the 2024-25 regular season."
    )
    assert (
        _count(_run("how many players had between 20 and 30 points and 10 rebounds in 2024-25"))
        == 17
    )


def test_player_count_headline_names_the_opponent():
    result = _run("how many players had 30 points vs the West this season")
    assert result.metadata["count_phrase"] == (
        "17 players have had a game with 30+ points against the West this season."
    )
