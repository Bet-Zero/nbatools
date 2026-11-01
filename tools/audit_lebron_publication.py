"""Read-only numeric diagnostic for one publication whose readiness gate failed.

This preserves failed operational acceptance. It cannot prepare, publish, repair
readiness, move a pointer, or label the generation published_and_verified.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import zipfile
from pathlib import Path

from tools import r2_publication as gate

PACKAGE = "lebron-season-participation-v1"
GENERATION = "availability-lebron-season-v1-20261031"
SOURCE_RUN = 41256695103
SOURCE_SHA = "a54db32f15bc1ec3b0f594423543921cfde74a65"
WRITE_JOB = 124701875340
VERIFY_JOB = 124704246656
ARTIFACT = 13063794517
ZIP_SHA = "9af21355ba611dd46f80eafff3961d548e91c43aacca6c84b001d50c5ffeeb92"
MANIFEST_SHA = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"


def authenticated_source(package, inventory):
    run = gate.api(f"/actions/runs/{SOURCE_RUN}")
    write = gate.api(f"/actions/jobs/{WRITE_JOB}")
    verify = gate.api(f"/actions/jobs/{VERIFY_JOB}")
    artifact = gate.api(f"/actions/artifacts/{ARTIFACT}")
    if (
        run.get("id") != SOURCE_RUN
        or run.get("head_sha") != SOURCE_SHA
        or run.get("head_branch") != "main"
        or run.get("event") != "workflow_dispatch"
        or run.get("path") != ".github/workflows/r2-data-publication.yml"
        or run.get("conclusion") != "failure"
        or run.get("status") != "completed"
        or write.get("id") != WRITE_JOB
        or write.get("run_id") != SOURCE_RUN
        or write.get("conclusion") != "success"
        or write.get("name") != f"Owner approval: {PACKAGE} → {GENERATION}"
        or verify.get("id") != VERIFY_JOB
        or verify.get("run_id") != SOURCE_RUN
        or verify.get("conclusion") != "failure"
        or artifact.get("id") != ARTIFACT
        or artifact.get("expired")
        or artifact.get("name") != f"publication-verified-{SOURCE_RUN}"
        or artifact.get("workflow_run", {}).get("id") != SOURCE_RUN
        or artifact.get("workflow_run", {}).get("head_sha") != SOURCE_SHA
    ):
        raise ValueError("Diagnostic source differs from the fixed protected publication/failure")
    raw = gate.api(f"/actions/artifacts/{ARTIFACT}/zip", binary=True)
    if gate.digest(raw) != ZIP_SHA:
        raise ValueError("Original failed verification artifact checksum differs")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.namelist() != ["receipt.json"]:
            raise ValueError("Unexpected original verification artifact inventory")
        receipt = json.loads(archive.read("receipt.json"))
    expected = dict(
        schema_version=1,
        package=PACKAGE,
        workflow_sha=SOURCE_SHA,
        workflow_run_id=str(SOURCE_RUN),
        registry_sha256=gate.digest(gate.REGISTRY.read_bytes()),
        publisher_sha=package["publisher_sha"],
        script_sha256=package["script_sha256"],
        inventory_sha256=package["inventory_sha256"],
        generation_id=GENERATION,
        base_generation=inventory["base_generation"],
        base_manifest_sha256=inventory["base_manifest_sha256"],
        artifact_id=inventory["artifact_id"],
        artifact_zip_sha256=inventory["artifact_zip_sha256"],
        source_run_id=inventory["run_id"],
        prepared_manifest_sha256=MANIFEST_SHA,
        file_count=775,
        total_bytes=403814381,
        publication_state="published_verification_failed",
    )
    if package["generation_id"] != GENERATION or any(
        receipt.get(k) != v for k, v in expected.items()
    ):
        raise ValueError("Original failed receipt differs from reviewed code/package/schema")
    gate.check_approval(receipt["environment_audit"], receipt["owner_approval"])
    if receipt.get("publication") != dict(
        action="publish",
        target="r2",
        generation_id=GENERATION,
        previous_generation_id=inventory["base_generation"],
        manifest_sha256=MANIFEST_SHA,
        file_count=775,
        total_bytes=403814381,
        pointer="metadata/active_generation.json",
    ):
        raise ValueError("Original protected writer result differs")
    objects = receipt.get("verified_objects", [])
    if (
        len(objects) != 775
        or len({item["path"] for item in objects}) != 775
        or sum(item["size_bytes"] for item in objects) != 403814381
    ):
        raise ValueError("Original verification did not check the complete object population")
    return receipt


def matching_snapshot(source, pointer, manifest, digest):
    if (
        pointer != source["verified_pointer"]
        or pointer.get("generation_id") != GENERATION
        or pointer.get("previous_generation_id") != source["base_generation"]
        or pointer.get("manifest_sha256") != MANIFEST_SHA
        or digest != MANIFEST_SHA
        or manifest.get("generation_id") != GENERATION
        or manifest.get("files") != source["verified_objects"]
    ):
        raise ValueError("Current pointer/manifest no longer matches the original 775 byte checks")


def readiness_observation():
    try:
        response = gate.requests.get("https://nbatools.vercel.app/readiness", timeout=20)
    except gate.requests.RequestException as exc:
        return dict(classification="unresolved", error_type=type(exc).__name__)
    try:
        body = response.json()
    except ValueError:
        return dict(
            classification="unresolved", http_status=response.status_code, body=response.text[:8192]
        )
    classification = "unresolved"
    if isinstance(body, dict) and body.get("active_generation") == GENERATION:
        blockers = body.get("blockers")
        if response.status_code == 200 and body.get("ready") is True and blockers == []:
            classification = "ready_observed"
        elif (
            response.status_code == 503
            and body.get("ready") is False
            and isinstance(blockers, list)
            and blockers
            and all(
                isinstance(row, dict) and row.get("code") == "new_season_not_loaded"
                for row in blockers
            )
        ):
            classification = "new_season_not_loaded"
    return dict(classification=classification, http_status=response.status_code, body=body)


def audit(publisher: Path, work: Path):
    if work.exists():
        raise ValueError("Diagnostic requires a new receipt workspace")
    work.mkdir(parents=True)
    result = dict(
        schema_version=1,
        evidence_type="read_only_publication_numeric_diagnostic",
        operational_acceptance_complete=False,
        production_writes=0,
        diagnostic_complete=False,
        numeric_checks_complete=False,
        source_publication_state="published_verification_failed",
        workflow_sha=os.environ.get("GITHUB_SHA"),
        workflow_run_id=os.environ.get("GITHUB_RUN_ID"),
    )
    try:
        _, package, inventory = gate.load_package(PACKAGE, publisher)
        source = authenticated_source(package, inventory)
        result["source"] = dict(
            workflow_run_id=SOURCE_RUN,
            workflow_sha=SOURCE_SHA,
            write_job=WRITE_JOB,
            failed_verify_job=VERIFY_JOB,
            artifact_id=ARTIFACT,
            artifact_zip_sha256=ZIP_SHA,
            package=PACKAGE,
            publisher_sha=source["publisher_sha"],
            registry_sha256=source["registry_sha256"],
            generation_id=GENERATION,
            manifest_sha256=MANIFEST_SHA,
            verified_object_count=775,
            verified_object_bytes=403814381,
            verified_objects_sha256=gate.digest(
                json.dumps(source["verified_objects"], sort_keys=True).encode()
            ),
        )
        publication = gate.publisher_modules(publisher)
        client, bucket = publication._resolve_r2_target(
            client=None, bucket_name=None, env=None, env_file=None
        )
        before, manifest, digest = gate.verify_pointer_manifest(client, bucket, GENERATION)
        matching_snapshot(source, before, manifest, digest)
        result["pointer_before"] = before
        result["readiness_before"] = readiness_observation()
        try:
            if len(package["deployed_checks"]) != 16:
                raise ValueError("Diagnostic requires all 16 registered answers")
            answers = gate.check_live_answers(package, result)
            if len(answers) != 16:
                raise ValueError("Diagnostic did not check all 16 registered answers")
            result["numeric_checks_complete"] = True
        finally:
            result["readiness_after"] = readiness_observation()
            after, manifest, digest = gate.verify_pointer_manifest(client, bucket, GENERATION)
            matching_snapshot(source, after, manifest, digest)
            if after != before:
                raise ValueError("Active pointer changed during numeric diagnostic")
            result["pointer_after"] = after
        if any(
            result[key]["classification"] == "unresolved"
            for key in ["readiness_before", "readiness_after"]
        ):
            raise ValueError("Readiness has an unresolved blocker; numeric evidence is separate")
        result["diagnostic_complete"] = True
        return result
    except Exception as exc:
        result["diagnostic_error"] = str(exc)
        raise
    finally:
        gate.write_json(work / "diagnostic.json", result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publisher", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    audit(args.publisher.resolve(), args.work.resolve())
