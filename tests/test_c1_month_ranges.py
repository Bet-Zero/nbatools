"""C1: month-name ranges without days.

"Lakers record from January to March", "between January and March",
"January through March", "before March" and "in January and February" read
no dates (the whole season) or January alone. They are whole-month windows
in the asked season; "in January and March" and a backwards span ("from March
to January" in one season) refuse. Expected records come from the fixture's
game rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands import entity_resolution
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _lakers(*seasons: str) -> pd.DataFrame:
    games = pd.concat(
        [pd.read_csv(RAW / "team_game_stats" / f"{s}_regular_season.csv") for s in seasons]
    )
    games = games[games["team_abbr"] == "LAL"].copy()
    games["game_date"] = pd.to_datetime(games["game_date"])
    return games


@pytest.mark.parametrize(
    ("query", "start", "end", "season"),
    [
        ("Lakers record from January to March", "2026-01-01", "2026-03-31", "2025-26"),
        ("Lakers record between January and March", "2026-01-01", "2026-03-31", "2025-26"),
        ("Lakers record January through March", "2026-01-01", "2026-03-31", "2025-26"),
        ("Lakers record from Jan to Mar", "2026-01-01", "2026-03-31", "2025-26"),
        ("Lakers record from November to January", "2025-11-01", "2026-01-31", "2025-26"),
        ("Lakers record in January and February", "2026-01-01", "2026-02-28", "2025-26"),
        ("Lakers record before March", None, "2026-02-28", "2025-26"),
        ("Lakers record after March", "2026-04-01", None, "2025-26"),
        ("Lakers record through February", None, "2026-02-28", "2025-26"),
        ("Lakers record from January to March 2025", "2025-01-01", "2025-03-31", "2024-25"),
        ("Lakers record from November 2024 to January", "2024-11-01", "2025-01-31", "2024-25"),
        ("Lakers record in January and February 2025", "2025-01-01", "2025-02-28", "2024-25"),
        ("Lakers record in January, February and March", "2026-01-01", "2026-03-31", "2025-26"),
        # A comma before one season names that season.
        ("Lakers record from January to March, last season", "2025-01-01", "2025-03-31", "2024-25"),
        ("Lakers record from Jan to Mar, 2024-25", "2025-01-01", "2025-03-31", "2024-25"),
    ],
)
def test_month_ranges_are_whole_months(query, start, end, season):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs.get("start_date"), kwargs.get("end_date")) == (start, end)
    games = _lakers(season)
    if start:
        games = games[games["game_date"] >= start]
    if end:
        games = games[games["game_date"] <= end]
    summary = execute_natural_query(query).result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (
        int((games["wl"] == "W").sum()),
        int((games["wl"] == "L").sum()),
    )


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record in January and March",
        "Lakers record from March to January",
        # A range named for two seasons.
        "Lakers record between January and March 2024 and 2025",
        "Lakers record from Jan to Mar 2025 and 2026",
        "Lakers record from January to March this season and last season",
    ],
)
def test_months_that_are_not_one_span_refuse(query):
    parsed = parse_query(query)
    assert "month_pair" in parsed["route_kwargs"]["unsupported_filters"]
    assert execute_natural_query(query).result_status == "no_result"


@pytest.mark.parametrize(
    ("query", "start", "end"),
    [
        # Day and month-year forms read as before.
        ("Lakers record from March 1 to March 31", "2026-03-01", "2026-03-31"),
        ("LeBron averages from December 2024 to February 2025", "2024-12-01", "2025-02-28"),
        ("Lakers record in January", "2026-01-01", "2026-01-31"),
        ("Lakers record since January", "2026-01-01", None),
    ],
)
def test_other_date_forms_are_unchanged(query, start, end):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs.get("start_date"), kwargs.get("end_date")) == (start, end)


@pytest.mark.parametrize(
    ("query", "start", "end"),
    [
        ("Lakers record from March 2025 to January", "2025-03-01", "2026-01-31"),
        ("Lakers record from March to January 2026", "2025-03-01", "2026-01-31"),
    ],
)
def test_one_named_year_across_seasons_reads_both(query, start, end):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs["start_date"], kwargs["end_date"]) == (start, end)
    assert (kwargs["start_season"], kwargs["end_season"]) == ("2024-25", "2025-26")
    games = _lakers("2024-25", "2025-26")
    games = games[(games["game_date"] >= start) & (games["game_date"] <= end)]
    summary = execute_natural_query(query).result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (
        int((games["wl"] == "W").sum()),
        int((games["wl"] == "L").sum()),
    )


@pytest.mark.parametrize(
    "query",
    [
        # One cut per season is not one window.
        "Lakers record before March in the last 3 seasons",
        "Lakers record through February in the last 3 seasons",
    ],
)
def test_yearless_cuts_over_seasons_refuse(query):
    assert "date_window_per_season" in parse_query(query)["route_kwargs"]["unsupported_filters"]


def test_a_name_is_not_a_month():
    kwargs = parse_query("Lakers record after Jan Vesely left")["route_kwargs"]
    assert kwargs.get("start_date") is None


@pytest.mark.parametrize(
    ("query", "end"),
    [
        ("Lakers record since 2022 through March 1", "2026-03-01"),
        ("LeBron points through February since 2022", "2026-02-28"),
    ],
)
def test_since_a_season_through_a_date_is_one_window(query, end):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs["start_season"], kwargs["end_date"]) == ("2022-23", end)


@pytest.mark.parametrize(
    ("query", "start", "end"),
    [
        ("Lakers record in the month of March", "2026-03-01", "2026-03-31"),
        ("LeBron points per game during the month of March", "2026-03-01", "2026-03-31"),
        ("Lakers record in the months of January and February", "2026-01-01", "2026-02-28"),
    ],
)
def test_the_month_of_is_the_month(query, start, end):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs["start_date"], kwargs["end_date"]) == (start, end)


def test_the_month_of_record_matches_the_rows():
    games = _lakers("2025-26")
    games = games[(games["game_date"] >= "2026-03-01") & (games["game_date"] <= "2026-03-31")]
    rows = execute_natural_query("Lakers record in the month of March").result.to_dict()
    summary = rows["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (
        int((games["wl"] == "W").sum()),
        int((games["wl"] == "L").sum()),
    )


@pytest.mark.parametrize(
    "query",
    [
        # Two months to compare or choose between: it read the first alone.
        "LeBron points in March vs April",
        "Lakers average points in January vs February",
        "Lakers record in March or April",
        "LeBron points in March 2026 compared to April 2026",
        "LeBron points in the month of March vs April",
    ],
)
def test_months_compared_refuse(query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert "month_pair" in parse_query(query)["route_kwargs"]["unsupported_filters"]


@pytest.mark.parametrize(
    "query",
    [
        # A landmark the date reader does not place read the whole season.
        "Lakers record since Christmas",
        "LeBron points per game after Christmas",
        "LeBron christmas day games",
        "Lakers record before the All-Star break",
        "Lakers record up to the all star break",
        "Lakers record since the trade deadline",
        "Lakers record after Thanksgiving",
        "Lakers record since New Year's",
        # The date reader spells it "all-star" / "all star".
        "LeBron stats since the allstar break",
    ],
)
def test_unread_date_landmarks_refuse(query):
    assert execute_natural_query(query).result_status == "no_result"
    assert "date_landmark" in parse_query(query)["route_kwargs"]["unsupported_filters"]


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record after the All-Star break",
        "LeBron stats since the all star break",
        "LeBron points in March vs the Celtics",
        "how many all star games has LeBron played",
    ],
)
def test_read_windows_and_other_wording_keep_their_reading(query):
    assert parse_query(query)["route"] is not None


@pytest.fixture
def landmark_named_players(monkeypatch, request):
    entity_resolution.reset_player_index()
    request.addfinalizer(entity_resolution.reset_player_index)
    monkeypatch.setattr(entity_resolution, "data_source_cache_key", lambda: "landmark-names")
    monkeypatch.setattr(
        entity_resolution,
        "_read_player_names",
        lambda data_dir=None: {"Rakeem Christmas", "Tim Thanksgiving", "LeBron James"},
    )


def test_a_player_named_for_a_landmark_is_the_player(landmark_named_players):
    for query, name in (
        ("Rakeem Christmas stats 2016-17", "Rakeem Christmas"),
        ("Tim Thanksgiving stats", "Tim Thanksgiving"),
    ):
        parsed = parse_query(query)
        assert parsed["route_kwargs"].get("player") == name
        assert not parsed["route_kwargs"].get("unsupported_filters")
    kwargs = parse_query("Tim Thanksgiving stats after Christmas")["route_kwargs"]
    assert "date_landmark" in kwargs["unsupported_filters"]
