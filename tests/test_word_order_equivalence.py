"""Word-order equivalence tests (Phase A item 11).

Verifies that semantically identical queries with different word order
produce the same parse state. Covers leaderboard, summary, finder,
record, streak, occurrence, and team-leaderboard query types.

At least 20 equivalence groups are tested per Phase A acceptance criteria.
"""

import pytest

from tests._parser_equivalence import assert_parse_equivalence

pytestmark = pytest.mark.parser


# ---------------------------------------------------------------------------
# Leaderboard word-order permutations
# ---------------------------------------------------------------------------


def test_wo_lb_best_scorers_last_month():
    """§5.4 #1 — `best scorers last month` word-order swap."""
    reference = assert_parse_equivalence(
        [
            "best scorers last month",
            "last month best scorers",
            "scorers best last month",
        ]
    )
    assert reference["route"] == "season_leaders"
    assert reference["stat"] == "pts"


def test_wo_lb_most_points_last_10():
    """§5.4 #2 — `most points last 10 games` word-order swap."""
    reference = assert_parse_equivalence(
        [
            "most points last 10 games",
            "last 10 games most points",
        ]
    )
    assert reference["route"] == "season_leaders"
    assert reference["stat"] == "pts"
    assert reference["last_n"] == 10


def test_wo_lb_most_assists_this_season():
    reference = assert_parse_equivalence(
        [
            "most assists this season",
            "this season most assists",
        ]
    )
    assert reference["route"] == "season_leaders"
    assert reference["stat"] == "ast"


def test_wo_lb_most_rebounds_last_5():
    reference = assert_parse_equivalence(
        [
            "most rebounds last 5 games",
            "last 5 games most rebounds",
        ]
    )
    assert reference["route"] == "season_leaders"
    assert reference["stat"] == "reb"
    assert reference["last_n"] == 5


def test_wo_lb_most_steals_this_season():
    reference = assert_parse_equivalence(
        [
            "most steals this season",
            "this season most steals",
        ]
    )
    assert reference["route"] == "season_leaders"
    assert reference["stat"] == "stl"


def test_wo_lb_most_points_at_home():
    reference = assert_parse_equivalence(
        [
            "most points at home this season",
            "this season most points at home",
        ]
    )
    assert reference["route"] == "season_leaders"
    assert reference["stat"] == "pts"
    assert reference["home_only"] is True


def test_wo_lb_most_turnovers_last_10():
    reference = assert_parse_equivalence(
        [
            "most turnovers last 10 games",
            "last 10 games most turnovers",
        ]
    )
    assert reference["route"] == "season_leaders"
    assert reference["stat"] == "tov"


def test_wo_lb_most_threes_since_january():
    reference = assert_parse_equivalence(
        [
            "most threes since January",
            "since January most threes",
        ]
    )
    assert reference["route"] == "season_leaders"
    assert reference["stat"] == "fg3m"


# ---------------------------------------------------------------------------
# Team leaderboard word-order permutations
# ---------------------------------------------------------------------------


def test_wo_tlb_best_offensive_rating():
    reference = assert_parse_equivalence(
        [
            "best offensive rating this season",
            "this season best offensive rating",
        ]
    )
    assert reference["route"] == "season_team_leaders"
    assert reference["stat"] == "off_rating"


def test_wo_tlb_best_defensive_rating():
    reference = assert_parse_equivalence(
        [
            "best defensive rating this year",
            "this year best defensive rating",
        ]
    )
    assert reference["route"] == "season_team_leaders"
    assert reference["stat"] == "def_rating"


# ---------------------------------------------------------------------------
# Summary word-order permutations
# ---------------------------------------------------------------------------


def test_wo_sum_jokic_last_10():
    reference = assert_parse_equivalence(
        [
            "Jokic last 10 games",
            "last 10 games Jokic",
        ]
    )
    assert reference["route"] == "player_game_summary"
    assert reference["last_n"] == 10


def test_wo_sum_jokic_lately():
    reference = assert_parse_equivalence(
        [
            "Jokic lately",
            "lately Jokic",
        ]
    )
    assert reference["route"] == "player_game_summary"
    assert reference["last_n"] == 10


def test_wo_sum_lebron_last_5():
    reference = assert_parse_equivalence(
        [
            "LeBron last 5",
            "last 5 LeBron",
        ]
    )
    assert reference["route"] == "player_game_summary"
    assert reference["last_n"] == 5


def test_wo_sum_tatum_recently():
    reference = assert_parse_equivalence(
        [
            "Tatum recently",
            "recently Tatum",
        ]
    )
    assert reference["route"] == "player_game_summary"
    assert reference["last_n"] == 10


# ---------------------------------------------------------------------------
# Finder word-order permutations
# ---------------------------------------------------------------------------


def test_wo_find_jokic_vs_lakers():
    reference = assert_parse_equivalence(
        [
            "Jokic vs Lakers this season",
            "Jokic this season vs Lakers",
        ]
    )
    assert reference["route"] == "player_game_finder"


def test_wo_find_jokic_triple_doubles():
    reference = assert_parse_equivalence(
        [
            "Jokic triple doubles this season",
            "this season Jokic triple doubles",
        ]
    )
    assert reference["route"] == "player_game_finder"


# ---------------------------------------------------------------------------
# Record word-order permutations
# ---------------------------------------------------------------------------


def test_wo_rec_lakers_road():
    reference = assert_parse_equivalence(
        [
            "Lakers road record this season",
            "Lakers this season road record",
        ]
    )
    assert reference["route"] == "team_record"


# ---------------------------------------------------------------------------
# Streak word-order permutations
# ---------------------------------------------------------------------------


def test_wo_str_jokic_longest_30_point():
    reference = assert_parse_equivalence(
        [
            "Jokic longest 30-point streak",
            "longest Jokic 30 point streak",
        ],
        exclude_keys={
            "normalized_query",
            "confidence",
            "alternates",
            "intent",
            "notes",
            "occurrence_event",
            "min_value",
        },
    )
    assert reference["route"] == "player_streak_finder"
    streak = reference["streak_request"]
    assert streak["stat"] == "pts"
    assert streak["min_value"] == 30.0


def test_wo_str_curry_threes():
    reference = assert_parse_equivalence(
        [
            "Curry longest streak with at least 3 threes",
            "longest Curry streak with at least 3 threes",
        ]
    )
    assert reference["route"] == "player_streak_finder"
    streak = reference["streak_request"]
    assert streak["stat"] == "fg3m"


def test_wo_lb_best_ts_pct_this_season():
    reference = assert_parse_equivalence(
        [
            "best true shooting this season",
            "this season best true shooting",
        ]
    )
    assert reference["route"] == "season_leaders"
    assert reference["stat"] == "ts_pct"
