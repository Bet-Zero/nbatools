"""C1: players by season average ("how many players average 25 points").

"how many players average 25 points" counted players with a single 25-point
game (25); "players averaging 25 ppg" errored; "Lakers players averaging 20"
counted the team's games. Every qualified player whose per-game average
reaches the number is listed and counted. Expected values come from the
fixture's player rows.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/player_game_stats")


def _averages(season: str = "2025-26", team: str | None = None) -> pd.DataFrame:
    games = pd.read_csv(RAW / f"{season}_regular_season.csv")
    if team:
        games = games[games["team_abbr"] == team]
    return games.groupby("player_name")[["pts", "reb", "ast"]].mean()


@pytest.mark.parametrize(
    ("query", "stat", "floor", "season", "team"),
    [
        ("how many players average 25 points", "pts", 25, "2025-26", None),
        ("how many players averaged 25 points in 2024-25", "pts", 25, "2024-25", None),
        ("how many Lakers players average 20 points", "pts", 20, "2025-26", "LAL"),
    ],
)
def test_average_counts(query, stat, floor, season, team):
    averages = _averages(season, team)
    result = execute_natural_query(query)
    assert result.result.to_dict()["sections"]["count"] == [
        {"count": int((averages[stat] >= floor).sum())}
    ]
    assert re.search(r" average(?:d)? ", result.metadata["count_phrase"])


@pytest.mark.parametrize(
    ("query", "stat", "floor"),
    [
        ("players averaging 25 ppg", "pts", 25),
        ("which players averaged 10 rebounds this season", "reb", 10),
        ("who averages 8 assists", "ast", 8),
    ],
)
def test_average_lists(query, stat, floor):
    averages = _averages()
    rows = execute_natural_query(query).result.to_dict()["sections"]["leaderboard"]
    assert {r["player_name"] for r in rows} == set(averages[averages[stat] >= floor].index)


@pytest.mark.parametrize(
    "query",
    [
        "players averaging 30 points and 10 rebounds",
        "players averaging 25 points in their last 10 games",
    ],
)
def test_average_conditions_refuse(query):
    assert execute_natural_query(query).result_status == "no_result"


def test_named_player_keeps_his_reading():
    result = execute_natural_query("does LeBron average 25 points")
    assert result.route != "season_leaders"


def test_guards_average_counts_guards_only():
    roster = pd.read_csv(Path("qa/fixtures/query_engine_sample/data/raw/rosters/2025-26.csv"))
    # The board's guard group: G and G-F.
    guards = set(roster[roster["position"].isin(["G", "G-F"])]["player_name"])
    averages = _averages()
    expected = averages[(averages["pts"] >= 20) & averages.index.isin(guards)]
    rows = execute_natural_query("which guards average 20 points").result.to_dict()["sections"][
        "leaderboard"
    ]
    assert {r["player_name"] for r in rows} == set(expected.index)


def test_an_opponent_window_has_no_games_floor():
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    games = games[
        (games["opponent_team_abbr"] == "BOS")
        & (games["game_date"] >= "2025-12-01")
        & (games["game_date"] <= "2026-01-31")
    ]
    means = games.groupby("player_name")["pts"].mean()
    result = execute_natural_query(
        "how many players averaged 25 points vs the Celtics from December 1 2025 to January 31 2026"
    )
    assert result.result.to_dict()["sections"]["count"] == [{"count": int((means >= 25).sum())}]
    assert result.metadata["count_phrase"].startswith(
        f"{int((means >= 25).sum())} players averaged"
    )


@pytest.mark.parametrize(
    ("query", "stat", "floor", "strict"),
    [
        ("how many players average 1.5 steals", "stl", 1.5, False),
        ("players averaging 2.5 assists", "ast", 2.5, False),
        ("how many players average 25.5 points", "pts", 25.5, False),
        ("players averaging over 25 points", "pts", 25, True),
        ("players averaging 25 or more points", "pts", 25, False),
        ("Lakers players averaging 20", "pts", 20, False),
    ],
)
def test_decimal_strict_and_bare_bounds(query, stat, floor, strict):
    team = "LAL" if query.startswith("Lakers") else None
    averages = _averages(team=team) if stat != "stl" else _stl()
    met = averages[stat] > floor if strict else averages[stat] >= floor
    result = execute_natural_query(query)
    sections = result.result.to_dict()["sections"]
    count = sections.get("count")
    if count:
        assert count == [{"count": int(met.sum())}]
    else:
        assert {r["player_name"] for r in sections["leaderboard"]} == set(averages[met].index)
    if strict:
        assert "more than 25 points per game" in result.metadata["answer_phrase"]


def _stl() -> pd.DataFrame:
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    return games.groupby("player_name")[["stl"]].mean()


@pytest.mark.parametrize(
    "query",
    [
        "players averaging less than 10 ppg",
        "players averaging 25 points per 100 possessions",
        "how many players average 20 points on 50% shooting",
    ],
)
def test_bounds_and_clauses_the_list_cannot_apply_refuse(query):
    assert execute_natural_query(query).result_status == "no_result"


def test_in_a_game_keeps_the_single_game_reading():
    assert execute_natural_query("who averages 30 points in a game").route != "season_leaders"


@pytest.mark.parametrize(
    "query",
    [
        "players averaging 20 minutes",
        "players averaging 30 mpg",
        "players averaging 3 turnovers",
        "players averaging 4 fouls",
        "players averaging 10 free throws",
        "players averaging 25 PER",
        "players averaging 30 percent from three",
        "players under 25 averaging 20 points",
        "players averaging 20 points on 30 minutes",
        "players averaging up to 10 points",
        "players averaging 10 in assists",
        "players averaging 10 at the line",
        "players averaging 20 from three",
        "players averaging 20 at the rim",
        "players averaging 20 in the paint",
        "players averaging 25 points this season vs last season",
        "players averaging 25 this season compared to last season",
    ],
)
def test_other_units_and_conditions_are_not_points(query):
    result = execute_natural_query(query)
    assert result.route != "season_leaders" or result.result_status == "no_result"


def test_a_leading_dot_decimal():
    averages = pd.read_csv(RAW / "2025-26_regular_season.csv").groupby("player_name")["blk"].mean()
    rows = execute_natural_query("players averaging .5 blocks").result.to_dict()["sections"][
        "leaderboard"
    ]
    assert {r["player_name"] for r in rows} == set(averages[averages >= 0.5].index)
    assert (
        execute_natural_query("players averaging .5 blocks")
        .metadata["answer_phrase"]
        .startswith(f"{int((averages >= 0.5).sum())} players average 0.5+ blocks")
    )
