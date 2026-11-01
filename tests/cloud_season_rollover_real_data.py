"""Explicit reviewed one-body source capture; excluded from ordinary discovery."""

import json
import os
from pathlib import Path

import pytest

from tools.collect_season_rollover import BLOB, BYTES, REVISION, collect_schedule

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def test_collect_pinned_2026_27_schedule_body():
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "rollover-2026-27-schedule"
    report = collect_schedule(output)
    assert report["archive_revision"] == REVISION and report["archive_git_blob_sha"] == BLOB
    assert report["source"]["bytes"] == BYTES
    assert report["acquired_source_bodies"] == 1 and report["production_writes"] == 0
    assert report["automatic_refresh"] is False and report["nba_stats_probes"] == 0
    assert report["season"] == "2026-27"
    assert report["schedule"]["regular_games"] == len(report["observed_regular_games"]) > 0
    assert len(report["observed_final_game_ids"]) == report["schedule"]["final_regular_games"]
    assert (output / report["source_file"]).stat().st_size == BYTES
    assert json.loads((output / "receipt.json").read_text()) == report
