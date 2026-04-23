import pytest

from nbatools.commands._natural_query_execution import _route_context_filters_for_execution
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.query, pytest.mark.engine]


def test_clutch_filter_propagates_to_route_kwargs():
    parsed = parse_query("Tatum clutch stats")

    assert parsed["route"] == "player_game_summary"
    assert parsed["route_kwargs"]["clutch"] is True


def test_supported_clutch_route_keeps_kwarg_and_note():
    routed, notes = _route_context_filters_for_execution(
        "player_game_summary",
        {"player": "Nikola Jokić", "clutch": True},
    )

    assert routed["clutch"] is True
    assert any("clutch" in note and "unfiltered" in note for note in notes)


def test_supported_period_route_keeps_kwarg_and_note():
    routed, notes = _route_context_filters_for_execution(
        "team_record",
        {"team": "NYK", "quarter": "OT"},
    )

    assert routed["quarter"] == "OT"
    assert any("quarter" in note and "unfiltered" in note for note in notes)


def test_supported_role_route_keeps_kwarg_without_note():
    routed, notes = _route_context_filters_for_execution(
        "player_game_finder",
        {"player": "Jalen Brunson", "role": "bench"},
    )

    assert routed["role"] == "bench"
    assert not any("role" in note and "unfiltered" in note for note in notes)


def test_unsupported_period_route_drops_kwarg_and_keeps_note():
    routed, notes = _route_context_filters_for_execution(
        "player_game_summary",
        {"player": "Nikola Jokić", "quarter": "4"},
    )

    assert "quarter" not in routed
    assert any("quarter" in note and "unfiltered" in note for note in notes)


def test_schedule_filter_still_drops_with_note():
    routed, notes = _route_context_filters_for_execution(
        "player_game_summary",
        {"player": "Nikola Jokić", "back_to_back": True},
    )

    assert "back_to_back" not in routed
    assert any("back_to_back" in note and "unfiltered" in note for note in notes)


def test_execute_natural_query_carries_clutch_in_metadata():
    qr = execute_natural_query("Jokic clutch stats 1950-51")

    assert qr.route == "player_game_summary"
    assert qr.metadata["clutch"] is True
    assert any("clutch" in note and "unfiltered" in note for note in qr.result.notes)


def test_execute_structured_query_carries_clutch_in_metadata():
    qr = execute_structured_query(
        "player_game_summary",
        season="1950-51",
        player="Nikola Jokić",
        clutch=True,
    )

    assert qr.route == "player_game_summary"
    assert qr.metadata["clutch"] is True
    assert any("clutch" in note and "unfiltered" in note for note in qr.result.notes)
