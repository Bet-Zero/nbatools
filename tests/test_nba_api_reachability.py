"""The NBA API reachability probe and its manual, secret-free workflow."""

import importlib.util
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/nba-api-reachability.yml"

_spec = importlib.util.spec_from_file_location(
    "nba_api_reachability", ROOT / "tools/nba_api_reachability.py"
)
reachability = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reachability)


class _Endpoint:
    def __init__(self, rows: int):
        self._rows = rows

    def get_data_frames(self):
        return [pd.DataFrame({"x": range(self._rows)})]


def _refused():
    raise ConnectionError("Read timed out")


def test_refresh_is_reachable_when_every_required_endpoint_answers():
    receipt = reachability.probe(
        "2025-26",
        [
            ("team_game_log", True, lambda: _Endpoint(2460)),
            ("play_by_play", False, _refused),
        ],
    )

    assert receipt["refresh_endpoints_reachable"] is True
    assert receipt["endpoints"]["team_game_log"]["rows"] == 2460
    assert receipt["endpoints"]["play_by_play"] == {
        "required_for_refresh": False,
        "ok": False,
        "seconds": receipt["endpoints"]["play_by_play"]["seconds"],
        "error": "ConnectionError",
        "detail": "Read timed out",
    }


def test_refresh_is_unreachable_when_a_required_endpoint_fails():
    receipt = reachability.probe(
        "2025-26",
        [
            ("team_game_log", True, _refused),
            ("standings", True, lambda: _Endpoint(30)),
        ],
    )

    assert receipt["refresh_endpoints_reachable"] is False


def test_workflow_is_manual_read_only_and_secret_free():
    text = WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.load(text, Loader=yaml.BaseLoader)

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    assert "secrets." not in text
    assert "environment" not in workflow["jobs"]["probe"]
