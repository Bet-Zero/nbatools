"""Synthetic diagnostic guards; numeric evidence never replaces readiness acceptance."""

import copy
import io
import json
import zipfile
from types import SimpleNamespace

import pytest

from tests.test_publication_recovery import original_receipt
from tools import audit_lebron_publication as audit
from tools import r2_publication as gate


def fixture_source():
    package, source = original_receipt()
    package.update(generation_id=audit.GENERATION, deployed_checks=[{}] * 16)
    inventory = dict(
        base_generation="base",
        base_manifest_sha256="b" * 64,
        artifact_id=17,
        artifact_zip_sha256="c" * 64,
        run_id=19,
    )
    source.update(
        schema_version=1,
        package=audit.PACKAGE,
        workflow_sha=audit.SOURCE_SHA,
        workflow_run_id=str(audit.SOURCE_RUN),
        **inventory,
        source_run_id=inventory["run_id"],
        generation_id=audit.GENERATION,
        publication_state="published_verification_failed",
        file_count=775,
        total_bytes=403814381,
        prepared_manifest_sha256=audit.MANIFEST_SHA,
    )
    source["verified_objects"] = [
        dict(path=f"raw/fixture/{n}.csv", size_bytes=0, sha256="a" * 64) for n in range(775)
    ]
    source["verified_objects"][-1]["size_bytes"] = 403814381
    source["publication"].update(
        generation_id=audit.GENERATION,
        file_count=775,
        total_bytes=403814381,
        manifest_sha256=audit.MANIFEST_SHA,
    )
    source["verified_pointer"] = dict(
        generation_id=audit.GENERATION,
        manifest_sha256=audit.MANIFEST_SHA,
        previous_generation_id="base",
    )
    return package, inventory, source


@pytest.mark.parametrize(
    "damage",
    [
        None,
        "run",
        "write",
        "verify",
        "artifact",
        "zip",
        "archive",
        "schema",
        "registry",
        "publisher",
        "state",
        "approval",
        "outcome",
        "objects",
    ],
)
def test_only_authenticated_original_failed_receipt_can_supply_prior_byte_evidence(
    monkeypatch, damage
):
    package, inventory, source = fixture_source()
    run = dict(
        id=audit.SOURCE_RUN,
        head_sha=audit.SOURCE_SHA,
        head_branch="main",
        event="workflow_dispatch",
        path=".github/workflows/r2-data-publication.yml",
        status="completed",
        conclusion="failure",
    )
    write = dict(
        id=audit.WRITE_JOB,
        run_id=audit.SOURCE_RUN,
        conclusion="success",
        name=f"Owner approval: {audit.PACKAGE} → {audit.GENERATION}",
    )
    verify = dict(id=audit.VERIFY_JOB, run_id=audit.SOURCE_RUN, conclusion="failure")
    artifact = dict(
        id=audit.ARTIFACT,
        expired=False,
        name=f"publication-verified-{audit.SOURCE_RUN}",
        workflow_run=dict(id=audit.SOURCE_RUN, head_sha=audit.SOURCE_SHA),
    )
    if damage == "run":
        run["event"] = "push"
    elif damage == "write":
        write["conclusion"] = "failure"
    elif damage == "verify":
        verify["run_id"] = 0
    elif damage == "artifact":
        artifact["expired"] = True
    elif damage == "schema":
        source["schema_version"] = 2
    elif damage == "registry":
        source["registry_sha256"] = "changed"
    elif damage == "publisher":
        source["publisher_sha"] = "changed"
    elif damage == "state":
        source["publication_state"] = "published_and_verified"
    elif damage == "approval":
        source["owner_approval"] = []
    elif damage == "outcome":
        source["publication"]["manifest_sha256"] = "changed"
    elif damage == "objects":
        source["verified_objects"].pop()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("receipt.json", json.dumps(source))
        if damage == "archive":
            archive.writestr("unexpected.json", "{}")
    payload = stream.getvalue()
    monkeypatch.setattr(audit, "ZIP_SHA", "bad" if damage == "zip" else gate.digest(payload))
    responses = {
        f"/actions/runs/{audit.SOURCE_RUN}": run,
        f"/actions/jobs/{audit.WRITE_JOB}": write,
        f"/actions/jobs/{audit.VERIFY_JOB}": verify,
        f"/actions/artifacts/{audit.ARTIFACT}": artifact,
        f"/actions/artifacts/{audit.ARTIFACT}/zip": payload,
    }
    monkeypatch.setattr(gate, "api", lambda path, **kwargs: responses[path])
    if damage:
        with pytest.raises(ValueError):
            audit.authenticated_source(package, inventory)
    else:
        assert audit.authenticated_source(package, inventory) == source


@pytest.mark.parametrize(
    "status,ready,codes,expected",
    [
        (503, False, ["new_season_not_loaded"], "new_season_not_loaded"),
        (200, True, [], "ready_observed"),
        (503, False, ["new_season_not_loaded", "invalid_generation"], "unresolved"),
        (503, False, [], "unresolved"),
        (200, False, ["new_season_not_loaded"], "unresolved"),
    ],
)
def test_readiness_body_is_recorded_without_waiving_unknown_blockers(
    monkeypatch, status, ready, codes, expected
):
    body = dict(
        active_generation=audit.GENERATION,
        ready=ready,
        blockers=[dict(code=code, detail="fixture") for code in codes],
    )
    monkeypatch.setattr(
        gate.requests,
        "get",
        lambda *args, **kwargs: SimpleNamespace(status_code=status, json=lambda: body),
    )
    observation = audit.readiness_observation()
    assert observation == dict(classification=expected, http_status=status, body=body)


@pytest.mark.parametrize("damage", [None, "pointer", "manifest", "objects", "query", "readiness"])
def test_diagnostic_keeps_operational_failure_and_checks_snapshot_around_live_answers(
    monkeypatch, tmp_path, damage
):
    package, inventory, source = fixture_source()
    monkeypatch.setattr(gate, "load_package", lambda *args: ({}, package, inventory))
    monkeypatch.setattr(audit, "authenticated_source", lambda *args: copy.deepcopy(source))
    client = SimpleNamespace(get_object=lambda **kwargs: pytest.fail("No 775-object redownload"))
    monkeypatch.setattr(
        gate,
        "publisher_modules",
        lambda *args: SimpleNamespace(
            _resolve_r2_target=lambda **kwargs: (client, "read-only-bucket")
        ),
    )
    snapshots = [0]

    def snapshot(*args):
        snapshots[0] += 1
        pointer = copy.deepcopy(source["verified_pointer"])
        manifest = dict(
            generation_id=audit.GENERATION, files=copy.deepcopy(source["verified_objects"])
        )
        digest = audit.MANIFEST_SHA
        if snapshots[0] == 2:
            if damage == "pointer":
                pointer["published_at"] = "changed"
            elif damage == "manifest":
                digest = "changed"
            elif damage == "objects":
                manifest["files"][0]["sha256"] = "changed"
        return pointer, manifest, digest

    monkeypatch.setattr(gate, "verify_pointer_manifest", snapshot)
    monkeypatch.setattr(
        audit,
        "readiness_observation",
        lambda: dict(
            classification="unresolved" if damage == "readiness" else "new_season_not_loaded",
            http_status=503,
            body={"ready": False, "blockers": [{"code": "new_season_not_loaded"}]},
        ),
    )
    calls = []

    def answers(selected, result):
        assert selected is package
        calls.append("unchanged_registered_answer_checker")
        if damage == "query":
            raise ValueError("query mismatch")
        result["deployed_answers"] = [{}] * 16
        return result["deployed_answers"]

    monkeypatch.setattr(gate, "check_live_answers", answers)
    monkeypatch.setattr(
        gate, "verify_published_snapshot", lambda *args: pytest.fail("No recovery verifier")
    )
    work = tmp_path / "diagnostic"
    if damage:
        with pytest.raises(ValueError):
            audit.audit(tmp_path / "publisher", work)
    else:
        audit.audit(tmp_path / "publisher", work)
    result = json.loads((work / "diagnostic.json").read_text())
    assert snapshots == [2] and len(calls) == 1
    assert result["operational_acceptance_complete"] is False and result["production_writes"] == 0
    assert result["source_publication_state"] == "published_verification_failed"
    assert result["diagnostic_complete"] is (damage is None)
    assert (
        result["readiness_before"]["http_status"] == result["readiness_after"]["http_status"] == 503
    )
