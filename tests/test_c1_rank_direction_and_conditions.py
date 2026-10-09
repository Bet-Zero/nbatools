"""C1: ranked game lists keep their direction and their condition.

"LeBron lowest 3 scoring games" / "worst 3 scoring games" ranked highest
first (a count between the rank word and the stat); "Celtics fewest points
allowed" ranked the Celtics' own points; "top 3 scoring games while shooting
5 threes" / "where they made 15 threes" dropped the condition. Expected values
come from the fixture's game rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _rows(query: str) -> list[dict]:
    return execute_natural_query(query).result.to_dict()["sections"]["finder"]


def _lebron() -> pd.DataFrame:
    games = pd.read_csv(RAW / "player_game_stats/2025-26_regular_season.csv")
    return games[games["player_name"] == "LeBron James"]


def _team(abbr: str) -> pd.DataFrame:
    games = pd.read_csv(RAW / "team_game_stats/2025-26_regular_season.csv")
    return games[games["team_abbr"] == abbr]


@pytest.mark.parametrize(
    ("query", "keep"),
    [
        ("LeBron lowest 3 scoring games with 5 assists", lambda g: g["ast"] >= 5),
        ("LeBron worst 3 scoring games", lambda g: g["pts"] > -1),
    ],
)
def test_lowest_n_ranks_from_the_bottom(query, keep):
    games = _lebron()
    games = games[keep(games)]
    assert [r["pts"] for r in _rows(query)] == games["pts"].nsmallest(3).tolist()


def test_fewest_points_allowed_ranks_the_opponent_score():
    games = pd.read_csv(RAW / "team_game_stats/2025-26_regular_season.csv")
    opp = games[["game_id", "team_abbr", "pts"]].rename(
        columns={"team_abbr": "opp", "pts": "opponent_pts"}
    )
    bos = games[games["team_abbr"] == "BOS"].merge(opp, on="game_id")
    bos = bos[bos["opp"] != "BOS"]
    rows = _rows("Celtics fewest points allowed")
    assert [r["opponent_pts"] for r in rows[:5]] == bos["opponent_pts"].nsmallest(5).tolist()


@pytest.mark.parametrize(
    ("query", "rows", "rank", "keep"),
    [
        (
            "LeBron top 3 scoring games while shooting 5 threes",
            _lebron,
            "pts",
            lambda g: g["fg3m"] >= 5,
        ),
        (
            "LeBron top 3 scoring games when he had 10 assists",
            _lebron,
            "pts",
            lambda g: g["ast"] >= 10,
        ),
        (
            "Lakers top 3 scoring games where they made 15 threes",
            lambda: _team("LAL"),
            "pts",
            lambda g: g["fg3m"] >= 15,
        ),
    ],
)
def test_while_where_when_conditions_apply(query, rows, rank, keep):
    games = rows()
    games = games[keep(games)]
    result = _rows(query)
    assert [r[rank] for r in result] == games[rank].nlargest(3).tolist()
    assert {r["game_id"] for r in result} <= set(games["game_id"])


@pytest.mark.parametrize(
    ("query", "stat", "n"),
    [
        # The count is the row count, not a bar ("3 assist" read as 3+ assists).
        ("LeBron lowest 3 rebounding games", "reb", 3),
        ("LeBron lowest 5 assist games", "ast", 5),
        ("LeBron fewest 3 assist games", "ast", 3),
        ("LeBron lowest 3 games by assists", "ast", 3),
        ("LeBron worst 5 passing games", "ast", 5),
        ("LeBron lowest 3 three point games", "fg3m", 3),
    ],
)
def test_lowest_n_stat_games(query, stat, n):
    rows = _rows(query)
    assert [r[stat] for r in rows] == _lebron()[stat].nsmallest(n).tolist()


@pytest.mark.parametrize(
    ("query", "rows", "stat"),
    [
        # A high value is the bad one: "worst" is the most.
        ("LeBron worst turnover games", _lebron, "tov"),
        ("Lakers worst turnover games", lambda: _team("LAL"), "tov"),
    ],
)
def test_worst_turnovers_are_the_most(query, rows, stat):
    result = _rows(query)
    assert [r[stat] for r in result[:3]] == rows()[stat].nlargest(3).tolist()


@pytest.mark.parametrize(
    ("query", "keep"),
    [
        # A team clause filters the team's games, not the player's own stat.
        ("LeBron top scoring games when the Lakers had 30 assists", ("LAL", "ast", 30)),
        ("LeBron top scoring games when they made 12 threes", ("LAL", "fg3m", 12)),
    ],
)
def test_team_clause_is_not_the_players_stat(query, keep):
    team, stat, floor = keep
    teams = _team(team)
    games = _lebron()
    games = games[games["game_id"].isin(teams[teams[stat] >= floor]["game_id"])]
    result = _rows(query)
    assert [r["pts"] for r in result[:4]] == games["pts"].nlargest(4).tolist()


def test_top_n_counts_keep_their_rows():
    assert len(_rows("LeBron top 12 rebounding games")) == 12
    assert len(_rows("LeBron top 10 assist games")) == 10


@pytest.mark.parametrize(
    ("query", "rows", "stat", "floor"),
    [
        # "at least N <stat> games" is a bound, not "the N lowest".
        ("LeBron at least 10 assist games", _lebron, "ast", 10),
        ("Lakers at least 30 assist games", lambda: _team("LAL"), "ast", 30),
    ],
)
def test_at_least_n_stat_games_is_a_bound(query, rows, stat, floor):
    games = rows()
    expected = games[games[stat] >= floor]
    assert {r["game_id"] for r in _rows(query)} == set(expected["game_id"])


def test_team_named_subject_applies():
    games = _team("BOS")
    games = games[games["fg3m"] >= 20]
    rows = _rows("Celtics highest scoring games where the Celtics made 20 threes")
    assert [r["pts"] for r in rows[:3]] == games["pts"].nlargest(3).tolist()
