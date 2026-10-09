"""C1: "LeBron's last 30 point game" is his most recent 30-point game.

The number after "last" was read as a game count: "LeBron's last 30 point
game" listed 23 games from his last 30 qualifying ones, ranked by points;
"Lakers last 130 point game" asked for 130 games; "Jokic last triple double"
listed all of them. A number written before a stat word is the game's bar,
a singular "game" is the most recent one, and last-N lists without a ranking
word read newest first. Expected values come from the fixture's game rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands._parse_helpers import extract_last_n
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")
SEASONS = ["2024-25", "2025-26"]


def _games(kind: str) -> pd.DataFrame:
    frames = [pd.read_csv(RAW / kind / f"{s}_regular_season.csv") for s in SEASONS]
    return pd.concat(frames).sort_values("game_date", ascending=False)


def _rows(query: str) -> list[dict]:
    return execute_natural_query(query).result.to_dict()["sections"]["finder"]


def _dates(rows: list[dict]) -> list[str]:
    return [str(r["game_date"])[:10] for r in rows]


@pytest.mark.parametrize(
    ("query", "name", "keep"),
    [
        ("LeBron's last 30 point game", "LeBron James", lambda g: g["pts"] >= 30),
        ("when was LeBron's last 30-point game", "LeBron James", lambda g: g["pts"] >= 30),
        ("LeBron last 10 assist game", "LeBron James", lambda g: g["ast"] >= 10),
        ("LeBron last 30 pt game", "LeBron James", lambda g: g["pts"] >= 30),
        ("LeBron last 30 point outing", "LeBron James", lambda g: g["pts"] >= 30),
        ("LeBron last 40 point performance", "LeBron James", lambda g: g["pts"] >= 40),
        ("when did LeBron last score 30", "LeBron James", lambda g: g["pts"] >= 30),
        ("Curry's last 5 3-pointer game", "Stephen Curry", lambda g: g["fg3m"] >= 5),
        ("Curry last 5 three pointer game", "Stephen Curry", lambda g: g["fg3m"] >= 5),
        (
            "Jokic last triple double",
            "Nikola Jokić",
            lambda g: (g[["pts", "reb", "ast", "stl", "blk"]] >= 10).sum(axis=1) >= 3,
        ),
    ],
)
def test_player_last_qualifying_game(query, name, keep):
    games = _games("player_game_stats")
    games = games[games["player_name"] == name]
    assert _dates(_rows(query)) == games[keep(games)]["game_date"].head(1).tolist()


def test_team_last_qualifying_game():
    games = _games("team_game_stats")
    games = games[(games["team_abbr"] == "LAL") & (games["pts"] >= 130)]
    assert _dates(_rows("Lakers last 130 point game")) == games["game_date"].head(1).tolist()


@pytest.mark.parametrize(
    "query",
    [
        "LeBron last 3 30 point games",
        "LeBron's most recent 3 30 point games",
        "LeBron's 3 most recent 30 point games",
        "LeBron's latest 3 30 point games",
        "last 3 30 point games by LeBron",
    ],
)
def test_last_n_qualifying_games_read_newest_first(query):
    games = _games("player_game_stats")
    games = games[(games["player_name"] == "LeBron James") & (games["pts"] >= 30)]
    assert _dates(_rows(query)) == games["game_date"].head(3).tolist()


@pytest.mark.parametrize(
    ("query", "name", "stat"),
    [
        ("LeBron last 10 pts", "LeBron James", "pts"),
        ("Curry last 10 threes", "Stephen Curry", "fg3m"),
    ],
)
def test_a_stat_without_a_game_noun_keeps_the_window(query, name, stat):
    games = _games("player_game_stats")
    games = games[games["player_name"] == name]
    assert sorted(_dates(_rows(query))) == sorted(games["game_date"].head(10).tolist())


def test_points_per_game_over_the_window_is_an_average():
    games = _games("player_game_stats")
    games = games[games["player_name"] == "LeBron James"].head(10)
    result = execute_natural_query("LeBron last 10 points per game")
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert summary["games"] == 10
    assert summary["pts_avg"] == pytest.approx(games["pts"].mean(), abs=0.05)


def test_a_ranking_word_keeps_the_ranking():
    rows = _rows("LeBron top 3 scoring games in his last 20")
    assert [r["pts"] for r in rows] == sorted((r["pts"] for r in rows), reverse=True)


@pytest.mark.parametrize(
    ("text", "last_n"),
    [
        ("last 30 point game", 1),
        ("last 30+ point game", 1),
        ("last 3 30 point games", 3),
        ("last 30 point games", None),
        ("last 10 games", 10),
        ("last 3 point games", 3),
        ("last 5 three point games", 5),
        ("last 3 games with 30 points", 3),
        ("last 10 pts", 10),
        ("last 10 threes", 10),
        ("last 10 points per game", 10),
        ("last 30 point and 10 assist game", 1),
    ],
)
def test_extract_last_n(text, last_n):
    assert extract_last_n(text) == last_n


@pytest.mark.parametrize(
    "text",
    [
        "the last time the lakers won 10 straight",
        "the last time lebron scored 30 in 2 straight games",
        "the last time the lakers won 60 games",
        "the last time lebron missed 10 games",
        "when was the last time the lakers had a top 3 pick",
        "the last time the lakers started 10-0",
        "when did the lakers last make the playoffs",
    ],
)
def test_last_time_streaks_and_season_counts_are_not_one_game(text):
    assert extract_last_n(text) is None


def test_last_time_streak_still_finds_the_streaks():
    result = execute_natural_query("the last time the Lakers won 10 straight")
    assert result.result_status == "ok"
