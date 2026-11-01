"""Explicit retained-source replay. No new acquisition or canonical publication."""

import json
import os
from pathlib import Path

import pytest

from tools.season_rollover_source_stats import qualify_stats_sources

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]


def test_qualify_retained_2026_27_season_stats():
    evidence = ROOT / "working/nba-tools-completion-program/source-evidence/rollover-2026-27"
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "rollover-stats-qualification"
    report = qualify_stats_sources(evidence, output)
    assert len(report["final_game_ids"]) == 81 and report["team_game_rows"] == 162
    assert report["player_game_rows"] == 1829 and report["player_ids"] == 432
    assert report["team_ids"] == 30 and report["final_points_total"] == 18464
    assert report["qualified_snapshot_rows"] == dict(
        player_season_advanced=432, team_season_advanced=30, standings_snapshots=30
    )
    # These are actual unresolved source conflicts, not waived core acceptance.
    assert {row["game_id"] for row in report["player_team_conflicts"]} == {
        "0022600138",
        "0022600142",
        "0022600144",
    }
    assert report["canonical_core_accepted"] is False
    assert report["period_coverage"] == "not_established" and report["production_writes"] == 0
    assert json.loads((output / "qualification.json").read_text()) == report
