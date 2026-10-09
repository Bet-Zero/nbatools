"""C1: month-and-year dates.

"since Jan. 2025" / "Jan, 2025" read the month in the current season
(2026-01-01: 32-12 for 75-29); "from January 2024 to March 2025" dropped the
dates (the whole span, 86-34 for 53-21). Expected values come from the
fixture's team rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands._date_utils import extract_date_range
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")


def _lakers(start: str, end: str | None = None) -> tuple[int, int]:
    games = pd.concat(
        [pd.read_csv(RAW / f"{s}_regular_season.csv") for s in ("2023-24", "2024-25", "2025-26")]
    )
    games = games[games["team_abbr"] == "LAL"]
    day = pd.to_datetime(games["game_date"])
    games = games[(day >= start) & ((day <= end) if end else True)]
    return int((games["wl"] == "W").sum()), int((games["wl"] == "L").sum())


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("since jan. 2025", ("2025-01-01", None)),
        ("since jan, 2025", ("2025-01-01", None)),
        ("since january, 2025", ("2025-01-01", None)),
        ("in dec. 2024", ("2024-12-01", "2024-12-31")),
        ("from january 2024 to march 2025", ("2024-01-01", "2025-03-31")),
        ("between january 2025 and march 2026", ("2025-01-01", "2026-03-31")),
        ("from jan. 2025 to mar. 2025", ("2025-01-01", "2025-03-31")),
        # A season label is not the month's year ("Jan. 2024-25" is January 2025).
        ("in jan. 2024-25", ("2025-01-01", "2025-01-31")),
        ("in march, 2024-25", ("2025-03-01", "2025-03-31")),
        # A range without "from".
        ("january 2024 to march 2025", ("2024-01-01", "2025-03-31")),
        ("jan 2025 - mar 2025", ("2025-01-01", "2025-03-31")),
    ],
)
def test_month_year_parsing(text, expected):
    assert extract_date_range(text, "2024-25") == expected


@pytest.mark.parametrize(
    ("query", "start", "end"),
    [
        ("Lakers record since Jan. 2025", "2025-01-01", None),
        ("Lakers record since Jan, 2025", "2025-01-01", None),
        ("Lakers record from January 2024 to March 2025", "2024-01-01", "2025-03-31"),
        ("Lakers record from October 2023 to April 2026", "2023-10-01", "2026-04-30"),
        ("Lakers record in March, 2024-25", "2025-03-01", "2025-03-31"),
        ("Lakers record January 2024 to March 2025", "2024-01-01", "2025-03-31"),
    ],
)
def test_month_year_records(query, start, end):
    summary = execute_natural_query(query).result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == _lakers(start, end)


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record in March 2024 and March 2025",
        "LeBron James points in January 2025 and March 2025",
    ],
)
def test_two_separate_months_refuse(query):
    # Read as one span (or the first month) before.
    assert execute_natural_query(query).result_status == "no_result"


def test_between_months_is_a_span():
    summary = execute_natural_query(
        "Lakers record between January 2025 and March 2026"
    ).result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == _lakers("2025-01-01", "2026-03-31")
