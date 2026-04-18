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


def test_summary_player_vs_teams_this_season():
    """examples.md §3.5 #24 — summary parity for `how has X played` Q form
    and the search-form shorthand with no specific finder signal.

    `Tatum vs winning teams this season` has no resolved opponent (phrase
    is not a known team), so the `<player> + <timeframe>` summary default
    fires just like the Q form's `how has X played` verb-phrase trigger.
    """
    reference = assert_parse_equivalence(
        [
            "How has Jayson Tatum played against winning teams this season?",
            "Tatum vs winning teams this season",
        ],
        # summary_intent differs (Q=True via verb phrase, S=False via
        # timeframe-default rule) but both reach player_game_summary.
        # notes also differs (Q emits stat-sampling note).
        exclude_keys={
            "normalized_query",
            "confidence",
            "alternates",
            "intent",
            "notes",
            "summary_intent",
        },
    )
    assert reference["route"] == "player_game_summary"
    assert reference["player"] == "Jayson Tatum"


def test_summary_team_when_player_out():
    """examples.md §3.6 #26 — `How do the Xs perform when Y out` verb phrase
    reaches summary and the shorthand `Xs when Y out` now defaults to
    summary via the player-plus-timeframe rule.
    """
    reference = assert_parse_equivalence(
        [
            "How do the Suns perform when Devin Booker didn't play?",
            "Suns when Booker out",
        ],
        exclude_keys={
            "normalized_query",
            "confidence",
            "alternates",
            "intent",
            "notes",
            "summary_intent",
        },
    )
    assert reference["route"] == "player_game_summary"


def test_summary_player_when_other_player_out_this_season():
    """examples.md §3.6 #30 — route parity verified.

    Both forms now route to ``player_game_summary``, but full canonical
    equivalence is blocked by the §6 entity-resolution anomaly (Q side
    resolves ``team='WAS'``). Only the route and core player slot are
    asserted here; the full equivalence test will land once the entity
    bug is fixed.
    """
    from nbatools.commands.natural_query import parse_query

    q = parse_query("How has Tyrese Maxey played when Joel Embiid was out this season?")
    s = parse_query("Maxey when Embiid out this season")
    assert q["route"] == "player_game_summary"
    assert s["route"] == "player_game_summary"
    assert q["player"] == s["player"]


def test_summary_shorthand_jokic_last_10():
    """parser/specification.md §15.3 worked example — `Jokic last 10`
    shorthand now routes to summary (the previously-documented default
    target). Locks in the player-plus-timeframe rule.
    """
    reference = assert_parse_equivalence(
        [
            "Jokic last 10",
            "Jokic last 10 games",
        ]
    )
    assert reference["route"] == "player_game_summary"
    assert reference["last_n"] == 10


def test_record_when_player_scores_35_or_more():
    """examples.md §3.9 #41 — record query with `N or more` threshold.

    Both `35 or more` (Q) and `35+` (S) now extract min_value=35
    and `scores` resolves to stat=pts via verbal-form alias.
    """
    reference = assert_parse_equivalence(
        [
            "What's the Mavericks' record when Luka Dončić scores 35 or more?",
            "Mavericks record when Luka scores 35+",
        ],
        exclude_keys={
            "normalized_query",
            "confidence",
            "alternates",
            "intent",
            "notes",
            "summary_intent",
        },
    )
    assert reference["route"] == "player_game_summary"
    assert reference["stat"] == "pts"
    assert reference["min_value"] == 35.0


def test_record_when_player_makes_6_threes():
    """examples.md §3.9 #44 — record query with `at least N threes`
    vs `6+ threes`. Both extract stat=fg3m, min_value=6.

    `threshold_conditions` differs (Q extracts via threshold-conditions
    pipeline, S via extract_min_value), but core slots agree.
    """
    reference = assert_parse_equivalence(
        [
            "What is the Warriors' record when Stephen Curry makes at least 6 threes?",
            "Warriors record when Curry makes 6+ threes",
        ],
        exclude_keys={
            "normalized_query",
            "confidence",
            "alternates",
            "intent",
            "notes",
            "summary_intent",
            "threshold_conditions",
            "extra_conditions",
            "leaderboard_intent",
        },
    )
    assert reference["route"] == "player_game_summary"
    assert reference["stat"] == "fg3m"
    assert reference["min_value"] == 6.0
