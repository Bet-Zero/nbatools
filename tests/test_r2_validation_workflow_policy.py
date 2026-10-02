"""Governance for the workflow that validates against the real R2 generation.

`.github/workflows/r2-real-data-validation.yml` is the only GitHub Actions path
that receives the bucket-scoped read-only NBA data credential, and the only
automated place the Raw QA corpus and the filter execution sweep run at all.
Before it existed they were local-only, on one machine, undated and unretained.

Three properties keep it working, and none is visible in a diff:

1. **It declares its environment.** The credential lives on the `r2-validation`
   GitHub Environment, deliberately, so ordinary CI stays secret-free. An
   environment secret reaches only a job that names that environment, so
   dropping `environment:` makes all three secrets resolve to empty and the job
   fail as though the data were gone.
2. **It cannot drift from the engine.** The secrets are named for their purpose
   and mapped onto the variable names the engine requires. A rename on either
   side alone surfaces as an opaque `DataSourceConfigError`.
3. **Its credential check cannot leak.** The check is handed all three values in
   order to test them for emptiness, so "it only reports names" is asserted
   against a canary rather than assumed.

A fourth property is about this repository's own history: there must be exactly
one of these workflows. A second one was added that duplicated this job against
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
# from the workflow is silent: the job runs and every secret is empty.
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

# Steps whose outcome is the verdict. Both are `continue-on-error` so evidence
# uploads either way, which makes the gate step the only thing enforcing them.
GATED_STEP_IDS = ("raw_qa", "filter_sweep")

SUPPRESSORS = ("|| true", "|| exit 0", "; true", "set +e", "|| :")


def _workflow() -> dict:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _job() -> dict:
    jobs = _workflow()["jobs"]
    assert len(jobs) == 1, f"expected a single job, found {sorted(jobs)}"
    return next(iter(jobs.values()))


def _steps() -> list[dict]:
    return _job().get("steps", [])


def _step(step_id: str) -> dict:
    matches = [step for step in _steps() if step.get("id") == step_id]
    assert len(matches) == 1, f"expected exactly one step with id {step_id!r}"
    return matches[0]


def _step_index(predicate) -> int:
    for index, step in enumerate(_steps()):
        if predicate(step):
            return index
    return -1


def _credential_check_script() -> str:
    """The Python the credential-verification step actually runs."""
    runs = [
        step["run"]
        for step in _steps()
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

    The real script imports nbatools and talks to R2 once the secrets are
    present, so only the missing-secret path is exercised here; that is the path
    that reports names, and so the only one that could leak one.
    """
    env_file = tmp_path / "github_env"
    env_file.touch()
    env = {key: value for key, value in os.environ.items() if key not in SECRET_ENV_VARS}
    return subprocess.run(
        [sys.executable, "-"],
        input=_credential_check_script(),
        capture_output=True,
        text=True,
        env={**env, **secrets, "GITHUB_ENV": str(env_file)},
    ), env_file


CANARY = "CANARY-7f3a9e2b-must-never-be-printed"


# ── The environment must be declared ──────────────────────────────────


def test_the_job_declares_the_environment_holding_the_credential() -> None:
    """Without this, all three secrets resolve to empty and nothing says why.

    The credential is an *environment* secret by design, so that ordinary CI
    stays secret-free and the values are released only to this job. An
    environment secret reaches only a job that names that environment. Removing
    `environment:` therefore does not fail loudly -- the job runs, every secret
    is empty, and the failure looks like missing data.
    """
    job = _job()
    assert job.get("environment") == ENVIRONMENT, (
        f"the job must declare `environment: {ENVIRONMENT}`; it has "
        f"{job.get('environment')!r}. The R2 credential is stored on that "
        f"environment, and a job that does not name it receives nothing."
    )


def test_exactly_one_workflow_reads_the_r2_credential() -> None:
    """Two workflows reading this credential is how it got misdiagnosed.

    A second workflow was added that duplicated this job against *repository*
    secrets of the same purpose, which were never created. It failed on every
    run, and the failures were read as a broken credential rather than as a
    duplicate looking in the wrong place -- costing several rounds before anyone
    compared the two files.

    One job owns this credential. A second copy is a defect even when it works.
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
    scenario. Without that breadth a step that printed a value went undetected,
    because the only failing scenarios had nothing populated left to leak.
    """
    secrets = {name: f"{CANARY}-{name}" for name in SECRET_ENV_VARS if name != absent}
    result, env_file = _run_credential_check(secrets, tmp_path)

    emitted = result.stdout + result.stderr + env_file.read_text(encoding="utf-8")
    assert CANARY not in emitted, (
        f"the credential check emitted a secret value. It may report names only.\n{emitted}"
    )


@pytest.mark.parametrize(
    "absent",
    [pytest.param(name, id=f"absent-{name.lower()}") for name in SECRET_ENV_VARS],
)
def test_credential_check_fails_and_names_what_is_missing(absent: str, tmp_path: Path) -> None:
    secrets = {name: f"{CANARY}-{name}" for name in SECRET_ENV_VARS if name != absent}
    result, _env_file = _run_credential_check(secrets, tmp_path)

    assert result.returncode != 0, "a missing credential must fail the step"
    assert absent in result.stdout + result.stderr, (
        f"the failure does not name {absent}, so it does not say what to fix"
    )


def test_credential_check_rejects_an_empty_secret(tmp_path: Path) -> None:
    """An empty secret is absent, not present.

    A secret saved with an empty value, or an environment secret that never
    reached the job, both arrive as the empty string. A membership check would
    pass them and fail opaquely in Raw QA minutes later instead.
    """
    secrets = {name: f"{CANARY}-{name}" for name in SECRET_ENV_VARS}
    secrets["R2_SECRET_ACCESS_KEY"] = ""
    result, _env_file = _run_credential_check(secrets, tmp_path)

    assert result.returncode != 0
    assert "R2_SECRET_ACCESS_KEY" in result.stdout + result.stderr


def test_the_workflow_never_enumerates_the_secrets_context() -> None:
    """`toJSON(secrets)` gets every run held for manual approval.

    A previous version of a workflow in this repository read `toJSON(secrets)`
    so it could report which secret names existed -- a strictly better
    diagnosis. Every run of it came back `action_required` with zero jobs
    created, so the diagnosis never ran and the workflow was worth less than
    before. Enumerating the whole secrets context is the shape of an
    exfiltration attempt; naming each secret individually is not.

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


def test_the_job_maps_exactly_the_secrets_the_engine_requires() -> None:
    """Renaming the engine's R2 variables must break this test, not a QA run.

    `data_source` raises `DataSourceConfigError` naming whatever it requires. If
    the workflow still supplies the old variable names, the job fails minutes in
    with a configuration error, which reads as broken data rather than broken
    wiring.
    """
    from nbatools.data_source import REQUIRED_R2_ENV_VARS

    secret_backed = set(REQUIRED_R2_ENV_VARS) - {"R2_BUCKET_NAME"}
    assert secret_backed == set(SECRET_ENV_VARS), (
        f"the engine now requires {sorted(REQUIRED_R2_ENV_VARS)}. Update the "
        f"workflow's env block and SECRET_SOURCES here together."
    )

    env = _job()["env"]
    for variable, secret in SECRET_SOURCES.items():
        assert env.get(variable) == f"${{{{ secrets.{secret} }}}}", (
            f"{variable} must be supplied from secrets.{secret}; it is {env.get(variable)!r}."
        )
    assert env.get("R2_BUCKET_NAME"), (
        "R2_BUCKET_NAME is required by the engine and is not secret; the "
        "workflow must keep setting it."
    )
    assert env.get("DATA_SOURCE") == "r2", (
        "without DATA_SOURCE=r2 the job reads the local filesystem, finds "
        "nothing, and skips every data-backed assertion while passing."
    )


# ── The gates stay gates ──────────────────────────────────────────────


def test_both_validation_gates_are_enforced() -> None:
    """Raw QA and the sweep are `continue-on-error`, so a step must enforce them.

    They are allowed to continue only so the evidence artifact uploads on
    failure. That makes the final gate step the single thing standing between a
    wrong answer and a green check. The sweep's exit 2 means nothing was
    comparable, which is explicitly not a pass.
    """
    for step_id in GATED_STEP_IDS:
        assert _step(step_id).get("continue-on-error") == "true", (
            f"step {step_id!r} is expected to continue on error so evidence "
            f"uploads; if that changed, the gate below needs rechecking."
        )

    gate = [step for step in _steps() if "outcome" in step.get("run", "")]
    assert len(gate) == 1, "expected exactly one step enforcing the gated outcomes"
    run = gate[0]["run"]

    for step_id in GATED_STEP_IDS:
        assert f"steps.{step_id}.outcome" in run, (
            f"the gate does not read steps.{step_id}.outcome, so that step "
            f"cannot fail the workflow and its verdict is decorative."
        )
    assert "exit 1" in run, "the gate must fail the job, not merely report"
    assert gate[0].get("if") == "always()", (
        "the gate must run even when a gated step failed, or a failure skips "
        "the only thing that would have reported it"
    )
    for suppressor in SUPPRESSORS:
        assert suppressor not in run, f"the gate suppresses its own exit status with {suppressor!r}"


def test_the_credential_check_runs_before_anything_reads_data() -> None:
    """Otherwise a missing credential surfaces as an opaque mid-run failure."""
    check = _step_index(lambda s: "run" in s and "missing" in s["run"])
    raw_qa = _step_index(lambda s: s.get("id") == "raw_qa")
    assert 0 <= check < raw_qa, (
        "the credential check must precede Raw QA so a missing secret is named "
        "rather than surfacing as a DataSourceConfigError minutes in"
    )


def test_evidence_is_uploaded_even_when_a_gate_fails() -> None:
    """A failing run with no evidence cannot be diagnosed afterwards."""
    uploads = [s for s in _steps() if "upload-artifact" in str(s.get("uses", ""))]
    assert uploads, "the workflow must upload its validation evidence"
    for step in uploads:
        assert step.get("if") == "always()", (
            "evidence must upload on failure too; that is the only reason the "
            "gated steps are allowed to continue on error"
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
