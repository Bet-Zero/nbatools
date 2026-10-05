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
        # Other spellings of the same bounds.
        ("Lakers record when opponents made 15 3s", (24, 17, 7)),
        ("Lakers record when they allow 45 rebounds or more", (5, 3, 2)),
        ("Lakers record when they allow 45 rebounds or fewer", (56, 44, 12)),
        ("Lakers record when they allowed 15+ 3-pointers", (24, 17, 7)),
        ("Lakers record when opponents hit 15+ three pointers", (24, 17, 7)),
        ("Lakers record when opponents made 15 or fewer threes", (42, 34, 8)),
        ("Lakers record when they held opponents under 40 rebounds", (46, 38, 8)),
        # A bare count after a holding verb is a ceiling.
        ("Lakers record when they held opponents to 10 threes", (22, 19, 3)),
        ("Lakers record when they limited opponents to 10 threes", (22, 19, 3)),
        ("Lakers record when they held opponents to 40 rebounds", (49, 41, 8)),
        ("Lakers record when they held opponents to 100 points", (43, 41, 2)),
        # "shot" counts attempts.
        ("Lakers record when opponents shot 15+ free throws", (57, 45, 12)),
        ("Lakers record when opponents shot 40+ threes", (1, 1, 0)),
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


def test_team_streak_reads_opponent_stat():
    # The streak runs on the opponent's threes (the Lakers' own threes give 6).
    row = _run("Lakers streak of games allowing 15+ threes").result.to_dict()["sections"]["streak"][
        0
    ]
    assert row["condition"] == "opponent_fg3m>=15"
    assert row["streak_length"] == 5


def test_team_win_streak_keeps_opponent_condition():
    # Every game of the run is a win where the opponent made 15+ threes; the
    # plain win streak is 13.
    row = _run("Lakers longest win streak when opponents made 15+ threes").result.to_dict()[
        "sections"
    ]["streak"][0]
    assert row["condition"] == "wins and opponent_fg3m>=15"
    assert row["streak_length"] == 3
