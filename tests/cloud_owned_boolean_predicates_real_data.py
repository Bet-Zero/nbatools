"""Qualified retained originals: shared owned Boolean consumers, exact keys."""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.data_source import data_read_csv, reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.cloud_distinct_player_boolean_counts_real_data import _verify
from tests.cloud_poeltl_full_season_real_data import build_qualified_stage

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
EVIDENCE = Path(
    "working/nba-tools-completion-program/source-evidence/distinct-player-or-20261106/independent"
)
ORACLE = json.loads((EVIDENCE / "oracle.json").read_text())


@pytest.mark.parametrize(
    "case,expression,selector",
    [
        (
            "native_team_owned",
            "(over 37 points or over 10 assists) with at least 125 team points",
            lambda r: (r.pts.gt(37) | r.ast.gt(10)) & r.team_points.ge(125),
        ),
        (
            "native_opponent_owned",
            "(over 37 points or over 10 assists) when opponents scored under 110 points",
            lambda r: (r.pts.gt(37) | r.ast.gt(10)) & r.opponent_points.lt(110),
        ),
    ],
)
def test_qualified_owned_boolean_keys_and_all_consumers(
    case, expression, selector, tmp_path, monkeypatch
):
    pinned = None
    if os.environ.get("DATA_SOURCE") == "r2":
        pinned = (
            data_read_csv("raw/player_game_stats/2022-23_regular_season.csv"),
            data_read_csv("raw/team_game_stats/2022-23_regular_season.csv"),
        )
    root, teams, players = build_qualified_stage(tmp_path, monkeypatch)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    try:
        # Direct reciprocal source-row joins, independent of the application helper.
        assert not teams.duplicated(["game_id", "team_id"]).any()
        raw = players.merge(
            teams[["game_id", "team_id", "pts"]].rename(columns={"pts": "team_points"}),
            on=["game_id", "team_id"],
            validate="many_to_one",
        )
        raw = raw.merge(
            teams[["game_id", "team_id", "pts"]].rename(
                columns={"team_id": "opponent_team_id", "pts": "opponent_points"}
            ),
            on=["game_id", "opponent_team_id"],
            validate="many_to_one",
        )
        assert raw[["team_points", "opponent_points"]].notna().all().all()
        expected = raw.loc[selector(raw)]
        oracle = ORACLE["cases"][case]
        full_keys = {
            tuple(map(int, r))
            for r in expected[["game_id", "team_id", "player_id"]].itertuples(
                index=False, name=None
            )
        }
        assert full_keys == {tuple(k) for k in oracle["selected_keys"]}
        assert len(expected) == oracle["player_games"]
        assert expected.player_id.nunique() == oracle["distinct_players"]
        assert expected.pts.sum() == oracle["pts_sum"]
        assert expected.ast.sum() == oracle["ast_sum"]
        if pinned is not None:
            p, t = pinned
            assert not t.duplicated(["game_id", "team_id"]).any()
            p = p.merge(
                t[["game_id", "team_id", "pts"]].rename(columns={"pts": "team_points"}),
                on=["game_id", "team_id"],
                validate="many_to_one",
            )
            p = p.merge(
                t[["game_id", "team_id", "pts"]].rename(
                    columns={"team_id": "opponent_team_id", "pts": "opponent_points"}
                ),
                on=["game_id", "opponent_team_id"],
                validate="many_to_one",
            )
            assert p[["team_points", "opponent_points"]].notna().all().all()
            selected = p.loc[selector(p)]
            assert {
                tuple(map(int, r))
                for r in selected[["game_id", "team_id", "player_id"]].itertuples(
                    index=False, name=None
                )
            } == full_keys
            assert (
                selected.groupby("player_id").size().to_dict()
                == expected.groupby("player_id").size().to_dict()
            )
            assert selected.pts.sum() == oracle["pts_sum"]
            assert selected.ast.sum() == oracle["ast_sum"]
        receipt = _verify(
            raw,
            expression,
            f"How many distinct players had {expression} in 2022-23?",
            selector,
            monkeypatch,
            scope={"season": "2022-23"},
        )
        game_question = f"How many player games with {expression} in 2022-23?"
        natural = execute_natural_query(game_question)
        assert natural.result_status == "ok", natural.to_dict()
        assert natural.metadata["primary_count"] == len(expected)
        structured = execute_structured_query(
            "player_game_finder", season="2022-23", condition_expression=expression, limit=None
        )
        http = TestClient(app).post("/query", json={"query": game_question})
        api = TestClient(app).post(
            "/structured-query",
            json={
                "route": "player_game_finder",
                "kwargs": {"season": "2022-23", "condition_expression": expression, "limit": None},
            },
        )
        assert http.status_code == api.status_code == 200
        assert http.json()["result_status"] == api.json()["result_status"] == "ok"
        expected_keys = {
            (int(r.game_id), r.team_abbr, int(r.player_id)) for r in expected.itertuples()
        }
        for doc in [
            natural.to_dict(),
            structured.to_dict(),
            http.json()["result"],
            api.json()["result"],
        ]:
            assert {
                (int(r["game_id"]), r["team_abbr"], int(r["player_id"]))
                for r in doc["sections"]["finder"]
            } == expected_keys
        receipt.update(
            classification="qualified_retained_originals_not_production",
            prior_oracle=case,
            points_sum=int(expected.pts.sum()),
            assists_sum=int(expected.ast.sum()),
            player_game_answer=natural.metadata["count_phrase"],
            pinned_original_reconciliation=pinned is not None,
        )
        out = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / "owned-boolean"
        out.mkdir(parents=True, exist_ok=True)
        (out / (case + ".json")).write_text(json.dumps(receipt, indent=2) + "\n")
    finally:
        reset_data_source_cache()
