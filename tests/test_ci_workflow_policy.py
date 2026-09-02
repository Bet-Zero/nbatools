"""Governance for the CI contract that keeps two verdicts independent.

Frontend code verification and frontend dependency security must stay
separate jobs.  Before this guard existed, a single `frontend` job ran
`npm audit` ahead of build/lint/test, so one newly published upstream
advisory marked all three verification steps *skipped* and the repo
lost the ability to learn whether its own code was healthy.

These tests assert the policy rather than the formatting: they locate
jobs by the commands they run, so renaming a job or reordering steps
keeps them meaningful.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"

BUILD_CMD = "npm --prefix frontend run build"
LINT_CMD = "npm --prefix frontend run lint"
TEST_CMD = "npm --prefix frontend test"
AUDIT_FRAGMENT = "npm --prefix frontend audit"


def _workflow() -> dict:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _run_steps(job: dict) -> list[str]:
    return [step["run"] for step in job.get("steps", []) if "run" in step]


def _jobs_running(fragment: str) -> dict[str, dict]:
    jobs = _workflow()["jobs"]
    return {
        name: job for name, job in jobs.items() if any(fragment in run for run in _run_steps(job))
    }


def test_frontend_verification_job_never_runs_a_dependency_audit() -> None:
    """The core policy: build/lint/test cannot be gated by the audit.

    This is the assertion that fails against the pre-repair workflow,
    where one `frontend` job ran the audit before the build.
    """
    verify_jobs = _jobs_running(BUILD_CMD)
    assert verify_jobs, f"no CI job runs {BUILD_CMD!r}"

    for name, job in verify_jobs.items():
        runs = _run_steps(job)
        assert not any(AUDIT_FRAGMENT in run for run in runs), (
            f"job {name!r} runs both the frontend build and a dependency "
            "audit. An audit failure would mark build/lint/test skipped. "
            "Keep the audit in its own job."
        )


def test_frontend_verification_runs_build_lint_and_tests() -> None:
    verify_jobs = _jobs_running(BUILD_CMD)
    for name, job in verify_jobs.items():
        runs = _run_steps(job)
        for command in (BUILD_CMD, LINT_CMD, TEST_CMD):
            assert any(command in run for run in runs), (
                f"job {name!r} builds the frontend but never runs {command!r}"
            )


def _needs(job: dict) -> list[str]:
    needs = job.get("needs", [])
    return [needs] if isinstance(needs, str) else list(needs)


def test_frontend_verification_does_not_depend_on_the_security_job() -> None:
    """A red security verdict must not skip code verification."""
    audit_job_names = set(_jobs_running(AUDIT_FRAGMENT))
    for name, job in _jobs_running(BUILD_CMD).items():
        overlap = set(_needs(job)) & audit_job_names
        assert not overlap, (
            f"job {name!r} declares needs={sorted(overlap)}; a failing audit "
            "would skip frontend verification"
        )


def test_security_job_does_not_depend_on_the_verification_job() -> None:
    """The independence runs both ways.

    If the audit job waited on verification, a broken build would skip
    the security verdict and a dependency-changing PR could merge
    without one.
    """
    verify_job_names = set(_jobs_running(BUILD_CMD))
    for name, job in _jobs_running(AUDIT_FRAGMENT).items():
        overlap = set(_needs(job)) & verify_job_names
        assert not overlap, (
            f"audit job {name!r} declares needs={sorted(overlap)}; a failing "
            "build would skip the dependency-security verdict"
        )


def test_dependency_audit_still_exists_and_blocks() -> None:
    audit_jobs = _jobs_running(AUDIT_FRAGMENT)
    assert audit_jobs, (
        "no CI job runs a frontend dependency audit; the security verdict "
        "was removed rather than separated"
    )

    for name, job in audit_jobs.items():
        assert job.get("continue-on-error") in (None, "false"), (
            f"audit job {name!r} sets continue-on-error; the security check "
            "must be able to fail the build"
        )
        for step in job.get("steps", []):
            if AUDIT_FRAGMENT in step.get("run", ""):
                assert step.get("continue-on-error") in (None, "false"), (
                    f"audit step in {name!r} sets continue-on-error"
                )


def test_dependency_audit_keeps_at_least_audit_level_low() -> None:
    """`low` is the weakest threshold allowed; nothing may relax it."""
    audit_runs = [
        run
        for job in _jobs_running(AUDIT_FRAGMENT).values()
        for run in _run_steps(job)
        if AUDIT_FRAGMENT in run
    ]
    assert audit_runs

    for run in audit_runs:
        assert "--audit-level=low" in run, (
            f"audit command {run!r} does not pin --audit-level=low; raising "
            "the threshold hides real advisories"
        )
        assert "--omit=dev" not in run, (
            f"audit command {run!r} omits dev dependencies to produce green"
        )
        assert "--production" not in run, (
            f"audit command {run!r} downgrades to a production-only audit"
        )


def test_dependency_audit_exit_code_is_not_suppressed() -> None:
    audit_runs = [
        run
        for job in _jobs_running(AUDIT_FRAGMENT).values()
        for run in _run_steps(job)
        if AUDIT_FRAGMENT in run
    ]
    assert audit_runs

    for run in audit_runs:
        for suppression in ("|| true", "|| exit 0", "; true", "set +e", "|| :"):
            assert suppression not in run, (
                f"audit command {run!r} suppresses its exit code with {suppression!r}"
            )
        assert "audit fix" not in run, (
            f"audit command {run!r} mutates the lockfile instead of reporting on it"
        )


def test_dependency_changing_pull_requests_cannot_bypass_the_audit() -> None:
    """The audit must run unconditionally on pull requests."""
    payload = _workflow()
    assert "pull_request" in payload["on"], "CI no longer runs on pull requests"

    for name, job in _jobs_running(AUDIT_FRAGMENT).items():
        assert "if" not in job, (
            f"audit job {name!r} is conditional ({job.get('if')!r}); a "
            "dependency-changing PR could skip the security verdict"
        )
        for step in job.get("steps", []):
            if AUDIT_FRAGMENT in step.get("run", ""):
                assert "if" not in step, (
                    f"audit step in {name!r} is conditional and could be skipped"
                )


def test_scheduled_security_signal_remains() -> None:
    """Advisories published after merge are caught by the nightly run."""
    payload = _workflow()
    schedule = payload["on"].get("schedule")
    assert schedule, (
        "the scheduled CI trigger was removed; advisories published after a "
        "lockfile is merged would go unnoticed"
    )
    assert any("cron" in entry for entry in schedule)

    for name, job in _jobs_running(AUDIT_FRAGMENT).items():
        assert "if" not in job, (
            f"audit job {name!r} is gated by an if-condition and may not run on the schedule"
        )
