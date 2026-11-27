"""Mixed calendar endpoints must select the complete requested game window."""

import csv
from datetime import date
from pathlib import Path

import pytest

from nbatools.commands._date_utils import extract_date_range
from nbatools.commands._seasons import request_calendar
from nbatools.query_service import execute_natural_query

FIXTURE_TEAM_GAMES = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")


@pytest.mark.query
@pytest.mark.fixture_data
@pytest.mark.parametrize(
    ("phrase", "start", "end", "seasons"),
    [
        ("from April 1, 2026 to yesterday", "2026-04-01", "2026-04-07", ("2025-26",)),
        ("between April 1, 2026 and yesterday", "2026-04-01", "2026-04-07", ("2025-26",)),
        ("between yesterday and April 10, 2026", "2026-04-07", "2026-04-10", ("2025-26",)),
        ("from yesterday through 2026-04-10", "2026-04-07", "2026-04-10", ("2025-26",)),
        (
            "between October 31, 2024 and yesterday",
            "2024-10-31",
            "2026-04-07",
            ("2024-25", "2025-26"),
        ),
    ],
)
def test_knicks_record_keeps_both_endpoints(monkeypatch, phrase, start, end, seasons):
    games = []
    for season in seasons:
        with (FIXTURE_TEAM_GAMES / f"{season}_regular_season.csv").open() as file:
            games.extend(csv.DictReader(file))

    # Fixture CSVs supply the statistics; they have no served freshness metadata.
    cutoff = max(row["game_date"] for row in games if row["season"] == seasons[-1])
    monkeypatch.setattr("nbatools.query_service.compute_current_through", lambda *_: cutoff)

    outcomes = [
        row["wl"] for row in games if row["team_abbr"] == "NYK" and start <= row["game_date"] <= end
    ]
    assert outcomes
    with request_calendar(date(2026, 4, 8)):
        result = execute_natural_query(f"Knicks record {phrase}")

    assert result.result_status == "ok", result.to_dict()
    payload = result.to_dict()
    metadata = payload["metadata"]
    assert metadata["team"] == "NYK"
    assert (metadata["start_date"], metadata["end_date"]) == (start, end)
    assert (metadata["start_season"] or metadata["season"]) == seasons[0]
    assert (metadata["end_season"] or metadata["season"]) == seasons[-1]
    summary = payload["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"], summary["games"]) == (
        outcomes.count("W"),
        outcomes.count("L"),
        len(outcomes),
    )


@pytest.mark.parser
@pytest.mark.parametrize(
    ("phrase", "bounds"),
    [
        ("between yesterday and tonight", ("2026-04-07", "2026-04-08")),
        ("2026-04-01 up to yesterday", ("2026-04-01", "2026-04-07")),
        ("from April 1, 2026 until yesterday", ("2026-04-01", "2026-04-07")),
        ("since April 1, 2026 before today", ("2026-04-01", "2026-04-07")),
        ("prior to yesterday", (None, "2026-04-06")),
        ("yesterday", ("2026-04-07", "2026-04-07")),
    ],
)
def test_mixed_ranges_keep_connector_meaning(phrase, bounds):
    with request_calendar(date(2026, 4, 8)):
        assert extract_date_range(phrase.lower(), "2025-26") == bounds
