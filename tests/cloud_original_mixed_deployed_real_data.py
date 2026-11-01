"""Verify three public original-window answers against retained raw-source arithmetic."""

import json
import os
import time
import unicodedata
from pathlib import Path

import pytest
import requests

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
BASE = "availability-lebron-season-v1-20261031"
MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
ROOT = Path(__file__).resolve().parents[1]


def test_deployed_original_mixed_windows_match_retained_source():
    assert os.environ["NBATOOLS_DATA_GENERATION"] == BASE
    proof = json.loads(
        (
            ROOT
            / "working/nba-tools-completion-program/source-evidence/k08-original-window"
            / "source-run-receipt.json"
        ).read_bytes()
    )
    assert proof["generation"] == BASE and proof["manifest_sha256"] == MANIFEST
    cases = proof["answers"]
    assert len(cases) == 3 and [case["games"] for case in cases] == [3, 2, 0]
    readiness = requests.get(
        "https://nbatools.vercel.app/readiness", timeout=30, allow_redirects=False
    )
    assert readiness.status_code == 503
    state = readiness.json()
    assert state["active_generation"] == BASE and state["ready"] is False
    assert [b["code"] for b in state["blockers"]] == ["new_season_not_loaded"]
    assert state["exception"]["applied"] is False
    responses = []
    next_start = time.monotonic()
    for case in cases:
        delay = max(0, next_start - time.monotonic())
        if delay:
            time.sleep(delay)
        next_start = time.monotonic() + 7.0
        response = requests.post(
            "https://nbatools.vercel.app/query",
            json={"query": case["query"]},
            timeout=30,
            allow_redirects=False,
        )
        assert response.status_code == 200
        answer = response.json()
        assert answer["route"] == "team_record"
        sections = answer["result"]["sections"]
        if case["games"] == 0:
            assert answer["result_status"] == "no_result" and answer["result_reason"] == "no_match"
            assert not sections
        else:
            assert answer["result_status"] == "ok"
            assert len(sections["summary"]) == 1
            summary = sections["summary"][0]
            for key in ("games", "wins", "losses"):
                assert summary[key] == case[key]
            assert summary["pts_avg"] == pytest.approx(case["points"] / case["games"], abs=0.001)
            assert summary["season_start"] == summary["season_end"] == "2025-26"
            assert len(sections["game_log"]) == case["games"]
            assert {int(row["game_id"]) for row in sections["game_log"]} == set(
                case["selected_game_ids"]
            )
            assert all(row["season"] == "2025-26" for row in sections["game_log"])
            caveats = [
                unicodedata.normalize("NFKD", note).encode("ascii", "ignore").decode().lower()
                for note in answer["caveats"]
            ]
            assert "record filtered to games without lebron james" in caveats
            assert "record filtered to games with luka doncic" in caveats
            assert any("last 20 original games (selected 20;" in note for note in caveats)
        responses.append(dict(query=case["query"], expected_source=case, answer=answer))
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "original-mixed-deployed"
    output.mkdir(parents=True, exist_ok=False)
    (output / "receipt.json").write_text(
        json.dumps(
            dict(
                classification="original_mixed_window_public_verification_no_data_publication",
                readiness=state,
                operational_acceptance_complete=False,
                public_readiness_requests=1,
                public_query_requests=3,
                attempts_per_request=1,
                minimum_query_start_spacing_seconds=7,
                nba_source_requests=0,
                production_data_writes=0,
                responses=responses,
            ),
            indent=2,
        )
        + "\n"
    )
