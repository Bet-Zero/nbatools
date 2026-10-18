"""Resolve list scope before interpreting who owns a scoring condition."""

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


@pytest.mark.parametrize(
    "opponents", ["Celtics and Wizards", "Wizards and Celtics", "Celtics and Knicks"]
)
def test_team_scoring_condition_keeps_its_owner_after_a_list(opponents):
    query = (
        f"LeBron James game summary against {opponents} when Lakers score at least 120 in 2023-24"
    )
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert kwargs["team"] == "LAL"
    assert kwargs["stat"] == "team_pts"
    assert kwargs["min_value"] == 120
    assert kwargs["conditions"] == [{"stat": "team_pts", "min_value": 120, "max_value": None}]
    assert not kwargs.get("unsupported_filters")
    meta = execute_natural_query(query).metadata
    assert meta["stat"] == "team_pts"
    assert meta["min_value"] == 120
    assert not any(item["label"] == "pts min" for item in meta["applied_filters"])


def test_independent_player_bound_is_not_replaced_by_the_team_bound():
    query = "LeBron James games with at least 30 points against Celtics and Wizards when Lakers score at least 120 in 2023-24"
    kwargs = parse_query(query)["route_kwargs"]
    conditions = {c["stat"]: c for c in kwargs["conditions"]}
    assert conditions["pts"]["min_value"] == 30
    assert conditions["team_pts"]["min_value"] == 120


@pytest.mark.parametrize(
    "subject", ["Lakers record", "LeBron James game summary", "Lakers LeBron James game summary"]
)
def test_named_opponent_condition_narrows_the_union(subject):
    query = f"{subject} against Celtics and Wizards when Celtics score at least 120 in 2023-24"
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert kwargs["opponent"] == ["BOS"]
    assert kwargs["stat"] == "opponent_pts"
    assert not kwargs.get("unsupported_filters")
    meta = execute_natural_query(query).metadata
    assert meta["opponents"] == ["BOS"]
    assert meta["threshold_conditions"] == meta["conditions"]
