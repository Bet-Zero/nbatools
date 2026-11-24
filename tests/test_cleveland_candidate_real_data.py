"""Complete retained candidate composition and consumer preservation; R2 reads only."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.commands.pipeline import generation_publication as publication
from nbatools.data_source import reset_data_source_cache
from nbatools.dataframe_cache import clear_frame_cache
from tools import r2_publication as gate

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"
SOURCES = PROGRAM / "source-evidence"
BASE = "availability-season-inactive-2024-v1-20261116"
BASE_SHA = "0abce6f8261957df6cffc19ce24a4ed408a548e1292a33456ce55c0481903ecc"
GENERATION = "availability-cleveland-2024-v3-20261124"
CLE = 1610612739


def test_exact_cleveland_candidate_snapshot_and_registered_answers(tmp_path, monkeypatch, capfd):
    r2, bucket = publication._resolve_r2_target(
        client=None, bucket_name=None, env=None, env_file=None
    )
    before, _, digest = gate.verify_pointer_manifest(r2, bucket, BASE)
    assert digest == BASE_SHA
    transport = tmp_path / "transport"
    transport.mkdir()
    shutil.copyfile(
        SOURCES / "cleveland-two-game-2024/qualified-overlay-v2.zip",
        transport / "qualified-overlay-v2.zip",
    )
    shutil.copyfile(
        SOURCES / "team-appearances-cleveland-2024-v1/2024-25_regular_season.json",
        transport / "2024-25_regular_season.json",
    )
    work = tmp_path / "prepared"
    subprocess.run(
        [
            sys.executable,
            str(PROGRAM / "prepare-cleveland-candidate.py"),
            "--artifact-dir",
            str(transport),
            "--code-root",
            str(ROOT),
            "--work-dir",
            str(work),
            "--generation-id",
            GENERATION,
            "--prepare",
        ],
        check=True,
    )
    local = json.loads((work / "local-validation.json").read_bytes())
    policy = json.loads(gate.REGISTRY.read_bytes())
    budget = gate.bucket_budget(r2, bucket, policy, local)
    snapshot = work / "validation/generations" / GENERATION
    manifest_raw = (snapshot / "metadata/generation_manifest.json").read_bytes()
    assert hashlib.sha256(manifest_raw).hexdigest() == local["manifest_sha256"]
    preservation = json.loads((work / "preservation.json").read_bytes())
    assert preservation["production_writes"] == 0
    # Original independently reviewed native-source expectations, unchanged.
    parent = json.loads(
        (SOURCES / "cleveland-full-boxscore-2024/independent/oracle.json").read_bytes()
    )
    replacement = json.loads(
        (SOURCES / "cleveland-two-game-2024/independent/source-oracle.json").read_bytes()
    )
    rows = parent["accepted_rows"] + replacement["accepted_rows"]
    games = {g["game_id"]: g for g in parent["games"]}
    for report in replacement["reports"]:
        games[report["game_id"]]["points_by_team"] = report["points_by_team"]
    assert len(games) == 82
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(work / "validation"))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", GENERATION)
    reset_data_source_cache()
    clear_frame_cache()
    answers = []
    try:
        client = TestClient(app)
        checks = policy["packages"]["season-inactive-2024-v1"]["deployed_checks"]
        for case in checks:
            body = client.post("/query", json={"query": case["query"]}).json()
            answers.append(gate.verify_answer(case, body))
        cohort = replacement["cleveland_cohort"] + [
            dict(player_id=201939, player_name="Stephen Curry")
        ]
        assert len(cohort) == 22
        for actor in cohort:
            played = {
                r["game_id"]
                for r in rows
                if r["team_id"] == CLE
                and r["player_id"] == actor["player_id"]
                and r["participation_state"] == "played"
            }
            for relation, selected in (("with", played), ("without", set(games) - played)):
                query = f"Cavaliers record {relation} {actor['player_name']} in 2024-25"
                body = client.post("/query", json={"query": query}).json()
                assert body["result"]["metadata"]["participation_scope"] == "team"
                if not selected:
                    assert (body["result_status"], body["result_reason"]) == (
                        "no_result",
                        "no_match",
                    )
                    assert not body["result"]["sections"]
                    answers.append(dict(query=query, empty=True))
                    continue
                assert body["result_status"] == "ok", body
                summary = body["result"]["sections"]["summary"][0]
                wins = sum(
                    games[g]["points_by_team"][str(CLE)] > min(games[g]["points_by_team"].values())
                    for g in selected
                )
                assert (summary["games"], summary["wins"], summary["losses"]) == (
                    len(selected),
                    wins,
                    len(selected) - wins,
                )
                assert summary["pts_avg"] == pytest.approx(
                    sum(games[g]["points_by_team"][str(CLE)] for g in selected) / len(selected),
                    abs=0.001,
                )
                assert {
                    int(r["game_id"]) for r in body["result"]["sections"]["game_log"]
                } == selected
                answers.append(dict(query=query, summary=summary))
        for case in replacement["cleveland_cohort"]:
            if case["after"]["unknown"]:
                body = client.post(
                    "/query",
                    json={
                        "query": f"Cavaliers record without {case['player_name']} while on the team in 2024-25"
                    },
                ).json()
                assert (
                    body["result_status"] == "no_result" and body["result_reason"] != "no_match"
                ), body
    finally:
        reset_data_source_cache()
        clear_frame_cache()
    after, _, digest = gate.verify_pointer_manifest(r2, bucket, BASE)
    assert before == after and digest == BASE_SHA
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", tmp_path)) / "cleveland-candidate"
    output.mkdir(parents=True)
    for name in ("local-validation.json", "base-manifest.json", "preservation.json"):
        shutil.copyfile(work / name, output / name)
    (output / "generation_manifest.json").write_bytes(manifest_raw)
    report = dict(
        local=local,
        budget=budget,
        source_requests=0,
        production_writes=0,
        prior_registered_checks=len(checks),
        team_answer_checks=44,
        team_complete=21,
        rostered_complete=14,
        rostered_unknown=7,
        answers=answers,
    )
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    with capfd.disabled():
        print(
            "CLEVELAND_CANDIDATE_PREPARED "
            + json.dumps({k: v for k, v in report.items() if k != "answers"}),
            flush=True,
        )
