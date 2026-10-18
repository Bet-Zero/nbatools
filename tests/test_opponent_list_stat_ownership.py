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
def test_named_opponent_condition_keeps_the_base_union(subject):
    query = f"{subject} against Celtics and Wizards when Celtics score at least 120 in 2023-24"
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert kwargs["opponent"] == ["BOS", "WAS"]
    assert kwargs["stat"] == "opponent_pts"
    assert kwargs["conditions"] == [
        {"stat": "opponent_pts", "min_value": 120, "max_value": None, "opponent_team": "BOS"}
    ]
    assert not kwargs.get("unsupported_filters")
    meta = execute_natural_query(query).metadata
    assert meta["opponents"] == ["BOS", "WAS"]
    assert meta["threshold_conditions"] == meta["conditions"]
    assert any(item["label"] == "BOS OPP PTS min" for item in meta["applied_filters"])


def test_condition_owner_survives_normalization_and_deduplication():
    import pandas as pd

    from nbatools.commands._condition_utils import (
        apply_stat_conditions,
        normalize_stat_conditions,
        stat_conditions_cover,
    )

    generic = {"stat": "opponent_pts", "min_value": 110, "max_value": None}
    boston = {**generic, "opponent_team": "BOS"}
    washington = {**generic, "opponent_team": "WAS"}
    assert normalize_stat_conditions([generic, boston, washington, boston]) == [
        generic,
        boston,
        washington,
    ]
    assert not stat_conditions_cover([generic], [boston])
    rows = pd.DataFrame(
        {"opponent_pts": [126, 131, 105], "opponent_team_abbr": ["BOS", "WAS", "BOS"]}
    )
    allowed = {"opponent_pts": "opponent_pts"}
    assert apply_stat_conditions(rows, [generic], allowed).index.tolist() == [0, 1]
    assert apply_stat_conditions(rows, [boston], allowed).index.tolist() == [0]
    assert apply_stat_conditions(rows, [boston, washington], allowed).empty
    assert apply_stat_conditions(rows.drop(columns="opponent_team_abbr"), [boston], allowed).empty


@pytest.mark.parametrize(
    "condition",
    [
        "when Celtics score at least 110 or Wizards score at least 125",
        "when Celtics score at least 110 and (at least 110 points or at least 50 rebounds)",
    ],
)
def test_unfinished_owned_boolean_composition_does_not_discard_the_owner(condition):
    result = execute_natural_query(
        f"Lakers games against Celtics and Wizards {condition} in 2023-24"
    )
    assert result.result_status == "no_result"
    assert result.result_reason in {"unsupported", "filter_not_supported"}


def test_extra_condition_preparation_preserves_an_existing_owner():
    from nbatools.commands._natural_query_execution import _prepare_route_conditions

    owned = {"stat": "opponent_pts", "min_value": 110, "max_value": None, "opponent_team": "BOS"}
    extra = {"stat": "reb", "min_value": 40, "max_value": None}
    kwargs, remaining = _prepare_route_conditions("game_finder", {"conditions": [owned]}, [extra])
    assert kwargs["conditions"] == [owned, extra]
    assert remaining == []
