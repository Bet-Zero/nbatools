"""Governance for the workflow that validates against the real R2 generation.

`.github/workflows/r2-real-data-validation.yml` is the only GitHub Actions path
that receives the bucket-scoped read-only NBA data credential, and the only
automated place the Raw QA corpus and the filter execution sweep run at all.
Before it existed they were local-only, on one machine, undated and unretained.

Four properties keep it working, and none is visible in a diff:

1. **Every job declares its environment.** The credential lives on the
   `r2-validation` GitHub Environment, deliberately, so ordinary CI stays
   secret-free. An environment secret reaches only a job that names that
   environment, so a job without the declaration receives three empty strings
   and fails as though the data were gone.
2. **Every gate judges one pinned generation.** The preflight resolves a single
   immutable generation and the gates pin it. Resolved independently, a
   publication landing mid-run leaves one gate judging data another never saw.
3. **It cannot drift from the engine.** The secrets are named for their purpose
   and mapped onto the variable names the engine requires.
4. **Its credential check cannot leak.** The check is handed all three values in
   order to test them for emptiness, so "it reports names only" is asserted
   against a canary rather than assumed.

A fifth is about this repository's own history: there must be exactly one of
these workflows. A second was once added that duplicated this job against
*repository* secrets, which do not exist; it failed repeatedly and the failures
were read as a credential problem rather than as a duplicate reading the wrong
place. `test_exactly_one_workflow_reads_the_r2_credential` exists so that cannot
recur.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
WORKFLOW = WORKFLOWS / "r2-real-data-validation.yml"

# The GitHub Environment holding the credential. Named here because dropping it
# from a job is silent: the job runs and every secret is empty.
ENVIRONMENT = "r2-validation"

# The engine's variable name -> the environment secret that feeds it.
#
# These differ on purpose. The variable names are fixed by the engine
# (REQUIRED_R2_ENV_VARS). The secret names carry VALIDATION because this
# credential is read-only and must not be confused with the operator's
# write-scoped publication credential.
#
# R2_BUCKET_NAME is the engine's fourth required variable but is not secret --
# it is already committed in vercel.json -- so it is set in plain sight.
SECRET_SOURCES = {
    "R2_ACCOUNT_ID": "R2_VALIDATION_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID": "R2_VALIDATION_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY": "R2_VALIDATION_SECRET_ACCESS_KEY",
}
SECRET_ENV_VARS = tuple(SECRET_SOURCES)

# The job that verifies the credential and pins the generation every other job
# reads, so that all gates judge the same immutable data.
PREFLIGHT_JOB = "preflight"

# Jobs whose outcome is the verdict. A pass here is load-bearing.
GATE_JOBS = ("raw-qa", "filter-sweep")

# Informational: no prior green run to regress from.
ADVISORY_JOBS = ("data-backed-tests",)

# Pins one generation for the whole run. The engine honours it over the live
# pointer -- see `_resolve_active_data_generation` in data_source.
GENERATION_ENV = "NBATOOLS_DATA_GENERATION"

SUPPRESSORS = ("|| true", "|| exit 0", "; true", "set +e", "|| :")

CANARY = "CANARY-7f3a9e2b-must-never-be-printed"


def _workflow() -> dict:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _jobs() -> dict[str, dict]:
    return _workflow()["jobs"]


def _job(name: str) -> dict:
    jobs = _jobs()
    assert name in jobs, f"expected a job named {name!r}, found {sorted(jobs)}"
    return jobs[name]


def _steps(job_name: str) -> list[dict]:
    return _job(job_name).get("steps", [])


def _needs(job: dict) -> list[str]:
    needs = job.get("needs")
    if isinstance(needs, str):
        return [needs]
    return needs or []


def _credential_check_script() -> str:
    """The Python the credential-verification step actually runs."""
    runs = [
        step["run"]
        for step in _steps(PREFLIGHT_JOB)
        if "run" in step and "missing" in step["run"] and "required" in step["run"]
    ]
    assert len(runs) == 1, (
        "could not find the credential-verification step. Update this test to "
        "locate whatever replaced it rather than deleting it -- the leak and "
        "naming assertions below are the point."
    )
    body = runs[0].split("python - <<'PY'", 1)[1]
    lines: list[str] = []
    for line in body.splitlines():
        if line.strip() == "PY":
            break
        lines.append(line.removeprefix("          "))
    return "\n".join(lines)


def _run_credential_check(secrets: dict[str, str], tmp_path: Path):
    """Run the credential check against synthetic secrets.

    The real script imports nbatools and reaches R2 once the secrets are
    present, so only the missing-secret path is exercised here. That is the path
    that reports names, and so the only one that could leak one.
    """
    output = tmp_path / "github_output"
    output.touch()
    env = {key: value for key, value in os.environ.items() if key not in SECRET_ENV_VARS}
    return subprocess.run(
        [sys.executable, "-"],
        input=_credential_check_script(),
        capture_output=True,
        text=True,
        env={**env, **secrets, "GITHUB_OUTPUT": str(output)},
    ), output


# ── Every job must reach the credential ───────────────────────────────


def test_every_job_declares_the_environment_holding_the_credential() -> None:
    """Without this, all three secrets resolve to empty and nothing says why.

    The credential is an *environment* secret by design, so that ordinary CI
    stays secret-free and the values reach only the jobs that name it. An
    environment secret reaches only a job declaring that environment, so
    omitting it does not fail loudly -- the job runs, every secret is empty, and
    the failure looks like missing data.

    Asserted per job because the gates run in parallel: a new job added without
    the declaration is the easy mistake, and its symptom is indistinguishable
    from a real data failure.
    """
    for name, job in _jobs().items():
        assert job.get("environment") == ENVIRONMENT, (
            f"job {name!r} must declare `environment: {ENVIRONMENT}`; it has "
            f"{job.get('environment')!r}. The R2 credential lives on that "
            f"environment and a job that does not name it receives nothing."
        )


def test_exactly_one_workflow_reads_the_r2_credential() -> None:
    """Two workflows reading this credential is how it got misdiagnosed.

    A second workflow was added that duplicated this job against *repository*
    secrets of the same purpose, which were never created. It failed on every
    run, and the failures were read as a broken credential rather than as a
    duplicate looking in the wrong place -- costing several rounds before the two
    files were compared.

    One workflow owns this credential. A second copy is a defect even when it
    works, because the two drift and the failure blames the credential.
    """
    readers = sorted(
        path.name
        for path in WORKFLOWS.glob("*.yml")
        if any(secret in path.read_text(encoding="utf-8") for secret in SECRET_SOURCES.values())
    )
    assert readers == [WORKFLOW.name], (
        f"these workflows all read the R2 validation credential: {readers}. "
        f"Exactly one may. Consolidate into {WORKFLOW.name} rather than keeping "
        f"a second copy in step with it by hand."
    )


# ── The credential check cannot leak ──────────────────────────────────


@pytest.mark.parametrize(
    "absent",
    [pytest.param(name, id=f"absent-{name.lower()}") for name in SECRET_ENV_VARS],
)
def test_credential_check_never_prints_a_secret_value(absent: str, tmp_path: Path) -> None:
    """The step is handed every value; it may report only names.

    One scenario per secret, each with that secret absent and the other two
    carrying canaries, so every secret is populated on the failure path in some
    scenario. Without that breadth a step printing a value went undetected,
    because the only failing scenarios had nothing populated left to leak.
    """
    secrets = {name: f"{CANARY}-{name}" for name in SECRET_ENV_VARS if name != absent}
    result, output = _run_credential_check(secrets, tmp_path)

    emitted = result.stdout + result.stderr + output.read_text(encoding="utf-8")
    assert CANARY not in emitted, (
        f"the credential check emitted a secret value. It may report names only.\n{emitted}"
    )


@pytest.mark.parametrize(
    "absent",
    [pytest.param(name, id=f"absent-{name.lower()}") for name in SECRET_ENV_VARS],
)
def test_credential_check_fails_and_names_what_is_missing(absent: str, tmp_path: Path) -> None:
    secrets = {name: f"{CANARY}-{name}" for name in SECRET_ENV_VARS if name != absent}
    result, _output = _run_credential_check(secrets, tmp_path)

    assert result.returncode != 0, "a missing credential must fail the step"
    assert absent in result.stdout + result.stderr, (
        f"the failure does not name {absent}, so it does not say what to fix"
    )


def test_credential_check_rejects_an_empty_secret(tmp_path: Path) -> None:
    """An empty secret is absent, not present.

    A secret saved with an empty value, and an environment secret that never
    reached the job, both arrive as the empty string. A membership check would
    pass them and fail opaquely in Raw QA minutes later instead.
    """
    secrets = {name: f"{CANARY}-{name}" for name in SECRET_ENV_VARS}
    secrets["R2_SECRET_ACCESS_KEY"] = ""
    result, _output = _run_credential_check(secrets, tmp_path)

    assert result.returncode != 0
    assert "R2_SECRET_ACCESS_KEY" in result.stdout + result.stderr


def test_the_credential_failure_names_the_environment() -> None:
    """The likeliest cause is a job missing `environment:`, so say so.

    Three empty secrets at once points at the declaration rather than at three
    deleted secrets, and the failure is the only place anyone will look.
    """
    script = _credential_check_script()
    assert ENVIRONMENT in script, (
        f"the credential failure must mention the {ENVIRONMENT!r} environment; "
        f"without it the likeliest cause goes unnamed."
    )


def test_the_workflow_never_enumerates_the_secrets_context() -> None:
    """`toJSON(secrets)` gets every run held for manual approval.

    A previous workflow in this repository read `toJSON(secrets)` so it could
    report which secret names existed -- a strictly better diagnosis. Every run
    of it came back `action_required` with zero jobs created, so the diagnosis
    never ran and the workflow was worth less than before. Enumerating the whole
    secrets context is the shape of an exfiltration attempt; naming each secret
    individually is not.

    Comment lines are excluded, because explaining this in prose would otherwise
    make the test its own first offender.
    """
    live = "\n".join(
        line
        for line in WORKFLOW.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "toJSON(secrets)" not in live, (
        "the workflow enumerates the secrets context. Every run will be held "
        "for manual approval with no job created, so nothing it reports can be "
        "read. Reference each secret by name instead."
    )


# ── The workflow cannot drift from the engine ─────────────────────────


def test_every_job_maps_exactly_the_secrets_the_engine_requires() -> None:
    """Renaming the engine's R2 variables must break this test, not a QA run.

    `data_source` raises `DataSourceConfigError` naming whatever it requires. If
    a job still supplies the old variable names it fails minutes in with a
    configuration error, which reads as broken data rather than broken wiring.
    """
    from nbatools.data_source import REQUIRED_R2_ENV_VARS

    secret_backed = set(REQUIRED_R2_ENV_VARS) - {"R2_BUCKET_NAME"}
    assert secret_backed == set(SECRET_ENV_VARS), (
        f"the engine now requires {sorted(REQUIRED_R2_ENV_VARS)}. Update the "
        f"workflow's env blocks and SECRET_SOURCES here together."
    )

    for name, job in _jobs().items():
        env = job.get("env", {})
        for variable, secret in SECRET_SOURCES.items():
            assert env.get(variable) == f"${{{{ secrets.{secret} }}}}", (
                f"job {name!r}: {variable} must be supplied from "
                f"secrets.{secret}; it is {env.get(variable)!r}."
            )

    top = _workflow()["env"]
    assert top.get("R2_BUCKET_NAME"), (
        "R2_BUCKET_NAME is required by the engine and is not secret; the "
        "workflow must keep setting it."
    )
    assert top.get("DATA_SOURCE") == "r2", (
        "without DATA_SOURCE=r2 every job reads the local filesystem, finds "
        "nothing, and skips every data-backed assertion while passing."
    )


def test_every_gate_judges_the_one_pinned_generation() -> None:
    """All gates must judge the same immutable data, or they are incomparable.

    The preflight resolves one generation and exports it; each job pins it via
    `NBATOOLS_DATA_GENERATION`, which the engine honours over the live pointer.
    Without that, a publication landing mid-run leaves one gate judging a
    generation another never saw, and the disagreement reads as an engine bug
    rather than as a moving dataset.
    """
    outputs = _job(PREFLIGHT_JOB).get("outputs", {})
    assert "generation" in outputs, (
        f"{PREFLIGHT_JOB} must expose the pinned generation as an output; it has {sorted(outputs)}."
    )

    expected = f"${{{{ needs.{PREFLIGHT_JOB}.outputs.generation }}}}"
    for name, job in _jobs().items():
        if name == PREFLIGHT_JOB:
            continue
        pinned = job.get("env", {}).get(GENERATION_ENV)
        assert pinned == expected, (
            f"job {name!r} must pin {GENERATION_ENV} from "
            f"needs.{PREFLIGHT_JOB}.outputs.generation; it has {pinned!r}. "
            f"Resolving the generation independently makes the gates judge "
            f"possibly different data."
        )


# ── The gates stay gates ──────────────────────────────────────────────


@pytest.mark.parametrize("job_name", GATE_JOBS)
def test_the_validation_gates_cannot_be_made_advisory(job_name: str) -> None:
    """These two jobs are the verdict; an advisory verdict is not one.

    The sweep exits 2 on NO_SIGNAL -- nothing was comparable -- which is
    explicitly not a pass. Letting either job continue on error would turn a
    wrong answer into a green run.
    """
    job = _job(job_name)
    assert job.get("continue-on-error", "false") == "false", (
        f"{job_name} must fail the workflow. It exists to answer whether the "
        f"answers are correct, and an advisory answer to that is not an answer."
    )
    # The only allowed condition is the targeted scope: a full run executes
    # every gate, and only a targeted run that names nothing for a gate skips it.
    condition = job.get("if")
    if condition is not None:
        assert condition.startswith("inputs.scope == 'full'"), (
            f"{job_name} may be skipped only outside the full scope; it has {condition!r}"
        )

    for step in _steps(job_name):
        run = step.get("run", "")
        for suppressor in SUPPRESSORS:
            assert suppressor not in run, (
                f"{job_name} suppresses a non-zero exit with {suppressor!r}, "
                f"hiding the failure the job exists to surface."
            )


def test_which_jobs_may_fail_the_workflow_is_a_deliberate_choice() -> None:
    """The gates must not quietly become informational, nor the reverse.

    Recorded explicitly so the split between verdict and signal is a decision in
    the tests rather than an accident of which jobs happen to carry
    `continue-on-error`.
    """
    advisory = {name for name, job in _jobs().items() if job.get("continue-on-error") == "true"}
    assert advisory == set(ADVISORY_JOBS), (
        f"jobs marked advisory are {sorted(advisory)}, expected "
        f"{sorted(ADVISORY_JOBS)}. Changing which jobs can fail the workflow is "
        f"a deliberate decision, not a formatting one."
    )


def test_every_data_job_waits_for_the_credential_check() -> None:
    """Otherwise a missing credential surfaces as several opaque failures at once.

    The preflight exists to fail fast and say what is wrong; a job that does not
    wait for it reports the symptom in parallel with the diagnosis.
    """
    for name, job in _jobs().items():
        if name == PREFLIGHT_JOB:
            continue
        assert PREFLIGHT_JOB in _needs(job), (
            f"job {name!r} does not wait for {PREFLIGHT_JOB!r}, so a missing "
            f"credential surfaces as an opaque failure beside the diagnosis."
        )


@pytest.mark.parametrize("job_name", GATE_JOBS)
def test_evidence_is_uploaded_even_when_a_gate_fails(job_name: str) -> None:
    """A failing run with no evidence cannot be diagnosed afterwards."""
    uploads = [s for s in _steps(job_name) if "upload-artifact" in str(s.get("uses", ""))]
    assert uploads, f"{job_name} must upload its validation evidence"
    for step in uploads:
        assert step.get("if") == "always()", (
            f"{job_name} uploads evidence only on success, so a failure leaves "
            f"nothing to diagnose it with"
        )


def test_the_gates_run_in_parallel_rather_than_in_sequence() -> None:
    """Run 1 timed out because they were sequential steps in one job.

    Raw QA took 42m30s of a 45-minute budget, so the filter execution sweep was
    cancelled at pair 54 of 521 and the data-backed tests never started.
    Sequencing also buried the sweep -- the highest-value trust check here --
    behind 43 minutes of Raw QA.

    Making either gate wait on the other reintroduces both problems.
    """
    for job_name in GATE_JOBS:
        others = [other for other in GATE_JOBS if other != job_name]
        depends = _needs(_job(job_name))
        for other in others:
            assert other not in depends, (
                f"{job_name} waits for {other}, so they run in sequence again. "
                f"The gates are independent and must run in parallel; the only "
                f"shared dependency is {PREFLIGHT_JOB}."
            )


@pytest.mark.parametrize("job_name", GATE_JOBS)
def test_each_gate_has_a_timeout_that_fits_its_measured_runtime(job_name: str) -> None:
    """A gate that times out reports nothing, which is worse than failing.

    Measured on run 1: Raw QA 42m30s for 361 cases; the sweep roughly 0.75s per
    pair across 521 pairs. The floors below leave headroom for a growing corpus
    and a slow runner.
    """
    floors = {"raw-qa": 60, "filter-sweep": 20}
    timeout = int(_job(job_name)["timeout-minutes"])
    assert timeout >= floors[job_name], (
        f"{job_name} allows {timeout} minutes; run 1 measured a runtime needing "
        f"at least {floors[job_name]}. A timeout here produces no verdict at all."
    )


def test_the_workflow_does_not_expose_the_credential_to_pull_requests() -> None:
    """`pull_request` would release the credential to fork PRs.

    Manual dispatch is deliberate: this is the only Actions path that receives
    the credential, and ordinary CI stays secret-free.
    """
    triggers = _workflow()["on"]
    assert "pull_request" not in triggers
    assert "pull_request_target" not in triggers
    assert "workflow_dispatch" in triggers, "on-demand runs must stay possible"


def test_the_workflow_only_reads() -> None:
    """A validation run must not be able to publish a generation."""
    assert _workflow()["permissions"] == {"contents": "read"}


def test_a_targeted_run_is_labelled_as_one() -> None:
    """A green targeted run is not a full validation, and must not read as one."""
    workflow = _workflow()
    inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    assert inputs["scope"]["default"] == "full"
    assert inputs["scope"]["options"] == ["full", "targeted"]
    assert "${{ inputs.scope }}" in workflow["run-name"]


def _run_targeted_test_selection(tests: str) -> subprocess.CompletedProcess:
    """Run the needs_data step's own script, with pytest replaced by echo."""
    step = next(s for s in _steps("data-backed-tests") if "needs_data" in s.get("name", ""))
    script = step["run"].replace("python -m pytest", "echo pytest")
    return subprocess.run(
        ["bash", "-e", "-c", script],
        env={"PATH": os.environ["PATH"], "SCOPE": "targeted", "TESTS": tests},
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "test_id",
    [
        "tests/test_explicit_date_ranges_real_data.py",
        "tests/test_leaderboard_metric_boundary.py::test_case[total-rebounds]",
    ],
)
def test_a_targeted_run_accepts_real_test_paths(test_id: str) -> None:
    result = _run_targeted_test_selection(test_id)
    assert result.returncode == 0, result.stderr
    assert test_id in result.stdout


@pytest.mark.parametrize("test_id", ["tests/../secrets.py", "tests/x.py;env", "qa/run.py", "-k"])
def test_a_targeted_run_rejects_other_arguments(test_id: str) -> None:
    result = _run_targeted_test_selection(test_id)
    assert result.returncode != 0
    assert "Invalid test path" in result.stderr
