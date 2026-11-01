"""Explicit one-game source capture; no other games, Stats probes or publication."""

import hashlib
import os
from pathlib import Path

import pytest

from tools.collect_rollover_cdn import URL, collect_missing_boxscore

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def test_collect_missing_atl_cle_2026_27_boxscore():
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "rollover-cdn-0022600144"
    report = collect_missing_boxscore(output)
    raw = (output / report["source_file"]).read_bytes()
    assert report["source_url"] == URL and report["game_id"] == "0022600144"
    assert report["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert report["source_bytes"] == len(raw) and report["source_identity_rows"] > 0
    assert (
        report["attempts"] == 1 and report["nba_stats_probes"] == report["production_writes"] == 0
    )
    assert report["statistical_qualification"] == "pending_independent_original_rows"
