"""Secret-free controlled requests; never contact R2 or dispatch real workflows."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "tools/resolve_r2_validation_request.py"
MANIFEST = ".github/r2-validation-request.json"


def _git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Request Test")
    _git(tmp_path, "config", "user.email", "request@example.invalid")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_reviewed.py").write_text("def test_reviewed():\n    pass\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "Reviewed synthetic candidate")
    parent = _git(tmp_path, "rev-parse", "HEAD")
    request = {
        "schema_version": 1,
        "reviewed_sha": parent,
        "generation": "controlled-immutable-fixture",
        "tests": ["tests/test_reviewed.py::test_reviewed"],
        "raw_qa_cases": ["controlled-case"],
    }
    return tmp_path, request


def run_request(repo, *, raw=None, env_changes=None, event_changes=None, edit_code=False):
    root, request = repo
    manifest = root / MANIFEST
    manifest.parent.mkdir(exist_ok=True)
    manifest.write_text(json.dumps(request) if raw is None else raw)
    if edit_code:
        (root / "tests/test_reviewed.py").write_text("raise RuntimeError('unreviewed edit')\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "Controlled request")
    sha = _git(root, "rev-parse", "HEAD")
    event = {
        "repository": {"full_name": "Bet-Zero/nbatools", "fork": False},
        "ref": "refs/heads/r2-validation/controlled-case",
        "after": sha,
        "deleted": False,
    }
    event.update(event_changes or {})
    event_path = root / "event.json"
    event_path.write_text(json.dumps(event))
    output = root / "github-output"
    env = {
        **os.environ,
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_REPOSITORY": "Bet-Zero/nbatools",
        "GITHUB_SHA": sha,
        "GITHUB_REF": event["ref"],
        "GITHUB_EVENT_PATH": str(event_path),
        "GITHUB_OUTPUT": str(output),
        "GITHUB_STEP_SUMMARY": str(root / "summary"),
    }
    env.update(env_changes or {})
    result = subprocess.run(
        [sys.executable, str(RESOLVER)],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
    )
    outputs = (
        dict(line.split("=", 1) for line in output.read_text().splitlines())
        if output.exists()
        else {}
    )
    return result, outputs


def test_valid_push_binds_reviewed_parent_exact_request_sha_and_generation(repo):
    result, outputs = run_request(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert outputs == {
        "candidate_sha": _git(repo[0], "rev-parse", "HEAD"),
        "reviewed_sha": repo[1]["reviewed_sha"],
        "generation": "controlled-immutable-fixture",
        "scope": "targeted",
        "tests": "tests/test_reviewed.py::test_reviewed",
        "raw_qa_cases": "controlled-case",
        "automatic": "true",
    }
    assert outputs["candidate_sha"] != outputs["reviewed_sha"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", 2),
        ("schema_version", True),
        ("scope", "full"),
        ("target_ref", "main"),
        ("reviewed_sha", "main"),
        ("reviewed_sha", "0" * 40),
        ("generation", ""),
        ("generation", "legacy"),
        ("generation", "snapshot\ninjected=value"),
        ("generation", "../snapshot"),
        ("generation", 42),
        ("tests", "tests/test_reviewed.py"),
        ("tests", [None]),
        ("tests", [" "]),
        ("tests", ["tests/"]),
        ("tests", ["tests/test_reviewed.py", "tests/test_reviewed.py"]),
        ("tests", ["tests/../tests/test_reviewed.py"]),
        ("tests", ["-k"]),
        ("tests", ["tests/test_reviewed.py;env"]),
        ("tests", ["tests/missing.py"]),
        ("tests", [f"tests/test_reviewed.py::case_{i}" for i in range(21)]),
        ("raw_qa_cases", ["case\nother"]),
        ("raw_qa_cases", ["--limit"]),
        ("raw_qa_cases", [f"case-{i}" for i in range(21)]),
        ("raw_qa_cases", ["same", "same"]),
    ],
)
def test_invalid_schema_or_selection_fails_without_job_outputs(repo, field, value):
    repo[1][field] = value
    result, outputs = run_request(repo)
    assert result.returncode != 0
    assert not outputs


@pytest.mark.parametrize("raw", ["{", "[]", "null", "{}", " " * 8193])
def test_malformed_nonobject_missing_or_oversized_request_fails(repo, raw):
    result, outputs = run_request(repo, raw=raw)
    assert result.returncode != 0
    assert not outputs


def test_duplicate_json_keys_fail(repo):
    raw = json.dumps(repo[1]).replace(
        '"schema_version": 1', '"schema_version": 1, "schema_version": 1'
    )
    result, outputs = run_request(repo, raw=raw)
    assert result.returncode != 0
    assert "Duplicate request field" in result.stdout
    assert not outputs


def test_empty_selection_fails(repo):
    repo[1]["tests"] = []
    repo[1]["raw_qa_cases"] = []
    result, outputs = run_request(repo)
    assert result.returncode != 0
    assert not outputs


@pytest.mark.parametrize("unselected", ["tests", "raw_qa_cases"])
def test_one_legitimately_unselected_gate_is_allowed(repo, unselected):
    repo[1][unselected] = []
    result, outputs = run_request(repo)
    assert result.returncode == 0
    assert outputs[unselected] == ""
    assert outputs["scope"] == "targeted"


@pytest.mark.parametrize(
    "env_changes",
    [
        {"GITHUB_EVENT_NAME": "pull_request"},
        {"GITHUB_EVENT_NAME": "pull_request_target"},
        {"GITHUB_EVENT_NAME": "workflow_run"},
        {"GITHUB_REPOSITORY": "someone/fork"},
        {"GITHUB_REF": "refs/heads/main"},
        {"GITHUB_SHA": "0" * 40},
    ],
)
def test_wrong_event_repository_branch_or_checkout_sha_fails(repo, env_changes):
    result, outputs = run_request(repo, env_changes=env_changes)
    assert result.returncode != 0
    assert not outputs


@pytest.mark.parametrize(
    "event_changes",
    [
        {"repository": {"full_name": "Bet-Zero/nbatools", "fork": True}},
        {"ref": "refs/heads/main"},
        {"after": "0" * 40},
        {"deleted": True},
    ],
)
def test_push_payload_must_match_real_repository_ref_and_sha(repo, event_changes):
    result, outputs = run_request(repo, event_changes=event_changes)
    assert result.returncode != 0
    assert not outputs


def test_request_commit_cannot_change_candidate_code(repo):
    result, outputs = run_request(repo, edit_code=True)
    assert result.returncode != 0
    assert "only the request manifest" in result.stdout
    assert not outputs
