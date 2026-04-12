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


def test_parse_top_scorers_this_season():
    parsed = parse_query("top scorers this season")
    assert parsed["season"] == "2025-26"
    assert parsed["season_type"] == "Regular Season"
    assert parsed["route"] == "season_leaders"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["limit"] == 10


def test_parse_top_15_scorers_this_season():
    parsed = parse_query("top 15 scorers this season")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "season_leaders"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["limit"] == 15


def test_parse_highest_ts_pct_this_season():
    parsed = parse_query("highest ts% this season")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "season_leaders"
    assert parsed["route_kwargs"]["stat"] == "ts_pct"


def test_parse_highest_ts_pct_among_players():
    parsed = parse_query("highest ts% among players")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "season_leaders"
    assert parsed["route_kwargs"]["stat"] == "ts_pct"


def test_parse_highest_efg_pct_this_season():
    parsed = parse_query("highest efg% this season")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "season_leaders"
    assert parsed["route_kwargs"]["stat"] == "efg_pct"


def test_parse_most_30_point_games_this_season():
    parsed = parse_query("most 30 point games this season")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "season_leaders"
    assert parsed["route_kwargs"]["stat"] == "games_30p"


def test_parse_highest_assists_per_game():
    parsed = parse_query("highest assists per game")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "season_leaders"
    assert parsed["route_kwargs"]["stat"] == "ast"


@pytest.mark.slow
@pytest.mark.needs_data
def test_natural_top_scorers_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="top scorers this season",
        pretty=False,
    )
    assert "player_name" in out
    assert "pts_per_game" in out
    assert "2025-26" in out


@pytest.mark.slow
@pytest.mark.needs_data
def test_natural_highest_ts_pct_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="highest ts% this season",
        pretty=False,
    )
    assert "player_name" in out
    assert "ts_pct" in out
    assert "2025-26" in out


@pytest.mark.slow
@pytest.mark.needs_data
def test_natural_most_30_point_games_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="most 30 point games this season",
        pretty=False,
    )
    assert "player_name" in out
    assert "games_30p" in out
    assert "2025-26" in out
