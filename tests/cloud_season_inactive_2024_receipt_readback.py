"""Read one protected no-write receipt; no dataset producer or publication call."""

import hashlib
import io
import json
from zipfile import ZipFile

import pytest

from nbatools.commands.pipeline import generation_publication as publication
from tools import r2_publication as gate

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
RUN = 43825619901
ARTIFACT = 14206368070
ZIP_SHA = "09c549f293b914976573136df322124de65f8ae5180a285d48dbcebd63c6afe6"
BASE = "availability-season-inactive-2023-v1-20261115"
TARGET = "availability-season-inactive-2024-v1-20261116"
MANIFEST = "0abce6f8261957df6cffc19ce24a4ed408a548e1292a33456ce55c0481903ecc"


def test_read_exact_protected_preparation_tuple(capfd):
    run = gate.api(f"/actions/runs/{RUN}")
    artifact = gate.api(f"/actions/artifacts/{ARTIFACT}")
    assert run["head_sha"] == "b8d1e26dd4a81990c25a5cdfc122b18f848160ac"
    assert run["conclusion"] == "success" and run["event"] == "workflow_dispatch"
    assert run["path"] == ".github/workflows/r2-data-publication.yml"
    assert run["display_title"] == "validate reviewed data package season-inactive-2024-v1"
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
        base_raw = archive.read("prepared/staging/base-manifest.json")
    assert prepared["publication_state"] == "prepared_no_writes"
    assert prepared["package"] == "season-inactive-2024-v1"
    assert prepared["generation_id"] == TARGET and prepared["base_generation"] == BASE
    assert (
        prepared["prepared_manifest_sha256"] == hashlib.sha256(manifest_raw).hexdigest() == MANIFEST
    )
    assert prepared["workflow_sha"] == "b8d1e26dd4a81990c25a5cdfc122b18f848160ac"
    assert prepared["workflow_run_id"] == str(RUN)
    assert (
        prepared["base_manifest_sha256"]
        == hashlib.sha256(base_raw).hexdigest()
        == ("8ec80812ae9dda9222d9d157c253d7a919af214ae40c49a27c20f87b52d156c8")
    )
    manifest = json.loads(manifest_raw)
    base = {r["path"]: r for r in json.loads(base_raw)["files"]}
    actual = {r["path"]: r for r in manifest["files"]}
    inventory = json.loads(
        (
            gate.ROOT / "working/nba-tools-completion-program/season-inactive-2024-inventory.json"
        ).read_bytes()
    )
    additions = {r["path"]: r for r in inventory["overlay_files"]}
    assert len(base) == 1213 and not base.keys() & additions.keys()
    assert actual == {**base, **additions}
    assert (
        prepared["artifact_zip_sha256"]
        == "d554fd638494e084ef29cf04e709bd264b642b4d70114e8350addfbaf9a269e4"
    )
    source = prepared["required_source_gate"]
    assert source["candidate_sha"] == "a13848048145b6571b2b806a903c19beb3901bd3"
    assert source["generation"] == BASE
    assert [source[k] for k in ("selected", "executed", "passed")] == [1, 1, 1]
    assert all(source[k] == 0 for k in ("skipped", "failed", "errors", "xfailed"))
    assert len(manifest["files"]) == prepared["file_count"] == 1216
    assert sum(p["size_bytes"] for p in manifest["files"]) == prepared["total_bytes"] == 419488508
    assert prepared["registry_sha256"] == gate.digest(gate.REGISTRY.read_bytes())
    assert prepared["publisher_sha"] == "a78164988b5396b341c7e42e1028a16071fad59e"
    assert prepared["artifact_id"] == 14205745241 and prepared["source_run_id"] == 43822127410
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
        print("SEASON_INACTIVE_2024_APPROVAL_TUPLE " + json.dumps(prepared), flush=True)
        print(
            "SEASON_INACTIVE_2024_PUBLICATION_POLICY "
            + json.dumps(
                dict(protected_environment_ready=True, pointer_unchanged=True, r2_writes=0)
            ),
            flush=True,
        )
