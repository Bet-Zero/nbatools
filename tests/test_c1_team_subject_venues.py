"""C1: the team a question is about stays the subject.

"which Laker scored the most points in Boston" and "who led the Lakers in
scoring over the Celtics" read the Celtics as the team (team game lists of
Boston). "in <city>" after a team subject is road games there and "over"
another team is the opponent. Expectations come from the fixture rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _rows(kind: str) -> pd.DataFrame:
    return pd.read_csv(RAW / kind / "2025-26_regular_season.csv")


@pytest.mark.parametrize(
    ("query", "road"),
    [
        ("which Laker scored the most points in Boston", True),
        ("who scored the most for the Lakers in Boston", True),
        ("who led the Lakers in scoring over the Celtics", False),
        ("Lakers leading scorer over the Celtics", False),
    ],
)
def test_team_players_against_the_other_team(query, road):
    rows = _rows("player_game_stats")
    rows = rows[(rows["team_abbr"] == "LAL") & (rows["opponent_team_abbr"] == "BOS")]
    if road:
        rows = rows[rows["is_home"] == 0]
    expected = rows.groupby("player_name")["pts"].mean().sort_values(ascending=False)
    result = execute_natural_query(query)
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs["team"], kwargs["opponent"], bool(kwargs.get("away_only"))) == (
        "LAL",
        "BOS",
        road,
    )
    board = result.result.to_dict()["sections"]["leaderboard"]
    assert [r["pts_per_game"] for r in board] == pytest.approx(list(expected.values)[: len(board)])
    assert {r["player_name"] for r in board} == set(expected.index[: len(board)])


@pytest.mark.parametrize(
    ("query", "home"),
    [("Lakers record in Boston", 0), ("Lakers record over the Celtics", None)],
)
def test_team_record_in_a_city_or_over_a_team(query, home):
    games = _rows("team_game_stats")
    games = games[(games["team_abbr"] == "LAL") & (games["opponent_team_abbr"] == "BOS")]
    if home is not None:
        games = games[games["is_home"] == home]
    summary = execute_natural_query(query).result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == (
        int((games["wl"] == "W").sum()),
        int((games["wl"] == "L").sum()),
    )


def test_a_team_in_its_own_city_is_home():
    kwargs = parse_query("Celtics record in Boston")["route_kwargs"]
    assert (kwargs["team"], kwargs.get("home_only"), kwargs.get("opponent")) == ("BOS", True, None)


def test_a_player_over_a_team_is_the_opponent():
    kwargs = parse_query("LeBron points over the Celtics")["route_kwargs"]
    assert (kwargs["player"], kwargs["opponent"], kwargs.get("team")) == (
        "LeBron James",
        "BOS",
        None,
    )


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        # A number after "over" is a threshold.
        ("Lakers games over 120 points", {"team": "LAL", "opponent": None}),
        ("Celtics over the last 10 games", {"team": "BOS", "opponent": None}),
        # A player "in Miami" may mean his Miami years: left as it was.
        ("LeBron points in Miami", {"team": "MIA", "opponent": None}),
        # "in Lakers wins" names a team, not a city.
        ("Lakers record in Lakers wins", {"team": "LAL", "opponent": None}),
    ],
)
def test_other_over_and_in_wording_is_unchanged(query, expected):
    kwargs = parse_query(query)["route_kwargs"]
    assert {key: kwargs.get(key) for key in expected} == expected


@pytest.mark.parametrize(
    ("query", "team", "last_n"),
    [
        # "over" his own team's games is a span, not an opponent.
        ("LeBron averages over the Lakers last 5 games", "LAL", 5),
        ("LeBron points over the Lakers' last 10 games", "LAL", 10),
        ("Tatum points over the Celtics last 10 games", "BOS", 10),
        ("LeBron points over the Lakers season", "LAL", None),
    ],
)
def test_over_a_players_own_team_is_not_the_opponent(query, team, last_n):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs.get("team"), kwargs.get("opponent"), kwargs.get("last_n")) == (
        team,
        None,
        last_n,
    )


@pytest.mark.parametrize(
    "query",
    ["Lakers games where the over was hit", "Lakers record over min", "Lakers drafted in Boston"],
)
def test_bets_and_non_venues_are_not_opponents(query):
    try:
        kwargs = parse_query(query)["route_kwargs"]
    except ValueError:
        return
    assert kwargs.get("opponent") is None
    assert not kwargs.get("away_only")
