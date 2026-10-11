"""C1: opponent-stat rankings and bounds combined with the team's own.

"at least 15 turnovers and at least 15 opponent turnovers" dropped the
team's floor; "most opponent points with at least 15 opponent turnovers"
ranked the team's own points; "the Lakers forced the most turnovers",
"ranked by opponent points" and multi-word stats ("opponent free throws",
"opponent 3 pointers", "opponent free throw attempts") ranked the team's own
number or nothing. Expected values come from the fixture's game rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")
STATS = ["pts", "tov", "ftm", "fta", "fg3m", "fgm", "fga"]


def _lakers() -> pd.DataFrame:
    games = pd.read_csv(RAW / "team_game_stats" / "2025-26_regular_season.csv")
    other = games[["game_id", "team_abbr", *STATS]].rename(
        columns={"team_abbr": "opp", **{s: f"opp_{s}" for s in STATS}}
    )
    rows = games[games["team_abbr"] == "LAL"].merge(other, on="game_id")
    return rows[rows["opp"] != "LAL"]


def _rows(query: str) -> list[dict]:
    return execute_natural_query(query).result.to_dict()["sections"]["finder"]


def test_own_and_opponent_floor_on_the_same_stat():
    games = _lakers()
    games = games[(games["tov"] >= 15) & (games["opp_tov"] >= 15)]
    rows = _rows("Lakers games with at least 15 turnovers and at least 15 opponent turnovers")
    assert sorted(r["game_id"] for r in rows) == sorted(games["game_id"].astype(int))


def test_own_floor_and_opponent_ceiling():
    games = _lakers()
    games = games[(games["pts"] > 110) & (games["opp_pts"] < 100)]
    rows = _rows("Lakers games with over 110 points and under 100 opponent points")
    assert len(rows) == min(25, len(games))
    assert all(r["pts"] > 110 and r["opponent_pts"] < 100 for r in rows)


def test_ranking_with_an_opponent_bound_ranks_the_opponent():
    games = _lakers()
    games = games[games["opp_tov"] >= 15]
    rows = _rows("Lakers games with the most opponent points with at least 15 opponent turnovers")
    expected = games["opp_pts"].sort_values(ascending=False).head(len(rows)).tolist()
    assert [r["opponent_pts"] for r in rows] == expected
    assert len(rows) == min(25, len(games))


@pytest.mark.parametrize(
    ("query", "column", "key", "ascending", "limit"),
    [
        ("games the Lakers forced the most turnovers", "opp_tov", "opponent_tov", False, 25),
        ("Lakers games ranked by opponent points", "opp_pts", "opponent_pts", False, 25),
        ("Lakers games sorted by opponent turnovers", "opp_tov", "opponent_tov", False, 25),
        ("Lakers games with the most opponent free throws", "opp_ftm", "opponent_ftm", False, 25),
        ("Lakers games with the most opponent 3 pointers", "opp_fg3m", "opponent_fg3m", False, 25),
        (
            "Lakers top 5 games by opponent free throw attempts",
            "opp_fta",
            "opponent_fta",
            False,
            5,
        ),
        ("Lakers games with the fewest opponent 3-pointers", "opp_fg3m", "opponent_fg3m", True, 25),
    ],
)
def test_opponent_rankings(query, column, key, ascending, limit):
    games = _lakers()
    rows = _rows(query)
    expected = games[column].sort_values(ascending=ascending).head(limit).tolist()
    assert [r[key] for r in rows] == expected


def test_the_opponent_forcing_turnovers_is_the_teams_own():
    kwargs = parse_query("Lakers games where the opponent forced the most turnovers")[
        "route_kwargs"
    ]
    assert kwargs["stat"] == "tov"


def test_own_bound_with_an_opponent_ranking():
    games = _lakers()
    games = games[games["pts"] >= 120]
    rows = _rows("Lakers games with the most opponent turnovers when scoring 120")
    assert [r["opponent_tov"] for r in rows] == (
        games["opp_tov"].sort_values(ascending=False).head(len(rows)).tolist()
    )
    assert len(rows) == min(25, len(games))


@pytest.mark.parametrize(
    ("query", "keep"),
    [
        (
            "Lakers games with at least 15 opponent turnovers with 120 points allowed",
            lambda g: (g["opp_tov"] >= 15) & (g["opp_pts"] >= 120),
        ),
        (
            "Lakers games with at least 15 opponent turnovers and 15 threes allowed",
            lambda g: (g["opp_tov"] >= 15) & (g["opp_fg3m"] >= 15),
        ),
        ("Lakers games with 120 points allowed", lambda g: g["opp_pts"] >= 120),
        ("Lakers games where they held the opponent to 100", lambda g: g["opp_pts"] <= 100),
        ("Lakers games where they held them to under 90", lambda g: g["opp_pts"] < 90),
    ],
)
def test_allowed_and_held_to_bounds_are_the_opponents(query, keep):
    games = _lakers()
    games = games[keep(games)]
    rows = _rows(f"how many {query[0].lower()}{query[1:]}")
    sections = execute_natural_query(f"how many {query[0].lower()}{query[1:]}").result.to_dict()[
        "sections"
    ]
    assert sections["count"][0]["count"] == len(games)
    assert rows or games.empty


def test_opponent_field_goal_percentage_ranking_and_bound():
    games = _lakers()
    games["opp_fg_pct"] = games["opp_fgm"] / games["opp_fga"]
    rows = _rows("Lakers games with the highest opponent field goal percentage")
    assert [round(r["opponent_fg_pct"], 4) for r in rows] == [
        round(v, 4) for v in games["opp_fg_pct"].sort_values(ascending=False).head(25)
    ]
    sections = execute_natural_query(
        "how many Lakers games with at least 50 opponent field goal percentage"
    ).result.to_dict()["sections"]
    assert sections["count"][0]["count"] == int((games["opp_fg_pct"] >= 0.5).sum())


def test_sorted_by_opponent_points_lowest_first():
    games = _lakers()
    rows = _rows("Lakers games sorted by opponent points, lowest first")
    assert [r["opponent_pts"] for r in rows] == games["opp_pts"].sort_values().head(25).tolist()


@pytest.mark.parametrize(
    ("query", "keep"),
    [
        ("Lakers games where they held opponents to 10 threes", lambda g: g["opp_fg3m"] <= 10),
        ("Lakers games where they held opponents to 10 turnovers", lambda g: g["opp_tov"] <= 10),
        (
            "Lakers games where they held opponents to 10 or fewer threes",
            lambda g: g["opp_fg3m"] <= 10,
        ),
        (
            "Lakers games where they held the opponent to 5 made threes",
            lambda g: g["opp_fg3m"] <= 5,
        ),
        (
            "Lakers games where they held opponents to 9 or fewer turnovers",
            lambda g: g["opp_tov"] <= 9,
        ),
        (
            "Lakers games where they held them to 100 in wins",
            lambda g: (g["opp_pts"] <= 100) & (g["wl"] == "W"),
        ),
    ],
)
def test_held_to_a_named_stat_is_that_stats_ceiling(query, keep):
    games = _lakers()
    sections = execute_natural_query(f"how many {query[0].lower()}{query[1:]}").result.to_dict()[
        "sections"
    ]
    assert sections["count"][0]["count"] == int(keep(games).sum())


@pytest.mark.parametrize(
    "query",
    [
        "Lakers games where they held them to under 40% shooting",
        "Lakers games where they held the opponent to 35 percent shooting",
    ],
)
def test_held_to_a_rate_is_not_a_points_ceiling(query):
    kwargs = parse_query(query)["route_kwargs"]
    stats = {kwargs.get("stat")} | {c["stat"] for c in kwargs.get("conditions") or []}
    assert "opponent_pts" not in stats
