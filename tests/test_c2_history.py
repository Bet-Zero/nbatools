"""C2 history: career highs and the covered span of a career.

"Jokic career high points" returned his career averages instead of his best
game, and career answers did not say the data starts in 1996-97. Expected
values come from the fixture's game CSVs, never from the engine.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

GAMES = Path("qa/fixtures/query_engine_sample/data/raw/player_game_stats")


def _career(name: str) -> pd.DataFrame:
    frame = pd.concat(pd.read_csv(path) for path in GAMES.glob("*_regular_season.csv"))
    return frame[frame["player_name"] == name]


@pytest.mark.parametrize(
    ("query", "stat"),
    [("Jokic career high points", "pts"), ("Jokic career high in rebounds", "reb")],
)
def test_career_high_is_the_best_single_game(query, stat):
    games = _career("Nikola Jokić")
    result = execute_natural_query(query)
    assert result.result_status == "ok"
    assert result.route == "player_game_finder"
    rows = result.result.to_dict()["sections"]["finder"]
    assert rows[0][stat] == games[stat].max()
    assert {r["season"] for r in rows} <= set(games["season"])


@pytest.mark.parametrize("query", ["Jokic career points", "Jokic career high points"])
def test_career_answers_label_the_covered_span(query):
    notes = execute_natural_query(query).metadata.get("notes") or []
    assert any("covers 1996-97 onward" in note for note in notes), notes


def test_single_season_answers_carry_no_career_label():
    notes = execute_natural_query("Jokic season high").metadata.get("notes") or []
    assert not any("career_span" in note for note in notes)
