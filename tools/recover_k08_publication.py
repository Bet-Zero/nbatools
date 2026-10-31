"""Read-only recovery for one already owner-published K08 generation.

The original approved publication identity is preserved. Recovery has a distinct
verification identity and cannot invoke preparation, publication or rollback.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import zipfile
from pathlib import Path

from tools import r2_publication as gate

PACKAGE = "retained-k08-availability-v1"
SOURCE_RUN = 41184300649
SOURCE_SHA = "6f98dfa7e3965d9e95e1e87f639ce394e58e6393"
WRITE_JOB = 124488478133
ARTIFACT = 13036273532
ZIP_SHA = "860b07cb6eb10398d9419771ee6c0faaaa05594ad4a642b1e4726461d96b5575"


def approved_receipt(package, inventory):
    run = gate.api(f"/actions/runs/{SOURCE_RUN}")
    job = gate.api(f"/actions/jobs/{WRITE_JOB}")
    artifact = gate.api(f"/actions/artifacts/{ARTIFACT}")
    if (
        run.get("head_sha") != SOURCE_SHA
        or run.get("head_branch") != "main"
        or run.get("event") != "workflow_dispatch"
        or run.get("path") != ".github/workflows/r2-data-publication.yml"
        or job.get("run_id") != SOURCE_RUN
        or job.get("conclusion") != "success"
        or job.get("name") != f"Owner approval: {PACKAGE} → {package['generation_id']}"
        or artifact.get("expired")
        or artifact.get("name") != f"publication-result-{SOURCE_RUN}"
        or artifact.get("workflow_run", {}).get("id") != SOURCE_RUN
        or artifact.get("workflow_run", {}).get("head_sha") != SOURCE_SHA
    ):
        raise ValueError("Recovery source is not the original successful protected write")
    payload = gate.api(f"/actions/artifacts/{ARTIFACT}/zip", binary=True)
    if gate.digest(payload) != ZIP_SHA:
        raise ValueError("Recovery publication artifact differs from reviewed bytes")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        if sorted(archive.namelist()) != ["prepared.json", "publication.json"]:
            raise ValueError("Unexpected original publication artifact inventory")
        receipt = json.loads(archive.read("publication.json"))
    expected = dict(
        package=PACKAGE,
        workflow_sha=SOURCE_SHA,
        workflow_run_id=str(SOURCE_RUN),
        registry_sha256=gate.digest(gate.REGISTRY.read_bytes()),
        publisher_sha=package["publisher_sha"],
        script_sha256=package["script_sha256"],
        inventory_sha256=package["inventory_sha256"],
        generation_id=package["generation_id"],
        publication_state="published_verification_pending",
    )
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError("Original publication receipt differs from the reviewed package")
    gate.check_approval(receipt["environment_audit"], receipt["owner_approval"])
    if receipt.get("publication") != dict(
        action="publish",
        target="r2",
        generation_id=package["generation_id"],
        previous_generation_id=inventory["base_generation"],
        manifest_sha256=receipt["prepared_manifest_sha256"],
        file_count=receipt["file_count"],
        total_bytes=receipt["total_bytes"],
        pointer="metadata/active_generation.json",
    ):
        raise ValueError("Original protected publication outcome is inconsistent")
    return receipt


def recover(publisher, work):
    if work.exists():
        raise ValueError("Recovery requires a new receipt workspace")
    _, package, inventory = gate.load_package(PACKAGE, publisher)
    receipt = approved_receipt(package, inventory)
    receipt["recovery"] = dict(
        source_run_id=SOURCE_RUN,
        source_artifact_id=ARTIFACT,
        source_artifact_zip_sha256=ZIP_SHA,
        workflow_sha=os.environ["GITHUB_SHA"],
        workflow_run_id=os.environ["GITHUB_RUN_ID"],
        production_writes=0,
    )
    publication = gate.publisher_modules(publisher)
    return gate.verify_published_snapshot(package, inventory, publication, work, receipt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publisher", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    recover(args.publisher.resolve(), args.work.resolve())
