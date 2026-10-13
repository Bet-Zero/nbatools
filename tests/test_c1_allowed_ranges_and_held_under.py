"""C1: points-allowed ranges, and "held to under N".

- "Lakers record when allowing between 100 and 110" answered every game, and
  "when they allow / opponents score between 100 and 110" read the Lakers'
  own points.
- "when held to under 100" refused.

Expected values are counted with pandas from the fixture.
"""

from __future__ import annotations

import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


def _execute(query: str):
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    return result.result.to_dict()["sections"]


def _record(query: str) -> tuple[int, int]:
    summary = _execute(query)["summary"][0]
    return summary["wins"], summary["losses"]


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record when allowing between 100 and 110",
        "Lakers record when they allow between 100 and 110 points",
        "Lakers record when opponents score between 100 and 110",
        "Lakers record when they held opponents to between 100 and 110",
    ],
)
def test_points_allowed_range(query):
    assert _record(query) == (4, 2)


def test_own_points_range_is_unchanged():
    assert _record("Lakers record when scoring between 100 and 110") == (15, 3)


def test_points_allowed_range_on_game_lists():
    assert len(_execute("Lakers games allowing between 100 and 110 points")["finder"]) == 6
    rows = _execute("LeBron James games when opponents score between 100 and 110")["finder"]
    assert len(rows) == 6


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when held to under 100", (6, 8)),
        ("Lakers record when they were held to below 100 points", (6, 8)),
        ("Lakers record when opponents were held to under 100", (40, 2)),
    ],
)
def test_held_to_under(query, record):
    assert _record(query) == record


def test_player_held_to_under():
    assert len(_execute("LeBron James games when held to under 20")["finder"]) == 15


def test_team_players_games_still_answer():
    assert len(_execute("did any Lakers player score 40")["finder"]) == 2
