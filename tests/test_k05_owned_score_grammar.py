"""Score clauses retain ownership even when both sides use the same value."""

import pytest

from nbatools.commands._parse_helpers import (
    detect_home_away,
    extract_opponent_points_allowed_conditions,
)
from nbatools.commands._player_game_context import team_subject_stat_conditions
from nbatools.commands.natural_query import _build_parse_state


@pytest.mark.parametrize(
    "venue,expected",
    [
        ("away from home", (False, True)),
        ("at home", (True, False)),
        ("on the road", (False, True)),
        ("home and away", (True, True)),
    ],
)
def test_venue_phrase(venue, expected):
    assert detect_home_away(venue) == expected


@pytest.mark.parametrize("subject", ["opponents", "the opposing team", "the other team"])
@pytest.mark.parametrize("verb", ["stayed", "finished"])
def test_explicit_opponent_ceiling(subject, verb):
    conditions = extract_opponent_points_allowed_conditions(f"{subject} {verb} below 110 points")
    assert len(conditions) == 1
    assert conditions[0]["stat"] == "opponent_pts"
    assert conditions[0]["max_value"] == pytest.approx(109.9999)


@pytest.mark.parametrize("suffix", ["percent shooting", "%", "rebounds", "assists"])
def test_non_points_not_inferred_as_score(suffix):
    assert not extract_opponent_points_allowed_conditions(f"opponents stayed below 40 {suffix}")


def test_same_number_different_owners():
    state = _build_parse_state(
        "lakers home record where lakers reached 110 points but opponents stayed below 110"
    )
    conditions = state["threshold_conditions"]
    assert {(c["stat"], c["min_value"], c["max_value"]) for c in conditions} == {
        ("pts", 110.0, None),
        ("opponent_pts", None, 109.9999),
    }


def test_opponent_reached_retains_owner():
    state = _build_parse_state("lakers record when opponents reached 110 points")
    assert {c["stat"] for c in state["threshold_conditions"]} == {"opponent_pts"}


def test_team_reached_on_player_request_retains_owner():
    conditions = team_subject_stat_conditions("lebron averages when the lakers reached 110 points")
    assert len(conditions) == 1
    assert conditions[0]["team"] == "LAL"
    assert conditions[0]["stat"] == "pts"
    assert conditions[0]["min_value"] == 110


@pytest.mark.parametrize("subject,stat", [("they", "pts"), ("opponents", "opponent_pts")])
def test_negated_reach_is_a_strict_ceiling(subject, stat):
    state = _build_parse_state(f"lakers record in 2023-24 when {subject} did not reach 110 points")
    assert {(c["stat"], c["min_value"], c["max_value"]) for c in state["threshold_conditions"]} == {
        (stat, None, 109.9999)
    }


def test_team_negated_reach_retains_owner():
    conditions = team_subject_stat_conditions(
        "lebron averages when the lakers did not reach 110 points"
    )
    assert len(conditions) == 1
    assert conditions[0]["team"] == "LAL"
    assert conditions[0]["min_value"] is None
    assert conditions[0]["max_value"] == 109.9999
