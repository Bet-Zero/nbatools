"""C1: "Lakers losses to the Celtics", "wins over", "games beaten by", "was".

"Lakers losses to the Celtics", "wins over" and "victories over" read the
Celtics as the subject; "defeats to" counted wins; "Lakers games beaten by
the Celtics" counted Lakers wins; "was LeBron's team beaten by the Nuggets"
read "was" as the Washington Wizards. Expected counts come from the fixture's
team game rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")


def _games(team: str, opponent: str, wl: str) -> int:
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    mask = (games["team_abbr"] == team) & (games["opponent_team_abbr"] == opponent)
    return int((mask & (games["wl"] == wl)).sum())


@pytest.mark.parametrize(
    ("query", "outcome"),
    [
        ("Lakers losses to the Celtics", "L"),
        ("Lakers defeats to the Celtics", "L"),
        ("Lakers losses at the hands of the Celtics", "L"),
        ("Lakers games beaten by the Celtics", "L"),
        ("Lakers wins over the Celtics", "W"),
        ("Lakers victories over the Celtics", "W"),
        ("Lakers victories against the Celtics", "W"),
    ],
)
def test_the_named_team_keeps_the_subject(query, outcome):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs["team"], kwargs["opponent"]) == ("LAL", "BOS")
    assert kwargs["wins_only" if outcome == "W" else "losses_only"] is True
    rows = execute_natural_query(query).result.to_dict()["sections"]["finder"]
    assert len(rows) == _games("LAL", "BOS", outcome)


def test_record_in_losses_to():
    kwargs = parse_query("Lakers record in losses to the Celtics")["route_kwargs"]
    assert (kwargs["team"], kwargs["opponent"], kwargs["losses_only"]) == ("LAL", "BOS", True)


def test_games_beaten_by_a_margin_are_losses():
    kwargs = parse_query("Lakers games beaten by 20")["route_kwargs"]
    assert kwargs["losses_only"] is True and kwargs["stat"] == "loss_margin"


def test_was_before_a_possessive_or_participle_is_not_washington():
    kwargs = parse_query("was LeBron's team beaten by the Nuggets")["route_kwargs"]
    assert kwargs.get("team") != "WAS"
    assert kwargs["opponent"] == "DEN" and kwargs["losses_only"] is True
    # A team word meant as a team still resolves.
    assert parse_query("was record this season")["route_kwargs"]["team"] == "WAS"


def test_active_beaten_by_a_margin_is_unchanged():
    kwargs = parse_query("which teams have the Celtics beaten by 20")["route_kwargs"]
    assert kwargs["team"] == "BOS" and kwargs["wins_only"] is True


def _over(team: str, stat: str, line: float, wl: str = "W") -> int:
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    games = games[(games["team_abbr"] == team) & (games["wl"] == wl)]
    return int((games[stat] > line).sum())


def test_wins_over_a_number_stay_strict():
    # "over" is a strict floor; the "wins over <team>" rewrite must not eat it.
    kwargs = parse_query("Lakers wins over 120 points")["route_kwargs"]
    assert kwargs["min_value"] > 120
    rows = execute_natural_query("Lakers wins over 120 points").result.to_dict()["sections"]
    assert len(rows["finder"]) == _over("LAL", "pts", 120)


def _losses_by(team: str, floor: int) -> int:
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    games = games[(games["team_abbr"] == team) & (games["wl"] == "L")]
    return int((-games["plus_minus"] >= floor).sum())


@pytest.mark.parametrize(
    ("query", "floor"),
    [
        ("Lakers games beaten by at least 20", 20),
        ("Lakers games beaten by more than 10", 11),
        ("Lakers games beaten by double digits", 10),
        ("Lakers games beaten by over 20", 21),
    ],
)
def test_games_beaten_by_a_margin_word(query, floor):
    rows = execute_natural_query(query).result.to_dict()["sections"]["finder"]
    assert len(rows) == _losses_by("LAL", floor)


def _against_by(team: str, opponent: str, wl: str, floor: int) -> int:
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    mine = games[
        (games["team_abbr"] == team)
        & (games["opponent_team_abbr"] == opponent)
        & (games["wl"] == wl)
    ]
    return int((mine["plus_minus"].abs() >= floor).sum())


@pytest.mark.parametrize(
    ("query", "wl", "floor"),
    [
        ("Lakers losses to the Celtics by 10 or more", "L", 10),
        ("Lakers losses to the Celtics by more than 10", "L", 11),
        ("Lakers wins over the Celtics by 10 or more", "W", 10),
        ("Lakers games beaten by 10 by the Celtics", "L", 10),
        ("Lakers games beaten by double digits by the Celtics", "L", 10),
    ],
)
def test_a_margin_beside_the_opponent_is_kept(query, wl, floor):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs["team"], kwargs["opponent"]) == ("LAL", "BOS")
    rows = execute_natural_query(query).result.to_dict()["sections"]["finder"]
    assert len(rows) == _against_by("LAL", "BOS", wl, floor)


@pytest.mark.parametrize(
    ("query", "outcome"),
    [
        ("Lakers games beaten by 76ers", "losses_only"),
        ("Lakers wins over 76ers", "wins_only"),
        ("Lakers victory over 76ers", "wins_only"),
    ],
)
def test_76ers_is_a_team_not_a_number(query, outcome):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["opponent"] == "PHI" and kwargs[outcome] is True
