"""C1: a clause about the other team is the opponent's number.

"Lakers top 3 scoring games where the Celtics made 15 threes" listed the
Celtics' own games (the clause's team became the subject); "Lakers highest
scoring games when the opponent scored 120" ranked by the opponent's points.
The named team is the opponent, its number is an opponent bound, and the rank
word ranks the subject's own stat. Expected values come from the fixture's
team rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")


def _lakers() -> pd.DataFrame:
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    other = games[["game_id", "team_abbr", "pts", "fg3m"]].rename(
        columns={"team_abbr": "opp", "pts": "opp_pts", "fg3m": "opp_fg3m"}
    )
    lakers = games[games["team_abbr"] == "LAL"].merge(other, on="game_id")
    return lakers[lakers["opp"] != "LAL"]


def _rows(query: str) -> list[dict]:
    return execute_natural_query(query).result.to_dict()["sections"]["finder"]


@pytest.mark.parametrize(
    ("query", "keep", "stat", "n", "ascending"),
    [
        (
            "Lakers top 3 scoring games where the Celtics made 15 threes",
            lambda g: (g["opp"] == "BOS") & (g["opp_fg3m"] >= 15),
            "pts",
            3,
            False,
        ),
        (
            "Lakers highest scoring games when the Celtics scored 120",
            lambda g: (g["opp"] == "BOS") & (g["opp_pts"] >= 120),
            "pts",
            25,
            False,
        ),
        (
            "Lakers highest scoring games when the opponent scored 120",
            lambda g: g["opp_pts"] >= 120,
            "pts",
            25,
            False,
        ),
        (
            "Lakers lowest scoring games when the opponent scored 120",
            lambda g: g["opp_pts"] >= 120,
            "pts",
            25,
            True,
        ),
        (
            "Lakers top 3 rebounding games when the Celtics made 15 threes",
            lambda g: (g["opp"] == "BOS") & (g["opp_fg3m"] >= 15),
            "reb",
            3,
            False,
        ),
    ],
)
def test_other_team_clause_is_an_opponent_bound(query, keep, stat, n, ascending):
    games = _lakers()
    games = games[keep(games)]
    expected = games[stat].sort_values(ascending=ascending).head(n).tolist()
    assert [r[stat] for r in _rows(query)] == expected


def test_other_team_games_list():
    games = _lakers()
    games = games[(games["opp"] == "BOS") & (games["opp_fg3m"] >= 15)]
    rows = _rows("Lakers games where the Celtics made 15 threes")
    assert sorted(str(r["game_date"])[:10] for r in rows) == sorted(games["game_date"].tolist())


def test_the_teams_own_name_stays_its_own_number():
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    games = games[(games["team_abbr"] == "BOS") & (games["fg3m"] >= 20)]
    rows = _rows("Celtics highest scoring games where the Celtics made 20 threes")
    assert [r["pts"] for r in rows] == games["pts"].sort_values(ascending=False).tolist()


_PAIRS = [("Lakers", "LAL", "Celtics", "BOS"), ("Heat", "MIA", "Celtics", "BOS")]
_PAIRS += [("Knicks", "NYK", "Celtics", "BOS"), ("Celtics", "BOS", "Lakers", "LAL")]


def _pair_games(team: str, opp: str) -> pd.DataFrame:
    games = pd.read_csv(RAW / "2025-26_regular_season.csv")
    other = games[["game_id", "team_abbr", "pts"]].rename(
        columns={"team_abbr": "opp", "pts": "opp_pts"}
    )
    rows = games[games["team_abbr"] == team].merge(other, on="game_id")
    return rows[rows["opp"] == opp]


@pytest.mark.parametrize(("a", "a_abbr", "b", "b_abbr"), _PAIRS)
@pytest.mark.parametrize("own", [True, False])
def test_against_a_team_the_clause_names_its_side(a, a_abbr, b, b_abbr, own):
    games = _pair_games(a_abbr, b_abbr)
    games = games[(games["pts"] if own else games["opp_pts"]) >= 110]
    named = a if own else b
    rows = _rows(f"{a} games against the {b} when the {named} scored 110")
    assert sorted(str(r["game_date"])[:10] for r in rows) == sorted(games["game_date"].tolist())


def test_top_n_by_the_same_stat_ranks_the_subject():
    games = _pair_games("LAL", "BOS")
    games = games[games["opp_pts"] >= 120]
    rows = _rows("Lakers top 3 scoring games when the Celtics scored 120")
    assert [r["pts"] for r in rows] == games["pts"].nlargest(3).tolist()


def test_a_clause_without_a_number_is_left_alone():
    from nbatools.commands.natural_query import _other_team_clause

    text = "lakers record when the celtics had a winning record"
    assert _other_team_clause(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "lakers vs celtics when the celtics scored 120",
        "lakers vs celtics head to head record when the celtics made 15 threes",
        "compare the lakers and celtics when the celtics scored 120",
        "los angeles lakers vs the boston celtics when the celtics scored 120",
        "lakers celtics head to head when the celtics scored 120",
        "lakers road games at boston when boston scored 120",
        "lakers games @ celtics when the celtics scored 120",
    ],
)
def test_two_sides_compared_and_at_forms_are_left_alone(text):
    from nbatools.commands.natural_query import _other_team_clause

    assert _other_team_clause(text) == text
