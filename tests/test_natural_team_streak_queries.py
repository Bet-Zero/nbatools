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


def test_parse_team_scoring_streak():
    parsed = parse_query("Celtics 5 straight games scoring 120+")
    assert parsed["route"] == "team_streak_finder"
    assert parsed["route_kwargs"]["team"] == "BOS"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["min_value"] == 120.0
    assert parsed["route_kwargs"]["min_streak_length"] == 5
    assert parsed["route_kwargs"]["longest"] is False


def test_parse_team_winning_streak():
    parsed = parse_query("longest Lakers winning streak")
    assert parsed["route"] == "team_streak_finder"
    assert parsed["route_kwargs"]["team"] == "LAL"
    assert parsed["route_kwargs"]["special_condition"] == "wins"
    assert parsed["route_kwargs"]["longest"] is True


def test_parse_team_threes_streak():
    parsed = parse_query("longest Bucks streak with 15+ threes")
    assert parsed["route"] == "team_streak_finder"
    assert parsed["route_kwargs"]["team"] == "MIL"
    assert parsed["route_kwargs"]["stat"] == "fg3m"
    assert parsed["route_kwargs"]["min_value"] == 15.0
    assert parsed["route_kwargs"]["longest"] is True


def test_parse_team_consecutive_points_streak():
    parsed = parse_query("Thunder consecutive games with 110+ points")
    assert parsed["route"] == "team_streak_finder"
    assert parsed["route_kwargs"]["team"] == "OKC"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["min_value"] == 110.0
    assert parsed["route_kwargs"]["longest"] is True


@pytest.mark.needs_data
def test_natural_team_winning_streak_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="longest Lakers winning streak",
        pretty=False,
    )
    assert "team_name" in out
    assert "streak_length" in out
    assert "LAL" in out or "Los Angeles Lakers" in out


@pytest.mark.needs_data
def test_natural_team_points_streak_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="Thunder consecutive games with 110+ points",
        pretty=False,
    )
    assert "team_name" in out
    assert "streak_length" in out
    assert "OKC" in out or "Oklahoma City Thunder" in out
