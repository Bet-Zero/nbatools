"""The ranking metric and an exact-zero condition must keep separate meanings."""

import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]
FIXTURE = Path("qa/fixtures/query_engine_sample")


@pytest.fixture
def zero_team_games(tmp_path, monkeypatch):
    root = tmp_path / "fixture"
    shutil.copytree(FIXTURE, root)
    path = root / "data/raw/team_game_stats/2025-26_regular_season.csv"
    teams = pd.read_csv(path)
    owner = teams.team_abbr.eq("DEN") & teams.opponent_team_abbr.eq("GSW")
    ids = sorted(teams.loc[owner, "game_id"])
    assert len(ids) > 3
    teams.loc[owner, "tov"] = 5
    teams.loc[owner & teams.game_id.isin(ids[:3]), "tov"] = 0
    # The opposing side has zero in DIFFERENT games, to discriminate ownership.
    opp = teams.team_abbr.eq("GSW") & teams.opponent_team_abbr.eq("DEN")
    teams.loc[opp, "tov"] = 4
    teams.loc[opp & teams.game_id.isin(ids[3:6]), "tov"] = 0
    teams.to_csv(path, index=False)
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    reset_data_source_cache()
    yield teams.loc[owner].copy()
    reset_data_source_cache()


@pytest.mark.parametrize(
    "condition",
    [
        "without turnovers",
        "without any turnovers",
        "with no turnovers",
        "with zero turnovers",
        "with 0 turnovers",
    ],
)
@pytest.mark.parametrize(
    "owner",
    [
        "best scoring games by Nuggets vs Warriors",
        "best scoring games vs Warriors by Nuggets",
        "Nuggets best scoring games vs Warriors",
    ],
)
def test_team_zero_is_a_filter_beside_scoring_rank(zero_team_games, condition, owner):
    expected = zero_team_games.loc[zero_team_games.tov.eq(0)].sort_values("pts", ascending=False)
    result = execute_natural_query(f"{owner} {condition} in 2025-26")
    assert result.result_status == "ok"
    rows = result.to_dict()["sections"]["finder"]
    assert [(r["game_id"], r["pts"], r["tov"]) for r in rows] == list(
        expected[["game_id", "pts", "tov"]].itertuples(index=False, name=None)
    )


@pytest.mark.parametrize("condition", ["with 0+ turnovers", "with at least 0 turnovers"])
def test_explicit_zero_floor_keeps_all_games(zero_team_games, condition):
    result = execute_natural_query(f"Nuggets best scoring games vs Warriors {condition} in 2025-26")
    assert result.result_status == "ok"
    rows = result.to_dict()["sections"]["finder"]
    assert {r["game_id"] for r in rows} == set(zero_team_games.game_id)


def test_player_zero_filter_matches_raw_ids_and_structured():
    players = pd.read_csv(FIXTURE / "data/raw/player_game_stats/2025-26_regular_season.csv")
    expected = players.loc[players.player_name.eq("Jrue Holiday") & players.tov.eq(0)].sort_values(
        "pts", ascending=False
    )
    assert 0 < len(expected) <= 25
    natural = execute_natural_query("Jrue Holiday top 25 scoring games with no turnovers in 2025-26")
    structured = execute_structured_query(
        "player_game_finder",
        player="Jrue Holiday",
        season="2025-26",
        stat="pts",
        sort_by="stat",
        conditions=[{"stat": "tov", "max_value": 0}],
    )
    for result in (natural, structured):
        assert result.result_status == "ok"
        rows = result.to_dict()["sections"]["finder"]
        assert {r["game_id"] for r in rows} == set(expected.game_id)
        assert [r["pts"] for r in rows] == sorted(expected.pts, reverse=True)
