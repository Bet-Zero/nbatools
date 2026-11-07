"""Required retained-source ID18 acceptance; authenticated base remains unchanged."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from nbatools.data_source import data_generation_context, data_path
from tests import test_current_id18_development as current

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def test_current_id18_qualified_empty_all_consumers_and_source_preservation(tmp_path, monkeypatch):
    with data_generation_context() as generation:
        assert generation == "availability-lebron-season-v1-20261031"
        raw = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == (
            "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
        )
        manifest = json.loads(raw)
        assert manifest["generation_id"] == generation and len(manifest["files"]) == 775
    root = current.pinned_reason.__wrapped__(tmp_path / "current", monkeypatch)
    current.test_original_source_replay_preserves_old_files_and_all_binary_facts(root)
    for route in [
        "team_record",
        "game_summary",
        "game_finder",
        "player_game_summary",
        "player_game_finder",
    ]:
        current.test_all_five_reason_consumers_qualified_empty(root, route)
    current.test_original_natural_http_labels_and_distinct_generic_absence(root)
    current.test_old_version_reader_stays_pinned_and_production_cannot_opt_in(root, monkeypatch)
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "current-id18"
    output.mkdir(parents=True, exist_ok=False)
    (output / "acceptance.json").write_text(
        json.dumps(
            dict(
                candidate_sha=os.environ["VALIDATION_SHA"],
                base_generation=generation,
                development_manifest_sha256=current.DIGEST,
                source_population_games=9,
                played=8,
                qualified_nonparticipations=1,
                reported_rest=0,
                reported_other=1,
                unknown=0,
                all_five_consumers="qualified_empty_no_match",
                original_natural_http="qualified_empty_no_match",
                generic_sits="1-0_103PTS",
                old_version="no_data_preserved",
                production_opt_in="rejected",
                original_pdf_replayed=True,
                production_writes=0,
                whole_snapshot_accepted=False,
            ),
            indent=2,
        )
        + "\n"
    )
