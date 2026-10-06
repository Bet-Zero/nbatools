"""Ranking a player's games by one stat inside another stat's games.

"most rebounds in a game with 30 points" read the 30 as a rebound bound and
refused; "top 5 games by assists with 30 points" dropped the 30 points;
"fewest points in a 30 minute game" dropped the minutes. Expected values are
counted from the fixture.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _rows(query: str) -> list[dict]:
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]["finder"]


@pytest.mark.parametrize(
    ("query", "stat", "values", "condition"),
    [
        (
            "LeBron James most rebounds in a game with 30 points",
            "reb",
            [11, 10, 9, 8, 8],
            ("pts", 30),
        ),
        (
            "LeBron James fewest turnovers in games with 30 points",
            "tov",
            [0, 0, 0, 2, 2],
            ("pts", 30),
        ),
        (
            "LeBron James 30 point games with the fewest turnovers",
            "tov",
            [0, 0, 0, 2, 2],
            ("pts", 30),
        ),
        (
            "LeBron James top 5 games by assists with 30 points",
            "ast",
            [10, 10, 9, 8, 8],
            ("pts", 30),
        ),
        (
            "LeBron James least minutes in a game with 30 points",
            "minutes",
            [19.8, 21.0, 23.1],
            ("pts", 30),
        ),
        (
            "LeBron James fewest points in a 30 minute game",
            "pts",
            [18, 18, 19, 19, 21],
            ("minutes", 30),
        ),
    ],
)
def test_ranked_stat_inside_condition_games(query, stat, values, condition):
    rows = _rows(query)
    assert [row[stat] for row in rows][: len(values)] == values
    column, floor = condition
    assert all(row[column] >= floor for row in rows)


def test_plain_rankings_unchanged():
    assert [row["pts"] for row in _rows("LeBron James top 5 scoring games")] == [36, 35, 33, 33, 32]
    assert [row["pts"] for row in _rows("LeBron James highest scoring 30 point games")][:3] == [
        36,
        35,
        33,
    ]
