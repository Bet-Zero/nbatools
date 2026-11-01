"""Bounded public verification of the newly deployed mixed participation route."""

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


def test_deployed_mixed_participation_matches_independent_season_source():
    assert os.environ["NBATOOLS_DATA_GENERATION"] == BASE
    proof = json.loads(
        (
            ROOT
            / "working/nba-tools-completion-program/source-evidence/k08-mixed"
            / "source-arithmetic.json"
        ).read_text()
    )
    assert proof["base_generation"] == BASE and proof["manifest_sha256"] == MANIFEST
    readiness = requests.get(
        "https://nbatools.vercel.app/readiness", timeout=30, allow_redirects=False
    )
    assert readiness.status_code == 503
    state = readiness.json()
    assert state["active_generation"] == BASE and state["ready"] is False
    assert [b["code"] for b in state["blockers"]] == ["new_season_not_loaded"]
    assert state["exception"]["applied"] is False
    cases = [
        a
        for a in proof["answers"]
        if a["scope"] == "fullseason" or a["positive_player_id"] == 1629029
    ]
    assert len(cases) == 3
    responses = []
    next_start = time.monotonic()
    for case in cases:
        delay = max(0, next_start - time.monotonic())
        if delay:
            time.sleep(delay)
        next_start = time.monotonic() + 7.0  # Existing public pacing; no quota override/retry.
        dates = " from 2025-10-24 to 2025-10-27" if case["scope"] != "fullseason" else ""
        question = (
            f"Lakers record with {case['positive_player']} playing and LeBron James out"
            f" in 2025-26{dates}"
        )
        response = requests.post(
            "https://nbatools.vercel.app/query",
            json={"query": question},
            timeout=30,
            allow_redirects=False,
        )
        assert response.status_code == 200
        answer = response.json()
        assert answer["result_status"] == "ok" and answer["route"] == "team_record"

        def normalized_text(value):
            return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").lower()

        caveats = [normalized_text(note) for note in answer["caveats"]]
        assert normalized_text("record filtered to games without LeBron James") in caveats
        assert (
            normalized_text(f"record filtered to games with {case['positive_player']}") in caveats
        )
        sections = answer["result"]["sections"]
        assert len(sections["summary"]) == 1
        summary = sections["summary"][0]
        for key in ["games", "wins", "losses"]:
            assert summary[key] == case[key]
        assert summary["pts_avg"] == pytest.approx(case["points_per_game"], abs=0.001)
        assert summary["season_start"] == summary["season_end"] == "2025-26"
        assert len(sections["game_log"]) == case["games"]
        assert {int(row["game_id"]) for row in sections["game_log"]} == set(case["game_ids"])
        assert all(row["season"] == "2025-26" for row in sections["game_log"])
        responses.append(dict(query=question, expected_source=case, answer=answer))
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "mixed-deployed"
    output.mkdir(parents=True, exist_ok=True)
    (output / "receipt.json").write_text(
        json.dumps(
            dict(
                classification="mixed_participation_public_query_verification_no_data_publication",
                readiness=state,
                operational_acceptance_complete=False,
                public_readiness_requests=1,
                public_query_requests=3,
                attempts_per_request=1,
                nba_source_requests=0,
                production_data_writes=0,
                responses=responses,
            ),
            indent=2,
        )
        + "\n"
    )
