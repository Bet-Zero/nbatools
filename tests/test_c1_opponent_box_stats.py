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


@pytest.mark.parametrize(
    "text",
    [
        "held opponents to 40% shooting",
        "held opponents to 40 percent shooting",
        "held opponents to 35 field goals",
        "held opponents to 10 threes",
    ],
)
def test_held_to_count_is_not_points_before_another_word(text):
    from nbatools.commands._parse_helpers import extract_opponent_points_allowed_conditions

    stats = [c["stat"] for c in extract_opponent_points_allowed_conditions(text)]
    assert "opponent_pts" not in stats


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        # Later list items share the opponent subject and, when bare, its bound.
        ("Lakers record when they held teams to 10 threes and 100 points", (16, 16, 0)),
        ("Lakers record when they gave up 15 threes and 50 rebounds", (3, 2, 1)),
        ("Lakers record when opponents had 15 threes and 30 assists", (1, 0, 1)),
        ("Lakers record when they allow 15+ threes and 120+ points", (4, 0, 4)),
        ("Lakers record when they held opponents under 100 points and 40 rebounds", (34, 33, 1)),
        # A verb starts the team's own clause.
        ("Lakers record when they allowed 15 threes and scored 120", (6, 5, 1)),
    ],
)
def test_opponent_subject_carries_through_list(query, expected):
    assert _summary(_run(query)) == expected


@pytest.mark.parametrize(
    ("query", "condition", "length"),
    [
        # Points allowed on a team streak read the opponent's score (the
        # Lakers' own 100+ points gave 16).
        ("Lakers streak of games holding opponents to 100 points", "opponent_pts<=100", 8),
        ("Lakers streak of games holding opponents under 100 points", "opponent_pts<100", 8),
        (
            "Lakers longest win streak when allowing 110 or more points",
            "wins and opponent_pts>=110",
            2,
        ),
    ],
)
def test_team_streak_points_allowed(query, condition, length):
    row = _run(query).result.to_dict()["sections"]["streak"][0]
    assert row["condition"] == condition
    assert row["streak_length"] == length


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        # "shot" stays attempts for later items; "N or more" may precede the stat.
        ("Lakers record when opponents shot 40+ threes and 20 free throws", (1, 1, 0)),
        ("Lakers record when they gave up 15 threes and 45 or more rebounds", (4, 2, 2)),
        ("Lakers record when they gave up 15 threes and 15 or more turnovers", (10, 8, 2)),
        # A count after the opponent no longer swaps the subject team.
        ("Lakers record vs Celtics when opponents made 15+ threes", (5, 1, 4)),
        ("Lakers record vs Celtics when they have 15+ threes", (3, 1, 2)),
    ],
)
def test_more_opponent_lists_and_matchups(query, expected):
    result = _run(query)
    assert result.result.to_dict()["sections"]["summary"][0]["team_name"].endswith("Lakers")
    assert _summary(result) == expected


def test_record_leaderboard_applies_conditions():
    # Boston's 14-5 when opponents made 15+ threes beats the Lakers' 17-7; the
    # overall standings put the Lakers (47-13) first.
    rows = _run("which team has the best record when opponents made 15+ threes").result.to_dict()[
        "sections"
    ]["leaderboard"]
    assert [(r["team_abbr"], r["wins"], r["losses"]) for r in rows[:2]] == [
        ("BOS", 14, 5),
        ("LAL", 17, 7),
    ]
    rows = _run("best record when allowing 110 or more points").result.to_dict()["sections"][
        "leaderboard"
    ]
    assert (rows[0]["team_abbr"], rows[0]["wins"], rows[0]["losses"]) == ("LAL", 3, 9)
