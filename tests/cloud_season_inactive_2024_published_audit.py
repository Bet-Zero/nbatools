"""Read-only verification of one explicitly approved historical-data activation."""

import io
import json
import os
import time
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from nbatools.commands._dated_membership import COLUMNS
from nbatools.commands._participation_observations import combined_observations, game_participation
from nbatools.commands.pipeline import generation_publication as publication
from tests.test_season_inactive_2024_real_data import EXPECTED_REJECTIONS
from tests.test_season_inactive_pilot_real_data import _census
from tests.test_season_inactive_publication_real_data import _facts
from tools import r2_publication as gate

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
RUN = 44040333371
WRITE_JOB = 133896348108
VERIFY_JOB = 133930564101
ARTIFACT = 14314132878
ARTIFACT_SHA = "95b769a4cbb20b357a89f125cd432903c5c214faab5a84b926a0b2e77beb9eec"
PACKAGE = "season-inactive-2024-v1"
BASE = "availability-season-inactive-2023-v1-20261115"
TARGET = "availability-season-inactive-2024-v1-20261116"
BASE_SHA = "8ec80812ae9dda9222d9d157c253d7a919af214ae40c49a27c20f87b52d156c8"
MANIFEST = "0abce6f8261957df6cffc19ce24a4ed408a548e1292a33456ce55c0481903ecc"
MAIN = "b8d1e26dd4a81990c25a5cdfc122b18f848160ac"
ROOT = Path(__file__).resolve().parents[1]


def published_census(captured):
    """Check the actual R2 consumer, using independently qualified original row keys."""
    season = "2024-25"
    stats = pd.read_csv(io.BytesIO(captured[f"raw/player_game_stats/{season}_regular_season.csv"]))
    teams = pd.read_csv(io.BytesIO(captured[f"raw/team_game_stats/{season}_regular_season.csv"]))
    old = pd.read_csv(
        io.BytesIO(captured[f"raw/player_game_availability/{season}_regular_season.csv"])
    )
    roster = pd.read_csv(io.BytesIO(captured[f"raw/rosters/{season}.csv"]))
    source_path = next(p for p in captured if p.startswith("raw/player_game_inactive_sources/"))
    raw = pd.read_csv(io.BytesIO(captured[source_path]))
    raw = raw.loc[raw.season_type_id.eq(2)].copy()
    valid = raw.loc[
        [
            (int(r.game_id), int(r.team_id), int(r.player_id)) not in EXPECTED_REJECTIONS
            for r in raw.itertuples()
        ]
    ].copy()
    valid["participation_state"] = "did_not_play"
    assert len(raw) == 10854 and len(valid) == 10847
    derived = pd.read_csv(
        io.BytesIO(captured[f"raw/player_game_inactive/{season}_regular_season.csv"])
    )
    receipt = json.loads(captured[f"raw/player_game_inactive/{season}_regular_season.source.json"])
    assert {
        (r["game_id"], r["team_id"], r["player_id"]) for r in receipt["identity_name_rejections"]
    } == EXPECTED_REJECTIONS
    assert len(derived) == 10847
    assert set(zip(derived.game_id, derived.team_id, derived.player_id)).isdisjoint(
        EXPECTED_REJECTIONS
    )
    pairs = {
        (int(t), int(p))
        for frame in (stats, old, roster, raw)
        for t, p in zip(frame.team_id, frame.player_id)
    }
    with ZipFile(
        ROOT
        / "working/nba-tools-completion-program/source-evidence/team-membership-20261114/originals.zip"
    ) as archive:
        movements = json.loads(archive.read("player-movement.json"))["NBA_Player_Movement"]["rows"]
    for move in movements:
        if "2024-10-21" <= move["TRANSACTION_DATE"][:10] <= "2025-04-13" and move["PLAYER_ID"]:
            pairs.add((int(move["TEAM_ID"]), int(move["PLAYER_ID"])))
            if move["Transaction_Type"] == "Trade":
                pairs.add((int(move["Additional_Sort"]), int(move["PLAYER_ID"])))
    facts = _facts(stats, old, valid)
    full_source = {
        (t, p)
        for t, p in pairs
        if all((int(g), p) in facts for g in teams.loc[teams.team_id.eq(t), "game_id"])
    }
    observations, _ = combined_observations([season], "Regular Season")
    census, full = _census(observations, teams, pairs, set(raw.game_id))
    proof = json.loads(
        (
            ROOT
            / "working/nba-tools-completion-program/source-evidence/season-inactive-2024/product-results.json"
        ).read_bytes()
    )
    assert census == proof["after"] and set(full) == full_source
    assert census["candidate_cases"] == 707 and census["complete_cases"] == 69
    assert (
        census["states"]["unknown"] == 20649
        and census["blocked_with_processed_game_omission"] == 638
    )
    for gid, tid, pid in EXPECTED_REJECTIONS:
        game = teams.loc[teams.game_id.eq(gid) & teams.team_id.eq(tid)].iloc[0]
        for team, other in ((tid, int(game.opponent_team_id)), (int(game.opponent_team_id), tid)):
            state, member = game_participation(
                observations,
                pd.DataFrame(columns=COLUMNS),
                pid,
                gid,
                team,
                pd.Timestamp(game.game_date).date(),
                other_team=other,
            )
            assert state == "unknown" and member.state == "unknown"
    return census


def readiness():
    response = gate.requests.get("https://nbatools.vercel.app/readiness", timeout=20)
    body = response.json()
    assert body["active_generation"] == TARGET and body["immutable_generation"] is True
    assert body["exception"]["applied"] is False
    if response.status_code == 503:
        assert body["ready"] is False
        assert [x["code"] for x in body["blockers"]] == ["new_season_not_loaded"]
    else:
        assert response.status_code == 200 and body["ready"] is True and not body["blockers"]
    return dict(http_status=response.status_code, body=body)


def test_verify_approved_2024_data_without_readiness_waiver(capfd):
    report = dict(
        classification="read_only_publication_data_verification",
        source_run_id=RUN,
        source_workflow_sha=MAIN,
        generation_id=TARGET,
        manifest_sha256=MANIFEST,
        r2_writes=0,
        data_verification_complete=False,
        operational_acceptance_complete=False,
    )
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "season-2024-publication-audit"
    output.mkdir(parents=True, exist_ok=False)
    try:
        run = gate.api(f"/actions/runs/{RUN}")
        write = gate.api(f"/actions/jobs/{WRITE_JOB}")
        verify = gate.api(f"/actions/jobs/{VERIFY_JOB}")
        artifact = gate.api(f"/actions/artifacts/{ARTIFACT}")
        assert run["head_sha"] == MAIN and run["conclusion"] == "failure"
        assert run["path"] == ".github/workflows/r2-data-publication.yml"
        assert run["event"] == "workflow_dispatch" and run["head_branch"] == "main"
        assert write["run_id"] == verify["run_id"] == RUN
        assert write["conclusion"] == "success" and verify["conclusion"] == "failure"
        assert (
            artifact["workflow_run"]["id"] == RUN and artifact["workflow_run"]["head_sha"] == MAIN
        )
        assert artifact["name"] == f"publication-verified-{RUN}" and not artifact["expired"]
        assert artifact["digest"] == "sha256:" + ARTIFACT_SHA
        raw = gate.api(f"/actions/artifacts/{ARTIFACT}/zip", binary=True)
        assert gate.digest(raw) == ARTIFACT_SHA
        with ZipFile(io.BytesIO(raw)) as archive:
            assert archive.namelist() == ["receipt.json"]
            source = json.loads(archive.read("receipt.json"))
        registry = json.loads(gate.REGISTRY.read_bytes())
        package = registry["packages"][PACKAGE]
        inventory = json.loads((ROOT / package["inventory"]).read_bytes())
        assert source["publication_state"] == "published_verification_failed"
        assert source["package"] == PACKAGE and source["generation_id"] == TARGET
        assert source["workflow_sha"] == MAIN and source["workflow_run_id"] == str(RUN)
        assert source["registry_sha256"] == gate.digest(gate.REGISTRY.read_bytes())
        for field in ("publisher_sha", "script_sha256", "inventory_sha256"):
            assert source[field] == package[field]
        assert source["prepared_manifest_sha256"] == MANIFEST
        assert source["file_count"] == 1216 and source["total_bytes"] == 419488508
        assert source["publication"]["target"] == "r2"
        assert source["publication"]["action"] == "publish"
        assert source["publication"]["file_count"] == 1216
        assert source["publication"]["total_bytes"] == 419488508
        assert source["publication"]["manifest_sha256"] == MANIFEST
        assert source["publication"]["generation_id"] == TARGET
        assert source["publication"]["previous_generation_id"] == BASE
        gate.check_approval(source["environment_audit"], source["owner_approval"])
        report["source_publication_state"] = source["publication_state"]
        report["source_artifact"] = dict(id=ARTIFACT, sha256=ARTIFACT_SHA)
        client, bucket = publication._resolve_r2_target(
            client=None, bucket_name=None, env=None, env_file=None
        )
        before, manifest, digest = gate.verify_pointer_manifest(client, bucket, TARGET)
        assert digest == MANIFEST and before["previous_generation_id"] == BASE
        assert (
            manifest["files"] == source["verified_objects"] and before == source["verified_pointer"]
        )
        assert len(manifest["files"]) == 1216
        files = {x["path"]: x for x in manifest["files"]}
        prefix = "raw/player_game_inactive/2024-25_regular_season"
        needed = {
            "raw/player_game_availability/2024-25_regular_season.csv",
            "raw/rosters/2024-25.csv",
            prefix + ".csv",
            prefix + ".source.json",
            *(
                f"raw/{kind}/2024-25_regular_season.csv"
                for kind in ("games", "team_game_stats", "player_game_stats")
            ),
            *(x["path"] for x in inventory["overlay_files"]),
        }
        captured = {}
        checked_bytes = 0
        for name, item in files.items():
            body = client.get_object(Bucket=bucket, Key=f"generations/{TARGET}/{name}")[
                "Body"
            ].read()
            assert len(body) == item["size_bytes"] and gate.digest(body) == item["sha256"], name
            checked_bytes += len(body)
            if name in needed:
                captured[name] = body
        assert checked_bytes == 419488508
        base_raw = client.get_object(
            Bucket=bucket, Key=f"generations/{BASE}/metadata/generation_manifest.json"
        )["Body"].read()
        assert gate.digest(base_raw) == BASE_SHA
        original = {x["path"]: x for x in json.loads(base_raw)["files"]}
        overlay = {x["path"]: x for x in inventory["overlay_files"] if x["path"].startswith("raw/")}
        assert files.keys() == original.keys() | overlay.keys()
        assert len(original) == 1213
        for name, item in original.items():
            if name not in inventory["append_only"]:
                assert files[name] == item, name
        for name, item in overlay.items():
            assert files[name] == item, name
        assert not inventory["append_only"] and not original.keys() & overlay.keys()
        assert files == {**original, **overlay}
        assert set(captured) == needed
        census = published_census(captured)
        report["published_2024_census"] = census
        report["quarantined_observations"] = 7
        report["quarantine_game_side_checks"] = 14
        report["preparation_138_query_proof_reused_against_identical_manifest"] = True
        report.update(
            verified_object_count=len(files),
            verified_object_bytes=checked_bytes,
            previous_generation_preserved=True,
            prior_cells_and_source_authority_preserved=True,
            pointer_before=before,
        )
        report["readiness_before"] = readiness()
        assert len(package["deployed_checks"]) == 45
        gate.check_live_answers(package, report)
        controls = []
        for question, reason in [
            ("Rockets record without Steven Adams in 2023-24", "unsupported"),
            ("Lakers record without Spencer Dinwiddie in 2023-24", "unsupported"),
            ("Denver Nuggets record with Vlatko Cancar in 2023-24", "no_match"),
            ("Lakers record without Luka Doncic in 2024-25", "unsupported"),
            ("Warriors record without Jimmy Butler in 2024-25", "unsupported"),
            ("Nets record without De'Anthony Melton in 2024-25", "unsupported"),
            ("Oklahoma City Thunder record with Nikola Topic in 2024-25", "no_match"),
        ]:
            time.sleep(7)
            response = gate.requests.post(
                "https://nbatools.vercel.app/query", json={"query": question}, timeout=30
            )
            assert response.status_code == 200, question
            body = response.json()
            assert (body["result_status"], body["result_reason"]) == ("no_result", reason), question
            controls.append(
                dict(
                    query=question,
                    result_status=body["result_status"],
                    result_reason=body["result_reason"],
                )
            )
        report["unknown_and_empty_controls"] = controls
        report["readiness_after"] = readiness()
        after, _, after_hash = gate.verify_pointer_manifest(client, bucket, TARGET)
        assert after == before and after_hash == MANIFEST
        report.update(
            pointer_after=after,
            pointer_unchanged=True,
            registered_live_answers=45,
            data_verification_complete=True,
        )
        with capfd.disabled():
            print("SEASON_2024_PUBLISHED_DATA_VERIFICATION " + json.dumps(report), flush=True)
    finally:
        (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
