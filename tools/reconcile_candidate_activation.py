"""Classify and verify an uncertain protected activation using read-only access."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

from tools import r2_publication as gate

UNKNOWN = "candidate_activation_started_outcome_unknown"
POINTER_FIELDS = {
    "schema_version",
    "generation_id",
    "previous_generation_id",
    "manifest_sha256",
    "published_at",
}


@dataclass(frozen=True)
class ActivationRun:
    workflow_sha: str
    run_id: int
    job_id: int
    artifact_id: int
    artifact_zip_sha256: str


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Expected timezone-aware activation timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("Expected timezone-aware activation timestamp")
    return parsed


def _approved_attempt(name, package, inventory, source):
    """Bind the failed writer and its preparation to the original protected run."""
    if not re.fullmatch(r"[0-9a-f]{40}", source.workflow_sha) or not re.fullmatch(
        r"[0-9a-f]{64}", source.artifact_zip_sha256
    ):
        raise ValueError("Reconciliation requires exact reviewed source hashes")
    run = gate.api(f"/actions/runs/{source.run_id}")
    job = gate.api(f"/actions/jobs/{source.job_id}")
    artifact = gate.api(f"/actions/artifacts/{source.artifact_id}")
    generation = package["generation_id"]
    if (
        run.get("head_sha") != source.workflow_sha
        or run.get("head_branch") != "main"
        or run.get("head_repository", {}).get("full_name") != gate.REPOSITORY
        or run.get("event") != "workflow_dispatch"
        or run.get("path") != ".github/workflows/r2-data-publication.yml"
        or run.get("display_title") != f"activate_candidate reviewed data package {name}"
        or run.get("status") != "completed"
        or run.get("run_attempt") != 1
        or job.get("head_sha") != source.workflow_sha
        or job.get("run_id") != source.run_id
        or job.get("run_attempt") != 1
        or job.get("conclusion") != "failure"
        or job.get("name") != f"Owner approval: {name} → {generation}"
        or artifact.get("expired") is not False
        or artifact.get("name") != f"publication-result-{source.run_id}"
        or artifact.get("workflow_run", {}).get("id") != source.run_id
        or artifact.get("workflow_run", {}).get("head_sha") != source.workflow_sha
        or artifact.get("digest") != f"sha256:{source.artifact_zip_sha256}"
    ):
        raise ValueError("Artifact does not belong to the failed original protected writer")
    raw = gate.api(f"/actions/artifacts/{source.artifact_id}/zip", binary=True)
    if gate.digest(raw) != source.artifact_zip_sha256:
        raise ValueError("Protected writer artifact differs from the reviewed bytes")
    with ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if sorted(item.filename for item in entries) != [
            "prepared.json",
            "publication.json",
        ] or any(item.file_size > gate.BACKUP_MAX_MANIFEST_BYTES for item in entries):
            raise ValueError("Unexpected publication result artifact inventory")
        attempt = json.loads(archive.read("publication.json"))
        prepared = json.loads(archive.read("prepared.json"))

    expected = {
        "schema_version": 1,
        "publication_state": "activation_prepared_no_writes",
        "package": name,
        "publisher_sha": package["publisher_sha"],
        "registry_sha256": gate.digest(gate.REGISTRY.read_bytes()),
        "workflow_sha": source.workflow_sha,
        "workflow_run_id": str(source.run_id),
        "generation_id": generation,
        "base_generation": inventory["base_generation"],
        "base_manifest_sha256": inventory["base_manifest_sha256"],
        "prepared_manifest_sha256": package["activation"]["manifest_sha256"],
        "activation_evidence": package["activation"],
        "operation_budget": {
            "active_pointer_puts": 1,
            "snapshot_object_puts": 0,
            "sdk_attempts": 1,
        },
    }
    if (
        any(prepared.get(key) != value for key, value in expected.items())
        or attempt.get("publication_state") != UNKNOWN
        or attempt
        != prepared
        | {
            "publication_state": UNKNOWN,
            "environment_audit": attempt.get("environment_audit"),
            "owner_approval": attempt.get("owner_approval"),
        }
    ):
        raise ValueError("Uncertain receipt does not match the protected preparation")
    backup = prepared["candidate_backup_preflight"]
    if (
        backup["generation_id"] != generation
        or backup["manifest_sha256"] != expected["prepared_manifest_sha256"]
        or backup["files"] != prepared["file_count"]
        or backup["data_bytes"] != prepared["total_bytes"]
        or not 0 < backup["files"] <= gate.BACKUP_MAX_FILES
        or not 0 < backup["data_bytes"] <= gate.BACKUP_MAX_BYTES
        or not 0 < backup["archive_bytes"] <= gate.BACKUP_MAX_ARCHIVE
        or backup["r2_writes"] != 0
    ):
        raise ValueError("Original preparation lacks exact candidate backup sizing")
    gate.check_approval(attempt["environment_audit"], attempt["owner_approval"])
    gate.check_approval(
        attempt["environment_audit"], gate.api(f"/actions/runs/{source.run_id}/approvals")
    )
    return attempt, (_timestamp(job["started_at"]), _timestamp(job["completed_at"]))


def reconcile(name, publisher, work, source):
    """Return the observed outcome and verify the exact active candidate, if any."""
    if work.exists():
        raise ValueError("Use a new workspace for the reconciliation receipt")
    _, package, inventory = gate.load_package(name, publisher)
    if "activate_candidate" not in package.get("operations", []):
        raise ValueError("Reconciliation requires a reviewed candidate activation package")
    receipt, job_window = _approved_attempt(name, package, inventory, source)
    publication = gate.publisher_modules(publisher)
    client, bucket = publication._resolve_r2_target(
        client=None, bucket_name=None, env=None, env_file=None
    )
    try:
        stream = client.get_object(Bucket=bucket, Key="metadata/active_generation.json")["Body"]
        try:
            raw = stream.read(gate.BACKUP_MAX_MANIFEST_BYTES + 1)
        finally:
            stream.close()
        if len(raw) > gate.BACKUP_MAX_MANIFEST_BYTES:
            raise ValueError("Active pointer exceeds the read bound")
        pointer = json.loads(raw)
        if not isinstance(pointer, dict):
            raise ValueError("Active pointer must be an object")

        status = "conflicting_publication"
        if gate.same_pointer(pointer, receipt["base_pointer"]):
            observed, _, manifest = gate.verify_pointer_manifest(
                client, bucket, receipt["base_generation"]
            )
            if gate.same_pointer(observed, pointer) and manifest == receipt["base_manifest_sha256"]:
                status = "base_unchanged"
        elif (
            pointer.keys() == POINTER_FIELDS
            and type(pointer["schema_version"]) is int
            and pointer["schema_version"] == 1
            and pointer.get("generation_id") == receipt["generation_id"]
            and pointer.get("previous_generation_id") == receipt["base_generation"]
            and pointer.get("manifest_sha256") == receipt["prepared_manifest_sha256"]
            and job_window[0] <= _timestamp(pointer["published_at"]) <= job_window[1]
        ):
            status = "exact_candidate_active"

        receipt["reconciliation"] = {
            "status": status,
            "observed_pointer": pointer,
            "observed_pointer_sha256": gate.digest(raw),
            "source_job_id": source.job_id,
            "source_artifact_id": source.artifact_id,
            "source_artifact_zip_sha256": source.artifact_zip_sha256,
            "observed_at": datetime.now(UTC).isoformat(),
            "source_publication_state": UNKNOWN,
            "source_writer_started_at": job_window[0].isoformat(),
            "source_writer_completed_at": job_window[1].isoformat(),
            "verification_workflow_sha": os.environ.get("GITHUB_SHA"),
            "verification_workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
            "production_writes": 0,
        }
        gate.write_json(work / "receipt.json", receipt)
    finally:
        client.close()

    if status == "exact_candidate_active":
        return gate.verify_published_snapshot(
            package,
            inventory,
            publication,
            work,
            receipt,
            activation=True,
            expected_pointer=pointer,
        )
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--publisher", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--source-run", type=int, required=True)
    parser.add_argument("--source-job", type=int, required=True)
    parser.add_argument("--source-artifact", type=int, required=True)
    parser.add_argument("--source-zip-sha256", required=True)
    args = parser.parse_args()
    source = ActivationRun(
        args.source_sha,
        args.source_run,
        args.source_job,
        args.source_artifact,
        args.source_zip_sha256,
    )
    receipt = reconcile(args.package, args.publisher.resolve(), args.work.resolve(), source)
    print(receipt["reconciliation"]["status"])


if __name__ == "__main__":
    main()
