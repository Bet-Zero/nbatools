"""Exact retained-bundle transport and full-snapshot preparation; no production writes."""

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nbatools.commands._participation_observations import combined_observations
from nbatools.commands.pipeline import generation_publication as publication
from nbatools.data_source import data_path, reset_data_source_cache
from nbatools.dataframe_cache import clear_frame_cache
from tests.test_season_inactive_pilot_real_data import _census
from tools import r2_publication as gate
from tools.audit_participation_2025_publication import readiness_observation
from tools.availability_overlay import verify_append

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"
EVIDENCE = PROGRAM / "source-evidence/season-inactive-pilot-20261115"
INVENTORY = PROGRAM / "season-inactive-inventory.json"
BASE = "availability-participation-2025-durant-v1-20261114"
MANIFEST = "cde98408f3390e6191da564197fb77ffbc598a3059963cfc21d9f2d7e1a6b366"
GENERATION = "availability-season-inactive-2023-v1-20261115"
AVAILABILITY = "raw/player_game_availability/2023-24_regular_season.csv"


def _facts(stats, old, inactive):
    facts = {
        (int(r.game_id), int(r.player_id)): (int(r.team_id), "played")
        for r in stats.loc[stats.minutes.gt(0)].itertuples()
    }
    for frame in (old, inactive):
        for r in frame.itertuples():
            key, value = (int(r.game_id), int(r.player_id)), (int(r.team_id), r.participation_state)
            assert key not in facts or facts[key] == value
            facts[key] = value
    return facts


def test_exact_pr623_bundle_complete_snapshot_prepare(tmp_path, monkeypatch, capfd):
    inventory = json.loads(INVENTORY.read_bytes())
    original = json.loads((EVIDENCE / "qualification.json").read_bytes())
    source = gate.api("/actions/runs/43690403060")
    assert source["head_sha"] == original["request_sha"] and source["conclusion"] == "success"
    job = gate.api("/actions/jobs/132739835179")
    assert job["run_id"] == source["id"] and job["conclusion"] == "success"
    client, bucket = publication._resolve_r2_target(
        client=None, bucket_name=None, env=None, env_file=None
    )
    before, _, manifest_hash = gate.verify_pointer_manifest(client, bucket, BASE)
    assert manifest_hash == MANIFEST
    # Existing deployed production source already includes the PR623 reader.
    deployments = gate.api("/deployments?environment=Production&per_page=5")
    deployed = None
    for item in deployments:
        statuses = gate.api(f"/deployments/{item['id']}/statuses")
        if statuses and statuses[0]["state"] == "success":
            deployed = item
            break
    assert deployed and deployed["sha"] == "b4c8b0631694c8ceca0867a383dfbd016ce900d6"
    readiness = readiness_observation()
    assert readiness["classification"] in {"ready_observed", "new_season_not_loaded"}
    assert readiness["body"]["active_generation"] == BASE
    raw_inputs = {
        path: data_path("data/" + path).read_bytes()
        for path in [
            AVAILABILITY,
            *[
                f"raw/{kind}/2023-24_regular_season.csv"
                for kind in ("team_game_stats", "player_game_stats")
            ],
            "raw/rosters/2023-24.csv",
        ]
    }
    transport = tmp_path / "transport"
    transport.mkdir()
    bundle = EVIDENCE / "qualified-overlay-v1.zip"
    shutil.copyfile(bundle, transport / bundle.name)
    work = tmp_path / "prepared"
    subprocess.run(
        [
            sys.executable,
            str(PROGRAM / "publish-season-inactive.py"),
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
    budget = gate.bucket_budget(client, bucket, json.loads(gate.REGISTRY.read_bytes()), local)
    snapshot = work / "validation/generations" / GENERATION
    manifest_raw = (snapshot / "metadata/generation_manifest.json").read_bytes()
    assert hashlib.sha256(manifest_raw).hexdigest() == local["manifest_sha256"]
    files = {x["path"]: x for x in json.loads(manifest_raw)["files"]}
    base = {x["path"]: x for x in json.loads((work / "base-manifest.json").read_bytes())["files"]}
    overlay = {x["path"]: x for x in inventory["overlay_files"] if x["path"].startswith("raw/")}
    assert files.keys() == base.keys() | overlay.keys()
    assert len(files) == local["file_count"] == 1213
    assert local["total_bytes"] == 415007162
    for name, item in base.items():
        if name not in inventory["append_only"]:
            assert files[name] == item, name
    for name, item in overlay.items():
        assert files[name] == item, name
    for name, item in files.items():
        raw = (snapshot / name).read_bytes()
        assert len(raw) == item["size_bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"]
    for name, spec in inventory["append_only"].items():
        verify_append(
            name, data_path("data/" + name).read_bytes(), (snapshot / name).read_bytes(), spec
        )
    teams = pd.read_csv(io.BytesIO(raw_inputs["raw/team_game_stats/2023-24_regular_season.csv"]))
    stats = pd.read_csv(io.BytesIO(raw_inputs["raw/player_game_stats/2023-24_regular_season.csv"]))
    old = pd.read_csv(io.BytesIO(raw_inputs[AVAILABILITY]))
    roster = pd.read_csv(io.BytesIO(raw_inputs["raw/rosters/2023-24.csv"]))
    pairs = {(int(t), int(p)) for f in (stats, old, roster) for t, p in zip(f.team_id, f.player_id)}
    with ZipFile(PROGRAM / "source-evidence/team-membership-20261114/originals.zip") as z:
        for move in json.loads(z.read("player-movement.json"))["NBA_Player_Movement"]["rows"]:
            if "2023-10-23" <= move["TRANSACTION_DATE"][:10] <= "2024-04-14" and move["PLAYER_ID"]:
                pairs.add((int(move["TEAM_ID"]), int(move["PLAYER_ID"])))
                if move["Transaction_Type"] == "Trade":
                    pairs.add((int(move["Additional_Sort"]), int(move["PLAYER_ID"])))
    with ZipFile(bundle) as z:
        inactive = pd.read_csv(
            io.BytesIO(
                z.read(
                    "raw/player_game_inactive_sources/adf13e62baeb356fab9f8507a37379f35a4631cae3846700cb49fab4cd01969b.csv"
                )
            )
        )
    inactive = inactive.loc[inactive.season_type_id.eq(2)].copy()
    inactive["participation_state"] = "did_not_play"
    inactive["player_name"] = inactive.first_name + " " + inactive.last_name
    before_facts = _facts(stats, old, inactive.iloc[:0])
    facts = _facts(stats, old, inactive)
    # Existing native game originals supply the prior PR619 observations.
    request = json.loads(
        (PROGRAM / "source-evidence/league-participation-20261114/game-request.json").read_bytes()
    )
    for item in request["requirements"]:
        gid = int(item["game_id"])
        native = json.loads(
            (
                PROGRAM
                / f"source-evidence/k08-tatum-2023/sources/boxscoretraditionalv3_{gid:010d}.json"
            ).read_bytes()
        )["boxScoreTraditional"]
        for side in ("homeTeam", "awayTeam"):
            for person in native[side]["players"]:
                clock = person["statistics"]["minutes"]
                if clock and sum(map(float, clock.split(":"))) > 0:
                    state = "played"
                elif person["comment"].startswith(("DNP", "DND", "NWT", "INACTIVE")):
                    state = "did_not_play"
                else:
                    continue
                key, value = (gid, int(person["personId"])), (int(native[side]["teamId"]), state)
                assert key not in facts or facts[key] == value
                facts[key] = value
    expected_full = {
        (t, p)
        for t, p in pairs
        if all((int(g), p) in facts for g in teams.loc[teams.team_id.eq(t), "game_id"])
    }
    before_full = {
        (t, p)
        for t, p in pairs
        if all((int(g), p) in before_facts for g in teams.loc[teams.team_id.eq(t), "game_id"])
    }
    assert len(before_full) == 18 and len(expected_full) == 93 and before_full <= expected_full
    for t, p in before_full:
        assert all(
            facts[int(g), p] == before_facts[int(g), p]
            for g in teams.loc[teams.team_id.eq(t), "game_id"]
        )
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    (consumer / "data").symlink_to(work / "validation", target_is_directory=True)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(consumer))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", GENERATION)
    reset_data_source_cache()
    clear_frame_cache()
    try:
        observations, _ = combined_observations(["2023-24"], "Regular Season")
        census, full = _census(
            observations, teams, pairs, set(pd.read_csv(snapshot / AVAILABILITY).game_id)
        )
        assert census == original["phases"]["retained_batch"]
        assert set(full) == expected_full
        assert not list((snapshot / "raw/player_team_membership").glob("*"))
        from nbatools.api import app

        api = TestClient(app)
        names = (
            pd.concat([stats, old, inactive])
            .drop_duplicates("player_id")
            .set_index("player_id")
            .player_name
        )
        checked = 0
        for t, p in sorted(expected_full):
            games = teams.loc[teams.team_id.eq(t)]
            for word, state in (("with", "played"), ("without", "did_not_play")):
                ids = {int(g) for g in games.game_id if facts[int(g), p] == (t, state)}
                expected = games.loc[games.game_id.isin(ids)]
                question = f"{games.team_name.iloc[0]} record {word} {names[p]} in 2023-24"
                response = api.post("/query", json={"query": question})
                assert response.status_code == 200
                answer = response.json()
                if not ids:
                    assert (answer["result_status"], answer["result_reason"]) == (
                        "no_result",
                        "no_match",
                    ), question
                else:
                    assert answer["result_status"] == "ok", question
                    sections = answer["result"]["sections"]
                    assert {int(r["game_id"]) for r in sections["game_log"]} == ids, question
                    summary = sections["summary"][0]
                    assert (summary["games"], summary["wins"], summary["losses"]) == (
                        len(ids),
                        int(expected.wl.eq("W").sum()),
                        int(expected.wl.eq("L").sum()),
                    ), question
                checked += 1
        assert checked == 186
        prior = json.loads(gate.REGISTRY.read_bytes())["packages"]["participation-2025-durant-v1"]
        for case in prior["deployed_checks"]:
            answer = api.post("/query", json={"query": case["query"]})
            assert answer.status_code == 200
            gate.verify_answer(case, answer.json())
        for question in (
            "Rockets record without Steven Adams in 2023-24",
            "Lakers record without Spencer Dinwiddie in 2023-24",
        ):
            answer = api.post("/query", json={"query": question}).json()
            assert (answer["result_status"], answer["result_reason"]) == (
                "no_result",
                "unsupported",
            )
    finally:
        reset_data_source_cache()
        clear_frame_cache()
    after, _, after_hash = gate.verify_pointer_manifest(client, bucket, BASE)
    assert after == before and after_hash == MANIFEST
    # Emit the existing ZIP, not a newly generated overlay. This test also forms
    # the ordinary acquired_data transport consumed by the unchanged protected gate.
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"])
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(bundle, output / bundle.name)
    report = dict(
        classification="prepared_no_writes_not_operational_acceptance",
        r2_writes=0,
        generation_id=GENERATION,
        base_generation=BASE,
        source_qualification_run=43690403060,
        local_validation=local,
        budget=budget,
        census=census,
        complete_season_queries=checked,
        preserved_registered_answers=len(prior["deployed_checks"]),
        pointer_unchanged=before == after,
        production_deployment=dict(id=deployed["id"], sha=deployed["sha"]),
        readiness=readiness,
        activation_ready=readiness["classification"] == "ready_observed",
    )
    (output.parent / "season-inactive-preparation.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    (output.parent / "season-inactive-manifest.json").write_bytes(manifest_raw)
    with capfd.disabled():
        print("SEASON_INACTIVE_PREPARATION " + json.dumps(report), flush=True)
