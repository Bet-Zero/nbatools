"""Exercise delivery selection against real Git histories, without app/data access."""

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "tools/delivery_scope.mjs"


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def commit(repo):
    git(repo, "add", "-A")
    git(
        repo,
        "-c",
        "user.name=Scope Test",
        "-c",
        "user.email=scope@example.invalid",
        "commit",
        "-qm",
        "case",
    )
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def history(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "AGENTS.md").write_text("original policy\n")
    (tmp_path / "README.md").write_text("package metadata\n")
    return tmp_path, commit(tmp_path)


def run_scope(repo, base, head, *, mode="ci", event="pull_request"):
    env = {
        **os.environ,
        "GITHUB_EVENT_NAME": event,
        "SCOPE_BASE_SHA": base,
        "SCOPE_HEAD_SHA": head,
        "VERCEL_GIT_PREVIOUS_SHA": base,
        "VERCEL_GIT_COMMIT_SHA": head,
    }
    # Tests never write a parent workflow's outputs or summary.
    env.pop("GITHUB_OUTPUT", None)
    env.pop("GITHUB_STEP_SUMMARY", None)
    result = subprocess.run(
        ["node", str(HELPER), mode], cwd=repo, env=env, capture_output=True, text=True
    )
    return result.returncode, json.loads(result.stdout)


@pytest.mark.parametrize(
    ("paths", "application", "deploy"),
    [
        (
            ["AGENTS.md", "ROADMAP.md", "working/nba-tools-completion-program/README.md"],
            False,
            False,
        ),
        (["tests/test_example.py"], True, False),
        (["frontend/tools/captureCoreIdentityFindCount.mjs"], True, False),
        (["frontend/tools/unknownBuildHelper.mjs"], True, True),
        (["working/nba-tools-completion-program/oracle.json"], True, False),
        (["src/nbatools/query_service.py"], True, True),
        (["api/query.py"], True, True),
        (["frontend/src/test/answer.test.tsx"], True, True),
        (["README.md"], True, True),
        (["docs/executable-example.md"], True, True),
        (["frontend/package-lock.json"], True, True),
        (["pyproject.toml"], True, True),
        (["contracts/query_transport.json"], True, True),
        (["AGENTS.md", "unclassified-input.json"], True, True),
        (["AGENTS.md", "src/nbatools/query_service.py"], True, True),
        ([".github/workflows/ci.yml"], True, True),
        (["tools/delivery_scope.mjs"], True, True),
        (["vercel.json"], True, True),
        ([".vercelignore"], True, True),
    ],
)
def test_real_change_ranges_select_required_work(history, paths, application, deploy):
    repo, base = history
    for name in paths:
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("changed\n")
    head = commit(repo)
    status, selected = run_scope(repo, base, head)
    assert status == 0
    assert selected["application"] is application
    assert selected["deploy"] is deploy
    status, selected = run_scope(repo, base, head, mode="vercel")
    assert status == int(deploy), "0 must ignore; 1 must continue Vercel's build"
    assert selected["deploy"] is deploy


def test_runtime_then_receipt_cannot_hide_unbuilt_or_unchecked_runtime(history):
    repo, base = history
    runtime = repo / "api/query.py"
    runtime.parent.mkdir()
    runtime.write_text("runtime\n")
    intermediate = commit(repo)
    (repo / "AGENTS.md").write_text("receipt\n")
    head = commit(repo)
    assert run_scope(repo, intermediate, head)[1]["application"] is False
    assert run_scope(repo, base, head)[1]["application"] is True
    assert run_scope(repo, base, head, mode="vercel")[0] == 1


@pytest.mark.parametrize("base", ["", "0" * 40, "not-a-sha", "--help", "$(touch unsafe)"])
def test_unknown_baseline_is_conservative(history, base):
    repo, head = history
    assert run_scope(repo, base, head)[1]["application"] is True
    assert run_scope(repo, base, head, mode="vercel")[0] == 1
    assert not (repo / "unsafe").exists()


def test_missing_shallow_history_is_conservative(history, tmp_path):
    repo, base = history
    (repo / "AGENTS.md").write_text("receipt\n")
    head = commit(repo)
    shallow = tmp_path / "shallow"
    subprocess.run(["git", "clone", "-q", "--depth=1", repo.as_uri(), str(shallow)], check=True)
    assert run_scope(shallow, base, head)[1]["application"] is True
    assert run_scope(shallow, base, head, mode="vercel")[0] == 1


def test_nonancestor_baseline_is_conservative(history):
    repo, base = history
    (repo / "AGENTS.md").write_text("branch one\n")
    other = commit(repo)
    git(repo, "checkout", "-q", "-b", "other", base)
    (repo / "AGENTS.md").write_text("branch two\n")
    head = commit(repo)
    assert run_scope(repo, other, head)[1]["application"] is True
    assert run_scope(repo, other, head, mode="vercel")[0] == 1


def test_no_change_same_revision_redeploy_is_not_suppressed(history):
    repo, sha = history
    assert run_scope(repo, sha, sha, mode="vercel")[0] == 1


@pytest.mark.parametrize("force", ["1", "0", "true", ""])
def test_explicit_environment_redeploy_can_force_a_newer_docs_revision(history, force):
    repo, base = history
    (repo / "AGENTS.md").write_text("newer receipt\n")
    head = commit(repo)
    result = subprocess.run(
        ["node", str(HELPER), "vercel"],
        cwd=repo,
        env={
            **os.environ,
            "VERCEL_GIT_PREVIOUS_SHA": base,
            "VERCEL_GIT_COMMIT_SHA": head,
            "NBATOOLS_FORCE_BUILD": force,
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == (1 if force == "1" else 0)
    assert json.loads(result.stdout)["deploy"] is (force == "1")


@pytest.mark.parametrize("event", ["schedule", "workflow_dispatch", "unknown"])
def test_nightly_manual_and_unknown_events_keep_full_backstop(history, event):
    repo, base = history
    (repo / "AGENTS.md").write_text("receipt\n")
    head = commit(repo)
    assert run_scope(repo, base, head, event=event)[1]["application"] is True


@pytest.mark.parametrize("kind", ["delete", "rename", "symlink", "executable"])
def test_build_input_deletion_rename_and_nonregular_docs_remain_conservative(history, kind):
    repo, base = history
    if kind in {"delete", "rename"}:
        if kind == "delete":
            (repo / "README.md").unlink()
        else:
            (repo / "README.md").replace(repo / "ROADMAP.md")
    elif kind == "symlink":
        (repo / "AGENTS.md").unlink()
        (repo / "AGENTS.md").symlink_to("README.md")
    else:
        (repo / "AGENTS.md").chmod(0o755)
    head = commit(repo)
    assert run_scope(repo, base, head)[1]["application"] is True
    assert run_scope(repo, base, head, mode="vercel")[0] == 1


def workflow():
    return yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)


def test_scope_failure_cannot_skip_app_checks_or_pass_ci():
    jobs = workflow()["jobs"]
    scope = jobs["change-scope"]
    assert "if" not in scope and "continue-on-error" not in scope
    for step in scope["steps"]:
        assert "continue-on-error" not in step and "if" not in step
        for suppressor in ("|| true", "|| exit 0", "; true", "set +e"):
            assert suppressor not in step.get("run", "")
    assert scope["outputs"]["application"] == "${{ steps.scope.outputs.application }}"
    assert scope["steps"][-1]["run"] == "node tools/delivery_scope.mjs ci"
    assert scope["steps"][-1]["env"] == {
        "SCOPE_BASE_SHA": "${{ github.event.pull_request.base.sha || github.event.before }}",
        "SCOPE_HEAD_SHA": "${{ github.event.pull_request.head.sha || github.sha }}",
    }
    policy = next(
        step
        for step in scope["steps"]
        if "pytest" in step.get("run", "") and "-m pytest" in step["run"]
    )
    assert "tests/test_delivery_scope.py" in policy["run"]
    assert "tests/test_ci_workflow_policy.py" in policy["run"]
    assert "tests/test_docs_governance.py" in policy["run"]
    for name in ("frontend-verify", "test-fast", "test-full"):
        assert jobs[name]["needs"] == "change-scope"
        assert jobs[name]["if"].startswith("always() && ")
        assert jobs[name]["if"].endswith("needs.change-scope.outputs.application != 'false'")
        assert "continue-on-error" not in jobs[name]


def test_selection_reports_nonexecution_instead_of_a_test_pass(history, tmp_path):
    repo, base = history
    (repo / "AGENTS.md").write_text("receipt\n")
    head = commit(repo)
    output, summary = tmp_path / "job-output", tmp_path / "summary"
    result = subprocess.run(
        ["node", str(HELPER), "ci"],
        cwd=repo,
        env={
            **os.environ,
            "GITHUB_EVENT_NAME": "pull_request",
            "SCOPE_BASE_SHA": base,
            "SCOPE_HEAD_SHA": head,
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(summary),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert output.read_text() == "application=false\n"
    assert "not selected" in summary.read_text()
    assert "not executed acceptance" in summary.read_text()


def test_broken_selection_command_fails_instead_of_emitting_false(history):
    repo, _ = history
    result = subprocess.run(
        ["node", str(HELPER), "misspelled-mode"], cwd=repo, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "application=false" not in result.stdout


def test_full_backstop_replaces_duplicate_fast_execution_without_narrowing_suite():
    jobs = workflow()["jobs"]
    gate = "needs.change-scope.outputs.application != 'false'"
    assert jobs["test-fast"]["if"] == f"always() && github.event_name == 'pull_request' && {gate}"
    assert jobs["test-full"]["if"] == f"always() && github.event_name != 'pull_request' && {gate}"
    for name, command in (("test-fast", "make test-unit"), ("test-full", "make test")):
        job = jobs[name]
        assert job["strategy"]["matrix"]["python-version"] == ["3.11", "3.12", "3.13"]
        assert {"run": command} in job["steps"]
        assert {"run": 'pip install -e ".[dev,api]"'} in job["steps"]
    makefile = (ROOT / "Makefile").read_text()
    assert 'test-unit:\n\t$(PYTEST) -m "not needs_data and not slow"' in makefile
    assert "test:\n\t$(PYTEST)" in makefile


def test_existing_deployment_suppression_and_build_inputs_are_preserved():
    config = json.loads((ROOT / "vercel.json").read_text())
    assert config["ignoreCommand"] == "node tools/delivery_scope.mjs vercel"
    assert config["git"]["deploymentEnabled"] == {
        "r2-validation/**": False,
        "codex/*-production-gate": False,
    }
    assert config["buildCommand"] == "npm --prefix frontend ci && npm --prefix frontend run build"
    assert config["outputDirectory"] == "src/nbatools/ui/dist"
    assert "working/" in (ROOT / ".vercelignore").read_text().splitlines()
    assert all("tests/**" in function["excludeFiles"] for function in config["functions"].values())


def test_no_workflow_path_filters_or_optional_governance():
    config = workflow()
    for event in ("push", "pull_request"):
        assert not ({"paths", "paths-ignore"} & config["on"][event].keys())
    for name in ("lint", "docs-governance"):
        assert "if" not in config["jobs"][name]
        assert "continue-on-error" not in config["jobs"][name]
