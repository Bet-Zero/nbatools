"""Negated stat bounds read the right way round.

"no fewer than 10 assists" is a floor and "not over 2 turnovers" a ceiling,
but the plain operator inside each ("fewer than", "over") was matched on its
own, so both answered the opposite question. "Lakers record in games with no
more than 10 turnovers" also refused: "no more than 10 turnovers" was read as
"no <player>". Expected values are counted from the fixture.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _result(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]


def _rows(query: str) -> list[dict]:
    return _result(query)["finder"]


@pytest.mark.parametrize(
    ("negated", "plain"),
    [
        (
            "LeBron James games with no fewer than 10 assists",
            "LeBron James games with at least 10 assists",
        ),
        (
            "LeBron James games with not less than 10 assists",
            "LeBron James games with at least 10 assists",
        ),
        (
            "LeBron James games with no greater than 2 turnovers",
            "LeBron James games with at most 2 turnovers",
        ),
        (
            "LeBron James games with not over 2 turnovers",
            "LeBron James games with at most 2 turnovers",
        ),
        (
            "LeBron James games with 30 points and no fewer than 10 assists",
            "LeBron James games with 30 points and at least 10 assists",
        ),
        (
            "LeBron James games with 30 points and not over 2 turnovers",
            "LeBron James games with 30 points and at most 2 turnovers",
        ),
        (
            "Lakers games with 120 points and no fewer than 15 threes",
            "Lakers games with 120 points and at least 15 threes",
        ),
    ],
)
def test_negated_bound_matches_its_plain_form(negated, plain):
    assert _rows(negated) == _rows(plain)


def test_negated_bound_counts():
    assert len(_rows("LeBron James games with no fewer than 10 assists")) == 6
    assert len(_rows("LeBron James games with not over 2 turnovers")) == 22
    assert len(_rows("LeBron James games with 30 points and not over 2 turnovers")) == 5


def test_plain_operators_keep_their_reading():
    assert len(_rows("LeBron James games with fewer than 3 turnovers")) == 22
    assert len(_rows("LeBron James games with over 10 assists")) == 1


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record in games with no more than 10 turnovers", (5, 2)),
        ("Lakers record in games with 120 points and no more than 10 turnovers", (3, 0)),
        ("Lakers record in games with 120 points and not more than 10 turnovers", (3, 0)),
        ("Lakers record in games with no fewer than 15 threes", (18, 2)),
    ],
)
def test_team_record_reads_negated_bound_as_a_stat(query, record):
    summary = _result(query)["summary"][0]
    assert (summary["wins"], summary["losses"]) == record
