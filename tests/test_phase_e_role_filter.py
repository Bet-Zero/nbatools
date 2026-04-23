import pytest

from nbatools.commands.natural_query import parse_query

pytestmark = pytest.mark.query


def test_bench_role_propagates_to_player_route_kwargs():
    parsed = parse_query("Brunson off the bench")
    assert parsed["route"] == "player_game_summary"
    assert parsed["route_kwargs"]["role"] == "bench"


def test_starter_role_propagates_to_player_route_kwargs():
    parsed = parse_query("LeBron as a starter stats")
    assert parsed["route"] == "player_game_summary"
    assert parsed["route_kwargs"]["role"] == "starter"


def test_team_bench_phrase_does_not_propagate_role():
    parsed = parse_query("Celtics bench scoring")
    assert parsed["role"] is None
    assert parsed["route_kwargs"]["role"] is None


def test_role_filter_does_not_append_parse_time_unfiltered_note_on_supported_route():
    parsed = parse_query("Brunson off the bench")
    assert not any("role" in note and "unfiltered" in note for note in parsed.get("notes", []))
