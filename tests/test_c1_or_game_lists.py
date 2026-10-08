"""C1: OR game lists ("LeBron 20 points or 10 assists").

Each clause was capped at 25 games (top by its own stat) before the merge, so
the list held an arbitrary 28 of LeBron's 47 such games; "last 10 games with
20 points or 10 assists" listed 18; "how many of his last 10 games had 20
points or 10 assists" counted 17 (the window was lost on the second clause).
Expected values come from the fixture's player game rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/player_game_stats")


def _lebron() -> pd.DataFrame:
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    games = games[games["player_name"] == "LeBron James"].copy()
    games["date"] = pd.to_datetime(games["game_date"])
    return games.sort_values("date", ascending=False)


def _ids(query: str) -> list:
    return [
        row["game_id"]
        for row in execute_natural_query(query).result.to_dict()["sections"]["finder"]
    ]


def test_or_list_holds_every_game():
    games = _lebron()
    either = games[(games["pts"] >= 20) | (games["ast"] >= 10)]
    assert sorted(_ids("LeBron 20 points or 10 assists")) == sorted(either["game_id"])


def test_top_n_caps_the_merged_list():
    assert len(_ids("top 5 LeBron games with 20 points or 10 assists")) == 5


def test_last_n_qualifying_is_the_most_recent_matches():
    games = _lebron()
    either = games[(games["pts"] >= 20) | (games["ast"] >= 10)].head(10)
    assert sorted(_ids("LeBron last 10 games with 20 points or 10 assists")) == sorted(
        either["game_id"]
    )


def test_last_n_window_carries_to_every_clause():
    window = _lebron().head(10)
    expected = int(((window["pts"] >= 20) | (window["ast"] >= 10)).sum())
    result = execute_natural_query("how many of LeBron's last 10 games had 20 points or 10 assists")
    assert result.result.to_dict()["sections"]["count"] == [{"count": expected}]
