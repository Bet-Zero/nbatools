import pytest

from nbatools.commands.natural_query import parse_query

pytestmark = pytest.mark.query


def test_back_to_back_filter_propagates_to_team_route_kwargs():
    parsed = parse_query("Lakers on back-to-backs")
    assert parsed["route"] == "game_finder"
    assert parsed["route_kwargs"]["back_to_back"] is True
    assert parsed["route_kwargs"]["rest_days"] is None


def test_rest_filter_propagates_to_player_route_kwargs():
    parsed = parse_query("Jokic with rest advantage")
    assert parsed["route"] == "player_game_summary"
    assert parsed["route_kwargs"]["rest_days"] == "advantage"
    assert parsed["route_kwargs"]["back_to_back"] is False


def test_one_possession_filter_propagates_to_team_record_route_kwargs():
    parsed = parse_query("Celtics one-possession record")
    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["one_possession"] is True


def test_national_tv_filter_propagates_to_team_record_route_kwargs():
    parsed = parse_query("Knicks on national TV record")
    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["nationally_televised"] is True


def test_rest_days_count_propagates_to_route_kwargs():
    parsed = parse_query("Jokic on 2 days rest")
    assert parsed["route"] == "player_game_summary"
    assert parsed["route_kwargs"]["rest_days"] == 2


def test_game_context_filters_append_unfiltered_note():
    parsed = parse_query("Lakers on back-to-backs")
    assert any("back_to_back" in note and "unfiltered" in note for note in parsed.get("notes", []))
