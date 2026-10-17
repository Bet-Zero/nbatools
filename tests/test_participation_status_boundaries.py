"""Participation evidence cannot substitute for status or court-presence facts."""

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


@pytest.mark.parametrize(
    "status",
    [
        "injured",
        "healthy",
        "fully fit",
        "questionable",
        "doubtful",
        "active",
        "inactive",
        "available",
        "unavailable",
        "suspended",
        "resting",
        "in the lineup",
        "out of the lineup",
    ],
)
def test_status_keeps_its_meaning(status):
    result = execute_natural_query(f"Lakers record with Anthony Davis {status}")
    assert result.result_status == "no_result"
    assert "availability_status" in result.metadata["unsupported_filters"]
    assert not result.to_dict()["sections"]


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record with Davis on the court",
        "Lakers record with Anthony Davis on the court",
        "LeBron James stats with Davis on the court",
        "LeBron James stats with Anthony Davis on the court",
        "LeBron James points with Anthony Davis on the floor",
        "Lakers record without Davis on the court",
        "LeBron James stats with Davis off the court",
        "LeBron James stats with Blorg off the court",
        "LeBron James net rating with Davis off the court",
        "LeBron net rating when Jokic is off the court",
        "LeBron net rating with LeBron on the court and Jokic off the court",
        "LeBron net rating when LeBron is on the floor and Curry is off the floor",
        "LeBron net rating after Jokic goes off the court",
    ],
)
def test_court_condition_never_becomes_whole_game_participation(query):
    parsed = parse_query(query)
    assert "on_court_presence" in parsed["route_kwargs"]["unsupported_filters"]
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert not result.to_dict()["sections"]


def test_supported_on_off_route_retains_requested_person_and_metric():
    parsed = parse_query("Lakers net rating with LeBron James on the court")
    assert parsed["route"] == "player_on_off"
    assert parsed["route_kwargs"]["lineup_members"] == ["LeBron James"]
    assert parsed["route_kwargs"]["presence_state"] == "on"
    assert not parsed["route_kwargs"].get("unsupported_filters")
