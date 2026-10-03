"""Explicit calendar date ranges ("Knicks record from 2025-11-01 to 2025-12-15").

ISO dates used to read as the season "2025-11" and refuse with no data, and
"from November 1 to December 15" kept only its first date. Both ends of a
range now bound the sample, the season follows the dates, and a range that
crosses a season boundary spans both seasons. Expected values come straight
from the fixture's game CSVs, never from the engine.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from nbatools.commands._date_utils import (
    CURRENT_QUERY_DATE,
    explicit_date_is_open_ended,
    extract_date_range,
    invalid_explicit_date,
    seasons_for_explicit_dates,
)
from nbatools.commands._parse_helpers import extract_season, extract_since_season

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _rows(kind: str, seasons: tuple[str, ...], **match: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for season in seasons:
        with (RAW / kind / f"{season}_regular_season.csv").open(encoding="utf-8") as handle:
            rows += [
                row
                for row in csv.DictReader(handle)
                if all(row[key] == value for key, value in match.items())
            ]
    return rows


def _in_range(rows: list[dict[str, str]], start: str, end: str) -> list[dict[str, str]]:
    return [row for row in rows if start <= row["game_date"] <= end]


def _record(rows: list[dict[str, str]]) -> dict[str, int]:
    return {
        "games": len(rows),
        "wins": sum(row["wl"] == "W" for row in rows),
        "losses": sum(row["wl"] == "L" for row in rows),
    }


@pytest.mark.parametrize(
    ("text", "season", "expected"),
    [
        ("knicks record from 2025-11-01 to 2025-12-15", "2025-26", ("2025-11-01", "2025-12-15")),
        ("knicks record between 2025-11-01 and 2025-12-15", None, ("2025-11-01", "2025-12-15")),
        ("knicks record from november 1 to december 15", "2025-26", ("2025-11-01", "2025-12-15")),
        ("knicks record from december 15 to january 10", "2025-26", ("2025-12-15", "2026-01-10")),
        (
            "knicks record from november 1, 2024 through march 3, 2025",
            None,
            ("2024-11-01", "2025-03-03"),
        ),
        ("knicks record on 2025-11-05", None, ("2025-11-05", "2025-11-05")),
        ("knicks record from 2025-02-30 to 2025-03-05", None, (None, None)),
    ],
)
def test_extract_date_range_bounds_both_ends(text, season, expected):
    assert extract_date_range(text, season) == expected


def test_iso_dates_are_not_seasons():
    assert extract_season("knicks record from 2025-11-01 to 2025-12-15") is None
    assert extract_season("knicks record 2025-26") == "2025-26"
    assert extract_since_season("knicks record since 2025-11-01") is None
    assert extract_since_season("knicks record since 2023-24") == "2023-24"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("from 2025-11-01 to 2025-12-15", ("2025-26", "2025-26")),
        ("from 2025-03-01 to 2025-11-15", ("2024-25", "2025-26")),
        ("in january 2024", ("2023-24", "2023-24")),
        ("from november 1 to december 15", (None, None)),
    ],
)
def test_seasons_follow_explicit_dates(text, expected):
    assert seasons_for_explicit_dates(text) == expected


@pytest.mark.fixture_data
@pytest.mark.query
@pytest.mark.parametrize(
    ("query", "seasons", "start", "end"),
    [
        ("Knicks record from 2025-11-01 to 2025-12-15", ("2025-26",), "2025-11-01", "2025-12-15"),
        (
            "Knicks record between 2025-11-01 and 2025-12-15",
            ("2025-26",),
            "2025-11-01",
            "2025-12-15",
        ),
        (
            "Knicks record from November 1, 2025 to December 15, 2025",
            ("2025-26",),
            "2025-11-01",
            "2025-12-15",
        ),
        (
            "Knicks record from 2025-03-01 to 2025-11-15",
            ("2024-25", "2025-26"),
            "2025-03-01",
            "2025-11-15",
        ),
        ("Celtics record from 2024-01-10 to 2024-02-20", ("2023-24",), "2024-01-10", "2024-02-20"),
    ],
)
def test_team_record_over_explicit_range_matches_fixture(query, seasons, start, end):
    from nbatools.query_service import execute_natural_query

    team = "NYK" if query.startswith("Knicks") else "BOS"
    expected = _record(_in_range(_rows("team_game_stats", seasons, team_abbr=team), start, end))
    assert expected["games"] > 0

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert {key: summary[key] for key in expected} == expected


@pytest.mark.fixture_data
@pytest.mark.query
def test_player_games_over_explicit_range_match_fixture():
    from nbatools.query_service import execute_natural_query

    expected = sorted(
        int(row["game_id"])
        for row in _in_range(
            _rows("player_game_stats", ("2025-26",), player_name="Jalen Brunson"),
            "2025-11-01",
            "2025-12-15",
        )
    )
    assert expected

    result = execute_natural_query("Jalen Brunson stats from 2025-11-01 to 2025-12-15")
    assert result.result_status == "ok", result.result_reason
    rows = result.result.to_dict()["sections"]["finder"]
    assert sorted(int(row["game_id"]) for row in rows) == expected


@pytest.mark.parametrize(
    ("text", "season", "expected"),
    [
        ("knicks record before 2023-10-30", None, (None, "2023-10-29")),
        ("knicks record until 2025-12-15", None, (None, "2025-12-15")),
        ("knicks record through december 15", "2025-26", (None, "2025-12-15")),
        ("knicks record prior to march 1, 2025", None, (None, "2025-02-28")),
    ],
)
def test_an_open_start_bounds_only_the_end(text, season, expected):
    assert extract_date_range(text, season) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("since 2025-03-01", True),
        ("since march 1, 2025", True),
        ("since january 2025", True),
        ("after 2024-01-01", True),
        ("since march 1", False),
        ("from 2025-03-01 to 2025-04-01", False),
    ],
)
def test_since_a_dated_day_runs_to_the_latest_season(text, expected):
    assert explicit_date_is_open_ended(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("knicks record on 2025-02-30", "2025-02-30"),
        ("knicks record from 2025-02-30 to 2025-03-10", "2025-02-30"),
        ("knicks record april 31", "april 31"),
        ("knicks record on february 29, 2025", "february 29, 2025"),
        ("knicks record on february 29, 2024", None),
        ("knicks record from 2025-11-01 to 2025-12-15", None),
        ("knicks record 2025-26", None),
    ],
)
def test_impossible_dates_are_named(text, expected):
    assert invalid_explicit_date(text) == expected


def _through_today(rows: list[dict[str, str]], start: str) -> list[dict[str, str]]:
    return _in_range(rows, start, CURRENT_QUERY_DATE.date().isoformat())


@pytest.mark.fixture_data
@pytest.mark.query
@pytest.mark.parametrize(
    ("query", "start"),
    [
        ("Knicks record since 2025-03-01", "2025-03-01"),
        ("Knicks record since 2024-01-01", "2024-01-01"),
        ("Knicks record since March 1, 2025", "2025-03-01"),
    ],
)
def test_since_an_earlier_season_counts_every_later_season(query, start):
    from nbatools.query_service import execute_natural_query

    seasons = ("2023-24", "2024-25", "2025-26")
    expected = _record(_through_today(_rows("team_game_stats", seasons, team_abbr="NYK"), start))
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert {key: summary[key] for key in expected} == expected


@pytest.mark.fixture_data
@pytest.mark.query
def test_until_a_date_counts_the_season_up_to_that_day():
    from nbatools.query_service import execute_natural_query

    expected = _record(
        _in_range(_rows("team_game_stats", ("2025-26",), team_abbr="NYK"), "", "2025-12-15")
    )
    assert expected["games"] > 1
    result = execute_natural_query("Knicks record until 2025-12-15")
    assert result.result_status == "ok", result.result_reason
    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert {key: summary[key] for key in expected} == expected


@pytest.mark.fixture_data
@pytest.mark.query
@pytest.mark.parametrize(
    "query", ["Knicks record on 2025-02-30", "Knicks record from 2025-02-30 to 2025-03-10"]
)
def test_an_impossible_date_is_refused_not_widened(query):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert any("invalid_date" in note for note in result.result.notes)
