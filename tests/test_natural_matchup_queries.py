from contextlib import redirect_stdout
from io import StringIO

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.commands.natural_query import run as natural_query_run


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
    assert "SUMMARY" in out
    assert "COMPARISON" in out
    assert "Joel Embiid" in out
    assert "Nikola Jokić" in out


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
