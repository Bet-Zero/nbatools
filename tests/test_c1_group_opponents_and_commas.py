"""Opponent groups written as "... opponents", and a comma after "vs <team>".

- "vs winning / good / above .500 / losing / below .500 / Western / Eastern
  opponents" and "vs Western teams" were ignored and answered with every
  game.
- "Lakers record vs Celtics, at home" answered Boston's whole record.
- "vs ranked opponents" and "vs LA opponents" answered with every game.

Expected values are counted with pandas from the fixture.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _result(query: str):
    from nbatools.query_service import execute_natural_query

    return execute_natural_query(query)


def _record(query: str) -> tuple[int, int]:
    result = _result(query)
    assert result.result_status == "ok", (query, result.metadata)
    summary = result.result.to_dict()["sections"]["summary"][0]
    return summary["wins"], summary["losses"]


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record vs winning opponents", (11, 13)),
        ("Lakers record vs good opponents", (11, 13)),
        ("Lakers record vs above .500 opponents", (11, 13)),
        ("Lakers record vs below .500 opponents", (36, 0)),
        ("Lakers record vs losing opponents", (36, 0)),
        ("Lakers record against Western opponents", (24, 0)),
        ("Lakers record vs Western teams", (24, 0)),
        ("Lakers record vs Eastern teams", (23, 13)),
        ("LeBron James games vs winning opponents", (11, 13)),
        ("Lakers record vs Celtics, at home", (3, 3)),
        ("Lakers record vs Celtics, this season", (4, 8)),
        ("Lakers record vs the Celtics, on the road", (1, 5)),
    ],
)
def test_group_and_comma_records(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record vs ranked opponents",
        "Lakers record vs LA opponents",
    ],
)
def test_unread_groups_refuse(query):
    assert _result(query).result_status == "no_result"
