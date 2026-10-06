"""Player clauses inside a team-record sample.

- "Lakers record when LeBron plays and scores 30" checked 30 points against
  the team's points and answered with the whole record.
- "when Luka sits" was not read as absence at all.
- "in games LeBron plays 35 minutes and Luka plays 35 minutes" dropped Luka.
- "and the Lakers play at home" after a minutes bound counted as a second
  player and refused.
- "below 3 turnovers" was read as a floor, and "... but loses" was ignored.

Expected values are counted from the fixture.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _execute(query: str):
    from nbatools.query_service import execute_natural_query

    return execute_natural_query(query)


def _record(query: str) -> tuple[int, int, int]:
    result = _execute(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    summary = result.result.to_dict()["sections"]["summary"][0]
    return summary["wins"], summary["losses"], summary["games"]


def _rows(query: str) -> list[dict]:
    result = _execute(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]["finder"]


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when LeBron James plays and scores at least 30 points", (10, 1, 11)),
        ("Lakers record when LeBron James plays and has 10 assists", (6, 0, 6)),
        (
            "Lakers record when LeBron James plays at least 35 minutes and the Lakers play at home",
            (2, 0, 2),
        ),
        ("Lakers record when LeBron James plays at least 35 minutes but loses", (0, 1, 1)),
        ("Lakers record when LeBron James scores 30 but they lose", (0, 1, 1)),
        ("Lakers record in games with not under 120 points", (18, 1, 19)),
    ],
)
def test_player_clause_is_applied(query, record):
    assert _record(query) == record


def test_plays_and_scores_matches_scores():
    assert _record("Lakers record when LeBron James plays and scores at least 30 points") == (
        _record("Lakers record when LeBron James scores at least 30 points")
    )


@pytest.mark.parametrize(
    "query",
    [
        # Luka played every fixture game, so his absence leaves no games.
        "Lakers record when Luka Doncic sits",
        "Lakers record when Luka Doncic rests",
    ],
)
def test_sits_is_absence(query):
    result = _execute(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "no_match"


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record when LeBron James plays and Luka Doncic sits",
        "Lakers record in games LeBron James plays at least 35 minutes and Luka Doncic plays "
        "at least 35 minutes",
    ],
)
def test_second_player_clause_refuses(query):
    result = _execute(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"


def test_below_is_a_ceiling():
    assert _rows("LeBron James games with below 3 turnovers") == _rows(
        "LeBron James games with at most 2 turnovers"
    )
    assert _rows("LeBron James games with 30 points and below 3 turnovers") == _rows(
        "LeBron James games with 30 points and at most 2 turnovers"
    )
