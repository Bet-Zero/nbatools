"""An occurrence's per-game threshold keeps its own statistical basis."""

import copy

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import _build_applied_filters, _build_query_metadata


@pytest.mark.parametrize(
    "query,stat,counter,bound",
    [
        ("Who has the most 30 point games in 2025-26?", "pts", "games_30p", 30),
        ("Who has the most 30-point games in 2025-26?", "pts", "games_30p", 30),
        ("Who has the most 40 point games in 2025-26?", "pts", "games_40p", 40),
        ("Who has the most 10 rebound games in 2025-26?", "reb", "games_10r", 10),
        ("Who has the most 10 assist games in 2025-26?", "ast", "games_10a", 10),
    ],
)
def test_natural_counter_metric_does_not_own_the_event_threshold(query, stat, counter, bound):
    parsed = parse_query(query)
    original = copy.deepcopy(parsed)
    meta = _build_query_metadata(parsed, query, grouped_boolean_used=False)
    assert meta["stat"] == parsed["route_kwargs"]["stat"] == counter
    assert meta["applied_filters"] == [
        {"label": stat + " min", "value": f"{bound}.0", "kind": "threshold"}
    ]
    assert parsed == original


@pytest.mark.parametrize(
    "event,label,value",
    [
        ({"stat": "reb", "min_value": 10}, "reb min", "10"),
        ({"stat": "ast", "max_value": 8}, "ast max", "8"),
        ({"stat": "pts", "min_value": 20, "max_value": 20}, "pts", "exactly 20"),
    ],
)
def test_event_bounds_and_metric_remain_paired(event, label, value):
    source = {"stat": "games_event", "occurrence_event": event}
    assert _build_applied_filters(source, route_kwargs={"stat": "games_event"}) == [
        {"label": label, "value": value, "kind": "threshold"}
    ]


def test_ordinary_metric_conditions_and_special_events_keep_their_labels():
    assert _build_applied_filters({"stat": "pts", "min_value": 25}) == [
        {"label": "pts min", "value": "25", "kind": "threshold"}
    ]
    assert _build_applied_filters({"occurrence_event": {"special_event": "triple_double"}}) == [
        {"label": "Special Event", "value": "Triple Double", "kind": "special_event"}
    ]
    assert _build_applied_filters(
        {"conditions": [{"stat": "reb", "min_value": 8}], "occurrence_event": {"stat": "pts"}}
    ) == [{"label": "reb min", "value": "8", "kind": "threshold"}]
    assert _build_applied_filters(
        {"stat": "games_event", "min_value": 3, "occurrence_event": {"stat": "pts"}}
    ) == [{"label": "games_event min", "value": "3", "kind": "threshold"}]
