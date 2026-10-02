"""Governance for the workflow that validates against the real R2 generation.

`.github/workflows/data-backed-validation.yml` is the only place the Raw QA
corpus and the filter execution sweep run automatically. Before it existed they
were local-only, on one machine, undated and unretained. Two properties keep it
worth having, and neither is visible in a diff:

1. **It cannot drift from the engine.** The workflow passes three secrets by
   name. The engine reads those same three names. If either side is renamed
   alone, the workflow fails several minutes into a Raw QA run with an opaque
   configuration error, and the obvious reading of that failure is "the data is
   broken" rather than "the wiring is."
2. **Its diagnostics cannot leak a credential.** The preflight reports which
   secret *names* exist, because "missing" has three causes with three different
   fixes and the owner cannot tell them apart otherwise. Names are not
   sensitive; values are. The step is handed every secret value in order to test
   them for emptiness, so "it only prints keys" has to be asserted, not assumed.

The tests run the preflight's own Python against synthetic secrets, so they
check the behaviour rather than the wording.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/data-backed-validation.yml"

# The secrets the workflow passes. R2_BUCKET_NAME is the engine's fourth
# required variable but is not secret -- it is already committed in vercel.json
# -- so the workflow sets it in plain sight and it is excluded here.
SECRET_ENV_VARS = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")

# Jobs that answer "are the answers correct". A pass here is load-bearing, so
# neither may be made advisory.
FAIL_CLOSED_JOBS = ("raw-qa", "filter-sweep")

SUPPRESSORS = ("|| true", "|| exit 0", "; true", "set +e", "|| :")


def _workflow() -> dict:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _jobs() -> dict[str, dict]:
    return _workflow()["jobs"]


def _steps(job: dict) -> list[dict]:
    return job.get("steps", [])


def _run_steps(job: dict) -> list[str]:
    return [step["run"] for step in _steps(job) if "run" in step]


def _preflight_check_step() -> dict:
    steps = [step for step in _steps(_jobs()["preflight"]) if step.get("id") == "check"]
    assert len(steps) == 1, "preflight must have exactly one step with id 'check'"
    return steps[0]


def _preflight_script() -> str:
    """The Python the preflight's secret check actually runs."""
    run = _preflight_check_step()["run"]
    opener = "python - <<'PY'"
    assert opener in run, (
        "the preflight secret check no longer runs an inline Python heredoc; "
        "update this test to extract whatever it runs instead, rather than "
        "deleting it -- the leak and diagnosis assertions below are the point."
    )
    body = run.split(opener, 1)[1]
    lines: list[str] = []
    for line in body.splitlines():
        if line.strip() == "PY":
            break
        lines.append(line.removeprefix("          "))
    return "\n".join(lines)


def _run_preflight(secrets: dict[str, str], variables: dict[str, str], tmp_path: Path):
    """Run the preflight check against synthetic secrets.

    `secrets` is passed the way the workflow passes it: one named environment
    variable per secret. The step no longer receives the secrets context as a
    whole -- see `test_preflight_never_enumerates_the_secrets_context`.
    """
    output = tmp_path / "github_output"
    output.touch()
    env = {key: value for key, value in os.environ.items() if key not in SECRET_ENV_VARS}
    return subprocess.run(
        [sys.executable, "-"],
        input=_preflight_script(),
        capture_output=True,
        text=True,
        env={
            **env,
            **secrets,
            "VARIABLES_JSON": json.dumps(variables),
            "GITHUB_OUTPUT": str(output),
        },
    ), output


def _cause(stdout: str) -> str:
    """The diagnosis line(s) only.

    Asserted separately from the rest of the output because the FIX text repeats
    much of the same vocabulary: a test that searches all of stdout passes even
    when the diagnosis itself has been gutted, which a mutation of exactly that
    line proved.
    """
    lines = [line.strip() for line in stdout.splitlines() if line.strip().startswith("CAUSE:")]
    assert len(lines) == 1, f"expected exactly one CAUSE line, got {lines}"
    return lines[0]


# A value distinctive enough that finding it in the output cannot be a
# coincidence, in each of the three secrets.
CANARY = "CANARY-7f3a9e2b-must-never-be-printed"
GOOD_SECRETS = {name: f"{CANARY}-{name}" for name in SECRET_ENV_VARS}


# ── The preflight never prints a value ────────────────────────────────


@pytest.mark.parametrize(
    "secrets,variables",
    [
        pytest.param(GOOD_SECRETS, {}, id="all-present"),
        pytest.param({}, {}, id="none-present"),
        pytest.param(
            {},
            {name: f"{CANARY}-{name}" for name in SECRET_ENV_VARS},
            id="saved-as-variables",
        ),
        # One scenario per secret, where that secret is the *absent* one and the
        # other two carry canaries. Without these the failure path only ever ran
        # with nothing populated to leak, so a mutation that printed a secret
        # value on that path went undetected.
        *[
            pytest.param(
                {k: v for k, v in GOOD_SECRETS.items() if k != absent},
                {},
                id=f"absent-{absent.lower()}",
            )
            for absent in SECRET_ENV_VARS
        ],
        # Same again for an empty value rather than an absent one.
        *[
            pytest.param(GOOD_SECRETS | {empty: ""}, {}, id=f"empty-{empty.lower()}")
            for empty in SECRET_ENV_VARS
        ],
    ],
)
def test_preflight_never_prints_a_secret_value(
    secrets: dict[str, str], variables: dict[str, str], tmp_path: Path
) -> None:
    """The step is handed every value; it may emit only names.

    This is asserted rather than assumed because the step needs the values to
    test them for emptiness. GitHub masks secrets in its own log rendering, but
    a preflight that relies on that masking is one `print(secrets)` away from
    putting a live R2 credential somewhere it cannot be recalled from.
    """
    result, output = _run_preflight(secrets, variables, tmp_path)

    emitted = result.stdout + result.stderr + output.read_text(encoding="utf-8")
    assert CANARY not in emitted, (
        f"the preflight emitted a secret value. It may report secret *names* only.\n{emitted}"
    )


# ── The preflight distinguishes the three causes ──────────────────────


def test_preflight_passes_when_all_three_secrets_are_present(tmp_path: Path) -> None:
    result, output = _run_preflight(GOOD_SECRETS, {}, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "configured=true" in output.read_text(encoding="utf-8")


def test_preflight_rejects_an_empty_secret(tmp_path: Path) -> None:
    """A secret created with an empty value is absent, not present.

    This is the exact state run #1 of this workflow found: GitHub resolved all
    three names to empty strings, so a membership check would have passed the
    preflight and failed opaquely in Raw QA instead.
    """
    secrets = GOOD_SECRETS | {"R2_SECRET_ACCESS_KEY": ""}
    result, _output = _run_preflight(secrets, {}, tmp_path)

    assert result.returncode == 1
    assert "R2_SECRET_ACCESS_KEY" in result.stdout


def test_preflight_names_the_variables_tab_when_secrets_were_saved_there(
    tmp_path: Path,
) -> None:
    variables = {name: f"{CANARY}-{name}" for name in SECRET_ENV_VARS}
    result, _output = _run_preflight({"github_token": "x"}, variables, tmp_path)

    assert result.returncode == 1
    assert "Variables tab" in _cause(result.stdout)


def test_preflight_names_every_wrong_place_when_the_secrets_resolve_to_nothing(
    tmp_path: Path,
) -> None:
    """Four places a secret can sit while looking perfectly saved.

    The step cannot tell them apart -- deliberately, since distinguishing them
    required enumerating the secrets context, which got every run of this
    workflow held for manual approval. So it offers all four instead:

    - the Codespaces or Dependabot tab, which a workflow does not read
    - an environment, which reaches only a job that declares it
    - a different name
    - another repository or a fork

    Reducing this to fewer suggestions is the regression to catch: all three
    secrets resolving empty at once is the signature of one wrong-place mistake
    rather than of three independent typos, so the breadth *is* the diagnosis.
    """
    result, _output = _run_preflight({}, {}, tmp_path)

    assert result.returncode == 1

    # Counted as numbered suggestions rather than searched for as words: the
    # surrounding prose repeats the same vocabulary, so a keyword search over
    # all of stdout passes with a suggestion deleted.
    suggestions = [
        line.strip() for line in result.stdout.splitlines() if re.match(r"^\s+\d\. ", line)
    ]
    assert len(suggestions) == 4, (
        f"expected four numbered wrong-place suggestions, got {len(suggestions)}: {suggestions}"
    )
    joined = " ".join(suggestions)
    for expected in ("Codespaces", "Dependabot", "Environment", "name", "repository"):
        assert expected in joined, (
            f"the diagnosis no longer mentions {expected!r}. All four wrong "
            f"places must stay offered; the owner cannot tell them apart from "
            f"the failure.\n{result.stdout}"
        )


def test_preflight_never_enumerates_the_secrets_context() -> None:
    """`toJSON(secrets)` gets every run of this workflow held for approval.

    This is not a style preference. The first version of this diagnosis read
    `toJSON(secrets)` so it could report which secret *names* existed -- a
    strictly better diagnosis. Every run of it came back `action_required`
    with zero jobs created, so the diagnosis never ran, and the workflow was
    worth less than before. Enumerating the whole secrets context is the shape
    of an exfiltration attempt; naming each secret individually is not.

    `toJSON(vars)` is fine: repository variables are not secret.
    """
    # Comment lines are excluded: the workflow explains in prose why it does
    # not do this, and that prose named the pattern, which made this test its
    # own first offender.
    live = "\n".join(
        line
        for line in WORKFLOW.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "toJSON(secrets)" not in live, (
        "the workflow enumerates the secrets context again. Every run of it "
        "will be held for manual approval and no job will be created, so the "
        "preflight that depends on it cannot report anything. Reference each "
        "secret by name instead."
    )
    assert "secrets.*" not in live


# ── The workflow cannot drift from the engine ─────────────────────────


def test_workflow_passes_exactly_the_secrets_the_engine_requires() -> None:
    """Renaming the engine's R2 variables must break this test, not a QA run.

    `data_source` raises `DataSourceConfigError` naming whatever it requires. If
    the workflow still passes the old names, every data-backed job fails minutes
    in with a configuration error, which reads as broken data rather than
    broken wiring.
    """
    from nbatools.data_source import REQUIRED_R2_ENV_VARS

    secret_vars = set(REQUIRED_R2_ENV_VARS) - {"R2_BUCKET_NAME"}
    assert secret_vars == set(SECRET_ENV_VARS), (
        f"the engine now requires {sorted(REQUIRED_R2_ENV_VARS)}. Update the "
        f"workflow's secret names and SECRET_ENV_VARS here together."
    )

    workflow = _workflow()
    assert workflow["env"]["R2_BUCKET_NAME"], (
        "R2_BUCKET_NAME is required by the engine and is not secret; the "
        "workflow must keep setting it."
    )


def test_every_data_reading_step_receives_all_three_secrets() -> None:
    """A step that reads data without the secrets fails opaquely.

    Adding a job here and forgetting its `env:` block is the easy mistake, and
    its symptom is indistinguishable from a real data failure.
    """
    for name, job in _jobs().items():
        for step in _steps(job):
            if "run" not in step:
                continue
            provided = set(step.get("env", {}))
            if not provided & set(SECRET_ENV_VARS):
                continue
            missing = sorted(set(SECRET_ENV_VARS) - provided)
            assert not missing, (
                f"job {name!r} step {step.get('name', step['run'][:40])!r} passes "
                f"some R2 secrets but not {missing}. The engine requires all of "
                f"them, so a partial set fails as though the data were missing."
            )


# ── The gates stay gates ──────────────────────────────────────────────


@pytest.mark.parametrize("job_name", FAIL_CLOSED_JOBS)
def test_fail_closed_jobs_cannot_be_made_advisory(job_name: str) -> None:
    """Raw QA and the sweep are the verdict; an advisory verdict is not one.

    The sweep exits 2 on NO_SIGNAL -- nothing was comparable -- which is
    explicitly not a pass. Letting either job continue on error would turn a
    wrong answer into a green check.
    """
    job = _jobs()[job_name]
    assert job.get("continue-on-error", "false") == "false", (
        f"{job_name} must fail the workflow. It exists to answer whether the "
        f"answers are correct; an advisory answer to that is not an answer."
    )
    assert "if" not in job, f"{job_name} must stay unconditional"

    for run in _run_steps(job):
        for suppressor in SUPPRESSORS:
            assert suppressor not in run, (
                f"{job_name} suppresses a non-zero exit with {suppressor!r}, "
                f"which hides the failure the job exists to surface."
            )


def test_every_job_waits_for_the_preflight() -> None:
    """Without this, a misconfigured secret produces four opaque failures.

    The preflight exists to fail fast and name the cause; a job that does not
    wait for it reports the symptom in parallel with the diagnosis.
    """
    for name, job in _jobs().items():
        if name == "preflight":
            continue
        assert "preflight" in job.get("needs", []), (
            f"job {name!r} does not wait for the preflight, so a missing secret "
            f"surfaces as an opaque mid-run failure alongside the diagnosis."
        )


def test_the_workflow_does_not_run_on_pull_requests() -> None:
    """Deliberate: `pull_request` would expose R2 credentials to fork PRs.

    It also costs a full read of the generation per push. `ci.yml` answers "is
    the code healthy" on every PR; this answers the slower question of whether
    the answers are right.
    """
    triggers = _workflow()["on"]
    assert "pull_request" not in triggers
    assert "pull_request_target" not in triggers
    assert "schedule" in triggers, "the nightly run is the point of the workflow"
    assert "workflow_dispatch" in triggers, "on-demand runs must stay possible"


def test_the_workflow_only_reads() -> None:
    """A validation run must not be able to publish a generation."""
    assert _workflow()["permissions"] == {"contents": "read"}
