from contextlib import redirect_stdout
from io import StringIO

import pandas as pd
import pytest

from nbatools.commands.format_output import METADATA_LABEL, parse_labeled_sections
from nbatools.commands.natural_query import parse_query
from nbatools.commands.natural_query import run as natural_query_run

pytestmark = pytest.mark.query


def _capture_output(func, *args, **kwargs) -> str:
    buffer = StringIO()
    with redirect_stdout(buffer):
        func(*args, **kwargs)
    return buffer.getvalue()


def test_parse_player_since_all_star_break():
    parsed = parse_query("Jokic since All-Star break")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "player_game_finder"
    assert parsed["route_kwargs"]["start_date"] == "2026-02-16"
    assert parsed["route_kwargs"]["end_date"] is None


def test_parse_player_summary_since_all_star_break():
    parsed = parse_query("Jokic summary since all star break")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "player_game_summary"
    assert parsed["route_kwargs"]["start_date"] == "2026-02-16"


def test_parse_team_since_all_star_break():
    parsed = parse_query("Celtics since All-Star break")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "game_finder"
    assert parsed["route_kwargs"]["start_date"] == "2026-02-16"


def test_parse_player_compare_since_all_star_break():
    parsed = parse_query("Jokic vs Embiid since All-Star break")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "player_compare"
    assert parsed["route_kwargs"]["start_date"] == "2026-02-16"


def test_parse_team_h2h_since_all_star_break():
    parsed = parse_query("Celtics h2h vs Bucks since All-Star break")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "team_compare"
    assert parsed["route_kwargs"]["head_to_head"] is True
    assert parsed["route_kwargs"]["start_date"] == "2026-02-16"


def test_parse_top_scorers_since_all_star_break():
    parsed = parse_query("top scorers since All-Star break")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "season_leaders"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["start_date"] == "2026-02-16"


def test_parse_best_offensive_teams_since_all_star_break():
    parsed = parse_query("best offensive teams since All-Star break")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "season_team_leaders"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["start_date"] == "2026-02-16"


def test_parse_explicit_2024_25_all_star_break():
    parsed = parse_query("top scorers since All-Star break in 2024-25")
    assert parsed["season"] == "2024-25"
    assert parsed["route"] == "season_leaders"
    assert parsed["route_kwargs"]["start_date"] == "2025-02-17"


def _extract_data_csv(raw_text: str) -> str:
    sections = parse_labeled_sections(raw_text)
    sections.pop(METADATA_LABEL, None)
    for label in ("FINDER", "LEADERBOARD", "STREAK", "TABLE"):
        if label in sections:
            return sections[label]
    return raw_text.strip()


@pytest.mark.needs_data
def test_natural_player_since_all_star_break_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic since All-Star break",
        pretty=False,
    )
    csv_block = _extract_data_csv(out)
    df = pd.read_csv(StringIO(csv_block))
    dates = pd.to_datetime(df["game_date"])
    assert not df.empty
    assert dates.min() >= pd.Timestamp("2026-02-16")


@pytest.mark.needs_data
def test_natural_top_scorers_since_all_star_break_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="top scorers since All-Star break",
        pretty=False,
    )
    assert "player_name" in out
    assert "pts_per_game" in out
    assert "2025-26" in out


@pytest.mark.needs_data
def test_natural_best_offensive_teams_since_all_star_break_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="best offensive teams since All-Star break",
        pretty=False,
    )
    assert "team_name" in out
    assert "pts_per_game" in out
    assert "2025-26" in out


@pytest.mark.needs_data
def test_natural_player_compare_since_all_star_break_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic vs Embiid since All-Star break",
        pretty=False,
    )
    assert "SUMMARY" in out
    assert "COMPARISON" in out
    assert "Nikola Jokić" in out
    assert "Joel Embiid" in out
