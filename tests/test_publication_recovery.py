"""Focused quota and authenticated recovery guards; synthetic, not NBA evidence."""

import copy
import io
import json
import zipfile

import pytest

from nbatools.admission_control import AdmissionController, AdmissionRejected
from tools import r2_publication as gate
from tools import recover_k08_publication as recovery


class Response:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code = status
        self.body = (
            body
            if body is not None
            else {"result_status": "ok", "result": {"sections": {"summary": [{"games": 1}]}}}
        )
        self.headers = headers or {}
        self.text = json.dumps(self.body)

    def json(self):
        return self.body


def package(count=1):
    return {
        "deployed_checks": [
            {"query": f"fixture {n}", "summary": {"games": 1}} for n in range(count)
        ]
    }


def test_all_thirteen_answers_pass_through_unchanged_real_admission_quota(monkeypatch):
    clock, sleeps = [0], []
    controller = AdmissionController()

    def post(*args, **kwargs):
        assert set(kwargs) == {"json", "timeout"}  # no identity bypass headers
        try:
            return controller.run_query("one-client", Response, now=clock[0])
        except AdmissionRejected as exc:
            return Response(exc.status, exc.payload(), exc.headers())

    def sleep(delay):
        sleeps.append(delay)
        clock[0] += delay

    monkeypatch.setattr(gate.requests, "post", post)
    monkeypatch.setattr(gate.time, "sleep", sleep)
    receipt = {}
    assert len(gate.check_live_answers(package(13), receipt)) == 13
    assert sleeps == [60]
    attempts = receipt["deployed_query_attempts"]
    assert len(attempts) == 14
    assert (attempts[10]["index"], attempts[10]["status"], attempts[10]["retry_after_seconds"]) == (
        11,
        429,
        60,
    )
    assert all(row["status"] == 200 for row in attempts if "retry_after_seconds" not in row)


@pytest.mark.parametrize(
    "status,error,delay",
    [
        (500, "internal_error", "1"),
        (504, "execution_timeout", "1"),
        (429, "concurrency_limited", "1"),
        (429, "rate_limited", ""),
        (429, "rate_limited", "0"),
        (429, "rate_limited", "-1"),
        (429, "rate_limited", "61"),
        (429, "rate_limited", "1.0"),
    ],
)
def test_only_the_diagnosed_bounded_rate_contract_is_retried(monkeypatch, status, error, delay):
    monkeypatch.setattr(
        gate.requests,
        "post",
        lambda *a, **k: Response(
            status, {"error": error}, {"Retry-After": delay, "Set-Cookie": "not-retained"}
        ),
    )
    monkeypatch.setattr(gate.time, "sleep", lambda *a: pytest.fail("Unexpected retry"))
    receipt = {}
    with pytest.raises(ValueError, match=f"query 1 HTTP {status}"):
        gate.check_live_answers(package(), receipt)
    attempt = receipt["deployed_query_attempts"][0]
    assert attempt["query"] == "fixture 0" and attempt["status"] == status
    assert json.loads(attempt["body"]) == {"error": error}
    assert "Set-Cookie" not in attempt["headers"]
    assert receipt["deployed_answers"] == []


def test_a_second_rate_rejection_still_fails_with_exact_query_evidence(monkeypatch):
    monkeypatch.setattr(
        gate.requests,
        "post",
        lambda *a, **k: Response(429, {"error": "rate_limited"}, {"Retry-After": "1"}),
    )
    sleeps = []
    monkeypatch.setattr(gate.time, "sleep", sleeps.append)
    receipt = {}
    with pytest.raises(ValueError, match="fixture 0"):
        gate.check_live_answers(package(), receipt)
    assert sleeps == [1]
    assert len(receipt["deployed_query_attempts"]) == 2


def test_numeric_contradiction_is_never_retried_or_accepted(monkeypatch):
    monkeypatch.setattr(
        gate.requests,
        "post",
        lambda *a, **k: Response(
            body={"result_status": "ok", "result": {"sections": {"summary": [{"games": 0}]}}}
        ),
    )
    monkeypatch.setattr(gate.time, "sleep", lambda *a: pytest.fail("Numeric failure retried"))
    receipt = {}
    with pytest.raises(ValueError, match="NBA evidence"):
        gate.check_live_answers(package(), receipt)
    assert len(receipt["deployed_query_attempts"]) == 1
    assert receipt["deployed_answers"] == []


def test_empty_live_selection_cannot_be_verification():
    with pytest.raises(ValueError, match="requires registered"):
        gate.check_live_answers(package(0), {})


@pytest.mark.parametrize(
    "field", ["workflow_sha", "workflow_run_id", "registry_sha256", "generation_id"]
)
def test_normal_verification_still_rejects_a_different_workflow_receipt(
    monkeypatch, tmp_path, field
):
    p = {"generation_id": "generation"}
    receipt = dict(
        package="package",
        registry_sha256=gate.digest(gate.REGISTRY.read_bytes()),
        workflow_sha="current",
        workflow_run_id="1",
        generation_id="generation",
    )
    receipt[field] = "other"
    source = tmp_path / "original.json"
    source.write_text(json.dumps(receipt))
    monkeypatch.setenv("GITHUB_SHA", "current")
    monkeypatch.setenv("GITHUB_RUN_ID", "1")
    monkeypatch.setattr(gate, "load_package", lambda *a: ({}, p, {}))
    monkeypatch.setattr(
        gate, "publisher_modules", lambda *a: pytest.fail("Invalid identity reached data")
    )
    with pytest.raises(ValueError, match="does not bind"):
        gate.verify("package", tmp_path, tmp_path / "work", source)


def original_receipt():
    p = dict(
        publisher_sha="publisher",
        script_sha256="script",
        inventory_sha256="inventory",
        generation_id="generation",
    )
    receipt = dict(
        package=recovery.PACKAGE,
        workflow_sha=recovery.SOURCE_SHA,
        workflow_run_id=str(recovery.SOURCE_RUN),
        registry_sha256=gate.digest(gate.REGISTRY.read_bytes()),
        **p,
        publication_state="published_verification_pending",
        prepared_manifest_sha256="manifest",
        file_count=1,
        total_bytes=2,
        environment_audit={
            "publication_ready": True,
            "configuration": {
                "id": 123,
                "name": gate.ENVIRONMENT,
                "can_admins_bypass": False,
                "deployment_branch_policy": {
                    "protected_branches": False,
                    "custom_branch_policies": True,
                },
                "protection_rules": [
                    {
                        "type": "required_reviewers",
                        "reviewers": [{"type": "User", "reviewer": {"id": gate.OWNER_ID}}],
                    }
                ],
            },
            "branches": {"branch_policies": [{"name": "main", "type": "branch"}]},
        },
        owner_approval=[
            {"state": "approved", "user": {"id": gate.OWNER_ID}, "environments": [{"id": 123}]}
        ],
    )
    receipt["publication"] = dict(
        action="publish",
        target="r2",
        generation_id="generation",
        previous_generation_id="base",
        manifest_sha256="manifest",
        file_count=1,
        total_bytes=2,
        pointer="metadata/active_generation.json",
    )
    return p, receipt


@pytest.mark.parametrize(
    "damage",
    [
        None,
        "run",
        "event",
        "branch",
        "job",
        "job_run",
        "artifact",
        "expired",
        "zip",
        "inventory",
        "registry",
        "publisher",
        "state",
        "approval",
        "outcome",
    ],
)
def test_recovery_requires_the_exact_original_approved_successful_write(monkeypatch, damage):
    p, receipt = original_receipt()
    run = dict(
        head_sha=recovery.SOURCE_SHA,
        head_branch="main",
        event="workflow_dispatch",
        path=".github/workflows/r2-data-publication.yml",
    )
    job = dict(
        run_id=recovery.SOURCE_RUN,
        conclusion="success",
        name=f"Owner approval: {recovery.PACKAGE} → generation",
    )
    artifact = dict(
        name=f"publication-result-{recovery.SOURCE_RUN}",
        expired=False,
        workflow_run={"id": recovery.SOURCE_RUN, "head_sha": recovery.SOURCE_SHA},
    )
    if damage == "run":
        run["head_sha"] = "other"
    elif damage == "event":
        run["event"] = "push"
    elif damage == "branch":
        run["head_branch"] = "other"
    elif damage == "job":
        job["conclusion"] = "failure"
    elif damage == "job_run":
        job["run_id"] = 1
    elif damage == "artifact":
        artifact["workflow_run"]["id"] = 1
    elif damage == "expired":
        artifact["expired"] = True
    elif damage == "registry":
        receipt["registry_sha256"] = "changed"
    elif damage == "publisher":
        receipt["publisher_sha"] = "changed"
    elif damage == "state":
        receipt["publication_state"] = "prepared_no_writes"
    elif damage == "approval":
        receipt["owner_approval"] = []
    elif damage == "outcome":
        receipt["publication"]["manifest_sha256"] = "changed"
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("publication.json", json.dumps(receipt))
        archive.writestr("prepared.json", "{}")
        if damage == "inventory":
            archive.writestr("unexpected", "bad")
    payload = stream.getvalue()
    monkeypatch.setattr(recovery, "ZIP_SHA", "changed" if damage == "zip" else gate.digest(payload))
    responses = {
        f"/actions/runs/{recovery.SOURCE_RUN}": run,
        f"/actions/jobs/{recovery.WRITE_JOB}": job,
        f"/actions/artifacts/{recovery.ARTIFACT}": artifact,
        f"/actions/artifacts/{recovery.ARTIFACT}/zip": payload,
    }
    monkeypatch.setattr(gate, "api", lambda path, **k: responses[path])
    if damage:
        with pytest.raises(ValueError):
            recovery.approved_receipt(p, {"base_generation": "base"})
    else:
        assert recovery.approved_receipt(p, {"base_generation": "base"}) == receipt


def test_recovery_preserves_original_identity_and_has_a_separate_readonly_identity(
    monkeypatch, tmp_path
):
    p, original = original_receipt()
    monkeypatch.setenv("GITHUB_SHA", "recovery-sha")
    monkeypatch.setenv("GITHUB_RUN_ID", "recovery-run")
    monkeypatch.setattr(gate, "load_package", lambda *a: ({}, p, {}))
    monkeypatch.setattr(recovery, "approved_receipt", lambda *a: copy.deepcopy(original))
    monkeypatch.setattr(gate, "publisher_modules", lambda *a: object())
    monkeypatch.setattr(gate, "verify_published_snapshot", lambda p, i, m, w, receipt: receipt)
    monkeypatch.setattr(gate, "publish", lambda *a: pytest.fail("Recovery reached publisher"))
    result = recovery.recover(tmp_path, tmp_path / "work")
    assert result["workflow_sha"] == recovery.SOURCE_SHA
    assert result["workflow_run_id"] == str(recovery.SOURCE_RUN)
    assert result["recovery"]["workflow_sha"] == "recovery-sha"
    assert result["recovery"]["workflow_run_id"] == "recovery-run"
    assert result["recovery"]["production_writes"] == 0
