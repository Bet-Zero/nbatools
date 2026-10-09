"""C1: yes/no last-game questions with "or" and "more than".

"did LeBron score 30 or 10 assists last game" listed his last game meeting
either clause (2026-09-26) instead of checking his last game; "did LeBron
score more than 22 last game" read no bound. Either clause passing is a yes;
"score more than 22" is a strict points floor. Expected values come from the
fixture's game rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands._parse_helpers import extract_threshold_conditions
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _last(kind: str, column: str, value: str, opponent: str | None = None) -> pd.Series:
    games = pd.read_csv(RAW / kind / "2025-26_regular_season.csv")
    games = games[games[column] == value]
    if opponent:
        games = games[games["opponent_team_abbr"] == opponent]
    return games.sort_values("game_date").iloc[-1]


@pytest.mark.parametrize(
    ("query", "checks", "opponent"),
    [
        ("did LeBron score 30 or 10 assists last game", [("pts", 30), ("ast", 10)], None),
        ("did LeBron score 20 points or 10 assists last game", [("pts", 20), ("ast", 10)], None),
        ("did LeBron score 30 points or 5 assists last game", [("pts", 30), ("ast", 5)], None),
        (
            "did LeBron score 30 or 10 assists in his last game against the Celtics",
            [("pts", 30), ("ast", 10)],
            "BOS",
        ),
    ],
)
def test_player_or_checks_his_last_game(query, checks, opponent):
    row = _last("player_game_stats", "player_name", "LeBron James", opponent)
    result = execute_natural_query(query)
    rows = result.result.to_dict()["sections"]["finder"]
    assert [str(r["game_date"])[:10] for r in rows] == [row["game_date"]]
    answer = "Yes" if any(row[stat] >= floor for stat, floor in checks) else "No"
    phrase = result.metadata["answer_phrase"]
    assert phrase.startswith(f"{answer}: LeBron James had {row['pts']} points and {row['ast']}")


@pytest.mark.parametrize(("points", "threes"), [(120, 15), (100, 15)])
def test_team_or_checks_their_last_game(points, threes):
    row = _last("team_game_stats", "team_abbr", "LAL")
    result = execute_natural_query(f"did the Lakers score {points} or {threes} threes last game")
    answer = "Yes" if row["pts"] >= points or row["fg3m"] >= threes else "No"
    assert result.metadata["answer_phrase"].startswith(f"{answer}: The Los Angeles Lakers had")


@pytest.mark.parametrize("floor", [21, 22])
def test_more_than_without_points_is_a_strict_floor(floor):
    row = _last("player_game_stats", "player_name", "LeBron James")
    result = execute_natural_query(f"did LeBron score more than {floor} last game")
    answer = "Yes" if row["pts"] > floor else "No"
    assert result.metadata["answer_phrase"].startswith(f"{answer}: LeBron James had")


def test_an_or_clause_it_cannot_phrase_lists_the_last_game_without_an_answer():
    row = _last("player_game_stats", "player_name", "LeBron James")
    result = execute_natural_query("did LeBron score 30 or have a triple double last game")
    rows = result.result.to_dict()["sections"]["finder"]
    assert [str(r["game_date"])[:10] for r in rows] == [row["game_date"]]
    assert "answer_phrase" not in result.metadata or not str(
        result.metadata.get("answer_phrase")
    ).startswith(("Yes", "No"))


@pytest.mark.parametrize(
    ("text", "bound"),
    [
        ("lebron scored more than 22", ("pts", 22.0001, None)),
        ("lebron rebounds fewer than 5", ("reb", None, 4.9999)),
        ("lebron scored 30 points more than 5 times", ("pts", 30.0, None)),
    ],
)
def test_verb_more_than_bounds(text, bound):
    conditions = extract_threshold_conditions(text)
    assert [(c["stat"], c["min_value"], c["max_value"]) for c in conditions] == [bound]


@pytest.mark.parametrize(
    "query",
    [
        "did LeBron or AD score 30 last game",
        "did LeBron score 30 or AD score 30 last game",
        "did the Lakers or Celtics win last game",
    ],
)
def test_two_subjects_refuse_rather_than_answer_for_one(query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert any("one player or team" in str(note) for note in result.metadata.get("notes") or [])


def test_the_same_stat_twice_is_shown_once():
    row = _last("player_game_stats", "player_name", "LeBron James")
    phrase = execute_natural_query("did LeBron score 20 or score 30 last game").metadata[
        "answer_phrase"
    ]
    assert phrase.count(f"{row['pts']} points") == 1
