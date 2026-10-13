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


@pytest.mark.parametrize(
    "query",
    [
        # Two clauses, one player's joined line, or a subject it cannot place:
        # a per-team best per stat cannot read these.
        "Lakers record when someone scores 30 and someone has 15 rebounds",
        "Lakers record when someone scores 30, someone has 15 rebounds",
        "Lakers record when someone scores 30 and has 15 rebounds",
        "Lakers record when someone scores 30 and 10 rebounds",
        "Lakers record when a player has 30 points and 10 rebounds",
        "Lakers record when an opposing player scores 40",
        "Lakers record when nobody scores 30",
        "Lakers record when someone scores 30 while shooting 50%",
        "Lakers record when someone scores 30 on 50% shooting",
        "Lakers record when one player scores 30 and another scores 20",
        "Lakers record when a player scores 30 and a teammate scores 20",
    ],
)
def test_unread_any_player_combinations_refuse(query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when they score 120 and someone scores 30", (13, 0)),
        ("Lakers record when someone scores 30 and they score 120", (13, 0)),
        ("Lakers record when someone scores 30 and opponents score 120", (2, 2)),
        ("LAL record when a Lakers player scores 40", (2, 0)),
    ],
)
def test_any_player_beside_team_clauses(query, record):
    assert _record(query) == record


def test_missing_player_rows_are_no_data(tmp_path, monkeypatch):
    import shutil
    from pathlib import Path

    root = tmp_path / "fx"
    shutil.copytree(Path("qa/fixtures/query_engine_sample"), root)
    (root / "data/raw/player_game_stats/2024-25_regular_season.csv").unlink()
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    result = execute_natural_query("Lakers record when someone scores 30 since 2023-24")
    assert result.result_status == "no_result"
    assert result.result_reason == "no_data"
