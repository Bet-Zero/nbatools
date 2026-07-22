from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/production-monitor.yml"


def test_production_monitor_workflow_is_structurally_valid() -> None:
    payload = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

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


def test_production_monitor_workflow_uses_fixed_target_and_safe_synthetic_failure() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "https://nbatools-fvdbt0pfv-brents-projects-686e97fc.vercel.app" in text
    assert "vars." not in text
    assert "secrets." not in text
    assert "tools/production_monitor.py" in text
    assert '"network_requests_made":0' in text
    assert "PYTHONPATH: src" in text
    assert "pip install" not in text
    assert "upload-artifact" not in text
    assert "top 10 scorers" not in text
    synthetic = text.split("  synthetic-alert:", maxsplit=1)[1]
    assert "production_monitor.py" not in synthetic
    assert "checkout" not in synthetic
    assert "setup-python" not in synthetic
    assert "PRODUCTION_MONITOR_BASE_URL" not in synthetic
