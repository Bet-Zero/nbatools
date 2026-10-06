"""Adjective game lists with a second condition.

"LeBron 30 point games with 10 assists" refused, and "Lakers record in 120
point games with 15+ threes" read "with 120 points" as a teammate. The
adjective form now reads as the condition list "games with 30 points and 10
assists". Expected values are counted from the fixture.
"""

from __future__ import annotations

import pytest

from nbatools.commands._parse_helpers import canonicalize_sample_phrases

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("lebron 30 point games with 10 assists", "lebron games with 30 points and 10 assists"),
        ("lakers 120 point games with 15+ threes", "lakers games with 120 points and 15+ threes"),
        (
            "lebron 30 point games with at least 8 assists",
            "lebron games with 30 points and at least 8 assists",
        ),
        (
            "lebron 30 point games where he had 10 rebounds",
            "lebron games with 30 points and 10 rebounds",
        ),
        # A teammate stays a teammate.
        ("lebron 30 point games with anthony davis", "lebron 30 point games with anthony davis"),
    ],
)
def test_adjective_games_with_rewrite(text, expected):
    assert canonicalize_sample_phrases(text) == expected


@pytest.mark.parametrize(
    ("query", "rows"),
    [
        ("LeBron 30 point games with 10 assists", 2),
        ("LeBron 30 point games with at least 8 assists", 6),
        ("LeBron 30 point games where he had 10 rebounds", 2),
        ("Lakers 120 point games with 15+ threes", 7),
    ],
)
def test_adjective_games_with_rows(query, rows):
    assert len(_run(query).result.to_dict()["sections"]["finder"]) == rows


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Lakers record in 120 point games with 15+ threes", (7, 7, 0)),
        ("Lakers record in games with 120 points and 15 threes", (7, 7, 0)),
        ("Lakers record with 120 points", (19, 18, 1)),
    ],
)
def test_record_with_a_count_is_a_condition(query, expected):
    row = _run(query).result.to_dict()["sections"]["summary"][0]
    assert (row["games"], row["wins"], row["losses"]) == expected
