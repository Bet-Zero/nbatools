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
    """examples.md §7.1 — currently-passing subset.

    The full §7.1 group lists six surface forms. The three covered here
    already parse identically; the remaining forms (`last 10 scoring
    leaders`, `top scorers last 10 games`, `highest scorers last 10`) are
    Phase A work queue item 3's scope — they will be added to this
    assertion once leaderboard phrasing parity lands.
    """
    reference = assert_parse_equivalence(
        [
            "Who has the most points in the last 10 games?",
            "most points last 10 games",
            "points leaders last 10",
        ]
    )

    # Sanity-check a few key slots so regressions in the reference form
    # itself don't silently pass (equivalence alone would be satisfied by
    # all three forms breaking the same way).
    assert reference["route"] == "season_leaders"
    assert reference["stat"] == "pts"
    assert reference["last_n"] == 10
    assert reference["leaderboard_intent"] is True
