"""Parser equivalence-group tests.

This module proves that semantically identical surface forms (full
question, search phrase, compressed shorthand) produce the same parse
state. It is the execution surface for the equivalence groups defined in
``docs/architecture/parser/examples.md`` §7 and drives Phase A of the
parser/query-surface expansion plan.

Subsequent Phase A work queue items will extend this file (or sibling
modules using the same helper) as each equivalence group reaches parity.
The helper's failure message surfaces the diverging keys, so regressions
point straight at the slot that broke.
"""

import pytest

from tests._parser_equivalence import assert_parse_equivalence

pytestmark = pytest.mark.parser


def test_leaderboard_points_leaders_last_10_games():
    """examples.md §7.1 — full group now at parity.

    All six surface forms (question, search-phrase, and `scoring`/`scorers`
    compressed shorthand) produce identical canonical parse states after
    Phase A work queue item 3.
    """
    reference = assert_parse_equivalence(
        [
            "Who has the most points in the last 10 games?",
            "most points last 10 games",
            "points leaders last 10",
            "last 10 scoring leaders",
            "top scorers last 10 games",
            "highest scorers last 10",
        ]
    )

    assert reference["route"] == "season_leaders"
    assert reference["stat"] == "pts"
    assert reference["last_n"] == 10
    assert reference["leaderboard_intent"] is True


def test_leaderboard_points_per_game_this_season():
    """examples.md §3.1 #1 — `leads the NBA in ...` question form."""
    reference = assert_parse_equivalence(
        [
            "Who leads the NBA in points per game this season?",
            "points per game leaders this season",
        ]
    )
    assert reference["stat"] == "pts"
    assert reference["leaderboard_intent"] is True


def test_leaderboard_true_shooting_this_season():
    """examples.md §3.1 #3 — advanced-stat leaderboard parity."""
    reference = assert_parse_equivalence(
        [
            "Who has the highest true shooting percentage this season?",
            "best true shooting percentage this season",
        ]
    )
    assert reference["stat"] == "ts_pct"
    assert reference["leaderboard_intent"] is True


def test_team_leaderboard_best_offensive_rating():
    """examples.md §3.1 #4 — team leaderboard parity."""
    reference = assert_parse_equivalence(
        [
            "Which team has the best offensive rating this year?",
            "best offensive rating team this year",
        ]
    )
    assert reference["stat"] == "off_rating"
    assert reference["team_leaderboard_intent"] is True
