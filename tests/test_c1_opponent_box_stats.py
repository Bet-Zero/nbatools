"""Opponent box-score filters on team records, finders, summaries and compares.

"Lakers record when they allow 15 or more threes" filters the opponent's threes
(it filtered the Lakers' own). Expected values are counted from the fixture by
joining each game's other team row.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def _summary(result) -> tuple[int, int, int]:
    row = result.result.to_dict()["sections"]["summary"][0]
    return row["games"], row["wins"], row["losses"]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Lakers record when they allow 15 or more threes", (24, 17, 7)),
        ("Lakers record when giving up 15+ threes", (24, 17, 7)),
        ("Lakers record when they allow 45 or more rebounds", (5, 3, 2)),
        ("Lakers record when opponents had 20 or more turnovers", (5, 5, 0)),
        ("Lakers record when they held opponents to under 40 rebounds", (46, 38, 8)),
        ("Lakers record when scoring 120 and allowing 15 or more threes", (6, 5, 1)),
        # The team's own threes are unchanged.
        ("Lakers record when they make 15 or more threes", (20, 18, 2)),
    ],
)
def test_team_record_opponent_box_stats(query, expected):
    result = _run(query)
    assert result.route == "team_record"
    assert _summary(result) == expected


def test_finder_count_and_headline():
    result = _run("how many games did the Lakers allow 15 or more threes")
    assert result.result.to_dict()["sections"]["count"][0]["count"] == 24
    assert "24 games with 15+ opponent threes" in result.metadata["count_phrase"]


def test_summary_and_compare():
    assert _summary(_run("Lakers summary when opponents made 15 or more threes")) == (24, 17, 7)
    result = _run("compare Lakers and Celtics when allowing 15 or more threes")
    rows = {
        row["team_name"]: (row["games"], row["wins"])
        for row in result.result.to_dict()["sections"]["summary"]
    }
    assert rows["LAL"] == (24, 17)
    assert rows["BOS"] == (19, 14)
