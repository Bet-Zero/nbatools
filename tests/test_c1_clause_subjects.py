"""Whose stat a clause names, and "held to" wording.

- "when the opponent scores 110 and makes 15 threes", "when teams score 110"
  and "when opposing teams score 110" read the Lakers' own points.
- "when opponents score 110 and they shoot 50%" refused: the shooting was
  taken as the opponent's.
- "when the Celtics shoot 50%" answered with the Celtics' record.
- "when LeBron is held to 20", "when opponents were held to 100" and "when
  held to 40% shooting" were ignored and answered with every game.

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


def _rows(query: str) -> list[dict]:
    return _execute(query)["finder"]


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when the opponent scores 110 and makes 15 threes", (1, 4)),
        ("Lakers record when teams score 110 and make 15 threes", (1, 4)),
        ("Lakers record when opposing teams score 110", (3, 9)),
        ("Lakers record when other teams score under 100", (40, 2)),
        ("Lakers record when they score 110 and opponents make 15 threes", (7, 1)),
    ],
)
def test_opponent_subject_clauses(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when opponents score 110 and they shoot 50%", (3, 8)),
        ("Lakers record when opponents score 110 and they shoot 50% with 15 threes", (2, 1)),
    ],
)
def test_own_subject_after_an_opponent_clause(query, record):
    assert _record(query) == record


def test_player_shooting_after_an_opponent_clause():
    query = "LeBron James games when opponents score 120 and he shoots 50% with 30 points"
    assert len(_rows(query)) == 2


@pytest.mark.parametrize(
    "query",
    [
        # Not read yet; must not answer with the Lakers' or the Celtics' own rate.
        "Lakers record when the Celtics shoot 50%",
        "Lakers record when they shoot 50% and opponents shoot 50%",
    ],
)
def test_other_teams_bare_shooting_refuses(query):
    from nbatools.query_service import execute_natural_query

    assert execute_natural_query(query).result_status == "no_result"


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when LeBron is held to 20", (12, 6)),
        ("Lakers record when opponents were held to 100", (41, 2)),
    ],
)
def test_held_to_records(query, record):
    assert _record(query) == record


def test_held_to_rates_and_player_points():
    assert len(_rows("LeBron James games when LeBron is held to 20")) == 18
    rows = _rows("Lakers games when held to 30% from three")
    assert len(rows) == 7
    from nbatools.commands.natural_query import parse_query

    kwargs = parse_query("Lakers record when held to 40% shooting")["route_kwargs"]
    assert (kwargs["stat"], kwargs["max_value"]) == ("fg_pct", 0.4)
