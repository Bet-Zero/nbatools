"""C1: "did LeBron play last night" and win/loss clauses in yes/no ORs.

"did LeBron play last night" summarised his last game without an answer;
"did the Lakers win or score 120 last game" refused. Playing is checked
against the team's last game, and a win/loss clause is one OR check.
Expected values come from the fixture's game rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query
from tests.test_qualified_scalar_played import explicit_lebron_dnp as _explicit_lebron_dnp

explicit_lebron_dnp = _explicit_lebron_dnp

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _last(kind: str, column: str, value: str) -> pd.Series:
    games = pd.read_csv(RAW / kind / "2025-26_regular_season.csv")
    return games[games[column] == value].sort_values("game_date").iloc[-1]


@pytest.mark.parametrize(
    ("query", "name", "team"),
    [
        ("did LeBron play last night", "LeBron James", "LAL"),
        ("did Curry play last game", "Stephen Curry", "GSW"),
    ],
)
def test_played_in_the_teams_last_game(query, name, team):
    player = _last("player_game_stats", "player_name", name)
    team_last = _last("team_game_stats", "team_abbr", team)
    answer = "Yes" if player["game_date"] == team_last["game_date"] else "No"
    phrase = execute_natural_query(query).metadata["answer_phrase"]
    assert phrase.startswith(f"{answer}: {name} ")
    assert f"({team_last['game_date']} vs the {team_last['opponent_team_name']})" in phrase


def test_explicit_dnp_in_the_teams_last_game_is_a_no(explicit_lebron_dnp):
    # A missing appearance alone cannot prove this desired No answer. The
    # controlled fixture explicitly states the selected game's DNP identity.
    result = execute_natural_query("did LeBron play in the Lakers' last game")
    original = explicit_lebron_dnp
    assert result.result_status == "ok"
    assert result.metadata["answer_phrase"].startswith(
        "No: LeBron James did not play in the Los Angeles Lakers' last game"
    )
    assert str(original.game_date)[:10] in result.metadata["answer_phrase"]
    rows = result.result.to_dict()["sections"]["finder"]
    assert [int(row["game_id"]) for row in rows] == [int(original.game_id)]
    assert not any("player_name" in row or "player_id" in row for row in rows)


@pytest.mark.parametrize(
    ("query", "won", "floor"),
    [
        ("did the Lakers win or score 120 last game", True, 120),
        ("did the Lakers lose or score 120 last game", False, 120),
        ("did the Lakers lose or score 100 last game", False, 100),
    ],
)
def test_win_or_loss_is_one_check(query, won, floor):
    row = _last("team_game_stats", "team_abbr", "LAL")
    met = (row["wl"] == ("W" if won else "L")) or row["pts"] >= floor
    phrase = execute_natural_query(query).metadata["answer_phrase"]
    assert phrase.startswith(f"{'Yes' if met else 'No'}: The Los Angeles Lakers ")


@pytest.mark.parametrize(
    "query",
    [
        "did LeBron play poorly last night",
        "did LeBron play the whole game last night",
        "did LeBron play point guard last night",
        "did LeBron appear in the play-in last game",
    ],
)
def test_other_play_questions_get_no_played_answer(query):
    phrase = str(execute_natural_query(query).metadata.get("answer_phrase") or "")
    assert not phrase.startswith(("Yes", "No"))


@pytest.mark.parametrize(
    "query",
    [
        "did the Lakers lose or did LeBron score 40 last game",
        "did the Lakers win or score 120 in the play-in last game",
    ],
)
def test_or_checks_that_are_not_one_game_refuse(query):
    assert execute_natural_query(query).result_status == "no_result"


def test_played_in_the_named_teams_last_game():
    team_last = _last("team_game_stats", "team_abbr", "LAL")
    phrase = execute_natural_query("did LeBron play in the Lakers' last game").metadata[
        "answer_phrase"
    ]
    assert phrase.startswith("Yes: LeBron James played in the Los Angeles Lakers' last game")
    assert team_last["game_date"] in phrase


def test_played_in_a_named_seasons_last_game():
    games = pd.read_csv(RAW / "team_game_stats" / "2024-25_regular_season.csv")
    team_last = games[games["team_abbr"] == "LAL"].sort_values("game_date").iloc[-1]
    phrase = execute_natural_query("did LeBron play in his last game in 2024-25").metadata[
        "answer_phrase"
    ]
    assert phrase.startswith("Yes: LeBron James played in the Los Angeles Lakers' last game")
    assert f"({team_last['game_date']} vs the {team_last['opponent_team_name']})" in phrase
