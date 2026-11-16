"""Read-only verification of one explicitly approved historical-data activation."""

import io
import json
import os
import time
from pathlib import Path
from zipfile import ZipFile

import pytest

from nbatools.commands.pipeline import generation_publication as publication
from tools import r2_publication as gate
from tools.availability_overlay import verify_append

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
RUN = 43801111855
WRITE_JOB = 133082322600
VERIFY_JOB = 133095078167
ARTIFACT = 14197934173
ARTIFACT_SHA = "d92fc9552cdc7856fc31658335268f21c84cee2a1b4531c9081ff1c364ff7ecf"
PACKAGE = "season-inactive-2023-v1"
BASE = "availability-participation-2025-durant-v1-20261114"
TARGET = "availability-season-inactive-2023-v1-20261115"
BASE_SHA = "cde98408f3390e6191da564197fb77ffbc598a3059963cfc21d9f2d7e1a6b366"
MANIFEST = "8ec80812ae9dda9222d9d157c253d7a919af214ae40c49a27c20f87b52d156c8"
MAIN = "15a67708ae43c33b80eaefa21e071497b896459d"
ROOT = Path(__file__).resolve().parents[1]


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


def test_verify_approved_season_data_without_readiness_waiver(capfd):
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
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "season-publication-audit"
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
        assert source["file_count"] == 1213 and source["total_bytes"] == 415007162
        assert source["publication"]["target"] == "r2"
        assert source["publication"]["action"] == "publish"
        assert source["publication"]["file_count"] == 1213
        assert source["publication"]["total_bytes"] == 415007162
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
        assert len(manifest["files"]) == 1213
        files = {x["path"]: x for x in manifest["files"]}
        captured = {}
        checked_bytes = 0
        for name, item in files.items():
            body = client.get_object(Bucket=bucket, Key=f"generations/{TARGET}/{name}")[
                "Body"
            ].read()
            assert len(body) == item["size_bytes"] and gate.digest(body) == item["sha256"], name
            checked_bytes += len(body)
            if name in inventory["append_only"]:
                captured[name] = body
        assert checked_bytes == 415007162
        base_raw = client.get_object(
            Bucket=bucket, Key=f"generations/{BASE}/metadata/generation_manifest.json"
        )["Body"].read()
        assert gate.digest(base_raw) == BASE_SHA
        original = {x["path"]: x for x in json.loads(base_raw)["files"]}
        overlay = {x["path"]: x for x in inventory["overlay_files"] if x["path"].startswith("raw/")}
        assert files.keys() == original.keys() | overlay.keys()
        assert len(original) == 1186
        for name, item in original.items():
            if name not in inventory["append_only"]:
                assert files[name] == item, name
        for name, item in overlay.items():
            assert files[name] == item, name
        for name, binding in inventory["append_only"].items():
            old = client.get_object(Bucket=bucket, Key=f"generations/{BASE}/{name}")["Body"].read()
            verify_append(name, old, captured[name], binding)
        report.update(
            verified_object_count=len(files),
            verified_object_bytes=checked_bytes,
            previous_generation_preserved=True,
            prior_cells_and_source_authority_preserved=True,
            pointer_before=before,
        )
        report["readiness_before"] = readiness()
        assert len(package["deployed_checks"]) == 38
        gate.check_live_answers(package, report)
        controls = []
        for question, reason in [
            ("Rockets record without Steven Adams in 2023-24", "unsupported"),
            ("Lakers record without Spencer Dinwiddie in 2023-24", "unsupported"),
            ("Denver Nuggets record with Vlatko Cancar in 2023-24", "no_match"),
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
            registered_live_answers=38,
            data_verification_complete=True,
        )
        with capfd.disabled():
            print("SEASON_PUBLISHED_DATA_VERIFICATION " + json.dumps(report), flush=True)
    finally:
        (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
