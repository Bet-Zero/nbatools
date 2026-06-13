from contextlib import redirect_stdout
from io import StringIO

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.commands.natural_query import run as natural_query_run

pytestmark = pytest.mark.query


def _capture_output(func, *args, **kwargs) -> str:
    buffer = StringIO()
    with redirect_stdout(buffer):
        func(*args, **kwargs)
    return buffer.getvalue()


def test_parse_player_vs_team_matchup():
    parsed = parse_query("Jokic vs Lakers")
    assert parsed["player"] == "Nikola Jokić"
    assert parsed["opponent"] == "LAL"
    assert parsed["route"] == "player_game_finder"


def test_parse_player_last_10_vs_team_matchup():
    parsed = parse_query("Jokic last 10 vs Lakers")
    assert parsed["player"] == "Nikola Jokić"
    assert parsed["opponent"] == "LAL"
    assert parsed["last_n"] == 10
    assert parsed["route"] == "player_game_finder"


def test_parse_player_summary_vs_team_matchup():
    parsed = parse_query("Jokic summary vs Lakers")
    assert parsed["player"] == "Nikola Jokić"
    assert parsed["opponent"] == "LAL"
    assert parsed["route"] == "player_game_summary"


def test_parse_player_head_to_head_vs_player():
    parsed = parse_query("Embiid head-to-head vs Jokic")
    assert parsed["player_a"] == "Joel Embiid"
    assert parsed["player_b"] == "Nikola Jokić"
    assert parsed["route"] == "player_compare"


def test_parse_player_h2h_vs_player():
    parsed = parse_query("Jokic h2h vs Embiid")
    assert parsed["player_a"] == "Nikola Jokić"
    assert parsed["player_b"] == "Joel Embiid"
    assert parsed["route"] == "player_compare"


def test_parse_team_head_to_head_vs_team():
    parsed = parse_query("Lakers head-to-head vs Celtics")
    assert parsed["team_a"] == "LAL"
    assert parsed["team_b"] == "BOS"
    assert parsed["route"] == "team_compare"


def test_parse_team_h2h_with_home_filter():
    parsed = parse_query("Celtics h2h vs Bucks home")
    assert parsed["team_a"] == "BOS"
    assert parsed["team_b"] == "MIL"
    assert parsed["home_only"] is True
    assert parsed["route"] == "team_compare"


@pytest.mark.needs_data
def test_natural_player_matchup_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic vs Lakers",
        pretty=False,
    )
    assert "player_name" in out
    assert "Nikola Jokić" in out
    assert "LAL" in out


@pytest.mark.needs_data
def test_natural_player_summary_vs_team_matchup_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic summary vs Lakers",
        pretty=False,
    )
    assert "SUMMARY" in out
    assert "Nikola Jokić" in out
    assert "2025-26" in out


@pytest.mark.needs_data
def test_natural_player_h2h_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="Embiid head-to-head vs Jokic",
        pretty=False,
    )
    # Routes to player_compare with head_to_head — data may or may not
    # contain shared games in the resolved season window.
    assert "player_compare" in out
    has_data = "SUMMARY" in out and "COMPARISON" in out
    has_no_result = "NO_RESULT" in out
    assert has_data or has_no_result


@pytest.mark.needs_data
def test_natural_team_h2h_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="Lakers head-to-head vs Celtics",
        pretty=False,
    )
    assert "SUMMARY" in out
    assert "COMPARISON" in out
    assert "LAL" in out
    assert "BOS" in out


@pytest.mark.parametrize(
    "query",
    [
        "jokic vs embiid this season",
        "curry vs dame 3 point shooting this year",
        "jokic vs embiid recent form",
    ],
)
def test_comparison_with_scope_or_stat_resolves_both_players(query):
    # A season/stat modifier after the second player must not be misread as a
    # name typo that blocks the comparison.
    parsed = parse_query(query)
    assert parsed["route"] == "player_compare"
    assert parsed["player_a"]
    assert parsed["player_b"]
    assert "unsupported_filters" not in parsed.get("route_kwargs", {})


def test_comparison_with_unidentified_second_player_refuses():
    # "jordan" is ambiguous and must not silently collapse into a
    # LeBron-only summary.
    parsed = parse_query("lebron vs jordan career")
    assert parsed["route"] == "player_compare"
    assert parsed["route_kwargs"].get("unsupported_filters") == ["unresolved_player"]


@pytest.mark.parametrize(
    ("query", "expected_route"),
    [
        ("lebron vs warriors career", "player_game_summary"),
        ("lebron stats vs kd", "player_game_finder"),
        ("jokic home vs away", "player_split_summary"),
        ("tatum in wins vs losses", "player_split_summary"),
    ],
)
def test_vs_neighbors_not_caught_by_comparison_guard(query, expected_route):
    parsed = parse_query(query)
    assert parsed["route"] == expected_route
