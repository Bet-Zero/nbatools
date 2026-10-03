"""Explicit date ranges against the real 1996-97+ game rows.

Companion to ``test_explicit_date_ranges.py`` (fixture). Expected records come
from the raw ``team_game_stats`` / ``player_game_stats`` rows of the pinned
generation filtered by game date, never from the code under test.
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _team_rows(team: str, seasons: tuple[str, ...], start: str, end: str) -> pd.DataFrame:
    frame = pd.concat(
        data_read_csv(f"raw/team_game_stats/{season}_regular_season.csv", dtype={"game_id": str})
        for season in seasons
    )
    rows = frame[frame["team_abbr"] == team]
    dates = pd.to_datetime(rows["game_date"]).dt.strftime("%Y-%m-%d")
    return rows[(dates >= start) & (dates <= end)]


@pytest.mark.parametrize(
    ("query", "team", "seasons", "start", "end"),
    [
        (
            "Knicks record from 2024-11-01 to 2024-12-15",
            "NYK",
            ("2024-25",),
            "2024-11-01",
            "2024-12-15",
        ),
        (
            "Celtics record between 2023-01-01 and 2023-02-28",
            "BOS",
            ("2022-23",),
            "2023-01-01",
            "2023-02-28",
        ),
        (
            "Bulls record from November 1, 1997 to December 15, 1997",
            "CHI",
            ("1997-98",),
            "1997-11-01",
            "1997-12-15",
        ),
        (
            "Warriors record from 2024-03-01 to 2024-11-15",
            "GSW",
            ("2023-24", "2024-25"),
            "2024-03-01",
            "2024-11-15",
        ),
        # A since-date in an earlier season runs through every later season.
        ("Knicks record since 2025-03-01", "NYK", ("2024-25", "2025-26"), "2025-03-01", "9999"),
        # An open start: the date's season, up to and including the day.
        ("Knicks record until 2024-12-15", "NYK", ("2024-25",), "", "2024-12-15"),
    ],
)
def test_team_record_over_explicit_range_matches_raw_rows(query, team, seasons, start, end):
    from nbatools.query_service import execute_natural_query

    rows = _team_rows(team, seasons, start, end)
    assert not rows.empty
    expected = {
        "games": len(rows),
        "wins": int((rows["wl"] == "W").sum()),
        "losses": int((rows["wl"] == "L").sum()),
    }

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert {key: summary[key] for key in expected} == expected
