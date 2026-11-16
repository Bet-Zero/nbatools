"""Exact retained transport and complete proposed snapshot; no production writes."""

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

from nbatools.commands._dated_membership import COLUMNS
from nbatools.commands._participation_observations import combined_observations, game_participation
from nbatools.commands.pipeline import generation_publication as publication
from nbatools.data_source import reset_data_source_cache
from nbatools.dataframe_cache import clear_frame_cache
from tests.test_season_inactive_2024_real_data import EXPECTED_REJECTIONS
from tests.test_season_inactive_pilot_real_data import _census
from tests.test_season_inactive_publication_real_data import _facts
from tools import r2_publication as gate
from tools.audit_participation_2025_publication import readiness_observation

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"
EVIDENCE = PROGRAM / "source-evidence/season-inactive-2024"
BASE = "availability-season-inactive-2023-v1-20261115"
MANIFEST = "8ec80812ae9dda9222d9d157c253d7a919af214ae40c49a27c20f87b52d156c8"
GENERATION = "availability-season-inactive-2024-v1-20261116"
SEASON = "2024-25"
AVAILABILITY = f"raw/player_game_availability/{SEASON}_regular_season.csv"


def test_exact_pr626_bundle_complete_snapshot_prepare(tmp_path, monkeypatch, capfd):
    inventory = json.loads((PROGRAM / "season-inactive-2024-inventory.json").read_bytes())
    original = json.loads((EVIDENCE / "product-results.json").read_bytes())
    qualified = inventory["source_qualification"]
    source = gate.api(f"/actions/runs/{qualified['run_id']}")
    job = gate.api(f"/actions/jobs/{qualified['job_id']}")
    request = gate.api(f"/commits/{qualified['request_sha']}")
    assert source["head_sha"] == qualified["request_sha"] and source["conclusion"] == "success"
    assert source["path"] == ".github/workflows/r2-real-data-validation.yml"
    assert job["run_id"] == source["id"] and job["conclusion"] == "success"
    assert [p["sha"] for p in request["parents"]] == [qualified["reviewed_sha"]]
    client, bucket = publication._resolve_r2_target(
        client=None, bucket_name=None, env=None, env_file=None
    )
    before, _, manifest_hash = gate.verify_pointer_manifest(client, bucket, BASE)
    assert manifest_hash == MANIFEST
    # Successful Production deployment, not merely a preview build status.
    deployed = None
    for item in gate.api("/deployments?environment=Production&per_page=5"):
        statuses = gate.api(f"/deployments/{item['id']}/statuses")
        if statuses and statuses[0]["state"] == "success":
            deployed = item
            break
    assert deployed and deployed["sha"] == "2c7d8ccab23c268b8206f266b6488cf737146d2f"
    # Bind the deployed reader to the executing reader; publication helpers and
    # this adapter are not part of the production query runtime.
    runtime = [
        "src/nbatools/commands/pipeline/structured_participation.py",
        "src/nbatools/commands/_participation_observations.py",
        "src/nbatools/data_source.py",
        "src/nbatools/query_service.py",
    ]
    import base64

    for path in runtime:
        body = gate.api(f"/contents/{path}?ref={deployed['sha']}")
        assert base64.b64decode(body["content"]) == (ROOT / path).read_bytes()
    readiness = readiness_observation()
    assert readiness["classification"] in {"ready_observed", "new_season_not_loaded"}
    assert readiness["body"]["active_generation"] == BASE
    before2023, _ = combined_observations(["2023-24"], "Regular Season")
    transport = tmp_path / "transport"
    transport.mkdir()
    bundle = EVIDENCE / "qualified-overlay-v1.zip"
    shutil.copyfile(bundle, transport / bundle.name)
    work = tmp_path / "prepared"
    subprocess.run(
        [
            sys.executable,
            str(PROGRAM / "publish-season-inactive-2024.py"),
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
    additions = {x["path"]: x for x in inventory["overlay_files"]}
    assert len(base) == 1213 and not base.keys() & additions.keys()
    assert files == {**base, **additions}  # no append, overwrite or lost source
    assert local["file_count"] == 1216 and local["total_bytes"] == 419488508
    for name, item in files.items():
        raw = (snapshot / name).read_bytes()
        assert len(raw) == item["size_bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"]
    with ZipFile(bundle) as archive:
        for name in additions:
            assert archive.read(name) == (snapshot / name).read_bytes()
        source_csv = next(p for p in additions if p.startswith("raw/player_game_inactive_sources/"))
        raw_inactive = pd.read_csv(io.BytesIO(archive.read(source_csv)))
    raw_inactive = raw_inactive.loc[raw_inactive.season_type_id.eq(2)].copy()
    raw_inactive["participation_state"] = "did_not_play"
    raw_inactive["player_name"] = raw_inactive.first_name + " " + raw_inactive.last_name
    valid = raw_inactive.loc[
        [
            (int(r.game_id), int(r.team_id), int(r.player_id)) not in EXPECTED_REJECTIONS
            for r in raw_inactive.itertuples()
        ]
    ]
    assert len(raw_inactive) == 10854 and len(valid) == 10847
    receipt = json.loads(
        (snapshot / "raw/player_game_inactive/2024-25_regular_season.source.json").read_bytes()
    )
    assert {
        (r["game_id"], r["team_id"], r["player_id"]) for r in receipt["identity_name_rejections"]
    } == EXPECTED_REJECTIONS
    teams = pd.read_csv(snapshot / f"raw/team_game_stats/{SEASON}_regular_season.csv")
    stats = pd.read_csv(snapshot / f"raw/player_game_stats/{SEASON}_regular_season.csv")
    old = pd.read_csv(snapshot / AVAILABILITY)
    roster = pd.read_csv(snapshot / f"raw/rosters/{SEASON}.csv")
    pairs = {
        (int(t), int(p))
        for frame in (stats, old, roster, raw_inactive)
        for t, p in zip(frame.team_id, frame.player_id)
    }
    with ZipFile(PROGRAM / "source-evidence/team-membership-20261114/originals.zip") as archive:
        movements = json.loads(archive.read("player-movement.json"))["NBA_Player_Movement"]["rows"]
    for move in movements:
        if "2024-10-21" <= move["TRANSACTION_DATE"][:10] <= "2025-04-13" and move["PLAYER_ID"]:
            pairs.add((int(move["TEAM_ID"]), int(move["PLAYER_ID"])))
            if move["Transaction_Type"] == "Trade":
                pairs.add((int(move["Additional_Sort"]), int(move["PLAYER_ID"])))
    facts = _facts(stats, old, valid)
    expected_full = {
        (t, p)
        for t, p in pairs
        if all((int(g), p) in facts for g in teams.loc[teams.team_id.eq(t), "game_id"])
    }
    assert len(expected_full) == 69
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    (consumer / "data").symlink_to(work / "validation", target_is_directory=True)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(consumer))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", GENERATION)
    reset_data_source_cache()
    clear_frame_cache()
    try:
        after2023, _ = combined_observations(["2023-24"], "Regular Season")
        pd.testing.assert_frame_equal(
            before2023.reset_index(drop=True), after2023.reset_index(drop=True)
        )
        observations, _ = combined_observations([SEASON], "Regular Season")
        census, full = _census(observations, teams, pairs, set(raw_inactive.game_id))
        assert census == original["after"] and set(full) == expected_full
        assert not list((snapshot / "raw/player_team_membership").glob("*"))
        from nbatools.api import app

        api = TestClient(app)
        names = (
            pd.concat([stats, old, valid])
            .drop_duplicates("player_id")
            .set_index("player_id")
            .player_name
        )
        checks = []
        for t, p in sorted(expected_full):
            games = teams.loc[teams.team_id.eq(t)]
            for word, state in (("with", "played"), ("without", "did_not_play")):
                ids = {int(g) for g in games.game_id if facts[int(g), p] == (t, state)}
                expected = games.loc[games.game_id.isin(ids)]
                query = f"{games.team_name.iloc[0]} record {word} {names[p]} in {SEASON}"
                response = api.post("/query", json={"query": query})
                assert response.status_code == 200
                answer = response.json()
                if not ids:
                    assert (answer["result_status"], answer["result_reason"]) == (
                        "no_result",
                        "no_match",
                    ), query
                else:
                    assert answer["result_status"] == "ok", query
                    sections = answer["result"]["sections"]
                    assert {int(r["game_id"]) for r in sections["game_log"]} == ids, query
                    summary = sections["summary"][0]
                    assert (
                        summary["team_name"],
                        summary["season_start"],
                        summary["season_end"],
                        summary["season_type"],
                    ) == (games.team_name.iloc[0], SEASON, SEASON, "Regular Season")
                    assert (summary["games"], summary["wins"], summary["losses"]) == (
                        len(ids),
                        int(expected.wl.eq("W").sum()),
                        int(expected.wl.eq("L").sum()),
                    )
                checks.append(
                    dict(
                        query=query,
                        games=len(ids),
                        wins=int(expected.wl.eq("W").sum()),
                        losses=int(expected.wl.eq("L").sum()),
                        status=answer["result_status"],
                    )
                )
        assert checks == original["complete_season_queries"] and len(checks) == 138
        prior = json.loads(gate.REGISTRY.read_bytes())["packages"]["season-inactive-2023-v1"]
        for case in prior["deployed_checks"]:
            answer = api.post("/query", json={"query": case["query"]})
            assert answer.status_code == 200
            gate.verify_answer(case, answer.json())
        for question in (
            "Lakers record without Luka Doncic in 2024-25",
            "Warriors record without Jimmy Butler in 2024-25",
            "Nets record without De'Anthony Melton in 2024-25",
            "Rockets record without Steven Adams in 2023-24",
            "Lakers record without Spencer Dinwiddie in 2023-24",
        ):
            answer = api.post("/query", json={"query": question}).json()
            assert (answer["result_status"], answer["result_reason"]) == (
                "no_result",
                "unsupported",
            )
        for gid, tid, pid in EXPECTED_REJECTIONS:
            game = teams.loc[teams.game_id.eq(gid) & teams.team_id.eq(tid)].iloc[0]
            for team, other in [
                (tid, int(game.opponent_team_id)),
                (int(game.opponent_team_id), tid),
            ]:
                state, membership = game_participation(
                    observations,
                    pd.DataFrame(columns=COLUMNS),
                    pid,
                    gid,
                    team,
                    pd.Timestamp(game.game_date).date(),
                    other_team=other,
                )
                assert state == "unknown" and membership.state == "unknown"
    finally:
        reset_data_source_cache()
        clear_frame_cache()
    after, _, after_hash = gate.verify_pointer_manifest(client, bucket, BASE)
    assert after == before and after_hash == MANIFEST
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"])
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(bundle, output / bundle.name)  # exact accepted ZIP, never rebuilt
    report = dict(
        classification="prepared_no_writes_not_operational_acceptance",
        r2_writes=0,
        generation_id=GENERATION,
        base_generation=BASE,
        source_qualification_run=source["id"],
        local_validation=local,
        budget=budget,
        census=census,
        complete_season_queries=len(checks),
        preserved_registered_answers=len(prior["deployed_checks"]),
        preserved_2023_cases=93,
        preserved_2023_observations=len(before2023),
        pointer_unchanged=True,
        production_deployment=dict(id=deployed["id"], sha=deployed["sha"]),
        readiness=readiness,
        activation_ready=readiness["classification"] == "ready_observed",
    )
    (output.parent / "season-inactive-2024-preparation.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    (output.parent / "season-inactive-2024-manifest.json").write_bytes(manifest_raw)
    with capfd.disabled():
        print("SEASON_INACTIVE_2024_PREPARATION " + json.dumps(report), flush=True)
