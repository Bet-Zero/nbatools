"""C1: "did LeBron score 30 last game" checks his last game.

The condition picked which game: it answered with his last 30-point game
(2026-09-26, 32) when his last game had 22. The last game is listed and the
answer says yes or no. Expected values come from the fixture's rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _last(kind: str, column: str, name: str) -> pd.Series:
    games = pd.read_csv(RAW / kind / "2025-26_regular_season.csv")
    games = games[games[column] == name]
    return games.sort_values("game_date").iloc[-1]


@pytest.mark.parametrize(
    ("query", "check"),
    [
        ("did LeBron score over 30 points last game", lambda g: g["pts"] > 30),
        ("did LeBron score 20 last game", lambda g: g["pts"] >= 20),
        ("did LeBron have 10 assists in his last game", lambda g: g["ast"] >= 10),
        ("was LeBron over 30 points last game", lambda g: g["pts"] > 30),
        ("did LeBron score 20 and 8 assists last game", lambda g: g["pts"] >= 20 and g["ast"] >= 8),
    ],
)
def test_player_last_game_yes_no(query, check):
    last = _last("player_game_stats", "player_name", "LeBron James")
    result = execute_natural_query(query)
    rows = result.result.to_dict()["sections"]["finder"]
    assert [row["game_id"] for row in rows] == [last["game_id"]]
    assert result.metadata["answer_phrase"].startswith("Yes" if check(last) else "No")


@pytest.mark.parametrize(
    ("query", "check"),
    [
        ("did the Lakers score 120 last game", lambda g: g["pts"] >= 120),
        ("did the Lakers win last game", lambda g: g["wl"] == "W"),
        ("did the Lakers lose last game", lambda g: g["wl"] == "L"),
    ],
)
def test_team_last_game_yes_no(query, check):
    last = _last("team_game_stats", "team_abbr", "LAL")
    result = execute_natural_query(query)
    rows = result.result.to_dict()["sections"]["finder"]
    assert [row["game_id"] for row in rows] == [last["game_id"]]
    assert result.metadata["answer_phrase"].startswith("Yes" if check(last) else "No")


def test_last_qualifying_game_keeps_its_reading():
    # Not a yes/no question: the most recent 30-point game.
    games = pd.read_csv(RAW / "player_game_stats/2025-26_regular_season.csv")
    games = games[(games["player_name"] == "LeBron James") & (games["pts"] >= 30)]
    rows = execute_natural_query("LeBron last game with 30 points").result.to_dict()["sections"][
        "finder"
    ]
    assert [row["game_id"] for row in rows] == [games.sort_values("game_date").iloc[-1]["game_id"]]


def _last_where(kind: str, column: str, name: str, keep) -> pd.Series:
    games = pd.read_csv(RAW / kind / "2025-26_regular_season.csv")
    games = games[(games[column] == name)]
    games = games[keep(games)]
    return games.sort_values("game_date").iloc[-1]


@pytest.mark.parametrize(
    ("query", "name", "check"),
    [
        # Other words for the last game.
        (
            "did LeBron score 30 or more points in his most recent game",
            "LeBron James",
            lambda g: g["pts"] >= 30,
        ),
        ("did LeBron score 30 in his last game", "LeBron James", lambda g: g["pts"] >= 30),
        ("did LeBron win last game", "LeBron James", lambda g: g["wl"] == "W"),
        # Triple / double doubles check the last game.
        (
            "did Nikola Jokic have a triple double last game",
            "Nikola Jokić",
            lambda g: sum(g[c] >= 10 for c in ("pts", "reb", "ast", "stl", "blk")) >= 3,
        ),
        (
            "did LeBron have a double double last game",
            "LeBron James",
            lambda g: sum(g[c] >= 10 for c in ("pts", "reb", "ast", "stl", "blk")) >= 2,
        ),
    ],
)
def test_more_player_last_game_forms(query, name, check):
    last = _last("player_game_stats", "player_name", name)
    result = execute_natural_query(query)
    rows = result.result.to_dict()["sections"]["finder"]
    assert [row["game_id"] for row in rows] == [last["game_id"]]
    assert result.metadata["answer_phrase"].startswith("Yes" if check(last) else "No")


def test_last_home_game():
    last = _last_where(
        "player_game_stats", "player_name", "LeBron James", lambda g: g["is_home"] == 1
    )
    result = execute_natural_query("did LeBron score 30 in his last home game")
    rows = result.result.to_dict()["sections"]["finder"]
    assert [row["game_id"] for row in rows] == [last["game_id"]]
    assert "last home game" in result.metadata["answer_phrase"]


def test_team_most_recent_game():
    last = _last("team_game_stats", "team_abbr", "BOS")
    result = execute_natural_query("did Boston win their most recent game")
    assert result.metadata["answer_phrase"].startswith("Yes" if last["wl"] == "W" else "No")


@pytest.mark.parametrize(
    "query",
    [
        # Not one subject's row, or a bound the answer cannot phrase: no yes/no.
        "did any Lakers player score 40 last game",
        "did the Lakers win by 10 last game",
    ],
)
def test_no_yes_no_answer_for_other_shapes(query):
    phrase = execute_natural_query(query).metadata.get("answer_phrase") or ""
    assert not phrase.startswith(("Yes", "No"))


@pytest.mark.parametrize(
    "text",
    ["was points over 110 last season", "was assists over 25 last game", "was losses over 50"],
)
def test_wizards_stat_questions_keep_the_team(text):
    from nbatools.commands.entity_resolution import mask_copula_team_lookalikes

    assert "was" in mask_copula_team_lookalikes(text).split()
