"""Operator words inside a stat-condition list.

"LeBron games with 30 points and 10 or more assists" refused: the condition
list reader needed the stat noun right after the number, so the "N or more
stat" clause matched nothing and a two-condition question fell back to one
condition. "more than 10 assists" had the opposite problem - it was read as a
bare number and counted games with exactly 10. Expected values are counted
from the fixture.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _rows(query: str) -> list[dict]:
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    sections = result.result.to_dict()["sections"]
    return sections.get("finder") or sections.get("summary") or []


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("LeBron James games with 30 points and 10 or more assists", 2),
        ("LeBron James games with 20 points and 10 or more assists", 4),
        ("LeBron James 30 point games with 10 or more assists", 2),
        ("LeBron James games with 20 points and 10 or more assists and 5 or more rebounds", 2),
        ("Lakers games with 120 points and 15 or more threes", 7),
    ],
)
def test_or_more_clause_keeps_every_condition(query, expected):
    assert len(_rows(query)) == expected


@pytest.mark.parametrize(
    ("operator_form", "canonical_form"),
    [
        (
            "LeBron James games with 30 points and 10 or more assists",
            "LeBron James games with 30 points and at least 10 assists",
        ),
        (
            "LeBron James games with 20 points and 10 or more assists",
            "LeBron James games with 20 points and at least 10 assists",
        ),
        (
            "Nikola Jokic games with 25 points and 12 or more rebounds",
            "Nikola Jokic games with 25 points and at least 12 rebounds",
        ),
        (
            "Lakers games with 120 points and 15 or more threes",
            "Lakers games with 120 points and at least 15 threes",
        ),
    ],
)
def test_or_more_matches_at_least(operator_form, canonical_form):
    # "10 or more assists" and "at least 10 assists" are the same bound.
    assert _rows(operator_form) == _rows(canonical_form)


def test_record_in_a_sample_with_an_or_more_clause():
    summary = _rows("Lakers record in games with 120 points and 15 or more threes")[0]
    assert (summary["wins"], summary["losses"]) == (7, 0)


def test_more_than_is_a_strict_floor():
    # "more than 10 assists" excludes the 10-assist games "at least 10" keeps.
    assert len(_rows("LeBron James games with more than 10 assists")) == 1
    assert len(_rows("LeBron James games with at least 10 assists")) == 6
    assert _rows("LeBron James games with more than 10 assists") == _rows(
        "LeBron James games with over 10 assists"
    )


@pytest.mark.parametrize(
    "query",
    [
        # Not a stat the box score carries: the clause must not be dropped.
        "LeBron James games with 30 points and 10 or more days rest",
        "LeBron James games with 30 points and 10 or more minutes",
    ],
)
def test_unreadable_or_more_clause_still_refuses(query):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        # "no more than" contains "more than" but is a ceiling, alone or in a list.
        ("LeBron James games with no more than 2 turnovers", 22),
        ("Lakers games with no more than 10 turnovers", 7),
        ("LeBron James games with 30 points and no more than 5 turnovers", 11),
        ("LeBron James games with 30 points and no more than 2 turnovers", 5),
        ("Lakers games with 120 points and no more than 10 turnovers", 3),
        ("LeBron James games with 10 or more assists and no more than 2 turnovers", 4),
    ],
)
def test_no_more_than_stays_a_ceiling(query, expected):
    assert len(_rows(query)) == expected


def test_not_more_than_is_a_ceiling():
    assert _rows("LeBron James games with not more than 2 turnovers") == _rows(
        "LeBron James games with no more than 2 turnovers"
    )
