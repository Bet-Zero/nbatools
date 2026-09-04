"""Exact-shape contract for the scheduled production monitor workflow.

These tests assert against the *parsed* workflow. Raw text matching cannot
tell an executable value from a comment, cannot see a second invocation
that overrides the first, and cannot see a whole extra job.

The contract is deliberately an exact shape rather than a general GitHub
Actions analysis: this workflow is tiny and fixed, so every level asserts
its exact key set. That is what makes the tests reject *unreviewed*
fields rather than only the specific attacks anyone happened to think of.
A monitor whose target and command are right is still worthless if the
job can be skipped, tolerated on failure, or run from a different
checkout, so failure sensitivity is asserted directly as well.

Adding anything to the workflow is expected to require editing this file
on purpose.
"""

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/production-monitor.yml"

STABLE_PRODUCTION_ALIAS = "https://nbatools.vercel.app"
TARGET_ENV_KEY = "PRODUCTION_MONITOR_BASE_URL"
MONITOR_ENTRYPOINT = "tools/production_monitor.py"
RETIRED_TARGET = "nbatools-fvdbt0pfv-brents-projects-686e97fc.vercel.app"

CANONICAL_MONITOR_COMMAND = f'python {MONITOR_ENTRYPOINT} --base-url "${TARGET_ENV_KEY}"'
MONITOR_STEP_NAME = "Run production monitor"
SYNTHETIC_STEP_NAME = "Trigger approved network-free notification failure"
SYNTHETIC_COMMAND_LINES = [
    r"""printf '%s\n' '{"kind":"production_monitor_synthetic_notification_test","""
    r""""network_requests_made":0,"ok":false}'""",
    "exit 1",
]

CHECKOUT_ACTION = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_PYTHON_ACTION = "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97"
APPROVED_ACTIONS = {CHECKOUT_ACTION, SETUP_PYTHON_ACTION}

# Exact parsed key sets. Anything outside these is an unreviewed change to
# executable policy, whether or not this file already names it.
TOP_LEVEL_KEYS = {"name", "on", "permissions", "concurrency", "jobs"}
JOB_KEYS = {"if", "runs-on", "timeout-minutes", "steps"}
ACTION_STEP_KEYS = {"uses", "with"}
MONITOR_STEP_KEYS = {"name", "env", "run"}
SYNTHETIC_STEP_KEYS = {"name", "run"}

# yaml.BaseLoader renders every scalar as a string, so booleans and numbers
# are compared against their string forms throughout.
NETWORK_COMMANDS = re.compile(r"\b(curl|wget|nc|ncat|telnet|ssh|scp|http|https)\b")


def _workflow() -> dict[str, Any]:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _steps(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [
        (job_name, step)
        for job_name, job in payload["jobs"].items()
        for step in job.get("steps", [])
    ]


def _run_steps(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [(job, step) for job, step in _steps(payload) if "run" in step]


def _monitor_steps(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [(job, step) for job, step in _run_steps(payload) if MONITOR_ENTRYPOINT in step["run"]]


def _env_scopes(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Every executable env mapping: workflow, job, and step scope."""

    scopes: list[tuple[str, dict[str, Any]]] = []
    if "env" in payload:
        scopes.append(("workflow", payload["env"]))
    for job_name, job in payload["jobs"].items():
        if "env" in job:
            scopes.append((f"job:{job_name}", job["env"]))
    for job_name, step in _steps(payload):
        if "env" in step:
            scopes.append((f"step:{job_name}:{step.get('name', '?')}", step["env"]))
    return scopes


def _normalized(command: str) -> str:
    """Collapse YAML folding and insignificant whitespace."""

    return " ".join(command.split())


def _command_lines(command: str) -> list[str]:
    """Executable lines, ignoring blank padding around a block scalar."""

    return [line.strip() for line in command.splitlines() if line.strip()]


def test_workflow_declares_exactly_the_approved_top_level_keys() -> None:
    """An exact key set rejects unreviewed policy fields such as `defaults`."""

    payload = _workflow()

    assert set(payload) == TOP_LEVEL_KEYS
    assert payload["name"] == "Production Monitor"
    assert payload["concurrency"] == {
        "group": "production-monitor",
        "cancel-in-progress": "false",
    }


def test_workflow_declares_exactly_the_approved_triggers() -> None:
    """Trigger policy is read from the parsed `on` mapping, not the text.

    A quoted `"push":` key is invisible to a raw-text search for `push:`.
    """

    payload = _workflow()

    assert set(payload["on"]) == {"schedule", "workflow_dispatch"}
    assert payload["on"]["schedule"] == [{"cron": "17 */2 * * *"}]

    inputs = payload["on"]["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"mode"}
    assert inputs["mode"]["type"] == "choice"
    assert inputs["mode"]["default"] == "probe"
    assert inputs["mode"]["options"] == ["probe", "synthetic-alert"]


def test_workflow_declares_exactly_read_only_permissions() -> None:
    """Permissions are read from the parsed mapping, not from a comment."""

    payload = _workflow()

    assert payload["permissions"] == {"contents": "read"}
    assert "write" not in str(payload["permissions"])


def test_workflow_declares_exactly_the_two_approved_jobs() -> None:
    """Two jobs, each with an exact key set. No third job, no `needs`."""

    payload = _workflow()

    assert list(payload["jobs"]) == ["monitor", "synthetic-alert"]
    for job_name, job in payload["jobs"].items():
        assert set(job) == JOB_KEYS, f"{job_name} declares unreviewed job fields"
        assert job["runs-on"] == "ubuntu-latest"

    monitor = payload["jobs"]["monitor"]
    synthetic = payload["jobs"]["synthetic-alert"]
    assert monitor["if"] == "${{ github.event_name == 'schedule' || inputs.mode == 'probe' }}"
    assert monitor["timeout-minutes"] == "3"
    assert synthetic["if"] == (
        "${{ github.event_name == 'workflow_dispatch' && inputs.mode == 'synthetic-alert' }}"
    )
    assert synthetic["timeout-minutes"] == "1"


def test_monitor_job_runs_exactly_the_three_approved_steps() -> None:
    """Checkout, setup-python, probe - each pinned to an exact shape.

    The checkout inputs matter as much as the command: a `ref` or
    `repository` input would run a different monitor implementation than
    the commit that triggered the workflow, with the target string intact.
    """

    payload = _workflow()
    steps = payload["jobs"]["monitor"]["steps"]

    assert len(steps) == 3

    checkout, setup, probe = steps
    assert set(checkout) == ACTION_STEP_KEYS
    assert checkout["uses"] == CHECKOUT_ACTION
    assert checkout["with"] == {"persist-credentials": "false"}

    assert set(setup) == ACTION_STEP_KEYS
    assert setup["uses"] == SETUP_PYTHON_ACTION
    assert setup["with"] == {"python-version": "3.13"}

    assert set(probe) == MONITOR_STEP_KEYS
    assert probe["name"] == MONITOR_STEP_NAME

    used = {step["uses"] for _, step in _steps(payload) if "uses" in step}
    assert used == APPROVED_ACTIONS


def test_exactly_one_executable_step_runs_the_canonical_monitor_command() -> None:
    """The probe is one fixed command, compared exactly after normalisation."""

    payload = _workflow()
    monitor_run_steps = [s for s in payload["jobs"]["monitor"]["steps"] if "run" in s]

    assert len(monitor_run_steps) == 1
    assert len(_monitor_steps(payload)) == 1
    assert _monitor_steps(payload)[0][0] == "monitor"

    command = _normalized(monitor_run_steps[0]["run"])
    assert command == CANONICAL_MONITOR_COMMAND

    # Stated explicitly so a failure says which property was lost.
    assert command.count(MONITOR_ENTRYPOINT) == 1
    assert command.count("--base-url") == 1
    assert command.count(TARGET_ENV_KEY) == 1
    assert "=" not in command, "the command must not assign or reassign a variable"
    assert not re.search(r"[;&|`\n]", command), "no chaining, pipe, or substitution"
    assert "$(" not in command and "${" not in command
    assert "://" not in command, "the command must not carry a literal URL"
    assert not NETWORK_COMMANDS.search(command)


def test_monitor_target_is_the_stable_alias_with_no_alternate_source() -> None:
    """The alias must be the value the command runs against.

    `nbatools-fvdbt0pfv-...` was one deployment's URL. After that
    deployment was removed the host answered HTTP 410, and the scheduled
    monitor kept reporting the dead target rather than the service. The
    target is therefore asserted from parsed env at every executable
    scope, where neither a comment nor a workflow-level override can
    stand in for it.
    """

    payload = _workflow()
    _, monitor_step = _monitor_steps(payload)[0]

    assert monitor_step["env"] == {
        "PYTHONPATH": "src",
        TARGET_ENV_KEY: STABLE_PRODUCTION_ALIAS,
    }

    scopes = _env_scopes(payload)
    assert [name for name, env in scopes if TARGET_ENV_KEY in env] == [
        f"step:monitor:{MONITOR_STEP_NAME}"
    ], "the monitor step must be the sole target source"

    for name, env in scopes:
        for key, value in env.items():
            if key == TARGET_ENV_KEY:
                continue
            assert "://" not in str(value), f"{name} declares a second URL-valued env key: {key}"

    for job_name, step in _run_steps(payload):
        if step is monitor_step:
            continue
        assert "--base-url" not in step["run"], f"{job_name} passes a second --base-url"

    for source in ("secrets.", "vars.", "inputs.", "github.event"):
        assert source not in monitor_step["run"]
        assert source not in str(monitor_step["env"])
    assert "url" not in payload["on"]["workflow_dispatch"]["inputs"]


def test_no_step_outside_the_canonical_probe_touches_the_network() -> None:
    """Only the one approved command may make a request."""

    payload = _workflow()
    _, monitor_step = _monitor_steps(payload)[0]

    for job_name, step in _run_steps(payload):
        if step is monitor_step:
            continue
        command = step["run"]
        assert "://" not in command, f"{job_name} step contains a URL"
        assert MONITOR_ENTRYPOINT not in command
        assert not NETWORK_COMMANDS.search(command), f"{job_name} step runs a network command"


def test_synthetic_alert_job_runs_exactly_the_approved_failing_command() -> None:
    """The notification test must actually fail when it is dispatched.

    Its whole purpose is to prove the owner receives a failure alert, so
    the command is compared line by line: an inserted `exit 0` would keep
    both required strings present while the job succeeded.
    """

    payload = _workflow()
    steps = payload["jobs"]["synthetic-alert"]["steps"]

    assert len(steps) == 1
    step = steps[0]
    assert set(step) == SYNTHETIC_STEP_KEYS
    assert step["name"] == SYNTHETIC_STEP_NAME
    assert _command_lines(step["run"]) == SYNTHETIC_COMMAND_LINES

    command = step["run"]
    assert MONITOR_ENTRYPOINT not in command
    assert TARGET_ENV_KEY not in command
    assert "--base-url" not in command
    assert "://" not in command


def test_workflow_declares_no_ambient_environment() -> None:
    """No workflow- or job-level env exists to shadow the step's target."""

    payload = _workflow()

    assert "env" not in payload, "workflow-level env is not part of the approved shape"
    for job_name, job in payload["jobs"].items():
        assert "env" not in job, f"{job_name} declares a job-level env"
    assert [name for name, _ in _env_scopes(payload)] == [f"step:monitor:{MONITOR_STEP_NAME}"]


def test_no_job_or_step_can_tolerate_or_skip_a_failure() -> None:
    """A probe that cannot fail the workflow is not a probe.

    These overlap the exact key sets above on purpose: when someone makes
    the monitor non-failing, the failure should name the lost policy
    rather than only report an unexpected key.
    """

    payload = _workflow()

    for job_name, job in payload["jobs"].items():
        assert "continue-on-error" not in job, (
            f"{job_name} tolerates its own failure; a failed probe would not fail the workflow"
        )
        assert "needs" not in job, (
            f"{job_name} depends on another job and could be skipped when that job is skipped"
        )

    for job_name, step in _steps(payload):
        label = step.get("name", step.get("uses", "?"))
        assert "continue-on-error" not in step, f"{job_name} step {label!r} tolerates failure"
        assert "if" not in step, f"{job_name} step {label!r} is conditionally skippable"

    # The two steps whose execution the monitoring policy depends on.
    _, monitor_step = _monitor_steps(payload)[0]
    assert set(monitor_step) == MONITOR_STEP_KEYS, "the probe step must carry no execution override"
    synthetic_step = payload["jobs"]["synthetic-alert"]["steps"][0]
    assert set(synthetic_step) == SYNTHETIC_STEP_KEYS
    assert _command_lines(synthetic_step["run"])[-1] == "exit 1"


def test_production_monitor_workflow_retains_its_safe_execution_shape() -> None:
    """Defence in depth. The parsed assertions above are load-bearing."""

    text = WORKFLOW.read_text(encoding="utf-8")

    assert RETIRED_TARGET not in text
    assert not re.search(r"nbatools-[0-9a-z]{9}-brents-projects-", text)
    assert "vars." not in text
    assert "secrets." not in text
    assert "pip install" not in text
    assert "upload-artifact" not in text
    assert "top 10 scorers" not in text
