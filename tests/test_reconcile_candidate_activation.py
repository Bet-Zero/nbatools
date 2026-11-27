"""Compose the failed writer receipt, real read-only verifier and native controls."""

import io
import json
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

from tests.test_r2_publication_gates import _native_activation_readiness, protected_environment
from tools import r2_publication as gate
from tools import reconcile_candidate_activation as recovery


@pytest.fixture
def incident(monkeypatch):
    base_manifest = json.dumps({"generation_id": "base", "files": [{"path": "base.csv"}]}).encode()
    item = {"path": "raw/games.csv", "size_bytes": 3, "sha256": gate.digest(b"abc")}
    candidate_manifest = json.dumps({"generation_id": "target", "files": [item]}).encode()
    base_pointer = {
        "generation_id": "base",
        "previous_generation_id": "earlier",
        "manifest_sha256": gate.digest(base_manifest),
        "schema_version": 1,
        "published_at": "2026-11-25T00:00:00+00:00",
    }
    candidate_pointer = {
        "generation_id": "target",
        "previous_generation_id": "base",
        "manifest_sha256": gate.digest(candidate_manifest),
        "schema_version": 1,
        "published_at": "2026-11-26T06:30:25+00:00",
    }
    source_sha = "a" * 40
    acts = {"manifest_sha256": candidate_pointer["manifest_sha256"]}
    inventory = {"base_generation": "base", "base_manifest_sha256": base_pointer["manifest_sha256"]}
    package = {
        "generation_id": "target",
        "operations": ["activate_candidate"],
        "publisher_sha": "b" * 40,
        "activation": acts,
        "deployed_checks": [{"query": "fixture record", "summary": {"games": 1}}],
    }
    prepared = {
        **inventory,
        "schema_version": 1,
        "publication_state": "activation_prepared_no_writes",
        "package": "pkg",
        "publisher_sha": package["publisher_sha"],
        "registry_sha256": gate.digest(gate.REGISTRY.read_bytes()),
        "workflow_sha": source_sha,
        "workflow_run_id": "100",
        "generation_id": "target",
        "prepared_manifest_sha256": acts["manifest_sha256"],
        "activation_evidence": acts,
        "base_pointer": base_pointer,
        "file_count": 1,
        "total_bytes": 3,
        "candidate_backup_preflight": {
            "generation_id": "target",
            "manifest_sha256": acts["manifest_sha256"],
            "files": 1,
            "data_bytes": 3,
            "archive_bytes": 250,
            "r2_writes": 0,
        },
        "operation_budget": {
            "active_pointer_puts": 1,
            "snapshot_object_puts": 0,
            "sdk_attempts": 1,
        },
    }
    configuration, branches = protected_environment()
    approvals = [
        {"state": "approved", "user": {"id": gate.OWNER_ID}, "environments": [{"id": 123}]}
    ]
    attempt = prepared | {
        "publication_state": recovery.UNKNOWN,
        "environment_audit": {
            "publication_ready": True,
            "configuration": configuration,
            "branches": branches,
        },
        "owner_approval": approvals,
    }
    response_bytes = io.BytesIO()
    with ZipFile(response_bytes, "w") as zipped:
        zipped.writestr("prepared.json", json.dumps(prepared))
        zipped.writestr("publication.json", json.dumps(attempt))
    raw = response_bytes.getvalue()
    source = recovery.ActivationRun(source_sha, 100, 200, 300, gate.digest(raw))
    replies = {
        "/actions/runs/100": {
            "head_sha": source_sha,
            "head_branch": "main",
            "head_repository": {"full_name": gate.REPOSITORY},
            "event": "workflow_dispatch",
            "path": ".github/workflows/r2-data-publication.yml",
            "display_title": "activate_candidate reviewed data package pkg",
            "status": "completed",
            "run_attempt": 1,
        },
        "/actions/jobs/200": {
            "head_sha": source_sha,
            "run_id": 100,
            "run_attempt": 1,
            "conclusion": "failure",
            "name": "Owner approval: pkg → target",
            "started_at": "2026-11-26T06:22:02Z",
            "completed_at": "2026-11-26T06:30:30Z",
        },
        "/actions/artifacts/300": {
            "expired": False,
            "name": "publication-result-100",
            "workflow_run": {"id": 100, "head_sha": source_sha},
            "digest": f"sha256:{gate.digest(raw)}",
        },
        "/actions/artifacts/300/zip": raw,
        "/actions/runs/100/approvals": approvals,
    }
    pointers = [candidate_pointer]
    reads = []

    class ReadOnlyClient:
        def get_object(self, *, Bucket, Key):
            assert Bucket == "fixture"
            reads.append(Key)
            if Key == "metadata/active_generation.json":
                pointer = pointers.pop(0) if len(pointers) > 1 else pointers[0]
                return {"Body": io.BytesIO(json.dumps(pointer).encode())}
            return {
                "Body": io.BytesIO(
                    {
                        "generations/base/metadata/generation_manifest.json": base_manifest,
                        "generations/target/metadata/generation_manifest.json": candidate_manifest,
                        "generations/target/raw/games.csv": b"abc",
                    }[Key]
                )
            }

        def close(self):
            pass

    def target(*, client, bucket_name, env, env_file):
        return ReadOnlyClient(), "fixture"

    publisher = SimpleNamespace(
        _resolve_r2_target=target, _validate_r2_manifest_inventory=lambda *_: None
    )
    monkeypatch.setattr(gate, "load_package", lambda *_: ({}, package, inventory))
    monkeypatch.setattr(gate, "publisher_modules", lambda *_: publisher)
    monkeypatch.setattr(gate, "api", lambda path, **_: replies[path])

    def get(url, *, timeout):
        if url.endswith("/readiness"):
            return SimpleNamespace(
                status_code=503, json=lambda: _native_activation_readiness("target")
            )
        assert url.endswith("/health")
        return SimpleNamespace(status_code=200, json=lambda: {"status": "ok"})

    monkeypatch.setattr(gate.requests, "get", get)

    def post(url, *, json, timeout):
        assert url.endswith("/query") and json == {"query": "fixture record"}
        return SimpleNamespace(
            status_code=200,
            headers={"X-Request-Id": "req_fixture"},
            json=lambda: {
                "result_status": "ok",
                "result": {"sections": {"summary": [{"games": 1}]}},
            },
        )

    monkeypatch.setattr(gate.requests, "post", post)
    return SimpleNamespace(
        source=source, pointers=pointers, base=base_pointer, replies=replies, reads=reads
    )


@pytest.mark.parametrize(
    "pointer,expected",
    [
        ("base", "base_unchanged"),
        ("malformed_base", "conflicting_publication"),
        ("target", "exact_candidate_active"),
        ("other", "conflicting_publication"),
        ("later_same_tuple", "conflicting_publication"),
        ("mismatched_manifest", "conflicting_publication"),
    ],
)
def test_reconcile_only_verifies_the_exact_candidate(incident, tmp_path, pointer, expected):
    if pointer == "base":
        incident.pointers[0] = incident.base
    elif pointer == "malformed_base":
        incident.pointers[0] = incident.base | {"schema_version": True}
    elif pointer in {"other", "later_same_tuple", "mismatched_manifest"}:
        changes = {
            "other": {"generation_id": "later"},
            "later_same_tuple": {"published_at": "2026-11-27T00:00:00Z"},
            "mismatched_manifest": {"manifest_sha256": "f" * 64},
        }
        incident.pointers[0].update(changes[pointer])
    output = tmp_path / "verified"
    receipt = recovery.reconcile("pkg", tmp_path, output, incident.source)
    assert json.loads((output / "receipt.json").read_text()) == receipt
    assert receipt["reconciliation"]["status"] == expected
    assert receipt["reconciliation"]["production_writes"] == 0
    if pointer == "target":
        assert receipt["publication_state"] == "candidate_activated_historical_verified"
        assert receipt["previous_manifest_preserved"] is True
        assert receipt["deployed_readiness_http_status"] == 503
        assert receipt["operational_acceptance_complete"] is False
        assert receipt["deployed_answers"] == [{"query": "fixture record", "summary": {"games": 1}}]
        assert len(receipt["verified_objects"]) == 1
    else:
        assert receipt["publication_state"] == recovery.UNKNOWN
        assert "verified_objects" not in receipt
        assert not any(key.startswith("generations/target/") for key in incident.reads)


@pytest.mark.parametrize(
    ("key", "change", "error"),
    [
        ("/actions/jobs/200", {"conclusion": "success"}, "failed original"),
        ("/actions/artifacts/300", {"digest": "sha256:wrong"}, "failed original"),
        ("/actions/runs/100", {"run_attempt": 2}, "failed original"),
        ("/actions/runs/100/approvals", None, "explicit owner approval"),
    ],
)
def test_invalid_original_provenance_prevents_all_r2_reads(incident, tmp_path, key, change, error):
    if change is None:
        incident.replies[key] = []
    else:
        incident.replies[key].update(change)
    with pytest.raises(ValueError, match=error):
        recovery.reconcile("pkg", tmp_path, tmp_path / "verified", incident.source)
    assert incident.reads == []


@pytest.mark.parametrize(
    ("read", "schema_version", "error"),
    [
        (1, True, "differs from approved"),
        (2, 1.0, "moved during verification"),
        (3, True, "moved during deployed verification"),
    ],
)
def test_candidate_schema_type_change_during_reconciliation_stops(
    incident, tmp_path, read, schema_version, error
):
    candidate = incident.pointers[0]
    incident.pointers[:] = [candidate] * read + [candidate | {"schema_version": schema_version}]
    output = tmp_path / "verified"
    with pytest.raises(ValueError, match=error):
        recovery.reconcile("pkg", tmp_path, output, incident.source)
    receipt = json.loads((output / "receipt.json").read_text())
    assert receipt["publication_state"] == "candidate_activation_verification_failed"


def test_candidate_republication_between_classification_and_verification_stops(incident, tmp_path):
    incident.pointers.append(incident.pointers[0] | {"published_at": "2026-11-26T07:00:00+00:00"})
    output = tmp_path / "verified"
    with pytest.raises(ValueError, match="differs from approved"):
        recovery.reconcile("pkg", tmp_path, output, incident.source)
    receipt = json.loads((output / "receipt.json").read_text())
    assert receipt["publication_state"] == "candidate_activation_verification_failed"
    assert "generations/target/raw/games.csv" not in incident.reads
