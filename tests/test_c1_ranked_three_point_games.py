"""C1: "LeBron top 3 three point games" ranks games by threes made.

It ranked his games by points ("three point" read as points, "3 point" as a
3-point bar). Expectations come from the fixture rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _rows(kind: str, seasons=("2025-26",)) -> pd.DataFrame:
    return pd.concat(
        [pd.read_csv(RAW / kind / f"{season}_regular_season.csv") for season in seasons]
    )


@pytest.mark.parametrize(
    ("query", "column", "value", "limit", "seasons", "ascending"),
    [
        ("LeBron top 3 three point games", "player_name", "LeBron James", 3, ("2025-26",), False),
        ("LeBron top 5 3 point games", "player_name", "LeBron James", 5, ("2025-26",), False),
        ("Curry best 5 3pt games", "player_name", "Stephen Curry", 5, ("2025-26",), False),
        (
            "LeBron top 3 three point games since 2024",
            "player_name",
            "LeBron James",
            3,
            ("2024-25", "2025-26"),
            False,
        ),
        ("LeBron lowest 3 three point games", "player_name", "LeBron James", 3, ("2025-26",), True),
        ("Lakers top 3 three point games", "team_abbr", "LAL", 3, ("2025-26",), False),
    ],
)
def test_ranked_three_point_games(query, column, value, limit, seasons, ascending):
    kind = "player_game_stats" if column == "player_name" else "team_game_stats"
    rows = _rows(kind, seasons)
    rows = rows[rows[column] == value]
    expected = rows["fg3m"].sort_values(ascending=ascending).head(limit).tolist()
    parsed = parse_query(query)
    assert parsed["route_kwargs"]["stat"] == "fg3m"
    assert parsed["route_kwargs"].get("min_value") is None
    got = [r["fg3m"] for r in execute_natural_query(query).result.to_dict()["sections"]["finder"]]
    assert got == expected


@pytest.mark.parametrize(
    "query",
    [
        "top 5 three point games",
        "show me the top 5 three point games",
        "who had the top 5 three point games this season",
        "in 2024-25 top 5 three point games",
        "rookie top 5 three point games",
        "which team had the top 5 three point games",
        # An opponent before the ranking is not the subject.
        "against the Celtics top 5 three point games",
        "vs Lakers top 5 three point games",
    ],
)
def test_the_league_form_reads_as_written(query):
    # Only a named player or team is rewritten; a lead-in alone keeps the
    # earlier reading (it would become a season board of threes per game).
    assert parse_query(query)["route_kwargs"].get("stat") != "fg3m"


def test_a_lead_in_before_a_named_subject():
    rows = _rows("player_game_stats")
    rows = rows[rows["player_name"] == "LeBron James"]
    result = execute_natural_query("show me LeBron top 3 three point games")
    got = [r["fg3m"] for r in result.result.to_dict()["sections"]["finder"]]
    assert got == rows["fg3m"].nlargest(3).tolist()


def test_a_player_against_an_opponent():
    rows = _rows("player_game_stats")
    rows = rows[(rows["player_name"] == "LeBron James") & (rows["opponent_team_abbr"] == "BOS")]
    result = execute_natural_query("LeBron against the Celtics top 3 three point games")
    got = [r["fg3m"] for r in result.result.to_dict()["sections"]["finder"]]
    assert got == rows["fg3m"].nlargest(3).tolist()
