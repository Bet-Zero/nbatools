import pytest

from nbatools.commands.natural_query import parse_query

pytestmark = pytest.mark.query


def test_quarter_filter_propagates_to_player_route_kwargs():
    parsed = parse_query("LeBron 4th quarter scoring")
    assert parsed["route"] == "player_game_finder"
    assert parsed["route_kwargs"]["quarter"] == "4"
    assert parsed["route_kwargs"]["half"] is None


def test_half_filter_propagates_to_team_route_kwargs():
    parsed = parse_query("Celtics first half record")
    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["half"] == "first"
    assert parsed["route_kwargs"]["quarter"] is None


def test_overtime_filter_propagates_to_route_kwargs():
    parsed = parse_query("Knicks OT record")
    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["quarter"] == "OT"


def test_supported_period_routes_no_longer_append_parser_note():
    parsed = parse_query("LeBron 4th quarter scoring")
    assert not any("quarter" in note and "unfiltered" in note for note in parsed.get("notes", []))


def test_unsupported_period_route_still_appends_unfiltered_note():
    parsed = parse_query("most 4th quarter points this season")
    assert any("quarter" in note and "unfiltered" in note for note in parsed.get("notes", []))
