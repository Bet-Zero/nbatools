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


def test_parse_player_compare_since_january():
    parsed = parse_query("Jokic vs Embiid since January")
    assert parsed["route"] == "player_compare"
    assert parsed["route_kwargs"]["start_date"] == "2026-01-01"
    assert parsed["route_kwargs"]["end_date"] is None


def test_parse_team_h2h_in_march():
    parsed = parse_query("Celtics h2h vs Bucks in March")
    assert parsed["route"] == "team_compare"
    assert parsed["route_kwargs"]["head_to_head"] is True
    assert parsed["route_kwargs"]["start_date"] == "2026-03-01"
    assert parsed["route_kwargs"]["end_date"] == "2026-03-31"


def test_parse_top_scorers_since_january():
    parsed = parse_query("top scorers since January")
    assert parsed["route"] == "season_leaders"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["start_date"] == "2026-01-01"
    assert parsed["route_kwargs"]["end_date"] is None


def test_parse_top_scorers_in_march():
    parsed = parse_query("top scorers in March")
    assert parsed["route"] == "season_leaders"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["start_date"] == "2026-03-01"
    assert parsed["route_kwargs"]["end_date"] == "2026-03-31"


def test_parse_teams_with_best_efg_in_march():
    parsed = parse_query("teams with best efg% in March")
    assert parsed["route"] == "season_team_leaders"
    assert parsed["route_kwargs"]["stat"] == "efg_pct"
    assert parsed["route_kwargs"]["start_date"] == "2026-03-01"
    assert parsed["route_kwargs"]["end_date"] == "2026-03-31"


def test_parse_best_offensive_teams_since_january_uses_points_per_game():
    parsed = parse_query("best offensive teams since January")
    assert parsed["route"] == "season_team_leaders"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["start_date"] == "2026-01-01"
    assert parsed["route_kwargs"]["end_date"] is None


def test_parse_best_offensive_teams_in_march_uses_points_per_game():
    parsed = parse_query("best offensive teams in March")
    assert parsed["route"] == "season_team_leaders"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["start_date"] == "2026-03-01"
    assert parsed["route_kwargs"]["end_date"] == "2026-03-31"


@pytest.mark.needs_data
def test_natural_player_compare_since_january_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic vs Embiid since January",
        pretty=False,
    )
    assert "SUMMARY" in out
    assert "COMPARISON" in out
    assert "Nikola Jokić" in out
    assert "Joel Embiid" in out


@pytest.mark.needs_data
def test_natural_top_scorers_since_january_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="top scorers since January",
        pretty=False,
    )
    assert "player_name" in out
    assert "pts_per_game" in out
    assert "2025-26" in out


@pytest.mark.needs_data
def test_natural_top_scorers_in_march_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="top scorers in March",
        pretty=False,
    )
    assert "player_name" in out
    assert "pts_per_game" in out
    assert "2025-26" in out


@pytest.mark.needs_data
def test_natural_best_team_efg_in_march_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="teams with best efg% in March",
        pretty=False,
    )
    assert "team_name" in out
    assert "efg_pct" in out
    assert "2025-26" in out


@pytest.mark.needs_data
def test_natural_best_offensive_teams_in_march_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="best offensive teams in March",
        pretty=False,
    )
    assert "team_name" in out
    assert "pts_per_game" in out
    assert "2025-26" in out
