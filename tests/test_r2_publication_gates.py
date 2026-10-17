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
