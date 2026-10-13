"""Points ranges, opposition subjects and teams outside the game.

- "opponents score 100 to 110" / "100-110" and "they allow 100-110 points"
  read the team's own points.
- "the opposition / another team scores 110 and makes 15 threes" put the
  threes on the Lakers; "and another team makes 15 threes" was dropped.
- "when the Lakers shoot 50% and the Celtics shoot 40%" answered Boston's
  record; "vs Celtics when the Lakers score 120 and the Celtics score 110"
  refused.
- A clause naming a team outside the game ("vs Celtics when ... the Knicks
  score 110", "Knicks and Celtics score 110") read the team's own points.

Expected values are counted with pandas from the fixture.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _execute(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]


def _record(query: str) -> tuple[int, int]:
    summary = _execute(query)["summary"][0]
    return summary["wins"], summary["losses"]


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when opponents score 100 to 110", (4, 2)),
        ("Lakers record when opponents score 100-110", (4, 2)),
        ("Lakers record when they allow 100-110 points", (4, 2)),
        ("Lakers record when they allow 100-110 points in 2024-25", (8, 6)),
        ("Lakers record when the opposition scores 110 and makes 15 threes", (1, 4)),
        ("Lakers record when another team scores 110 and makes 15 threes", (1, 4)),
        ("Lakers record when they score 110 and another team makes 15 threes", (7, 1)),
        (
            "Lakers record vs Celtics when the Lakers score 120 and the Celtics score 110",
            (2, 1),
        ),
    ],
)
def test_records(query, record):
    assert _record(query) == record


def test_joined_opponent_shooting_on_a_game_list():
    rows = _execute("Lakers games when they score 120 and the Celtics shoot under 50%")["finder"]
    assert len(rows) == 1


@pytest.mark.parametrize(
    "query",
    [
        # A team outside the game.
        "Lakers record vs Celtics when the Lakers score 120 and the Knicks score 110",
        "Lakers record when they score 120 and Knicks and Celtics score 110",
    ],
)
def test_refuses(query):
    from nbatools.query_service import execute_natural_query

    assert execute_natural_query(query).result_status == "no_result"
