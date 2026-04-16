from contextlib import redirect_stdout
from io import StringIO

import pandas as pd
import pytest

from nbatools.commands.format_output import METADATA_LABEL, parse_labeled_sections
from nbatools.commands.natural_query import (
    CURRENT_QUERY_DATE,
    parse_query,
)
from nbatools.commands.natural_query import (
    run as natural_query_run,
)

pytestmark = pytest.mark.query


def _capture_output(func, *args, **kwargs) -> str:
    buffer = StringIO()
    with redirect_stdout(buffer):
        func(*args, **kwargs)
    return buffer.getvalue()


def _extract_data_csv(raw_text: str) -> str:
    sections = parse_labeled_sections(raw_text)
    sections.pop(METADATA_LABEL, None)
    for label in ("FINDER", "LEADERBOARD", "STREAK", "TABLE"):
        if label in sections:
            return sections[label]
    return raw_text.strip()


def test_parse_player_since_january():
    parsed = parse_query("Jokic since January")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "player_game_finder"
    assert parsed["route_kwargs"]["start_date"] == "2026-01-01"
    assert parsed["route_kwargs"]["end_date"] is None


def test_parse_team_summary_in_march():
    parsed = parse_query("Celtics summary in March")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "game_summary"
    assert parsed["route_kwargs"]["start_date"] == "2026-03-01"
    assert parsed["route_kwargs"]["end_date"] == "2026-03-31"


def test_parse_matchup_last_30_days():
    parsed = parse_query("Jokic vs Lakers last 30 days")
    expected_start = (CURRENT_QUERY_DATE - pd.Timedelta(days=29)).date().isoformat()
    expected_end = CURRENT_QUERY_DATE.date().isoformat()

    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "player_game_finder"
    assert parsed["route_kwargs"]["start_date"] == expected_start
    assert parsed["route_kwargs"]["end_date"] == expected_end


@pytest.mark.needs_data
def test_natural_player_since_january_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic since January",
        pretty=False,
    )
    csv_block = _extract_data_csv(out)
    df = pd.read_csv(StringIO(csv_block))
    dates = pd.to_datetime(df["game_date"])
    assert not df.empty
    assert dates.min() >= pd.Timestamp("2026-01-01")


@pytest.mark.needs_data
def test_natural_team_in_march_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="Celtics in March",
        pretty=False,
    )
    csv_block = _extract_data_csv(out)
    df = pd.read_csv(StringIO(csv_block))
    dates = pd.to_datetime(df["game_date"])
    assert not df.empty
    assert set(dates.dt.month.unique()) == {3}


@pytest.mark.needs_data
def test_natural_player_summary_since_january_raw_smoke():
    out = _capture_output(
        natural_query_run,
        query="Jokic summary since January",
        pretty=False,
    )
    assert "SUMMARY" in out
    assert "BY_SEASON" in out
