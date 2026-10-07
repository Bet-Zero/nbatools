"""C1: "how many teams have the Lakers beaten", "Lakers lost to 76ers".

"how many teams have the Lakers beaten" counted every game (60) and "how many
different teams have the Lakers lost to" every loss; they count the teams on
the "which teams" board. "how many losses to the Celtics do the Lakers have"
did not route; "Lakers lost to 76ers" / "Lakers beat 76ers" dropped the
opponent. Expected counts come from the fixture's team game rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")


def _teams(team: str, wl: str, minimum: int = 1, season: str = "2025-26") -> int:
    games = pd.read_csv(RAW / f"{season}_regular_season.csv")
    mine = games[(games["team_abbr"] == team) & (games["wl"] == wl)]
    counts = mine["opponent_team_abbr"].value_counts()
    return int((counts >= minimum).sum())


@pytest.mark.parametrize(
    ("query", "team", "wl", "minimum"),
    [
        ("how many teams have the Lakers beaten", "LAL", "W", 1),
        ("how many teams did the Lakers beat this season", "LAL", "W", 1),
        ("how many different teams have the Lakers lost to", "LAL", "L", 1),
        ("how many teams have beaten the Lakers", "LAL", "L", 1),
        ("how many teams beat the Lakers twice", "LAL", "L", 2),
        ("how many teams have the Celtics lost to", "BOS", "L", 1),
    ],
)
def test_counts_the_teams(query, team, wl, minimum):
    result = execute_natural_query(query)
    sections = result.result.to_dict()["sections"]
    assert sections["count"] == [{"count": _teams(team, wl, minimum)}]
    assert len(sections["leaderboard"]) == _teams(team, wl, minimum)
    assert "teams" in result.metadata["count_phrase"]


@pytest.mark.parametrize(
    ("query", "outcome", "count"),
    [
        ("how many losses to the Celtics do the Lakers have", "losses_only", ("LAL", "BOS", "L")),
        ("how many wins over the Celtics do the Lakers have", "wins_only", ("LAL", "BOS", "W")),
    ],
)
def test_results_against_with_the_subject_last(query, outcome, count):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs["team"], kwargs["opponent"], kwargs[outcome]) == ("LAL", "BOS", True)
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    team, opponent, wl = count
    expected = int(
        (
            (games["team_abbr"] == team)
            & (games["opponent_team_abbr"] == opponent)
            & (games["wl"] == wl)
        ).sum()
    )
    assert execute_natural_query(query).result.to_dict()["sections"]["count"] == [
        {"count": expected}
    ]


@pytest.mark.parametrize(
    ("query", "outcome"),
    [("Lakers lost to 76ers", "losses_only"), ("Lakers beat 76ers", "wins_only")],
)
def test_76ers_after_beat_and_lost_to(query, outcome):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["opponent"] == "PHI" and kwargs[outcome] is True


@pytest.mark.parametrize(
    "query",
    [
        # The board would count a different set (or the games route games).
        "how many teams did the Lakers never beat",
        "how many teams have the Lakers not beaten",
        "how many teams did the Lakers beat with 120 points",
        "how many teams have the Lakers beaten the most",
        "how many teams beat the Lakers and Celtics",
        "how many teams has LeBron beaten",
        "how many teams have the Celtics beaten in a row",
        "how many teams have the Lakers beaten more than the Celtics",
        # A margin or an exact count, and "didn't": the games route counted games.
        "how many teams did the Lakers lose to by 10",
        "how many teams beat the Lakers by 20",
        "how many teams did the Celtics lose to exactly once",
        "how many teams didn't the Lakers beat",
    ],
)
def test_team_counts_the_board_cannot_give_refuse(query):
    assert execute_natural_query(query).result_status == "no_result"


@pytest.mark.parametrize(
    ("query", "team", "wl", "minimum"),
    [
        ("how many teams did the Celtics lose to more than once", "BOS", "L", 2),
        ("how many teams did the Lakers beat 3 times or more", "LAL", "W", 3),
    ],
)
def test_once_and_times_or_more(query, team, wl, minimum):
    sections = execute_natural_query(query).result.to_dict()["sections"]
    assert sections["count"] == [{"count": _teams(team, wl, minimum)}]


def test_streak_team_counts_keep_their_route():
    assert (
        execute_natural_query("how many teams have won 8 straight this season").result_status
        == "ok"
    )


def test_subject_last_keeps_the_margin():
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    mine = games[
        (games["team_abbr"] == "LAL")
        & (games["opponent_team_abbr"] == "BOS")
        & (games["wl"] == "L")
        & (games["plus_minus"].abs() >= 10)
    ]
    query = "how many losses against the Celtics do the Lakers have by 10 or more"
    assert execute_natural_query(query).result.to_dict()["sections"]["count"] == [
        {"count": len(mine)}
    ]


def test_zero_teams_reads_as_a_sentence():
    phrase = execute_natural_query("how many teams did the 76ers beat").metadata["count_phrase"]
    assert phrase.endswith("beat no teams in the 2025-26 regular season.")
