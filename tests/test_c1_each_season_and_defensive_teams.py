"""C1: each season's top games, rating groups named as teams, three pointers.

"Lakers biggest win each season" gave one game (or the span's top 25),
"vs good / elite defensive teams" refused or became a player-list error,
"best three pointer games" became "best three games", and "Lakers top 5
games with 120 points and 30 assists" became a team board. Expected values
come from the fixture's rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")
SEASONS = ("2023-24", "2024-25", "2025-26")


def _games(kind: str) -> pd.DataFrame:
    return pd.concat(
        [pd.read_csv(RAW / kind / f"{season}_regular_season.csv") for season in SEASONS]
    )


def _lakers() -> pd.DataFrame:
    games = _games("team_game_stats")
    return games[games["team_abbr"] == "LAL"]


def _rows(query: str) -> list[dict]:
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    return result.result.to_dict()["sections"]["finder"]


def _per_season(games: pd.DataFrame, column: str, count: int = 1) -> list[tuple]:
    out = []
    for season in sorted(games["season"].unique(), reverse=True):
        top = games[games["season"] == season].sort_values(column, ascending=False).head(count)
        out += [(season, value) for value in top[column]]
    return out


@pytest.mark.parametrize(
    ("query", "column", "keep", "count"),
    [
        ("Lakers biggest win each season", "plus_minus", lambda g: g["wl"] == "W", 1),
        ("Lakers best game every season", "plus_minus", lambda g: g["pts"] > -1, 1),
        ("Lakers highest scoring game each season", "pts", lambda g: g["pts"] > -1, 1),
        ("Lakers top 2 scoring games each season", "pts", lambda g: g["pts"] > -1, 2),
    ],
)
def test_team_top_games_each_season(query, column, keep, count):
    games = _lakers()
    games = games[keep(games)]
    rows = _rows(query)
    assert [(row["season"], row[column]) for row in rows] == _per_season(games, column, count)


def test_player_top_game_each_season():
    players = _games("player_game_stats")
    lebron = players[players["player_name"] == "LeBron James"]
    rows = _rows("LeBron highest scoring game in each season")
    assert [(row["season"], row["pts"]) for row in rows] == _per_season(lebron, "pts")


@pytest.mark.parametrize(
    "query",
    [
        # No ranking word, a threshold or a count: every qualifying game of
        # the season, not each season's top one.
        "LeBron James 30 point games by season",
        "LeBron James games with 30 points each season",
        "how many 30 point games did LeBron James have each season",
        "LeBron most 30 point games each season",
    ],
)
def test_threshold_lists_by_season_keep_every_game(query):
    players = _games("player_game_stats")
    lebron = players[(players["player_name"] == "LeBron James") & (players["season"] == "2025-26")]
    assert len(_rows(query)) == int((lebron["pts"] >= 30).sum())


def test_team_threshold_list_per_season_keeps_every_game():
    games = _lakers()
    games = games[(games["season"] == "2025-26") & (games["pts"] >= 120)]
    assert len(_rows("Lakers games with 120 points per season")) == len(games)


def test_named_span_keeps_its_seasons():
    rows = _rows("Lakers biggest win each season since 2024-25")
    assert [row["season"] for row in rows] == ["2025-26", "2024-25"]


@pytest.mark.parametrize(
    ("query", "games", "wins"),
    [
        # 6-team fixture: the top 10 is every team, elite (5) leaves out MIA.
        ("Lakers record vs good defensive teams", 60, 47),
        ("Lakers record vs elite defensive teams", 48, 35),
        ("LeBron James games vs elite defensive teams", 48, 35),
        ("LeBron James averages vs top 3 defensive teams", 24, 11),
    ],
)
def test_defensive_teams_are_rating_groups(query, games, wins):
    row = execute_natural_query(query).result.to_dict()["sections"]["summary"][0]
    assert (row["games"], row["wins"]) == (games, wins)


def test_described_defensive_teams_still_refuse():
    result = execute_natural_query("Lakers record vs physical defensive teams")
    assert result.result_status == "no_result"


@pytest.mark.parametrize(
    ("query", "count"),
    [("Lakers best three pointer games", 25), ("Lakers top 3 3 pointer games", 3)],
)
def test_three_pointer_games_rank_by_threes(query, count):
    games = _lakers()
    games = games[games["season"] == "2025-26"]
    rows = _rows(query)
    assert [row["fg3m"] for row in rows] == games["fg3m"].nlargest(count).tolist()


def test_player_numbered_three_pointer_games():
    players = _games("player_game_stats")
    lebron = players[(players["player_name"] == "LeBron James") & (players["season"] == "2025-26")]
    rows = _rows("LeBron James top 5 three pointer games")
    assert [row["fg3m"] for row in rows] == lebron["fg3m"].nlargest(5).tolist()
    # A count before "three pointer games" is still a threes floor.
    rows = _rows("LeBron 5 three pointer games")
    assert len(rows) == int((lebron["fg3m"] >= 5).sum())


def test_team_top_games_with_two_conditions():
    games = _lakers()
    games = games[(games["season"] == "2025-26") & (games["pts"] >= 120) & (games["ast"] >= 30)]
    rows = _rows("Lakers top 5 games with 120 points and 30 assists")
    assert [row["plus_minus"] for row in rows] == games["plus_minus"].nlargest(5).tolist()


def test_counts_keep_the_occurrence_route():
    result = execute_natural_query("how many Lakers games with 120 points and 30 assists")
    assert result.route == "team_occurrence_leaders"
