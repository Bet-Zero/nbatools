"""C1: "how many games since LeBron's last 30 point game".

It counted his 30-point games ("1 game with 30+ points"); "since the Lakers
lost" counted every loss. The answer is the subject's games after the most
recent qualifying one. Expected values come from the fixture's game rows over
the default two-season sample.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")
SEASONS = ["2024-25", "2025-26"]


def _games(kind: str, column: str, value: str) -> pd.DataFrame:
    frames = [pd.read_csv(RAW / kind / f"{s}_regular_season.csv") for s in SEASONS]
    games = pd.concat(frames)
    return games[games[column] == value]


def _triple(g: pd.DataFrame) -> pd.Series:
    return (g[["pts", "reb", "ast", "stl", "blk"]] >= 10).sum(axis=1) >= 3


@pytest.mark.parametrize(
    ("query", "kind", "column", "value", "keep"),
    [
        (
            "how many games since LeBron's last 30 point game",
            "player_game_stats",
            "player_name",
            "LeBron James",
            lambda g: g["pts"] >= 30,
        ),
        (
            "how many games has it been since LeBron scored 30",
            "player_game_stats",
            "player_name",
            "LeBron James",
            lambda g: g["pts"] >= 30,
        ),
        (
            "how many games since Curry's last 8 three game",
            "player_game_stats",
            "player_name",
            "Stephen Curry",
            lambda g: g["fg3m"] >= 8,
        ),
        (
            "how many games since LeBron's last triple double",
            "player_game_stats",
            "player_name",
            "LeBron James",
            _triple,
        ),
        (
            "how many games since the Lakers lost",
            "team_game_stats",
            "team_abbr",
            "LAL",
            lambda g: g["wl"] == "L",
        ),
        (
            "how many games since the Lakers scored 130",
            "team_game_stats",
            "team_abbr",
            "LAL",
            lambda g: g["pts"] >= 130,
        ),
    ],
)
def test_games_since_the_last_qualifying_game(query, kind, column, value, keep):
    games = _games(kind, column, value)
    last = games[keep(games)]["game_date"].max()
    since = int((games["game_date"] > last).sum())
    phrase = execute_natural_query(query).metadata["answer_phrase"]
    played = "has played" if kind == "player_game_stats" else "have played"
    assert f"{played} {since} game" in phrase
    assert f"on {last}" in phrase


def test_games_since_without_a_condition_refuses():
    assert execute_natural_query("how many games since LeBron").result_status == "no_result"


def test_last_loss_is_one_game():
    games = _games("team_game_stats", "team_abbr", "LAL")
    rows = execute_natural_query("Lakers last loss").result.to_dict()["sections"]["finder"]
    last = games[games["wl"] == "L"]["game_date"].max()
    assert [str(r["game_date"])[:10] for r in rows] == [last]


@pytest.mark.parametrize(
    "query",
    [
        "how many games since january has LeBron scored 30",
        "how many games since the all star break have the Lakers won",
        "how many games since 2024 has LeBron scored 30",
        "how many games since january LeBron scored 30",
        "how many games since the all star break the Lakers won",
        "how many games since december the Lakers lost",
        "how many games since january for LeBron with 30 points",
    ],
)
def test_a_date_window_keeps_its_count_reading(query):
    phrase = str(execute_natural_query(query).metadata.get("answer_phrase") or "")
    assert " since his last " not in phrase and " since their last " not in phrase


@pytest.mark.parametrize(
    ("query", "words"),
    [
        (
            "how many games since LeBron's last 30 point game against the Celtics",
            "since his last game with 30+ points against the Boston Celtics",
        ),
        (
            "how many games since LeBron scored 30 in a loss",
            "since his last game with 30+ points in a loss",
        ),
        (
            "how many games since LeBron scored 30 and had 10 assists",
            "since his last game with 30+ points and 10+ assists",
        ),
        (
            "how many games since LeBron scored fewer than 15",
            "since his last game with fewer than 15 points",
        ),
        (
            "how many games since LeBron scored more than 30",
            "since his last game with more than 30 points",
        ),
    ],
)
def test_the_sentence_names_every_condition(query, words):
    assert words in execute_natural_query(query).metadata["answer_phrase"]


def test_a_named_season_counts_every_game_since():
    games = _games("player_game_stats", "player_name", "LeBron James")
    old = pd.read_csv(RAW / "player_game_stats" / "2024-25_regular_season.csv")
    old = old[(old["player_name"] == "LeBron James") & (old["pts"] >= 30)]
    last = old["game_date"].max()
    since = int((games["game_date"] > last).sum())
    phrase = execute_natural_query(
        "how many games since LeBron's last 30 point game in 2024-25"
    ).metadata["answer_phrase"]
    assert f"has played {since} games" in phrase
    assert "30+ points in 2024-25" in phrase


@pytest.mark.parametrize(
    "query",
    [
        "how many games since LeBron and AD both scored 30",
        "how many games since the Lakers won by 20",
    ],
)
def test_conditions_the_answer_cannot_name_refuse(query):
    assert execute_natural_query(query).result_status == "no_result"
