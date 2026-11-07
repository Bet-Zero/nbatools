"""Required source-stage admission and consumer checks; incomplete snapshot stays failed."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from nbatools.commands.validation_control import DATASET_SPECS, build_slice_manifest
from nbatools.data_source import data_generation_context, data_path
from tests import test_current123_required_integration as current

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def test_required_current_source_composition_and_affected_consumers(tmp_path, monkeypatch):
    with data_generation_context() as generation:
        assert generation == "availability-lebron-season-v1-20261031"
        original = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert hashlib.sha256(original).hexdigest() == (
            "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
        )
        assert len(json.loads(original)["files"]) == 775
    selected = current.integrated.__wrapped__(tmp_path / "current", monkeypatch)
    root, digest = selected
    current.test_required_contract_tracks_source_known_ot_and_retains_id18_sources(selected)
    current.test_current_starter_natural_structured_http_and_id18_are_distinct_qualified_scopes(
        selected
    )
    report = build_slice_manifest(
        "2026-27",
        "Regular Season",
        data_root=root / "data",
        generation_id="required-current-source-replay",
    )
    failures = {
        r["name"]: r["validation"]["errors"]
        for r in report["datasets"]
        if r["validation"]["errors"]
    }
    assert failures == {
        "player_game_period_stats": ["coverage missing 2208 requested keys"],
        "team_game_period_stats": ["coverage missing 196 requested keys"],
    }
    team = next(r for r in report["datasets"] if r["name"] == "team_game_period_stats")
    assert team["coverage"]["expected_keys"] == 1490
    required = [s for s in DATASET_SPECS if s.required and s.applies("Regular Season")]
    assert sum(s.layer == "raw" for s in required) == 11
    assert sum(s.layer == "processed" for s in required) == 5
    assert report["validation_state"] == "failed"
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "current-required-integration"
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(
        candidate_sha=os.environ["VALIDATION_SHA"],
        base_generation=generation,
        development_manifest_sha256=digest,
        source_due_games=123,
        source_role_keys_added=368,
        source_advanced_player_keys=452,
        required_team_windows=745,
        required_team_period_keys=1490,
        unresolved_team_period_keys=196,
        unresolved_standard_player_period_keys=2208,
        new_ot_player_keys="unknown until actual source windows qualify",
        original_id18="fullLAL9 reportedRest0/other1/unknown0 qualified_no_match",
        starter_consumer="Reaves9starts_210PTS_natural_structured_HTTP",
        raw_required=11,
        processed_required=5,
        validation_state="failed",
        source_admission_and_affected_consumers="passed",
        whole_snapshot_accepted=False,
        production_writes=0,
    )
    (output / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
