"""C1: games ranked by the final margin.

"Lakers biggest win", "worst loss", "largest margin of victory", "closest
games" listed games by date; "LeBron biggest win" was a season summary.
Expected orders come from the fixture's game rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _team(abbr: str, season: str = "2025-26") -> pd.DataFrame:
    games = pd.read_csv(RAW / "team_game_stats" / f"{season}_regular_season.csv")
    return games[games["team_abbr"] == abbr]


def _finder(query: str) -> list[dict]:
    return execute_natural_query(query).result.to_dict()["sections"]["finder"]


@pytest.mark.parametrize(
    ("query", "keep", "key", "ascending", "limit"),
    [
        # One game for a singular ("biggest win"), every game for a plural.
        ("Lakers biggest win this season", lambda g: g["plus_minus"] > 0, "pm", False, 1),
        ("Lakers biggest wins this season", lambda g: g["plus_minus"] > 0, "pm", False, 25),
        ("Lakers 5 biggest wins", lambda g: g["plus_minus"] > 0, "pm", False, 5),
        ("Lakers largest margins of victory", lambda g: g["plus_minus"] > 0, "pm", False, 25),
        ("Lakers worst loss", lambda g: g["plus_minus"] < 0, "pm", True, 1),
        ("Lakers worst losses", lambda g: g["plus_minus"] < 0, "pm", True, 25),
        # "best wins" are the biggest margins, like "best games".
        ("Lakers best wins", lambda g: g["plus_minus"] > 0, "pm", False, 25),
        ("Lakers closest losses", lambda g: g["plus_minus"] < 0, "pm", False, 25),
        ("Lakers closest games", lambda g: g["plus_minus"] != 0, "abs", True, 25),
    ],
)
def test_team_margin_rankings(query, keep, key, ascending, limit):
    games = _team("LAL")
    games = games[keep(games)]
    values = games["plus_minus"].abs() if key == "abs" else games["plus_minus"]
    expected = values.sort_values(ascending=ascending).head(limit).tolist()
    rows = _finder(query)
    got = [abs(r["plus_minus"]) if key == "abs" else r["plus_minus"] for r in rows]
    assert got == expected


def test_biggest_loss_against_an_opponent():
    games = _team("LAL")
    games = games[(games["opponent_team_abbr"] == "BOS") & (games["plus_minus"] < 0)]
    rows = _finder("Lakers biggest loss vs the Celtics")
    assert [r["plus_minus"] for r in rows] == sorted(games["plus_minus"])[: len(rows)]


def test_a_players_biggest_wins_rank_his_teams_margin():
    players = pd.read_csv(RAW / "player_game_stats" / "2025-26_regular_season.csv")
    games = _team("LAL")[["game_id", "plus_minus"]].rename(columns={"plus_minus": "team_pm"})
    lebron = players[players["player_name"] == "LeBron James"].merge(games, on="game_id")
    expected = lebron.loc[lebron["team_pm"] > 0, "team_pm"].sort_values(ascending=False)
    rows = _finder("LeBron biggest wins this season")
    assert [r["win_margin"] for r in rows] == expected.head(len(rows)).tolist()


def test_biggest_road_wins():
    games = _team("LAL")
    games = games[(games["plus_minus"] > 0) & (games["is_away"].astype(str).isin(["True", "1"]))]
    rows = _finder("Lakers biggest road wins")
    assert [r["plus_minus"] for r in rows] == sorted(games["plus_minus"], reverse=True)[:25]


@pytest.mark.parametrize(
    "query",
    [
        # Filters the game list cannot apply: not ranked (they were not dropped).
        "LeBron biggest wins on back to backs",
        "LeBron closest games on national tv",
        # Not a margin.
        "Lakers biggest 2024 wins",
    ],
)
def test_not_margin_ranked(query):
    from nbatools.commands.natural_query import parse_query

    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs.get("stat") not in ("win_margin", "loss_margin", "margin")
