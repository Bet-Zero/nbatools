"""Review discovery: canonical owner survives legacy alias spellings after H10 repair."""

from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query


@pytest.mark.parametrize(
    "opponents,owner", [("BOS and DEN", "BOS"), ("Celtics and Nuggets", "Celtics")]
)
def test_named_opponent_owner_keeps_raw_same_game_ids(monkeypatch, opponents, owner):
    root = Path("qa/fixtures/query_engine_sample")
    raw = root / "data/raw"
    teams = pd.read_csv(raw / "team_game_stats/2025-26_regular_season.csv")
    players = pd.read_csv(raw / "player_game_stats/2025-26_regular_season.csv")
    own = players.loc[players.player_name.eq("Stephen Curry")].merge(
        teams[["game_id", "team_id", "pts"]], on=["game_id", "team_id"], suffixes=("", "_team")
    )
    other = teams[["game_id", "team_id", "ast"]].rename(
        columns={"team_id": "opponent_team_id", "ast": "opponent_ast"}
    )
    expected = own.merge(other, on=["game_id", "opponent_team_id"])
    expected = expected.loc[
        expected.pts_team.ge(80)
        & expected.opponent_ast.ge(20)
        & expected.opponent_team_abbr.eq("BOS")
    ]
    assert len(expected) > 0
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.resolve()))
    reset_data_source_cache()
    try:
        answer = execute_natural_query(
            f"Stephen Curry games vs {opponents} when {owner} had at least 20 assists "
            "with 80+ team points in 2025-26"
        )
        assert answer.result_status == "ok", answer.metadata
        sections = answer.result.to_dict()["sections"]
        rows = sections.get("game_log", sections.get("finder", []))
        assert sorted(int(row["game_id"]) for row in rows) == sorted(
            expected.game_id.astype(int).tolist()
        )
        assert any(
            c.get("stat") == "opponent_ast" and c.get("opponent_team") == "BOS"
            for c in answer.metadata["conditions"]
        )
    finally:
        reset_data_source_cache()
