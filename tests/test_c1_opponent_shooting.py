"""C1: "games where the opponent shot under 40 percent" bounds the opponent.

It filtered the team's own shooting ("holding opponents under 40 percent
shooting" read 40 points allowed). Team game lists and counts read the
opponent's rate; records and player games, which cannot, refuse. Expected
counts come from the fixture's two team rows of each game.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _lakers_with_opponent() -> pd.DataFrame:
    games = pd.read_csv(RAW / "team_game_stats" / "2025-26_regular_season.csv")
    opp = games[["game_id", "team_abbr", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta"]]
    opp = opp.rename(columns=lambda c: c if c == "game_id" else f"opp_{c}")
    merged = games.merge(opp, on="game_id")
    merged = merged[(merged["team_abbr"] == "LAL") & (merged["opp_team_abbr"] != "LAL")].copy()
    merged["opp_fg_pct"] = merged["opp_fgm"] / merged["opp_fga"]
    merged["opp_fg3_pct"] = merged["opp_fg3m"] / merged["opp_fg3a"]
    merged["opp_ft_pct"] = merged["opp_ftm"] / merged["opp_fta"]
    return merged


@pytest.mark.parametrize(
    ("query", "keep"),
    [
        ("Lakers games where the opponent shot under 45 percent", lambda g: g["opp_fg_pct"] < 0.45),
        ("Lakers games where opponents shot over 50% from three", lambda g: g["opp_fg3_pct"] > 0.5),
        (
            "Lakers games where the opponent shot under 75 percent from the line",
            lambda g: g["opp_ft_pct"] < 0.75,
        ),
        (
            "Lakers games where they held opponents to under 45 percent shooting",
            lambda g: g["opp_fg_pct"] < 0.45,
        ),
        (
            "Lakers games holding opponents under 45 percent shooting",
            lambda g: g["opp_fg_pct"] < 0.45,
        ),
        (
            "Lakers wins where the opponent shot under 45 percent",
            lambda g: (g["opp_fg_pct"] < 0.45) & (g["wl"] == "W"),
        ),
        ("Lakers games where the opponent shot under 48 percent", lambda g: g["opp_fg_pct"] < 0.48),
        (
            "Lakers games where the opponent shot under 48 percent at home",
            lambda g: (g["opp_fg_pct"] < 0.48) & (g["is_home"] == 1),
        ),
        ("Lakers games holding opponents under 47.5 percent", lambda g: g["opp_fg_pct"] < 0.475),
        (
            "Lakers games where they held opponents to under 47.5 percent shooting",
            lambda g: g["opp_fg_pct"] < 0.475,
        ),
        (
            "Lakers games where they held opponents to 47.5 percent shooting",
            lambda g: g["opp_fg_pct"] <= 0.475,
        ),
        (
            "Lakers games where opponents shot under 35 percent from behind the arc",
            lambda g: g["opp_fg3_pct"] < 0.35,
        ),
        (
            "Lakers games where opponents shot under 35 percent from downtown",
            lambda g: g["opp_fg3_pct"] < 0.35,
        ),
        (
            "Lakers games where opponents shot under 75 percent from the stripe",
            lambda g: g["opp_ft_pct"] < 0.75,
        ),
    ],
)
def test_opponent_shooting_bounds_the_opponent(query, keep):
    games = _lakers_with_opponent()
    expected = int(keep(games).sum())
    count_query = f"how many {query[0].lower()}{query[1:]}"
    sections = execute_natural_query(count_query).result.to_dict()["sections"]
    assert sections["count"][0]["count"] == expected
    stat = parse_query(query)["route_kwargs"]["stat"]
    assert stat.startswith("opponent_") and stat.endswith("_pct")


@pytest.mark.parametrize(
    "query",
    [
        # Records and player game lists do not read the opponent's rate; they
        # filtered the subject's own shooting.
        "Lakers record when opponents shoot under 40 percent",
        "LeBron games where the opponent shot under 40 percent",
        # The second clause is the opponent's too and is not read.
        "Lakers wins where the opponent shot under 45 percent and scored under 100",
        "Lakers games where the opponent shot under 48 percent, scoring over 110",
        "Lakers games where the opponent shot under 48 percent and under 35 percent from three",
        "Lakers games where they held them under 48 percent shooting and under 110 points",
        # An area the reader does not know.
        "Lakers games where opponents shot under 48 percent from the corner",
        "Lakers games where the opponent shot under 48 percent from 2 point range",
    ],
)
def test_unread_opponent_shooting_refuses(query):
    assert "opponent_shooting" in parse_query(query)["route_kwargs"]["unsupported_filters"]
    assert execute_natural_query(query).result_status == "no_result"


def test_the_teams_own_shooting_is_unchanged():
    kwargs = parse_query("Lakers games where they shot under 40 percent")["route_kwargs"]
    assert kwargs["stat"] == "fg_pct"


def test_a_season_after_the_clause_is_the_sample():
    games = pd.read_csv(RAW / "team_game_stats" / "2024-25_regular_season.csv")
    opp = games[["game_id", "team_abbr", "fgm", "fga"]].rename(
        columns={"team_abbr": "oa", "fgm": "ofgm", "fga": "ofga"}
    )
    merged = games.merge(opp, on="game_id")
    merged = merged[(merged["team_abbr"] == "LAL") & (merged["oa"] != "LAL")]
    expected = int((merged["ofgm"] / merged["ofga"] < 0.48).sum())
    for tail in (", 2024-25", " from last season"):
        query = f"how many Lakers games where the opponent shot under 48 percent{tail}"
        assert execute_natural_query(query).result.to_dict()["sections"]["count"][0]["count"] == (
            expected
        )
