"""Contract tests for the scheduled production monitor workflow.

These tests assert against the *parsed* workflow, not against raw file
text. Text matching alone cannot tell an executable target from a
comment, and cannot see a second invocation that overrides the first, so
a workflow can read correctly and still probe somewhere else.
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


def _workflow() -> dict[str, Any]:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _run_steps(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Return every ``(job_name, step)`` pair that executes a shell command."""

    steps: list[tuple[str, dict[str, Any]]] = []
    for job_name, job in payload["jobs"].items():
        for step in job.get("steps", []):
            if "run" in step:
                steps.append((job_name, step))
    return steps


def _monitor_steps(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Return every executable step that invokes the production monitor."""

    return [
        (job_name, step)
        for job_name, step in _run_steps(payload)
        if MONITOR_ENTRYPOINT in step["run"]
    ]


def test_production_monitor_workflow_is_structurally_valid() -> None:
    payload = _workflow()

    assert payload["on"]["schedule"] == [{"cron": "17 */2 * * *"}]
    assert payload["on"]["workflow_dispatch"]["inputs"]["mode"]["options"] == [
        "probe",
        "synthetic-alert",
    ]
    assert payload["jobs"]["monitor"]["if"] == (
        "${{ github.event_name == 'schedule' || inputs.mode == 'probe' }}"
    )
    assert payload["jobs"]["synthetic-alert"]["if"] == (
        "${{ github.event_name == 'workflow_dispatch' && inputs.mode == 'synthetic-alert' }}"
    )


def test_production_monitor_workflow_encodes_approved_schedule_and_permissions() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert 'cron: "17 */2 * * *"' in text
    assert "workflow_dispatch:" in text
    assert "synthetic-alert" in text
    assert "contents: read" in text
    assert "timeout-minutes: 3" in text
    assert "cancel-in-progress: false" in text
    assert "persist-credentials: false" in text
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in text
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97" in text
    assert "pull_request:" not in text
    assert "\n  push:" not in text


def test_exactly_one_executable_step_invokes_the_production_monitor() -> None:
    """One probe, in the monitor job. A second invocation would override it."""

    payload = _workflow()
    monitor_steps = _monitor_steps(payload)

    assert len(monitor_steps) == 1, (
        f"expected exactly one {MONITOR_ENTRYPOINT} invocation, found {len(monitor_steps)}"
    )
    job_name, step = monitor_steps[0]
    assert job_name == "monitor"
    assert step["run"].count(MONITOR_ENTRYPOINT) == 1
    assert step["run"].count("--base-url") == 1


def test_monitor_step_executes_against_the_stable_production_alias() -> None:
    """The alias must be the value the command actually runs against.

    `nbatools-fvdbt0pfv-...` was a single deployment's URL. After that
    deployment was removed the host answered HTTP 410, and the scheduled
    monitor kept reporting the dead target rather than the service. The
    executable target is therefore asserted from the parsed step, where a
    comment cannot stand in for it.
    """

    payload = _workflow()
    _, step = _monitor_steps(payload)[0]

    env = step.get("env")
    assert isinstance(env, dict), "monitor step must declare an env mapping"
    assert env[TARGET_ENV_KEY] == STABLE_PRODUCTION_ALIAS

    command = step["run"]
    assert f'--base-url "${TARGET_ENV_KEY}"' in command
    assert "http://" not in command
    assert "https://" not in command, "the command must not carry a literal URL"


def test_monitor_target_has_no_second_or_indirect_source() -> None:
    """Nothing else may supply, override, or redirect the probe target."""

    payload = _workflow()

    assignments = []
    for job_name, job in payload["jobs"].items():
        for scope in (job, *job.get("steps", [])):
            env = scope.get("env")
            if isinstance(env, dict) and TARGET_ENV_KEY in env:
                assignments.append((job_name, env[TARGET_ENV_KEY]))
    assert len(assignments) == 1, f"expected one {TARGET_ENV_KEY} assignment, got {assignments}"

    # No other env key may carry a URL that a command could probe instead.
    for job_name, job in payload["jobs"].items():
        for scope in (job, *job.get("steps", [])):
            env = scope.get("env")
            if not isinstance(env, dict):
                continue
            for key, value in env.items():
                if key == TARGET_ENV_KEY:
                    continue
                assert "://" not in str(value), (
                    f"{job_name} declares a second URL-valued env key: {key}"
                )

    # No step anywhere may pass its own --base-url.
    for job_name, step in _run_steps(payload):
        if step is _monitor_steps(payload)[0][1]:
            continue
        assert "--base-url" not in step["run"], f"{job_name} passes a second --base-url"

    # The target must not be redirectable from outside the tracked file.
    _, monitor_step = _monitor_steps(payload)[0]
    indirection = ("secrets.", "vars.", "inputs.", "github.event")
    for source in indirection:
        assert source not in monitor_step["run"]
        assert source not in str(monitor_step.get("env", {}))
    assert "url" not in payload["on"]["workflow_dispatch"]["inputs"]


def test_synthetic_alert_job_makes_no_network_request() -> None:
    payload = _workflow()
    steps = payload["jobs"]["synthetic-alert"]["steps"]

    for step in steps:
        assert "uses" not in step, "synthetic-alert must check out and install nothing"
        command = step["run"]
        assert MONITOR_ENTRYPOINT not in command
        assert "--base-url" not in command
        assert "://" not in command
        assert not re.search(r"\b(curl|wget|nc|python -m http)\b", command)
        assert TARGET_ENV_KEY not in command
        assert TARGET_ENV_KEY not in str(step.get("env", {}))
    assert '"network_requests_made":0' in steps[-1]["run"]


def test_production_monitor_workflow_retains_its_safe_execution_shape() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert RETIRED_TARGET not in text
    assert not re.search(r"nbatools-[0-9a-z]{9}-brents-projects-", text)
    assert "vars." not in text
    assert "secrets." not in text
    assert "PYTHONPATH: src" in text
    assert "pip install" not in text
    assert "upload-artifact" not in text
    assert "top 10 scorers" not in text
