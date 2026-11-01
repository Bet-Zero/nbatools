"""One reviewed Q1 Traditional+Advanced V3 probe; failure is never source acceptance."""

import os
from pathlib import Path

import pytest

from tools.probe_rollover_q1 import probe

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]


def test_capture_exact_one_game_q1_traditional_and_advanced_v3():
    evidence = ROOT / "working/nba-tools-completion-program/source-evidence/rollover-2026-27"
    report = probe(
        Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "rollover-q1-0022600001", evidence
    )
    assert report["source_scope_qualified"] is True
    assert report["canonical_period_accepted"] is False and report["production_writes"] == 0
    assert len(report["captures"]) == 2 and all(row["attempts"] == 1 for row in report["captures"])
    assert {row["q1_points"] for row in report["checked_teams"]} == {27, 28}
    assert all(row["team_minutes"] == 60 for row in report["checked_teams"])
