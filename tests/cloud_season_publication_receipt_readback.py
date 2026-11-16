"""Read one protected no-write receipt; no dataset producer or publication call."""

import hashlib
import io
import json
from zipfile import ZipFile

import pytest

from nbatools.commands.pipeline import generation_publication as publication
from tools import r2_publication as gate

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
RUN = 43801111855
ARTIFACT = 14196209318
ZIP_SHA = "777673808b1091794150dee1930d73f938b960cd02ecd447b99b451b3b843a85"
BASE = "availability-participation-2025-durant-v1-20261114"
TARGET = "availability-season-inactive-2023-v1-20261115"
MANIFEST = "8ec80812ae9dda9222d9d157c253d7a919af214ae40c49a27c20f87b52d156c8"


def test_read_exact_protected_preparation_tuple(capfd):
    run = gate.api(f"/actions/runs/{RUN}")
    artifact = gate.api(f"/actions/artifacts/{ARTIFACT}")
    assert run["head_sha"] == "15a67708ae43c33b80eaefa21e071497b896459d"
    assert run["event"] == "workflow_dispatch"
    assert run["status"] == "waiting" and run["conclusion"] is None
    assert gate.api("/actions/jobs/133081459664")["conclusion"] == "success"
    assert gate.api("/actions/jobs/133082322600")["status"] == "waiting"
    assert run["path"] == ".github/workflows/r2-data-publication.yml"
    assert run["display_title"] == "publish reviewed data package season-inactive-2023-v1"
    assert artifact["workflow_run"]["id"] == RUN and artifact["expired"] is False
    assert artifact["digest"] == "sha256:" + ZIP_SHA
    raw = gate.api(f"/actions/artifacts/{ARTIFACT}/zip", binary=True)
    assert hashlib.sha256(raw).hexdigest() == ZIP_SHA
    paths = {
        "policy/environment-audit.json",
        "prepared/prepared.json",
        "prepared/staging/local-validation.json",
        "prepared/staging/base-manifest.json",
        f"prepared/staging/validation/generations/{TARGET}/metadata/generation_manifest.json",
    }
    with ZipFile(io.BytesIO(raw)) as archive:
        assert set(archive.namelist()) == paths and len(archive.namelist()) == len(paths)
        assert sum(p.file_size for p in archive.infolist()) < 1_500_000
        prepared = json.loads(archive.read("prepared/prepared.json"))
        manifest_raw = archive.read(
            f"prepared/staging/validation/generations/{TARGET}/metadata/generation_manifest.json"
        )
        audit = json.loads(archive.read("policy/environment-audit.json"))
    assert prepared["publication_state"] == "prepared_no_writes"
    assert prepared["package"] == "season-inactive-2023-v1"
    assert prepared["generation_id"] == TARGET and prepared["base_generation"] == BASE
    assert (
        prepared["prepared_manifest_sha256"] == hashlib.sha256(manifest_raw).hexdigest() == MANIFEST
    )
    manifest = json.loads(manifest_raw)
    assert len(manifest["files"]) == prepared["file_count"] == 1213
    assert sum(p["size_bytes"] for p in manifest["files"]) == prepared["total_bytes"] == 415007162
    assert prepared["registry_sha256"] == gate.digest(gate.REGISTRY.read_bytes())
    assert prepared["publisher_sha"] == "c9171b7b0a6e4ff84b8dd7689c84c0dbca3c64de"
    assert prepared["artifact_id"] == 14191895908 and prepared["source_run_id"] == 43788034248
    assert prepared["budget"]["conservative_projected_bytes"] <= 10_000_000_000
    assert audit["publication_ready"] is True
    gate.check_environment(audit["configuration"], audit["branches"])
    client, bucket = publication._resolve_r2_target(
        client=None, bucket_name=None, env=None, env_file=None
    )
    pointer, _, digest = gate.verify_pointer_manifest(client, bucket, BASE)
    assert pointer == prepared["base_pointer"]
    assert digest == prepared["base_manifest_sha256"]
    with capfd.disabled():
        print("SEASON_PUBLICATION_APPROVAL_TUPLE " + json.dumps(prepared), flush=True)
        print(
            "SEASON_PUBLICATION_POLICY "
            + json.dumps(
                dict(protected_environment_ready=True, pointer_unchanged=True, r2_writes=0)
            ),
            flush=True,
        )
