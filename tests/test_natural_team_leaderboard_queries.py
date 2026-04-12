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


def test_parse_best_offensive_teams():
    parsed = parse_query("best offensive teams")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "season_team_leaders"
    assert parsed["route_kwargs"]["stat"] == "off_rating"


def test_parse_teams_with_most_threes():
    parsed = parse_query("teams with most threes")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "season_team_leaders"
    assert parsed["route_kwargs"]["stat"] == "fg3m"


def test_parse_teams_with_best_efg():
    parsed = parse_query("teams with best efg%")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "season_team_leaders"
    assert parsed["route_kwargs"]["stat"] == "efg_pct"


def test_parse_teams_with_best_ts():
    parsed = parse_query("teams with best ts%")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "season_team_leaders"
    assert parsed["route_kwargs"]["stat"] == "ts_pct"


@pytest.mark.needs_data
def test_natural_best_offensive_teams_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="best offensive teams",
        pretty=False,
    )
    assert "team_name" in out
    assert "off_rating" in out
    assert "2025-26" in out


@pytest.mark.needs_data
def test_natural_teams_with_most_threes_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="teams with most threes",
        pretty=False,
    )
    assert "team_name" in out
    assert "fg3m_per_game" in out
    assert "2025-26" in out


@pytest.mark.needs_data
def test_natural_teams_with_best_efg_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="teams with best efg%",
        pretty=False,
    )
    assert "team_name" in out
    assert "efg_pct" in out
    assert "2025-26" in out
