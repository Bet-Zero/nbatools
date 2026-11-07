"""Required finite period-source numerical/consumer milestone; no publication acceptance."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from nbatools.data_source import data_generation_context, data_path
from tests import test_current123_period_integration as current

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def test_required_period_source_composition_and_qualified_consumers(tmp_path, monkeypatch):
    with data_generation_context() as generation:
        assert generation == "availability-lebron-season-v1-20261031"
        raw = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert (
            hashlib.sha256(raw).hexdigest()
            == "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
        )
        assert len(json.loads(raw)["files"]) == 775
    selected = current.snapshot.__wrapped__(tmp_path / "periods", monkeypatch)
    current.test_all_new_canonical_values_match_independent_original_byte_oracle(selected)
    current.test_existing_importer_replays_all_sources_and_explicit_clock_ledger(
        tmp_path / "replay"
    )
    current.test_parent_versions_bytes_unknowns_and_required_coverage_preserved(selected)
    for case in current.CASES:
        current.test_qualified_period_record_natural_structured_http_and_labels(selected, *case)
    current.test_old_rate_unknowns_still_block_strict_player_period_delivery(selected)
    current.test_production_cannot_select_provisional_period_snapshot(selected, monkeypatch)
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "current123-period-integration"
    output.mkdir(parents=True, exist_ok=False)
    (output / "acceptance.json").write_text(
        json.dumps(
            dict(
                candidate_sha=os.environ["VALIDATION_SHA"],
                base_generation=generation,
                development_manifest_sha256=selected[1],
                original_requests=196,
                newly_integrated_windows=98,
                new_standard_player_keys=2208,
                new_source_ot_player_keys=28,
                new_team_keys=196,
                total_period_windows=745,
                total_player_keys=16783,
                total_team_keys=1490,
                period_acquisition_and_key_coverage_complete=True,
                strict_structural_validation="passed",
                numerical_source_oracle_new_keys="passed_with_explicit184_rebound_basis_conflict",
                affected_team_record_consumers="quarter_half_OT_natural_structured_HTTP_pass",
                player_period_delivery="blocked_old484_unknowns_not_positive_acceptance",
                new184_rebound_fact="open_separate_source_exception",
                old484_rate_unknowns="preserved",
                dq006="separate_unresolved",
                whole_snapshot_accepted=False,
                production_writes=0,
            ),
            indent=2,
        )
        + "\n"
    )
