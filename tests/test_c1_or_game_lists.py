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


def test_ranked_or_list_orders_by_the_ranking_stat():
    games = _lebron()
    either = games[(games["pts"] >= 30) | (games["ast"] >= 10)]
    top = either.sort_values("pts", ascending=False)["pts"].head(5).tolist()
    rows = execute_natural_query(
        "LeBron top 5 scoring games with 30 points or 10 assists"
    ).result.to_dict()["sections"]["finder"]
    assert [row["pts"] for row in rows] == top


def test_ranked_by_stat_keeps_the_clause_condition():
    # "top 3 games by assists with 20 points" stores its bound in the route's
    # conditions rather than min_value; the clause must not read as unbounded.
    games = _lebron()
    either = games[(games["pts"] >= 20) | (games["reb"] >= 10)]
    top = either.sort_values("ast", ascending=False)["ast"].head(3).tolist()
    rows = execute_natural_query(
        "LeBron top 3 games by assists with 20 points or 10 rebounds"
    ).result.to_dict()["sections"]["finder"]
    assert [row["ast"] for row in rows] == top
    assert set(row["game_id"] for row in rows) <= set(either["game_id"])


def test_playoffs_apply_to_every_clause():
    games = pd.read_csv(RAW / "2025-26_playoffs.csv")
    games = games[games["player_name"] == "LeBron James"]
    either = games[(games["pts"] >= 30) | (games["ast"] >= 10)]
    assert sorted(_ids("LeBron 30 points or 10 assists in the playoffs")) == sorted(
        either["game_id"]
    )


def test_a_span_applies_to_every_clause():
    frames = [
        pd.read_csv(RAW / f"{season}_regular_season.csv") for season in ("2024-25", "2025-26")
    ]
    games = pd.concat(frames)
    games = games[games["player_name"] == "LeBron James"]
    either = games[(games["pts"] >= 30) | (games["ast"] >= 10)]
    assert sorted(_ids("LeBron 30 points or 10 assists since 2024")) == sorted(either["game_id"])


def test_each_clause_keeps_its_own_season_and_season_type():
    frames = {
        name: pd.read_csv(RAW / f"{name}.csv")
        for name in ("2024-25_regular_season", "2025-26_regular_season", "2025-26_playoffs")
    }
    lebron = {k: v[v["player_name"] == "LeBron James"] for k, v in frames.items()}
    mixed = int((lebron["2024-25_regular_season"]["pts"] >= 30).sum()) + int(
        (lebron["2025-26_regular_season"]["ast"] >= 10).sum()
    )
    assert len(_ids("LeBron 30 points in 2024-25 or 10 assists in 2025-26")) == mixed
    types = int((lebron["2025-26_regular_season"]["pts"] >= 30).sum()) + int(
        (lebron["2025-26_playoffs"]["ast"] >= 10).sum()
    )
    assert (
        len(_ids("LeBron 30 points in the regular season or 10 assists in the playoffs")) == types
    )


@pytest.mark.parametrize(
    "query",
    [
        # A clause with no condition would list every game of that team.
        "Lakers or Celtics over 130 points",
        # Stats over the games are a summary, not a list.
        "LeBron stats in games with 30 points or 10 assists since 2024",
    ],
)
def test_or_questions_that_are_not_game_lists_refuse(query):
    assert execute_natural_query(query).result_status == "no_result"
