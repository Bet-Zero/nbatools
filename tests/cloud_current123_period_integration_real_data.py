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


def test_required_game184_scorer_correction_and_affected_consumers(tmp_path, monkeypatch):
    from tests import test_current123_period_book_correction as scorer

    with data_generation_context() as generation:
        assert generation == "availability-lebron-season-v1-20261031"
        original = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert (
            hashlib.sha256(original).hexdigest()
            == "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
        )
        assert len(json.loads(original)["files"]) == 775
    selected = scorer.corrected.__wrapped__(tmp_path / "corrected", monkeypatch)
    scorer.test_scorer_count_and_rebound_exposure_facts_are_applied_exactly(selected)
    scorer.test_only_declared_tokens_change_and_all_old_versions_unknowns_survive(selected)
    scorer.test_existing_versioned_correction_replays_and_rejects_stale_oracle(tmp_path / "replay")
    for window, points, rebounds, label in [
        (dict(quarter="2"), 25, 8, "second quarter"),
        (dict(half="first"), 51, 20, "first half"),
    ]:
        scorer.test_corrected_rebounds_reach_actual_natural_structured_http_consumers(
            selected, window, points, rebounds, label
        )
    scorer.test_original_rate_unknown_guard_and_production_isolation_still_apply(
        selected, monkeypatch
    )
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "current123-period-scorer"
    output.mkdir(parents=True, exist_ok=False)
    (output / "acceptance.json").write_text(
        json.dumps(
            dict(
                candidate_sha=os.environ["VALIDATION_SHA"],
                base_generation=generation,
                development_manifest_sha256=selected[1],
                new_source_requests_this_test=0,
                original_book_sha256="5d11d1974ca1426afda19575cc9a8af316d5a9471f26ced48f8470bbaf830b2b",
                corrected_period_count_cells=8,
                independently_rederived_rebound_rates=38,
                remaining_new184_rebound_conflicts=0,
                old_unknown_rate_cells=484,
                new_unknowns=0,
                required_windows=745,
                player_keys=16783,
                team_keys=1490,
                affected_team_natural_structured_HTTP="DALQ2_25PTS8REB_H1_51PTS20REB_verified",
                strict_player_period="no_data_old484_containment_not_positive",
                whole_snapshot_accepted=False,
                production_writes=0,
            ),
            indent=2,
        )
        + "\n"
    )
