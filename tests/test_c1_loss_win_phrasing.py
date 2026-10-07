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
