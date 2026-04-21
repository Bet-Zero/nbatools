import pytest

from nbatools.commands.data_utils import resolve_opponent_quality_teams
from nbatools.commands.natural_query import parse_query
from nbatools.commands.player_game_summary import build_result as build_player_summary_result
from nbatools.commands.team_record import build_team_record_result
from nbatools.query_service import execute_natural_query

pytestmark = pytest.mark.query


def test_opponent_quality_propagates_to_route_kwargs():
    parsed = parse_query("Jokic against contenders")
    assert parsed["route"] == "player_game_summary"
    assert parsed["route_kwargs"]["opponent_quality"]["surface_term"] == "contenders"


def test_top_ten_defenses_propagates_to_team_record_route_kwargs():
    parsed = parse_query("Lakers record against top-10 defenses")
    assert parsed["route"] == "team_record"
    assert parsed["route_kwargs"]["opponent_quality"]["surface_term"] == "top-10 defenses"


@pytest.mark.needs_data
def test_natural_query_filters_player_summary_against_contenders():
    query = "Jokic against contenders 2024-25"
    parsed = parse_query(query)
    qr = execute_natural_query(query)

    assert qr.route == "player_game_summary"
    assert qr.is_ok

    resolved = resolve_opponent_quality_teams(
        parsed["opponent_quality"],
        ["2024-25"],
        "Regular Season",
    )
    expected = build_player_summary_result(
        season="2024-25",
        player=parsed["player"],
        opponent=resolved,
    )

    actual_games = int(qr.result.summary.iloc[0]["games"])
    filtered_games = int(expected.summary.iloc[0]["games"])
    baseline_games = int(
        build_player_summary_result(season="2024-25", player=parsed["player"]).summary.iloc[0][
            "games"
        ]
    )

    assert actual_games == filtered_games
    assert actual_games < baseline_games
    assert any("opponent_quality" in note for note in qr.result.notes)


@pytest.mark.needs_data
def test_natural_query_filters_team_record_against_top_ten_defenses():
    query = "Lakers record against top-10 defenses 2024-25"
    parsed = parse_query(query)
    qr = execute_natural_query(query)

    assert qr.route == "team_record"
    assert qr.is_ok

    resolved = resolve_opponent_quality_teams(
        parsed["opponent_quality"],
        ["2024-25"],
        "Regular Season",
    )
    expected = build_team_record_result(
        season="2024-25",
        team=parsed["team"],
        opponent=resolved,
    )

    actual_row = qr.result.summary.iloc[0]
    expected_row = expected.summary.iloc[0]
    baseline_games = int(
        build_team_record_result(season="2024-25", team=parsed["team"]).summary.iloc[0]["games"]
    )

    assert int(actual_row["games"]) == int(expected_row["games"])
    assert int(actual_row["wins"]) == int(expected_row["wins"])
    assert int(actual_row["losses"]) == int(expected_row["losses"])
    assert int(actual_row["games"]) < baseline_games
    assert any("opponent_quality" in note for note in qr.result.notes)
