"""C2: "most points" over several seasons ranks the total.

"most career points", "most playoff points all time" and "most points since
2000" ranked the best scoring average; over a span the most points is the
cumulative list. "per game" / "average" keeps the rate, and single-season
boards and one-season questions are unchanged. Expected totals come from the
fixture CSVs.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = pytest.mark.query

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


@pytest.mark.parametrize(
    ("query", "stat"),
    [
        ("most career points", "pts_total"),
        ("most playoff points all time", "pts_total"),
        ("most rebounds in the 2010s", "reb_total"),
        ("all time scoring leaders", "pts_total"),
        ("most threes over the last 3 seasons", "fg3m_total"),
        ("most points per game since 2000", "pts"),
        ("most points averaged since 2000", "pts"),
        ("most points this season", "pts"),
        ("scoring leaders since 2000", "pts"),
    ],
)
def test_span_most_is_a_total(query, stat):
    assert parse_query(query)["route_kwargs"]["stat"] == stat


@pytest.mark.parametrize(
    "query",
    ["most points in a single season since 2000", "most points in any season since 2023"],
)
def test_single_season_board_is_unchanged(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["stat"] == "pts" and kwargs["per_season"] is True


@pytest.mark.fixture_data
def test_most_points_since_2023_ranks_the_total():
    games = pd.concat(
        pd.read_csv(RAW / "player_game_stats" / f"{s}_regular_season.csv")
        for s in ("2023-24", "2024-25", "2025-26")
    )
    totals = games.groupby("player_name")["pts"].sum().sort_values(ascending=False)

    result = execute_natural_query("most points since 2023")
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert rows[0]["player_name"] == totals.index[0]
    assert rows[0]["pts_total"] == totals.iloc[0]
