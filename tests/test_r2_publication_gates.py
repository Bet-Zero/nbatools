"""Adversarial checks for the separate, manual publication authority."""

import copy
import importlib.util
import io
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publication_gate", ROOT / "tools/r2_publication.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def protected_environment():
    return {
        "name": gate.ENVIRONMENT,
        "id": 123,
        "can_admins_bypass": False,
        "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True},
        "protection_rules": [
            {
                "type": "required_reviewers",
                "reviewers": [{"type": "User", "reviewer": {"id": gate.OWNER_ID}}],
            }
        ],
    }, {"branch_policies": [{"name": "main", "type": "branch"}]}


def test_only_current_owner_environment_approval_is_accepted():
    document, branches = protected_environment()
    audit = dict(publication_ready=True, configuration=document, branches=branches)
    approval = {"state": "approved", "user": {"id": gate.OWNER_ID}, "environments": [{"id": 123}]}
    gate.check_approval(audit, [approval])
    for changes in ({"state": "rejected"}, {"user": {"id": 7}}, {"environments": [{"id": 456}]}):
        with pytest.raises(ValueError):
            gate.check_approval(audit, [approval | changes])
    with pytest.raises(ValueError):
        gate.check_approval(audit, [])
    with pytest.raises(ValueError):
        gate.check_approval(audit | {"publication_ready": False}, [approval])


@pytest.mark.parametrize(
    "change", ["unknown_bypass", "bypass", "wildcard", "tag", "no_reviewer", "other_reviewer"]
)
def test_environment_weakening_fails_closed(change):
    document, branches = protected_environment()
    if change == "unknown_bypass":
        document.pop("can_admins_bypass")
    elif change == "bypass":
        document["can_admins_bypass"] = True
    elif change == "wildcard":
        branches["branch_policies"][0]["name"] = "*"
    elif change == "tag":
        branches["branch_policies"][0]["type"] = "tag"
    elif change == "no_reviewer":
        document["protection_rules"] = []
    else:
        document["protection_rules"][0]["reviewers"][0]["reviewer"]["id"] = 7
    with pytest.raises(ValueError):
        gate.check_environment(document, branches)


def test_unreviewed_changed_or_failed_main_is_rejected(monkeypatch):
    for key, value in dict(
        GITHUB_REPOSITORY=gate.REPOSITORY,
        GITHUB_REF="refs/heads/main",
        GITHUB_EVENT_NAME="workflow_dispatch",
        GITHUB_RUN_ATTEMPT="1",
    ).items():
        monkeypatch.setenv(key, value)
    responses = {
        "/git/ref/heads/main": {"object": {"sha": "abc"}},
        "/commits/abc/pulls": [
            {"merged_at": "today", "merge_commit_sha": "abc", "base": {"ref": "main"}}
        ],
        "/actions/runs?head_sha=abc&event=push&per_page=100": {
            "workflow_runs": [
                {"id": 1, "path": ".github/workflows/ci.yml", "conclusion": "success"}
            ]
        },
    }
    monkeypatch.setattr(gate, "api", lambda path: responses[path])
    gate.check_main_revision("abc")
    baseline = copy.deepcopy(responses)
    for key, value in [
        ("/git/ref/heads/main", {"object": {"sha": "new"}}),
        ("/commits/abc/pulls", []),
        ("/actions/runs?head_sha=abc&event=push&per_page=100", {"workflow_runs": []}),
    ]:
        responses.clear()
        responses.update(copy.deepcopy(baseline))
        responses[key] = value
        with pytest.raises(ValueError):
            gate.check_main_revision("abc")


def test_pointer_authenticates_manifest_bytes():
    raw = json.dumps({"generation_id": "base", "files": [{"path": "a"}]}).encode()
    pointer = {"generation_id": "base", "manifest_sha256": gate.digest(raw)}

    class Client:
        def get_object(self, *, Bucket, Key):
            return {
                "Body": io.BytesIO(
                    json.dumps(pointer).encode()
                    if Key == "metadata/active_generation.json"
                    else raw
                )
            }

    gate.verify_pointer_manifest(Client(), "bucket", "base")
    pointer["manifest_sha256"] = "corrupt"
    with pytest.raises(ValueError, match="authenticate"):
        gate.verify_pointer_manifest(Client(), "bucket", "base")


def test_publication_cannot_reach_prepare_or_writer_without_approval(tmp_path, monkeypatch):
    prepared = tmp_path / "prepared.json"
    prepared.write_text("{}")
    monkeypatch.setenv("GITHUB_SHA", "abc")
    monkeypatch.setenv("GITHUB_RUN_ID", "1")
    monkeypatch.setattr(gate, "check_main_revision", lambda sha: None)
    monkeypatch.setattr(gate, "environment_audit", lambda: {"publication_ready": False})
    monkeypatch.setattr(gate, "api", lambda path: [])
    monkeypatch.setattr(
        gate, "prepare", lambda *a, **k: pytest.fail("Preparation reached without approval")
    )
    with pytest.raises(ValueError, match="unverified"):
        gate.publish("package", tmp_path, tmp_path / "work", prepared)


def test_publisher_workflow_is_manual_and_credentials_are_job_and_step_scoped():
    workflow = yaml.safe_load((ROOT / ".github/workflows/r2-data-publication.yml").read_text())
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers) == {"workflow_dispatch"}
    assert triggers["workflow_dispatch"]["inputs"]["mode"]["default"] == "validate"
    assert workflow["permissions"] == {"contents": "read", "actions": "read"}
    jobs = workflow["jobs"]
    assert jobs["publish"]["environment"]["name"] == "r2-publication"
    assert jobs["publish"]["if"] == "inputs.mode == 'publish'"
    assert "env" not in jobs["publish"]
    secret_steps = [
        step for step in jobs["publish"]["steps"] if "R2_SECRET_ACCESS_KEY" in step.get("env", {})
    ]
    assert len(secret_steps) == 1
    assert "r2_publication.py publish" in secret_steps[0]["run"]
    assert (
        "secrets.R2_PUBLICATION_SECRET_ACCESS_KEY" in secret_steps[0]["env"]["R2_SECRET_ACCESS_KEY"]
    )
    for name, job in jobs.items():
        for step in job.get("steps", []):
            if "uses" in step:
                assert len(step["uses"].split("@")[-1]) == 40
        if name != "publish":
            assert "R2_PUBLICATION_" not in json.dumps(job)
    assert "environment" not in jobs["receipt"]
    assert "R2_" not in json.dumps(jobs["receipt"])
    assert (
        "secrets: inherit" not in (ROOT / ".github/workflows/r2-data-publication.yml").read_text()
    )


def test_reusable_publication_only_receives_named_readonly_r2_secrets():
    """Required environment secrets must be explicitly passed across workflow_call."""
    caller = yaml.safe_load((ROOT / ".github/workflows/r2-data-publication.yml").read_text())
    reusable = yaml.safe_load((ROOT / ".github/workflows/r2-real-data-validation.yml").read_text())
    expected = {
        name: "${{ secrets." + name + " }}"
        for name in (
            "R2_VALIDATION_ACCOUNT_ID",
            "R2_VALIDATION_ACCESS_KEY_ID",
            "R2_VALIDATION_SECRET_ACCESS_KEY",
        )
    }
    jobs = caller["jobs"]
    for name in ("prepare", "verify"):
        assert jobs[name]["secrets"] == expected
        assert jobs[name]["uses"] == "./.github/workflows/r2-real-data-validation.yml"
    # No broad repository-secret inheritance or write-credential propagation.
    assert "secrets: inherit" not in (ROOT / ".github/workflows/r2-data-publication.yml").read_text()
    assert "secrets" not in jobs["publish"]
    call = reusable.get("on", reusable.get(True))["workflow_call"]
    assert call["secrets"] == {name: {"required": True} for name in expected}
    assert reusable["jobs"]["publication-readonly"]["environment"] == "r2-validation"


def test_source_archive_validation_rejects_substitution_and_traversal(tmp_path, monkeypatch):
    import zipfile

    inventory = dict(
        run_id=10,
        artifact_id=20,
        request_sha="request",
        reviewed_sha="reviewed",
        base_generation="base",
        files=[{"path": "raw/evidence.csv"}],
    )
    summary = dict(
        candidate_sha="request",
        generation="base",
        selected=2,
        executed=2,
        passed=2,
        skipped=0,
        failed=0,
        errors=0,
        xfailed=0,
    )

    def archive(extra=None, values=None):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as z:
            z.writestr("summary.json", json.dumps(summary if values is None else values))
            z.writestr("acquired_data/raw/evidence.csv", "a,b\n1,2\n")
            if extra:
                z.writestr(extra, "bad")
        return stream.getvalue()

    payload = archive()

    def api(path, **kwargs):
        if path.endswith("/zip"):
            return payload
        if path == "/actions/runs/10":
            return dict(
                head_sha="request",
                conclusion="success",
                path=".github/workflows/r2-real-data-validation.yml",
            )
        if path == "/actions/artifacts/20":
            return dict(expired=False, workflow_run=dict(id=10, head_sha="request"))
        if path == "/commits/request":
            return {"parents": [{"sha": "reviewed"}]}
        pytest.fail(path)

    monkeypatch.setattr(gate, "api", api)
    inventory["artifact_zip_sha256"] = gate.digest(payload)
    gate.acquire_overlay(inventory, tmp_path / "good")
    assert (tmp_path / "good/raw/evidence.csv").read_text() == "a,b\n1,2\n"
    payload = archive("../escape")
    inventory["artifact_zip_sha256"] = gate.digest(payload)
    with pytest.raises(ValueError, match="Unsafe"):
        gate.acquire_overlay(inventory, tmp_path / "bad")
    assert not (tmp_path / "escape").exists()
    payload = archive("acquired_data/unreviewed.csv")
    inventory["artifact_zip_sha256"] = gate.digest(payload)
    with pytest.raises(ValueError, match="inventory differs"):
        gate.acquire_overlay(inventory, tmp_path / "bad")
    payload = archive(values=summary | {"executed": 0, "passed": 0, "skipped": 2})
    inventory["artifact_zip_sha256"] = gate.digest(payload)
    with pytest.raises(ValueError, match="did not execute"):
        gate.acquire_overlay(inventory, tmp_path / "bad")
    inventory["artifact_zip_sha256"] = "unreviewed"
    with pytest.raises(ValueError, match="checksum"):
        gate.acquire_overlay(inventory, tmp_path / "bad")


def test_bucket_budget_counts_existing_generations_and_never_prunes():
    class Client:
        def get_paginator(self, operation):
            assert operation == "list_objects_v2"
            return self

        def paginate(self, **kwargs):
            yield {"Contents": [{"Size": 60}]}
            yield {"Contents": [{"Size": 40}]}

    policy = dict(max_snapshot_bytes=50, max_snapshot_objects=3, max_bucket_bytes=10_000_149)
    with pytest.raises(ValueError, match="storage ceiling"):
        gate.bucket_budget(Client(), "bucket", policy, dict(total_bytes=50, file_count=3))
    policy["max_bucket_bytes"] += 1
    assert (
        gate.bucket_budget(Client(), "bucket", policy, dict(total_bytes=50, file_count=3))[
            "current_bytes"
        ]
        == 100
    )
    with pytest.raises(ValueError, match="size/object"):
        gate.bucket_budget(Client(), "bucket", policy, dict(total_bytes=51, file_count=3))


@pytest.mark.parametrize("corrupt,drift", [(False, False), (True, False), (False, True)])
def test_postpublication_verifies_bytes_and_final_pointer(tmp_path, monkeypatch, corrupt, drift):
    from types import SimpleNamespace

    monkeypatch.setenv("GITHUB_SHA", "code")
    monkeypatch.setenv("GITHUB_RUN_ID", "run")
    package = dict(
        generation_id="target",
        deployed_checks=[dict(query="verified question", summary={"games": 1})],
    )
    monkeypatch.setattr(gate, "load_package", lambda *a: ({}, package, {"base_generation": "base"}))
    item = dict(path="raw/data.csv", size_bytes=3, sha256=gate.digest(b"abc"))
    pointer = dict(generation_id="target", previous_generation_id="base")
    reads = []

    def verify_pointer(*args):
        reads.append("pointer")
        return (
            pointer | ({"published_at": "changed"} if drift and len(reads) == 3 else {}),
            {"files": [item]},
            "hash",
        )

    monkeypatch.setattr(gate, "verify_pointer_manifest", verify_pointer)

    class Client:
        def get_object(self, **kwargs):
            assert kwargs["Key"] == "generations/target/raw/data.csv"
            return {"Body": io.BytesIO(b"bad" if corrupt else b"abc")}

    module = SimpleNamespace(
        _resolve_r2_target=lambda **k: (Client(), "bucket"),
        _validate_r2_manifest_inventory=lambda *a: None,
    )
    monkeypatch.setattr(gate, "publisher_modules", lambda *a: module)
    monkeypatch.setattr(
        gate.requests,
        "get",
        lambda *a, **k: SimpleNamespace(
            status_code=200, json=lambda: {"ready": True, "active_generation": "target"}
        ),
    )
    monkeypatch.setattr(
        gate.requests,
        "post",
        lambda *a, **k: SimpleNamespace(
            status_code=200,
            json=lambda: {
                "result_status": "ok",
                "result": {"sections": {"summary": [{"games": 1}]}},
            },
        ),
    )
    source = tmp_path / "publication.json"
    source.write_text(
        json.dumps(
            dict(
                package="pkg",
                registry_sha256=gate.digest(gate.REGISTRY.read_bytes()),
                workflow_sha="code",
                workflow_run_id="run",
                generation_id="target",
                prepared_manifest_sha256="hash",
                file_count=1,
            )
        )
    )
    output = tmp_path / "verified"
    if corrupt or drift:
        with pytest.raises(ValueError):
            gate.verify("pkg", tmp_path, output, source)
        assert (
            json.loads((output / "receipt.json").read_text())["publication_state"]
            == "published_verification_failed"
        )
    else:
        result = gate.verify("pkg", tmp_path, output, source)
        assert result["publication_state"] == "published_and_verified"
        assert result["verified_objects"] == [item]
        assert len(reads) == 3


def test_writer_failure_retains_durable_unknown_outcome(tmp_path, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setenv("GITHUB_SHA", "code")
    monkeypatch.setenv("GITHUB_RUN_ID", "run")
    monkeypatch.setattr(gate, "check_main_revision", lambda *a: None)
    document, branches = protected_environment()
    monkeypatch.setattr(
        gate,
        "environment_audit",
        lambda: dict(publication_ready=True, configuration=document, branches=branches),
    )
    approvals = [
        {"state": "approved", "user": {"id": gate.OWNER_ID}, "environments": [{"id": 123}]}
    ]
    monkeypatch.setattr(gate, "api", lambda *a: approvals)
    work = tmp_path / "work"
    expected = {"manifest": "owner-visible"}
    prepared = tmp_path / "approved.json"
    prepared.write_text(json.dumps(expected))

    def writer(generation, **kwargs):
        assert generation == "target"
        assert kwargs["expected_base"] == "base"
        assert kwargs["source_dir"] == work / "staging/data"
        assert (
            json.loads((work / "publication.json").read_text())["publication_state"]
            == "publication_started_outcome_unknown"
        )
        raise RuntimeError("simulated failure after a write")

    def prepare(*args, **kwargs):
        assert kwargs["expected"] == expected
        return (
            {"generation_id": "target", "base_generation": "base"},
            SimpleNamespace(publish_r2_generation=writer),
            None,
            None,
        )

    monkeypatch.setattr(gate, "prepare", prepare)
    with pytest.raises(RuntimeError, match="simulated"):
        gate.publish("pkg", tmp_path, work, prepared)
    receipt = json.loads((work / "publication.json").read_text())
    assert receipt["publication_state"] == "publication_started_outcome_unknown"
    assert receipt["owner_approval"] == approvals


def test_publish_resolver_blocks_before_github_can_create_unprotected_environment(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(gate.sys, "argv", ["r2_publication.py", "resolve"])
    monkeypatch.setenv("PUBLICATION_MODE", "publish")
    monkeypatch.setenv("GITHUB_SHA", "reviewed")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "outputs"))
    monkeypatch.setattr(gate, "check_main_revision", lambda *a: None)
    monkeypatch.setattr(gate, "environment_audit", lambda: {"publication_ready": False})
    with pytest.raises(ValueError, match="Configure protected"):
        gate.main()
    assert not (tmp_path / "outputs").exists()
    monkeypatch.setenv("PUBLICATION_MODE", "validate")
    gate.main()
    assert "publisher_sha=" in (tmp_path / "outputs").read_text()


def test_empty_approval_snapshot_cannot_disable_rebuild_comparison(tmp_path, monkeypatch):
    from types import SimpleNamespace

    policy = json.loads(gate.REGISTRY.read_text())
    package = policy["packages"]["opening-availability-v1"]
    inventory = json.loads((ROOT / package["inventory"]).read_text())
    monkeypatch.setattr(gate, "load_package", lambda *a: (policy, package, inventory))
    monkeypatch.setattr(gate, "acquire_overlay", lambda *a: {"passed": 1})
    monkeypatch.setattr(
        gate,
        "publisher_modules",
        lambda *a: SimpleNamespace(_resolve_r2_target=lambda **k: (None, "bucket")),
    )
    monkeypatch.setattr(
        gate, "verify_pointer_manifest", lambda *a: ({"generation_id": "base"}, {}, "basehash")
    )
    monkeypatch.setattr(gate, "bucket_budget", lambda *a: {"limit_bytes": 100})

    def stage(command, **kwargs):
        directory = Path(command[command.index("--work-dir") + 1])
        gate.write_json(
            directory / "local-validation.json",
            dict(manifest_sha256="rebuilt", file_count=1, total_bytes=3),
        )

    monkeypatch.setattr(gate.subprocess, "run", stage)
    receipt, *_ = gate.prepare("opening-availability-v1", tmp_path, tmp_path / "normal")
    assert receipt["prepared_manifest_sha256"] == "rebuilt"
    with pytest.raises(ValueError, match="owner-visible preparation"):
        gate.prepare("opening-availability-v1", tmp_path, tmp_path / "empty", expected={})
    with pytest.raises(ValueError, match="owner-visible preparation"):
        gate.prepare(
            "opening-availability-v1",
            tmp_path,
            tmp_path / "changed",
            expected=receipt | {"prepared_manifest_sha256": "different"},
        )
