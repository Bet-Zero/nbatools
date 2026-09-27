"""Governance for the CI contract that keeps two verdicts independent.

Frontend code verification and frontend dependency security must stay
separate jobs.  Before this guard existed, a single `frontend` job ran
`npm audit` ahead of build/lint/test, so one newly published upstream
advisory marked all three verification steps *skipped* and the repo
lost the ability to learn whether its own code was healthy.

These tests assert the policy rather than the formatting: they locate
jobs by the commands they run, so renaming a job or reordering steps
keeps them meaningful.  They cover the ordinary regression paths -- a
dropped locked install, a condition or `continue-on-error` that turns a
required command into an optional one, a weakened audit, a removed
trigger.  They deliberately do not try to defeat deceptive shell
wrappers, decoy job chains, or matrix-expression tricks; that would be a
general workflow-security framework, which this repo does not need.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"

INSTALL_CMD = "npm --prefix frontend ci"
BUILD_CMD = "npm --prefix frontend run build"
LINT_CMD = "npm --prefix frontend run lint"
TEST_CMD = "npm --prefix frontend test"
AUDIT_FRAGMENT = "npm --prefix frontend audit"

# CI-SEC-01 splits the audit into two verdicts. Only one may block.
#
# The blocking audit is production-scoped: an advisory in a dependency that
# reaches a visitor's browser is reachable by real users, so it stays strict.
# The advisory audit covers the whole tree including development dependencies,
# which never reach a visitor; it reports but cannot fail the workflow.
#
# Both are pinned here. Making the production audit non-blocking, dropping the
# dev-tree audit, or narrowing it to production as well are all regressions.
PRODUCTION_SCOPE_FLAG = "--omit=dev"
BLOCKING_AUDIT_FRAGMENT = f"{AUDIT_FRAGMENT} {PRODUCTION_SCOPE_FLAG}"

VERIFY_COMMANDS = (BUILD_CMD, LINT_CMD, TEST_CMD)

# Installs that can resolve versions the committed lockfile does not pin.
MUTABLE_INSTALLS = (
    "npm install",
    "npm --prefix frontend install",
    "npm update",
    "npm --prefix frontend update",
    "npm audit fix",
    "npm --prefix frontend audit fix",
)

# Ways a shell command can hide a non-zero exit status.
SUPPRESSORS = ("|| true", "|| exit 0", "; true", "set +e", "|| :")


def _workflow() -> dict:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _steps(job: dict) -> list[dict]:
    return job.get("steps", [])


def _run_steps(job: dict) -> list[str]:
    return [step["run"] for step in _steps(job) if "run" in step]


def _jobs_running(fragment: str) -> dict[str, dict]:
    jobs = _workflow()["jobs"]
    return {
        name: job for name, job in jobs.items() if any(fragment in run for run in _run_steps(job))
    }


def _needs(job: dict) -> list[str]:
    needs = job.get("needs", [])
    return [needs] if isinstance(needs, str) else list(needs)


def _first_index(job: dict, fragment: str) -> int:
    """Position of the first run step containing `fragment`, or -1."""
    for index, run in enumerate(_run_steps(job)):
        if fragment in run:
            return index
    return -1


def _steps_running(job: dict, fragment: str) -> list[dict]:
    return [step for step in _steps(job) if fragment in step.get("run", "")]


def _blocking_audit_jobs() -> dict[str, dict]:
    """Jobs running the production-scoped audit — the one allowed to block."""
    return _jobs_running(BLOCKING_AUDIT_FRAGMENT)


def _advisory_audit_jobs() -> dict[str, dict]:
    """Jobs running a whole-tree audit — informational, dev deps included."""
    return {
        name: job
        for name, job in _jobs_running(AUDIT_FRAGMENT).items()
        if name not in _blocking_audit_jobs()
    }


def _audit_runs(jobs: dict[str, dict]) -> list[str]:
    return [run for job in jobs.values() for run in _run_steps(job) if AUDIT_FRAGMENT in run]


def _is_blocking(job: dict) -> bool:
    """A job blocks the workflow unless it declares continue-on-error."""
    return job.get("continue-on-error") in (None, "false", False)


def _assert_not_continue_on_error(container: dict, label: str) -> None:
    value = container.get("continue-on-error")
    assert value in (None, "false", False), (
        f"{label} sets continue-on-error={value!r}; a failing command would still report success"
    )


def _assert_unconditional(container: dict, label: str) -> None:
    assert "if" not in container, (
        f"{label} is gated by if={container.get('if')!r}; it could be silently "
        "skipped instead of reporting a verdict"
    )


# ── A. Locked installation is mandatory ──────────────────────────────


def test_verification_installs_exactly_once_from_the_committed_lockfile() -> None:
    verify_jobs = _jobs_running(BUILD_CMD)
    assert verify_jobs, f"no CI job runs {BUILD_CMD!r}"

    for name, job in verify_jobs.items():
        installs = [run for run in _run_steps(job) if INSTALL_CMD in run]
        assert len(installs) == 1, (
            f"job {name!r} runs {len(installs)} {INSTALL_CMD!r} steps; frontend "
            "verification must install exactly once from the committed lockfile"
        )


def test_verification_install_runs_before_build_lint_and_test() -> None:
    for name, job in _jobs_running(BUILD_CMD).items():
        install_at = _first_index(job, INSTALL_CMD)
        assert install_at >= 0, f"job {name!r} never runs {INSTALL_CMD!r}"
        for command in VERIFY_COMMANDS:
            command_at = _first_index(job, command)
            if command_at < 0:
                continue
            assert install_at < command_at, (
                f"job {name!r} runs {command!r} before {INSTALL_CMD!r}; the "
                "verified tree would not come from the committed lockfile"
            )


def test_security_installs_from_the_committed_lockfile_before_auditing() -> None:
    audit_jobs = _jobs_running(AUDIT_FRAGMENT)
    assert audit_jobs, "no CI job runs a frontend dependency audit"

    for name, job in audit_jobs.items():
        install_at = _first_index(job, INSTALL_CMD)
        audit_at = _first_index(job, AUDIT_FRAGMENT)
        assert install_at >= 0, (
            f"audit job {name!r} never runs {INSTALL_CMD!r}; it would not audit "
            "the tree the lockfile actually installs"
        )
        assert install_at < audit_at, (
            f"audit job {name!r} audits before installing; the audited tree "
            "would not be the installed one"
        )


def test_frontend_jobs_never_use_a_lockfile_mutating_install() -> None:
    """`npm install`/`update`/`audit fix` can drift from the lockfile."""
    jobs = {**_jobs_running(BUILD_CMD), **_jobs_running(AUDIT_FRAGMENT)}
    for name, job in jobs.items():
        for run in _run_steps(job):
            for mutable in MUTABLE_INSTALLS:
                assert mutable not in run, (
                    f"job {name!r} runs {run!r}, which uses {mutable!r} instead "
                    f"of the locked {INSTALL_CMD!r}"
                )


def test_frontend_install_steps_are_unconditional_and_failure_sensitive() -> None:
    jobs = {**_jobs_running(BUILD_CMD), **_jobs_running(AUDIT_FRAGMENT)}
    for name, job in jobs.items():
        for step in _steps_running(job, INSTALL_CMD):
            label = f"the {INSTALL_CMD!r} step in job {name!r}"
            _assert_unconditional(step, label)
            _assert_not_continue_on_error(step, label)
            for suppressor in SUPPRESSORS:
                assert suppressor not in step["run"], (
                    f"{label} suppresses its exit code with {suppressor!r}"
                )


# ── B. Frontend verification is unconditional ────────────────────────


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
        for command in VERIFY_COMMANDS:
            assert any(command in run for run in runs), (
                f"job {name!r} builds the frontend but never runs {command!r}"
            )


def test_frontend_verification_job_is_unconditional() -> None:
    """Verification must report a verdict on every supported trigger."""
    for name, job in _jobs_running(BUILD_CMD).items():
        label = f"frontend verification job {name!r}"
        _assert_unconditional(job, label)
        _assert_not_continue_on_error(job, label)
        assert not _needs(job), (
            f"{label} declares needs={_needs(job)}; another job's failure "
            "would skip frontend verification entirely"
        )


def test_frontend_verification_steps_are_unconditional_and_failure_sensitive() -> None:
    """No required verification command may be skipped or made optional."""
    required = (INSTALL_CMD, *VERIFY_COMMANDS)
    for name, job in _jobs_running(BUILD_CMD).items():
        for command in required:
            for step in _steps_running(job, command):
                label = f"the {command!r} step in job {name!r}"
                _assert_unconditional(step, label)
                _assert_not_continue_on_error(step, label)
                for suppressor in SUPPRESSORS:
                    assert suppressor not in step["run"], (
                        f"{label} suppresses its exit code with {suppressor!r}"
                    )


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


# ── C. Dependency security stays unconditional and strict ────────────


def test_dependency_audit_still_exists_and_blocks() -> None:
    """The production-scoped audit must exist and must be able to fail CI."""
    blocking = _blocking_audit_jobs()
    assert blocking, (
        "no CI job runs the production-scoped frontend dependency audit "
        f"({BLOCKING_AUDIT_FRAGMENT!r}); the blocking security verdict was "
        "removed rather than scoped"
    )

    for name, job in blocking.items():
        _assert_not_continue_on_error(job, f"audit job {name!r}")
        for step in _steps_running(job, AUDIT_FRAGMENT):
            _assert_not_continue_on_error(step, f"the audit step in job {name!r}")


def test_exactly_one_audit_verdict_can_block_the_workflow() -> None:
    """CI-SEC-01's core invariant: the blocking audit is the production one.

    Making the dev-tree audit blocking again reintroduces the recurring red;
    making the production audit non-blocking removes the only real gate.
    """
    blocking_names = sorted(
        name for name, job in _jobs_running(AUDIT_FRAGMENT).items() if _is_blocking(job)
    )
    assert blocking_names == sorted(_blocking_audit_jobs()), (
        f"jobs able to fail CI on an audit are {blocking_names}, but only the "
        f"production-scoped job(s) {sorted(_blocking_audit_jobs())} may block"
    )


def test_dev_tree_advisory_audit_still_runs_and_stays_whole_tree() -> None:
    """Scoping the gate must not stop dev advisories being reported at all."""
    advisory = _advisory_audit_jobs()
    assert advisory, (
        "no CI job audits the whole dependency tree any more; development "
        "advisories would go unreported rather than merely non-blocking"
    )

    for name, job in advisory.items():
        for run in _run_steps(job):
            if AUDIT_FRAGMENT not in run:
                continue
            assert PRODUCTION_SCOPE_FLAG not in run, (
                f"the advisory audit in job {name!r} runs {run!r}, which omits "
                "dev dependencies; nothing would report on them"
            )
            assert "--production" not in run, (
                f"the advisory audit in job {name!r} runs {run!r}, which "
                "downgrades to a production-only audit"
            )


def test_dependency_audit_keeps_at_least_audit_level_low() -> None:
    """`low` is the weakest threshold allowed, on both audits."""
    audit_runs = _audit_runs(_jobs_running(AUDIT_FRAGMENT))
    assert audit_runs

    for run in audit_runs:
        assert "--audit-level=low" in run, (
            f"audit command {run!r} does not pin --audit-level=low; raising "
            "the threshold hides real advisories"
        )


def test_blocking_audit_is_scoped_to_shipped_dependencies() -> None:
    """The gate covers what reaches a browser, and says so explicitly."""
    for name, job in _blocking_audit_jobs().items():
        runs = [run for run in _run_steps(job) if AUDIT_FRAGMENT in run]
        assert runs, f"blocking audit job {name!r} runs no audit command"
        for run in runs:
            assert PRODUCTION_SCOPE_FLAG in run, (
                f"the blocking audit in job {name!r} runs {run!r} without "
                f"{PRODUCTION_SCOPE_FLAG!r}; it would block on development "
                "advisories again"
            )


def test_dependency_audit_exit_code_is_not_suppressed() -> None:
    """Neither audit may hide its result in the shell.

    The advisory audit is non-blocking by declaring `continue-on-error` in the
    workflow, where this test can see it — not by swallowing an exit code.
    """
    audit_runs = _audit_runs(_jobs_running(AUDIT_FRAGMENT))
    assert audit_runs

    for run in audit_runs:
        for suppressor in SUPPRESSORS:
            assert suppressor not in run, (
                f"audit command {run!r} suppresses its exit code with {suppressor!r}"
            )
        assert "audit fix" not in run, (
            f"audit command {run!r} mutates the lockfile instead of reporting on it"
        )


def test_dependency_changing_pull_requests_cannot_bypass_the_audit() -> None:
    """The audit must run unconditionally on pull requests."""
    payload = _workflow()
    assert "pull_request" in payload["on"], "CI no longer runs on pull requests"

    for name, job in _jobs_running(AUDIT_FRAGMENT).items():
        _assert_unconditional(job, f"audit job {name!r}")
        for step in _steps_running(job, AUDIT_FRAGMENT):
            _assert_unconditional(step, f"the audit step in job {name!r}")


# ── D. Required workflow triggers remain ─────────────────────────────


def test_workflow_runs_on_pull_requests_and_pushes_targeting_main() -> None:
    triggers = _workflow()["on"]

    for event in ("pull_request", "push"):
        assert event in triggers, (
            f"the {event!r} trigger was removed; frontend verification and "
            "dependency security would stop running on it"
        )
        branches = (triggers[event] or {}).get("branches")
        assert branches and "main" in branches, (
            f"the {event!r} trigger targets {branches!r} rather than main; CI "
            "would no longer gate the default branch"
        )


def test_workflow_keeps_a_manual_dispatch_trigger() -> None:
    assert "workflow_dispatch" in _workflow()["on"], (
        "workflow_dispatch was removed; an advisory could no longer be "
        "re-checked on demand between scheduled runs"
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
        _assert_unconditional(job, f"audit job {name!r} (it may not run on the schedule)")
