from contextlib import redirect_stdout
from io import StringIO

from nbatools.commands.natural_query import parse_query
from nbatools.commands.natural_query import run as natural_query_run


def _capture_output(func, *args, **kwargs) -> str:
    buffer = StringIO()
    with redirect_stdout(buffer):
        func(*args, **kwargs)
    return buffer.getvalue()


def test_parse_player_straight_points_streak():
    parsed = parse_query("Jokic 5 straight games with 20+ points")
    assert parsed["route"] == "player_streak_finder"
    assert parsed["route_kwargs"]["player"] == "Nikola Jokić"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["min_value"] == 20.0
    assert parsed["route_kwargs"]["min_streak_length"] == 5
    assert parsed["route_kwargs"]["longest"] is False


def test_parse_player_longest_points_streak():
    parsed = parse_query("Jokic longest streak of 30 point games")
    assert parsed["route"] == "player_streak_finder"
    assert parsed["route_kwargs"]["player"] == "Nikola Jokić"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["min_value"] == 30.0
    assert parsed["route_kwargs"]["longest"] is True


def test_parse_player_made_three_streak():
    parsed = parse_query("Jokic consecutive games with a made three")
    assert parsed["route"] == "player_streak_finder"
    assert parsed["route_kwargs"]["special_condition"] == "made_three"
    assert parsed["route_kwargs"]["longest"] is True


def test_parse_player_triple_double_streak():
    parsed = parse_query("Jokic longest triple-double streak")
    assert parsed["route"] == "player_streak_finder"
    assert parsed["route_kwargs"]["special_condition"] == "triple_double"
    assert parsed["route_kwargs"]["longest"] is True


def test_natural_player_points_streak_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic 5 straight games with 20+ points",
        pretty=False,
    )
    assert "player_name" in out
    assert "streak_length" in out
    assert "Nikola Jokić" in out


def test_natural_player_triple_double_streak_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic longest triple-double streak",
        pretty=False,
    )
    assert "player_name" in out
    assert "streak_length" in out
    assert "Nikola Jokić" in out


def test_parse_player_streak_defaults_to_recent_three_seasons():
    parsed = parse_query("Jokic longest triple-double streak")
    assert parsed["route"] == "player_streak_finder"
    assert parsed["route_kwargs"]["season"] is None
    assert parsed["route_kwargs"]["start_season"] == "2023-24"
    assert parsed["route_kwargs"]["end_season"] == "2025-26"
