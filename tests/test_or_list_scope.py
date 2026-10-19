"""OR branches inherit the resolved sample while explicit branch scopes win."""

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]
RAW = Path(__file__).resolve().parents[1] / "qa/fixtures/query_engine_sample/data/raw"


@pytest.mark.parametrize("second", ["at least 9 assists", "against Knicks with at least 9 assists"])
def test_or_inherits_only_missing_scope(second):
    players = pd.read_csv(RAW / "player_game_stats/2025-26_regular_season.csv")
    rows = players[players.player_id.eq(2544)]
    first = rows.opponent_team_abbr.isin(["BOS", "WAS"]) & rows.pts.ge(30)
    other_scope = ["NYK"] if second.startswith("against") else ["BOS", "WAS"]
    last = rows.opponent_team_abbr.isin(other_scope) & rows.ast.ge(9)
    expected = rows.loc[first | last]
    assert not expected.empty
    q = f"LeBron James games against Celtics and Wizards with at least 30 points or {second} in 2025-26"
    result = execute_natural_query(q)
    assert result.result_status == "ok", result.metadata
    actual = result.result.to_dict()["sections"]["finder"]
    assert sorted(int(row["game_id"]) for row in actual) == sorted(expected.game_id.astype(int))
    assert len(actual) == len({row["game_id"] for row in actual})
    assert all(row["player_id"] == 2544 for row in actual)
    assert result.metadata["boolean_filter_mode"] == "any"
    if second.startswith("against"):
        meta = result.metadata
        assert meta["opponent"] is None and not meta.get("opponents")
        assert not meta.get("opponent_context")
        assert not meta["threshold_conditions"] and not meta["conditions"]
        branches = meta["boolean_filter_branches"]
        assert [branch["scope"]["opponent"] for branch in branches] == [["BOS", "WAS"], "NYK"]
        assert [branch["conditions"][0]["stat"] for branch in branches] == ["pts", "ast"]
        paired = next(f["value"] for f in meta["applied_filters"] if f["kind"] == "boolean")
        assert paired == "(Opponent: BOS, WAS; 30+ PTS) OR (Opponent: NYK; 9+ AST)"
    else:
        assert not result.metadata.get("boolean_filter_branches")
        assert result.metadata["opponents"] == ["BOS", "WAS"]
