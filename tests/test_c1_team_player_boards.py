"""C1: a team's players, counted and ranked.

"Lakers player with the most 30 point games" listed team games; "which
Lakers player has the most triple doubles" ranked the whole league; "which
Laker ..." read no team; "how many 40 point games have Lakers players had"
counted players (1, not 2); "how many times did a Lakers player score 40"
counted team games; "Celtics players with a triple double" refused.
Expected values come from the fixture's player rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _team(abbr: str) -> pd.DataFrame:
    rows = pd.read_csv(RAW / "player_game_stats" / "2025-26_regular_season.csv")
    return rows[rows["team_abbr"] == abbr]


def _doubles(rows: pd.DataFrame) -> pd.Series:
    return (rows[["pts", "reb", "ast", "stl", "blk"]] >= 10).sum(axis=1)


def _sections(query: str) -> dict:
    return execute_natural_query(query).result.to_dict()["sections"]


@pytest.mark.parametrize(
    ("query", "abbr", "flag"),
    [
        ("Lakers player with the most 30 point games", "LAL", lambda r: r["pts"] >= 30),
        ("which Lakers player has the most 30 point games", "LAL", lambda r: r["pts"] >= 30),
        ("most 30 point games by a Laker", "LAL", lambda r: r["pts"] >= 30),
        ("which Laker has the most triple doubles", "LAL", lambda r: _doubles(r) >= 3),
        ("which Lakers player has the most triple doubles", "LAL", lambda r: _doubles(r) >= 3),
        ("who has the most double doubles for the Lakers", "LAL", lambda r: _doubles(r) >= 2),
        ("which Celtic has the most double doubles this season", "BOS", lambda r: _doubles(r) >= 2),
    ],
)
def test_occurrence_boards_keep_the_team(query, abbr, flag):
    rows = _team(abbr)
    counts = rows[flag(rows)].groupby("player_name").size().sort_values(ascending=False)
    board = _sections(query)["leaderboard"]
    assert board[0]["player_name"] == counts.index[0]
    skip = {
        "rank",
        "player_name",
        "player_id",
        "team_abbr",
        "games_played",
        "season",
        "season_type",
    }
    got = {r["player_name"]: next(v for k, v in r.items() if k not in skip) for r in board}
    assert got == counts.head(len(board)).to_dict()


@pytest.mark.parametrize(
    ("query", "column"),
    [
        ("which Lakers player scored the most points", "pts"),
        ("which Lakers player averages the most rebounds", "reb"),
        ("who has the most rebounds for the Celtics", "reb"),
    ],
)
def test_stat_boards_keep_the_team(query, column):
    abbr = "BOS" if "Celtics" in query else "LAL"
    means = _team(abbr).groupby("player_name")[column].mean().sort_values(ascending=False)
    board = _sections(query)["leaderboard"]
    assert {r["team_abbr"] for r in board} == {abbr}
    assert board[0]["player_name"] == means.index[0]


def test_most_total_points_for_a_team():
    totals = _team("LAL").groupby("player_name")["pts"].sum().sort_values(ascending=False)
    board = _sections("Lakers player with the most total points")["leaderboard"]
    assert [(r["player_name"], r["pts_total"]) for r in board[:3]] == list(totals.head(3).items())


def test_most_points_in_a_game_by_a_teams_player():
    rows = _team("LAL")
    finder = _sections("which Lakers player scored the most points in a game")["finder"]
    assert [r["pts"] for r in finder[:5]] == rows["pts"].nlargest(5).tolist()


@pytest.mark.parametrize(
    ("query", "abbr", "flag"),
    [
        ("how many 40 point games have Lakers players had", "LAL", lambda r: r["pts"] >= 40),
        ("how many 30 point games do Lakers players have", "LAL", lambda r: r["pts"] >= 30),
        ("how many times did a Lakers player score 40", "LAL", lambda r: r["pts"] >= 40),
        ("how many triple doubles do Celtics players have", "BOS", lambda r: _doubles(r) >= 3),
        ("how many double doubles have Lakers players had", "LAL", lambda r: _doubles(r) >= 2),
    ],
)
def test_game_counts(query, abbr, flag):
    rows = _team(abbr)
    assert _sections(query)["count"][0]["count"] == int(flag(rows).sum())


def test_player_count_stays_a_player_count():
    rows = _team("LAL")
    expected = rows.loc[rows["pts"] >= 40, "player_name"].nunique()
    assert _sections("how many Lakers players scored 40")["count"][0]["count"] == expected


def test_team_players_with_a_triple_double():
    rows = _team("BOS")
    expected = rows[_doubles(rows) >= 3]
    finder = _sections("Celtics players with a triple double")["finder"]
    assert sorted(r["game_id"] for r in finder) == sorted(expected["game_id"].astype(int))


def test_team_games_stay_team_games():
    result = execute_natural_query("Lakers games with the most points")
    assert result.metadata["route"] == "game_finder"


@pytest.mark.parametrize(
    "query",
    [
        # Not one of the team's players: left as they were.
        "which Laker game had the most points",
        "how many games has no Laker scored 30",
        "are the Lakers leading the league in rebounds",
        "who scored the most points at boston",
        "scoring leaders min minutes 2000",
        "who has the most points for the Lakers and Celtics",
    ],
)
def test_not_a_team_player_board(query):
    from nbatools.commands.natural_query import parse_query

    try:
        parsed = parse_query(query)
    except ValueError:
        return
    assert "team_players" not in " ".join(str(n) for n in parsed.get("notes") or [])


def test_board_against_an_opponent():
    rows = _team("LAL")
    rows = rows[(rows["opponent_team_abbr"] == "BOS") & (rows["pts"] >= 30)]
    counts = rows.groupby("player_name").size().to_dict()
    board = _sections("which Lakers player has the most 30 point games against the Celtics")[
        "leaderboard"
    ]
    skip = {
        "rank",
        "player_name",
        "player_id",
        "team_abbr",
        "games_played",
        "season",
        "season_type",
    }
    assert {
        r["player_name"]: next(v for k, v in r.items() if k not in skip) for r in board
    } == counts


def test_events_by_a_teams_player_are_player_games():
    rows = _team("LAL")
    finder = _sections("30 point games by a Laker")["finder"]
    assert len(finder) == int((rows["pts"] >= 30).sum())
