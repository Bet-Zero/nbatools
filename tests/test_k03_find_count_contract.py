"""Controlled, synthetic discrimination for Core-1 find/count semantics."""

import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands._parse_helpers import detect_distinct_player_count
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]
FIXTURE = Path("qa/fixtures/query_engine_sample")


@pytest.fixture
def population(tmp_path, monkeypatch):
    root = tmp_path / "fixture"
    shutil.copytree(FIXTURE, root)
    path = root / "data/raw/player_game_stats/2025-26_regular_season.csv"
    seeds = pd.read_csv(path)
    identities = {"A": 203999, "B": 1628973, "C": 1627750}
    values = [
        (1, "A", 25, 12, 0, -2),
        (2, "A", 25, 5, 1, 0),
        (3, "B", 18, 12, 0, 2),
        (4, "B", 18, 5, 0, -2),
        (5, "C", 20, 10, 0, 0),
        (1, "C", 30, 11, 2, 2),
        (6, "A", 0, 0, 0, 0),
    ]
    rows = []
    for game, who, pts, ast, tov, pm in values:
        row = seeds.loc[seeds.player_id.eq(identities[who])].iloc[0].to_dict()
        row.update(
            game_id=game, game_date=f"2025-11-{game:02d}", pts=pts, ast=ast, tov=tov, plus_minus=pm
        )
        rows.append(row)
    pd.DataFrame(rows).to_csv(path, index=False)
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    reset_data_source_cache()
    yield identities
    reset_data_source_cache()


@pytest.mark.parametrize(
    ("predicate", "keys"),
    [
        ("at least 10 assists and exactly zero turnovers", [(1, "A"), (3, "B"), (5, "C")]),
        ("above 20 points", [(1, "A"), (2, "A"), (1, "C")]),
        ("at least 20 points", [(1, "A"), (2, "A"), (1, "C"), (5, "C")]),
        ("under 20 points", [(3, "B"), (4, "B"), (6, "A")]),
        ("at most 20 points", [(3, "B"), (4, "B"), (6, "A"), (5, "C")]),
        ("(over 20 points or over 10 assists)", [(1, "A"), (2, "A"), (3, "B"), (1, "C")]),
    ],
)
def test_complete_player_game_population(population, predicate, keys):
    response = execute_natural_query(f"How many player games with {predicate} in 2025-26?")
    assert response.result_status == "ok", response.to_dict()
    assert response.result.count == len(keys)
    rows = response.result.games
    assert len(rows) == len(keys)
    assert set(zip(rows.game_id, rows.player_id)) == {(g, population[p]) for g, p in keys}
    assert "games" in response.metadata["count_phrase"]


def test_distinct_count_is_not_games_or_truncated_leaders(population):
    response = execute_natural_query(
        "How many distinct players scored at least 20 points in a game in 2025-26?"
    )
    assert response.result_status == "ok"
    # Same predicate above selects four player-games, three game IDs, two players.
    assert response.result.count == 2
    assert "players" in response.metadata["count_phrase"]


def test_qualified_zero(population):
    response = execute_natural_query("How many player games with at least 80 points in 2025-26?")
    assert response.result_status == "ok"
    assert response.result.count == 0


@pytest.mark.parametrize(
    ("query", "distinct"),
    [
        ("how many player games", False),
        ("count player games", False),
        ("number of player games", False),
        ("how many distinct players", True),
        ("number of distinct players", True),
        ("count of players", True),
    ],
)
def test_count_grain_grammar(query, distinct):
    assert detect_distinct_player_count(query) is distinct


def test_unimplemented_exact_nonzero_cannot_be_silently_inclusive(population):
    response = execute_natural_query(
        "How many player games with exactly 10 assists and zero turnovers in 2025-26?"
    )
    # A future positive equality implementation may replace this containment,
    # but accepting all >=10 assist games is never correct.
    assert response.result_status != "ok"
    assert "primary_count" not in response.metadata


@pytest.mark.parametrize("operator", ["above", "exceeded"])
def test_grouped_strict_synonyms(population, operator):
    response = execute_natural_query(
        f"How many player games with ({operator} 20 points or over 10 assists) in 2025-26?"
    )
    assert response.result_status == "ok"
    assert response.result.count == 4
    assert set(zip(response.result.games.game_id, response.result.games.player_id)) == {
        (1, population["A"]),
        (2, population["A"]),
        (3, population["B"]),
        (1, population["C"]),
    }
