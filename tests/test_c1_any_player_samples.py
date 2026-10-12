"""C1: a team's sample when one of its players reaches a mark.

"Lakers record when a player scores 40" answered every game (it read the
team's 40 points). A floor now reads the team's best single-player line in
the game (``top_player_<stat>``); ceilings and another team's player refuse.

Expected values are counted with pandas from the fixture.
"""

from __future__ import annotations

import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


def _execute(query: str):
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    return result.result.to_dict()["sections"]


def _record(query: str) -> tuple[int, int]:
    summary = _execute(query)["summary"][0]
    return summary["wins"], summary["losses"]


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when a player scores 40", (2, 0)),
        ("Lakers record when someone scores 40", (2, 0)),
        ("Lakers record when anyone has 40 points", (2, 0)),
        ("Lakers record when a Lakers player scores 40", (2, 0)),
        ("Lakers record when a player scores 30 this season", (30, 7)),
        ("Lakers record when someone has 15 boards", (7, 1)),
        ("Lakers record when someone scores 40 points at home", (1, 0)),
        ("Lakers record vs Celtics when someone scores 30", (3, 4)),
    ],
)
def test_team_record_when_a_player_reaches_a_mark(query, record):
    assert _record(query) == record


def test_game_list_and_leaderboard():
    assert len(_execute("Lakers games when someone scores 40")["finder"]) == 2
    board = _execute("best record when a player scores 30")["leaderboard"]
    assert [(r["team_abbr"], r["wins"], r["losses"]) for r in board[:3]] == [
        ("NYK", 21, 2),
        ("BOS", 26, 6),
        ("LAL", 30, 7),
    ]


@pytest.mark.parametrize(
    "query",
    [
        # "Under 10" is not "the best line is under 10"; another team's
        # player is not read.
        "Lakers record when a player scores under 10",
        "Lakers record when a Celtics player scores 40",
    ],
)
def test_unread_any_player_clauses_refuse(query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"
