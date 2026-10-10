"""C1: "Lakers games at the Celtics" are road games against the Celtics.

The named home team became the subject ("Lakers record at Boston" gave the
Celtics' record; "LeBron stats at Boston" filtered to LeBron on the
Celtics). A team after "at" / "@" with a subject before it is the road
opponent. Expected values come from the fixture's game rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import _at_team
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _road(kind: str, column: str, value: str) -> pd.DataFrame:
    games = pd.read_csv(RAW / kind / "2025-26_regular_season.csv")
    return games[
        (games[column] == value) & (games["opponent_team_abbr"] == "BOS") & (games["is_away"] == 1)
    ]


@pytest.mark.parametrize(
    "query", ["Lakers games at the Celtics", "Lakers at Celtics", "Lakers @ Celtics"]
)
def test_team_games_at_a_team(query):
    games = _road("team_game_stats", "team_abbr", "LAL")
    rows = execute_natural_query(query).result.to_dict()["sections"]["finder"]
    assert sorted(str(r["game_date"])[:10] for r in rows) == sorted(games["game_date"].tolist())


def test_team_record_at_a_team():
    games = _road("team_game_stats", "team_abbr", "LAL")
    summary = execute_natural_query("Lakers record at Boston").result.to_dict()["sections"][
        "summary"
    ][0]
    assert (summary["wins"], summary["losses"]) == (
        int((games["wl"] == "W").sum()),
        int((games["wl"] == "L").sum()),
    )


def test_player_games_at_a_team():
    games = _road("player_game_stats", "player_name", "LeBron James")
    rows = execute_natural_query("LeBron games at the Celtics").result.to_dict()["sections"][
        "finder"
    ]
    assert sorted(str(r["game_date"])[:10] for r in rows) == sorted(games["game_date"].tolist())


@pytest.mark.parametrize(
    "text",
    [
        "lakers record at home",
        "lebron points at the half",
        "who scored the most points at boston",
        "lakers vs celtics at home",
    ],
)
def test_other_at_phrases_are_left_alone(text):
    assert _at_team(text) == text


def test_a_players_own_team_after_at_is_home():
    games = pd.read_csv(RAW / "player_game_stats" / "2025-26_regular_season.csv")
    games = games[
        (games["player_name"] == "Jayson Tatum")
        & (games["opponent_team_abbr"] == "LAL")
        & (games["is_home"] == 1)
    ]
    rows = execute_natural_query("Tatum points against the Lakers at Boston").result.to_dict()[
        "sections"
    ]["finder"]
    assert sorted(str(r["game_date"])[:10] for r in rows) == sorted(games["game_date"].tolist())


def test_a_teams_own_city_is_home():
    games = pd.read_csv(RAW / "team_game_stats" / "2025-26_regular_season.csv")
    games = games[(games["team_abbr"] == "BOS") & (games["is_home"] == 1)]
    summary = execute_natural_query("Celtics record at Boston").result.to_dict()["sections"][
        "summary"
    ][0]
    assert (summary["wins"], summary["losses"]) == (
        int((games["wl"] == "W").sum()),
        int((games["wl"] == "L").sum()),
    )


@pytest.mark.parametrize("query", ["LAL@BOS", "Lakers@Celtics"])
def test_at_sign_without_spaces(query):
    games = _road("team_game_stats", "team_abbr", "LAL")
    rows = execute_natural_query(query).result.to_dict()["sections"]["finder"]
    assert sorted(str(r["game_date"])[:10] for r in rows) == sorted(games["game_date"].tolist())


def test_an_opponent_already_named_is_the_road_team():
    games = _road("team_game_stats", "team_abbr", "LAL")
    summary = execute_natural_query("Lakers record against the Celtics at Boston").result.to_dict()[
        "sections"
    ]["summary"][0]
    assert summary["games"] == len(games)


@pytest.mark.parametrize(
    "text",
    ["lebron vs tatum at boston", "lakers vs celtics at boston", "lebron points at min 30"],
)
def test_compared_sides_and_minutes_are_left_alone(text):
    assert _at_team(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "teams that beat the lakers at boston",
        "who beat the lakers at boston",
        "jimmy butler averages at miami in 2023-24",
        "lebron career averages at boston",
    ],
)
def test_no_subject_or_another_season_for_a_player_is_left_alone(text):
    assert _at_team(text) == text


def test_player_team_cache_follows_the_data_generation(monkeypatch):
    from nbatools import data_source
    from nbatools.commands import data_utils
    from nbatools.commands import natural_query as nq

    frames = {
        "g1": pd.DataFrame({"player_name": ["Jimmy Butler"], "team_abbr": ["MIA"]}),
        "g2": pd.DataFrame({"player_name": ["Jimmy Butler"], "team_abbr": ["GSW"]}),
    }
    generation = {"key": "g1"}
    monkeypatch.setattr(data_source, "data_source_cache_key", lambda: generation["key"])
    monkeypatch.setattr(
        data_utils, "load_player_games_for_seasons", lambda *a, **k: frames[generation["key"]]
    )
    assert nq._player_latest_team("Jimmy Butler") == "MIA"
    generation["key"] = "g2"
    assert nq._player_latest_team("Jimmy Butler") == "GSW"
