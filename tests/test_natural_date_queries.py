from contextlib import redirect_stdout
from datetime import date, timedelta
from io import StringIO

import pandas as pd
import pytest

from nbatools.commands._date_utils import current_query_date
from nbatools.commands._seasons import request_calendar
from nbatools.commands.format_output import METADATA_LABEL, parse_labeled_sections
from nbatools.commands.freshness import compute_current_through
from nbatools.commands.natural_query import (
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


def test_parse_explicit_date_top_scorer_uses_game_level_route():
    parsed = parse_query("Who scored the most points on January 1 2026?")
    assert parsed["season"] == "2025-26"
    assert parsed["route"] == "top_player_games"
    assert parsed["route_kwargs"]["stat"] == "pts"
    assert parsed["route_kwargs"]["start_date"] == "2026-01-01"
    assert parsed["route_kwargs"]["end_date"] == "2026-01-01"


@pytest.mark.parametrize("qualifier", ["this regular season", "in the current NBA season"])
def test_qualified_current_season_win_board_keeps_one_calendar_season(qualifier):
    with request_calendar(date(2026, 4, 10)):
        parsed = parse_query(f"Teams with 40 wins {qualifier}")
    assert parsed["route"] == "team_record_leaderboard"
    assert parsed["route_kwargs"]["season"] == "2025-26"
    assert parsed["route_kwargs"]["start_season"] is None
    assert parsed["route_kwargs"]["end_season"] is None


def test_parse_matchup_last_30_days():
    parsed = parse_query("Jokic vs Lakers last 30 days")
    # Anchor to data end date when data is stale, otherwise the request day
    ct = compute_current_through("2025-26", "Regular Season")
    anchor = (
        pd.Timestamp(ct) if ct and pd.Timestamp(ct) < current_query_date() else current_query_date()
    )
    expected_start = (anchor - pd.Timedelta(days=29)).date().isoformat()
    expected_end = anchor.date().isoformat()

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


@pytest.mark.needs_data
def test_literal_calendar_and_last_games_use_the_requested_raw_sample():
    from nbatools.data_source import data_read_csv
    from nbatools.query_service import execute_natural_query

    raw = data_read_csv("raw/player_game_stats/2025-26_regular_season.csv")
    rows = raw.loc[raw["player_id"] == 203999].sort_values(["game_date", "game_id"])
    assert len(rows) > 5
    latest_day = rows.iloc[-1]["game_date"]
    yesterday = rows.loc[rows["game_date"] == latest_day]
    with request_calendar(date.fromisoformat(latest_day) + timedelta(days=1)):
        covered = execute_natural_query("Nikola Jokic stats yesterday")
    assert covered.result_status == "ok", (covered.result_reason, covered.metadata)
    assert covered.metadata["start_date"] == latest_day == covered.metadata["end_date"]
    assert covered.metadata["season"] == "2025-26"
    games = covered.result.to_dict()["sections"]["finder"]
    assert [int(game["game_id"]) for game in games] == yesterday["game_id"].astype(int).tolist()
    assert sum(game["pts"] for game in games) == pytest.approx(yesterday["pts"].sum())

    with request_calendar(date(2026, 7, 28)):
        stale = execute_natural_query("Nikola Jokic stats yesterday")
        retained = execute_natural_query("Nikola Jokic summary last 5 games in 2025-26")
    assert stale.result_reason == "no_data"
    assert stale.metadata["start_date"] == "2026-07-27" == stale.metadata["end_date"]
    assert "2026-07-27" in " ".join(stale.result.notes)
    assert retained.result_status == "ok", (retained.result_reason, retained.metadata)
    assert retained.metadata["last_n"] == 5
    summary = retained.result.to_dict()["sections"]["summary"][0]
    assert summary["games"] == 5
    assert summary["pts_sum"] == pytest.approx(rows.tail(5)["pts"].sum())


@pytest.mark.needs_data
@pytest.mark.parametrize(
    ("question", "request_day", "start", "end", "seasons"),
    [
        (
            "Cavaliers record since January 2026 through yesterday",
            date(2026, 4, 10),
            "2026-01-01",
            "2026-04-09",
            ["2025-26"],
        ),
        (
            "Cavaliers record from March 1, 2025 to yesterday",
            date(2026, 4, 10),
            "2025-03-01",
            "2026-04-09",
            ["2024-25", "2025-26"],
        ),
        (
            "Cavaliers record between March 1st, 2025 and last night",
            date(2026, 4, 10),
            "2025-03-01",
            "2026-04-09",
            ["2024-25", "2025-26"],
        ),
        (
            "Cavaliers record from yesterday thru April 9, 2026",
            date(2026, 4, 2),
            "2026-04-01",
            "2026-04-09",
            ["2025-26"],
        ),
    ],
)
def test_literal_range_preserves_both_ends_in_the_served_record(
    question, request_day, start, end, seasons
):
    from nbatools.data_source import data_read_csv
    from nbatools.query_service import execute_natural_query

    raw = pd.concat([data_read_csv(f"raw/team_game_stats/{s}_regular_season.csv") for s in seasons])
    dates = raw["game_date"]
    selected = raw.loc[(raw["team_id"] == 1610612739) & dates.between(start, end)]
    assert len(selected) > 1
    with request_calendar(request_day):
        result = execute_natural_query(question)
    assert result.result_status == "ok", (result.result_reason, result.metadata)
    assert result.metadata["start_date"] == start
    assert result.metadata["end_date"] == end
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert summary["games"] == len(selected)
    assert summary["wins"] == (selected["wl"] == "W").sum()
    assert summary["losses"] == (selected["wl"] == "L").sum()
    assert not any("snapshot cutoff" in note for note in result.metadata.get("notes", []))
