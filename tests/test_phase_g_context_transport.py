import pytest

from nbatools.commands._natural_query_execution import _route_context_filters_for_execution
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.query, pytest.mark.engine]


def test_clutch_filter_propagates_to_route_kwargs():
    parsed = parse_query("Tatum clutch stats")

    assert parsed["route"] == "player_game_summary"
    assert parsed["route_kwargs"]["clutch"] is True


def test_supported_clutch_route_keeps_kwarg_without_transport_note():
    routed, notes, blocked = _route_context_filters_for_execution(
        "player_game_summary",
        {"player": "Nikola Jokić", "clutch": True},
    )

    assert routed["clutch"] is True
    assert "clutch" not in blocked
    assert blocked == []


def test_supported_period_route_keeps_kwarg_without_transport_note():
    routed, notes, blocked = _route_context_filters_for_execution(
        "team_record",
        {"team": "NYK", "quarter": "OT"},
    )

    assert routed["quarter"] == "OT"
    assert "quarter" not in blocked
    assert blocked == []


def test_supported_role_route_keeps_kwarg_without_note():
    routed, notes, blocked = _route_context_filters_for_execution(
        "player_game_finder",
        {"player": "Jalen Brunson", "role": "bench"},
    )

    assert routed["role"] == "bench"
    assert "role" not in blocked
    assert blocked == []


def test_unsupported_period_route_drops_kwarg_and_keeps_note():
    routed, notes, blocked = _route_context_filters_for_execution(
        "player_game_summary",
        {"player": "Nikola Jokić", "quarter": "4"},
    )

    assert "quarter" not in routed
    assert "quarter" in blocked


def test_supported_schedule_filter_keeps_kwarg_without_transport_note():
    routed, notes, blocked = _route_context_filters_for_execution(
        "player_game_summary",
        {"player": "Nikola Jokić", "back_to_back": True},
    )

    assert routed["back_to_back"] is True
    assert "back_to_back" not in blocked
    assert blocked == []


def test_execute_natural_query_reports_missing_clutch_coverage():
    qr = execute_natural_query("Jokic clutch stats 1950-51")

    assert qr.route == "player_game_summary"
    assert qr.metadata["clutch"] is True
    # 1950-51 has no base player data, so reason is no_data (base data missing)
    # or filter_not_supported (base data exists but clutch data missing).
    # Either way the query returns an honest no-result, not an unfiltered result.
    assert qr.result_reason in ("filter_not_supported", "no_data")
    assert qr.result.result_status == "no_result"


def test_execute_structured_query_reports_missing_clutch_coverage():
    qr = execute_structured_query(
        "player_game_summary",
        season="1950-51",
        player="Nikola Jokić",
        clutch=True,
    )

    assert qr.route == "player_game_summary"
    assert qr.metadata["clutch"] is True
    # 1950-51 has no base player data, so reason is no_data (base data missing)
    # or filter_not_supported (base data exists but clutch data missing).
    # Either way the query returns an honest no-result, not an unfiltered result.
    assert qr.result_reason in ("filter_not_supported", "no_data")
    assert qr.result.result_status == "no_result"
