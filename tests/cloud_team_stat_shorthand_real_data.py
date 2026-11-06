"""Required NBA consumers using retained qualified date-specific populations.

All originals and preparation checks are reused, never reacquired. Expected IDs
and values are selected directly from qualified raw team/player rows. Full-season
Poeltl tenure remains unaccepted and is unrelated to this interpretation repair.
"""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.cloud_multi_team_absence_real_data import MISSED, build_native_stage

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_qualified_team_noun_thresholds_across_consumers(tmp_path, monkeypatch):
    root, teams, players = build_native_stage(tmp_path, monkeypatch)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    receipts = []
    try:
        sas = teams.loc[teams.team_abbr.eq("SAS") & teams.game_date.le("2023-02-08")]
        missed = sas.loc[sas.game_id.isin(MISSED)]
        assert len(sas) == 55 and len(missed) == 9
        cases = [
            ("80+ team points", "pts", 80, None),
            ("under 110 team points", "pts", None, 109.9999),
            ("110 or fewer team points", "pts", None, 110),
            ("at least 25 team assists", "ast", 25, None),
            ("at most 12 team turnovers", "tov", None, 12),
        ]
        for wording, stat, floor, ceiling in cases:
            expected = missed
            if floor is not None:
                expected = expected.loc[expected[stat].ge(floor)]
            if ceiling is not None:
                expected = expected.loc[expected[stat].le(ceiling)]
            question = (
                "How many games did Jakob Poeltl miss for the Spurs in 2022-23 "
                f"before February 9, 2023 with {wording}?"
            )
            natural = execute_natural_query(question)
            assert natural.result_status == "ok", natural.metadata
            body = natural.result.to_dict()
            assert body["sections"]["count"] == [{"count": len(expected)}]
            assert {int(r["game_id"]) for r in body["sections"].get("finder", [])} == set(
                expected.game_id
            )
            assert body["metadata"]["membership_coverage"]["complete"]
            structured = execute_structured_query(
                "game_finder",
                season="2022-23",
                team="SAS",
                membership_player="Jakob Poeltl",
                end_date="2023-02-08",
                stat=stat,
                min_value=floor,
                max_value=ceiling,
                limit=1000,
            )
            assert {
                int(r["game_id"]) for r in structured.result.to_dict()["sections"].get("finder", [])
            } == set(expected.game_id)
            response = TestClient(app).post("/query", json={"query": question})
            assert response.status_code == 200 and response.json()["result_status"] == "ok"
            assert response.json()["result"]["sections"]["count"] == [{"count": len(expected)}]
            assert "team " in natural.metadata["answer_phrase"]
            receipts.append(
                dict(
                    query=question,
                    game_ids=sorted(int(x) for x in expected.game_id),
                    count=len(expected),
                    team_points_sum=int(expected.pts.sum()),
                    answer=natural.metadata["answer_phrase"],
                )
            )
        # A different player's real played-game summary verifies that the team
        # threshold never moves to the individual's own box score.
        warriors = teams.loc[teams.team_abbr.eq("GSW") & teams.pts.lt(110)]
        expected = players.loc[players.player_id.eq(1626172)].merge(
            warriors[["game_id", "team_id"]], on=["game_id", "team_id"], validate="one_to_one"
        )
        answer = execute_natural_query(
            "Kevon Looney average rebounds in 2022-23 with under 110 team points"
        )
        assert answer.result_status == "ok", answer.metadata
        body = answer.result.to_dict()["sections"]
        assert {int(r["game_id"]) for r in body["game_log"]} == set(expected.game_id)
        assert body["summary"][0]["games"] == len(expected)
        assert body["summary"][0]["reb_sum"] == expected.reb.sum()
        receipts.append(
            dict(
                query="Looney summary with under 110 team points",
                game_ids=sorted(int(x) for x in expected.game_id),
                games=len(expected),
                rebounds_sum=int(expected.reb.sum()),
            )
        )
        # Named-team record is another consumer of the shared noun interpretation.
        result = execute_natural_query("Warriors record in 2022-23 with under 110 team points")
        assert result.result_status == "ok", result.metadata
        summary = result.result.to_dict()["sections"]["summary"][0]
        assert summary["games"] == len(warriors)
        assert summary["wins"] == warriors.wl.eq("W").sum()
        assert summary["losses"] == warriors.wl.eq("L").sum()
        output = (
            Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path / "evidence")))
            / "team-stat-shorthand"
        )
        output.mkdir(parents=True, exist_ok=True)
        (output / "qualified-acceptance.json").write_text(
            json.dumps(
                dict(
                    answers=receipts,
                    warriors_record={k: summary[k] for k in ("games", "wins", "losses")},
                    scope="retained qualified scoped originals; no new source capture",
                    full_season_poeltl_accepted=False,
                    production_writes=0,
                ),
                indent=2,
            )
            + "\n"
        )
    finally:
        reset_data_source_cache()
