"""C1: "how many Lakers players scored 40" reads the team's players.

"did any Lakers player score 40", "Lakers players with 40 point games", "how
many Lakers players scored 30" and "anyone on the Lakers score 30" read the
team's points (60 "games with 40+ points"). They list the team's players'
games and count players. Expected values come from the fixture's player rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/player_game_stats")


def _lakers() -> pd.DataFrame:
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    return games[games["team_abbr"] == "LAL"]


@pytest.mark.parametrize(
    ("query", "floor"),
    [
        ("how many Lakers players scored 40 this season", 40),
        ("how many Lakers players scored 30 this season", 30),
    ],
)
def test_count_is_players(query, floor):
    games = _lakers()
    expected = games[games["pts"] >= floor]["player_id"].nunique()
    result = execute_natural_query(query)
    assert result.result.to_dict()["sections"]["count"] == [{"count": int(expected)}]
    assert "Los Angeles Lakers player" in result.metadata["count_phrase"]


@pytest.mark.parametrize(
    ("query", "keep"),
    [
        ("Lakers players with 40 point games", lambda g: g["pts"] >= 40),
        ("has any Lakers player scored 40 this season", lambda g: g["pts"] >= 40),
        ("did anyone on the Lakers score 30", lambda g: g["pts"] >= 30),
        ("Lakers players with 20 rebounds", lambda g: g["reb"] >= 20),
        (
            "Lakers players over 30 points vs the Celtics",
            lambda g: (g["pts"] > 30) & (g["opponent_team_abbr"] == "BOS"),
        ),
    ],
)
def test_list_is_the_players_games(query, keep):
    games = _lakers()
    expected = set(games[keep(games)]["game_id"].astype(str) + games[keep(games)]["player_name"])
    rows = execute_natural_query(query).result.to_dict()["sections"]["finder"]
    assert {str(r["game_id"]) + r["player_name"] for r in rows} == expected


def test_last_game_window_refuses():
    result = execute_natural_query("did any Lakers player score 40 last game")
    assert result.result_status == "no_result"


def test_season_totals_keep_their_board():
    result = execute_natural_query("how many Lakers players have 1000 points")
    assert result.route == "season_leaders"


@pytest.mark.parametrize(
    "query",
    [
        # Conditions the players' game list cannot apply refuse (they were dropped).
        "how many Lakers players had 30 points and 10 rebounds",
        "Lakers players with 20 points 10 rebounds and 10 assists",
        "how many Lakers players scored 30 at least twice",
        "how many Lakers players have at least 3 30 point games",
        "how many Lakers players scored 30 without LeBron",
        "how many Lakers players scored 30 in the 4th quarter",
        "how many Lakers players scored 30 against winning teams",
        "how many Lakers and Celtics players scored 30",
        # Opponent conference/division and modifiers the list cannot apply.
        "how many Lakers players scored 30 against the Atlantic division",
        "Lakers players with 30 points against the west",
        "how many Lakers players scored 30 with 5 threes",
        "how many Lakers players scored 30 with 5 3-pointers",
        # "how many times" must not switch off the modifier refusals.
        "how many times has a Lakers player scored 30 on Christmas",
        "how many times has a Lakers player scored 30 in the first 10 games",
        "how many times has a Lakers player scored 30 off the bench",
    ],
)
def test_other_conditions_refuse(query):
    assert execute_natural_query(query).result_status == "no_result"


def test_count_reads_every_row():
    # It counted after a 200-row cap.
    games = pd.concat(
        [pd.read_csv(RAW / f"{s}_regular_season.csv") for s in ("2023-24", "2024-25", "2025-26")]
    )
    games = games[(games["team_abbr"] == "LAL") & (games["pts"] >= 10)]
    result = execute_natural_query("how many Lakers players scored 10 from 2023-24 to 2025-26")
    assert result.result.to_dict()["sections"]["count"] == [
        {"count": int(games["player_id"].nunique())}
    ]


def test_how_many_times_counts_games():
    games = _lakers()
    result = execute_natural_query("how many times has a Lakers player scored 40")
    assert result.result.to_dict()["sections"]["count"] == [
        {"count": int((games["pts"] >= 40).sum())}
    ]
    assert result.metadata["count_phrase"].startswith("Los Angeles Lakers players have had")


def test_threes_as_the_stat_answers():
    games = _lakers()
    games = games[games["fg3m"] >= 5]
    result = execute_natural_query("how many Lakers players made 5 threes")
    assert result.result.to_dict()["sections"]["count"] == [
        {"count": int(games["player_id"].nunique())}
    ]


def test_sentence_names_losses():
    phrase = execute_natural_query("how many Lakers players scored 30 in losses").metadata[
        "count_phrase"
    ]
    assert "in losses" in phrase


def test_games_count_sentence_names_losses():
    games = _lakers()
    pts30_losses = games[(games["pts"] >= 30) & (games["wl"] == "L")]
    result = execute_natural_query("how many times has a Lakers player scored 30 in losses")
    assert result.result.to_dict()["sections"]["count"] == [{"count": len(pts30_losses)}]
    assert "in losses" in result.metadata["count_phrase"]
