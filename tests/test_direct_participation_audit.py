"""Input audits preserve raw facts without bypassing the runtime's global guards."""

import json

import pandas as pd
import pytest

from tests import test_participation_coverage as coverage_fixture
from tests.cloud_lal_2023_participation_coverage_real_data import (
    AVAILABILITY_COLUMNS,
    _capture_scope,
    _raw_states,
)
from tests.test_participation_coverage import GENERATION, PLAYER, SEASON, SUFFIX, TEAM
from tools.participation_coverage import build_report

pytestmark = pytest.mark.engine


@pytest.fixture
def snapshot(tmp_path, monkeypatch):
    yield from coverage_fixture.snapshot.__wrapped__(tmp_path, monkeypatch)


def capture(snapshot, tmp_path):
    root, _, bind = snapshot
    digest = bind()
    teams = pd.read_csv(root / "raw/team_game_stats" / SUFFIX)
    own = teams.loc[teams.team_id.eq(TEAM)]
    players = pd.read_csv(root / "raw/player_game_stats" / SUFFIX)
    availability_path = root / "raw/player_game_availability" / SUFFIX
    availability = (
        pd.read_csv(availability_path)
        if availability_path.exists()
        else pd.DataFrame(columns=AVAILABILITY_COLUMNS)
    )
    raw = _raw_states(own, players, availability, TEAM, [PLAYER])[PLAYER]
    dates = dict(zip(own.game_id, own.game_date))
    manifest = json.loads((root / "metadata/generation_manifest.json").read_bytes())
    path = tmp_path / "audit.json"
    result = _capture_scope(
        path,
        build=lambda: build_report(
            generation=GENERATION,
            manifest_sha256=digest,
            season=SEASON,
            team_id=TEAM,
            player_id=PLAYER,
        ),
        states=raw,
        dates=dates,
        team_id=TEAM,
        player_id=PLAYER,
        source_view=dict(
            generation=GENERATION,
            manifest_sha256=digest,
            season=SEASON,
            team_id=TEAM,
            player_id=PLAYER,
        ),
        source_files=manifest["files"],
        absent=[] if availability_path.exists() else [f"raw/player_game_availability/{SUFFIX}"],
    )
    assert json.loads(path.read_bytes()) == result
    assert result["source_files"] == manifest["files"]
    assert result["source_view"]["generation"] == GENERATION
    assert result["source_view"]["manifest_sha256"] == digest
    assert not result["capability_complete"] and result["requirement_closures"] == 0
    return result


@pytest.mark.parametrize("unrelated", [False, True], ids=["legacy-negative", "unrelated-bad-row"])
def test_unqualified_authority_is_persisted_without_collection_keys(snapshot, tmp_path, unrelated):
    path = snapshot[0] / "raw/player_game_availability" / SUFFIX
    rows = pd.read_csv(path)
    if unrelated:
        bad = rows.iloc[[0]].assign(
            player_id=999999, player_name="Unrelated Player", source="legacy"
        )
        rows = pd.concat([rows, bad], ignore_index=True)
    else:
        rows["source"] = "legacy"
    rows.to_csv(path, index=False)
    result = capture(snapshot, tmp_path)
    assert result["raw_projection"]["counts"] == {"played": 60, "did_not_play": 5, "unknown": 17}
    assert result["disposition"] == "existing_evidence_repair"
    assert result["runtime_exception"]["type"] == "ValueError"
    assert "lacks retained qualified source evidence" in result["runtime_exception"]["message"]
    assert result["runtime_report"] is None
    assert result["qualified_counts"] is None and result["missed_games"] is None
    assert not result["complete_requested_population"] and result["collection_candidate_keys"] == []


def test_qualified_conflict_preserves_runtime_global_unknowns_without_new_collection(
    snapshot, tmp_path
):
    root, games, _ = snapshot
    path = root / "raw/player_game_availability" / SUFFIX
    rows = pd.read_csv(path)
    conflicting = rows.iloc[[0]].assign(
        game_id=games.game_id.iloc[0], game_date=games.game_date.iloc[0]
    )
    pd.concat([rows, conflicting], ignore_index=True).to_csv(path, index=False)
    result = capture(snapshot, tmp_path)
    assert result["raw_projection"]["counts"] == {"played": 59, "did_not_play": 5, "unknown": 18}
    assert result["runtime_exception"] is None
    assert result["runtime_report"]["counts"]["unknown"] == 82
    assert result["disposition"] == "existing_evidence_repair"
    assert any("Contradictory" in e for e in result["existing_evidence_errors"])
    assert result["qualified_counts"] is None and result["collection_candidate_keys"] == []


def test_normal_missing_evidence_keeps_exact_unknown_keys_and_no_total(snapshot, tmp_path):
    result = capture(snapshot, tmp_path)
    assert result["disposition"] == "qualified_incomplete_missing_evidence"
    assert result["qualified_counts"] == dict(
        played=60, did_not_play=5, same_game_other_side=0, unknown=17
    )
    assert result["missed_games"] is None and not result["complete_requested_population"]
    assert result["collection_candidate_keys"] == result["runtime_report"]["missing_keys"]
    assert [key["game_id"] for key in result["collection_candidate_keys"]] == [
        f"{22510000 + i:010d}" for i in range(65, 82)
    ]


def test_complete_positive_population_can_prove_zero_with_absent_availability(snapshot, tmp_path):
    root, games, _ = snapshot
    path = root / "raw/player_game_stats" / SUFFIX
    rows = pd.read_csv(path)
    additions = pd.DataFrame([rows.iloc[0]] * 22).reset_index(drop=True)
    additions["game_id"] = games.game_id.iloc[60:].to_numpy()
    additions["game_date"] = games.game_date.iloc[60:].to_numpy()
    pd.concat([rows, additions], ignore_index=True).to_csv(path, index=False)
    (root / "raw/player_game_availability" / SUFFIX).unlink()
    result = capture(snapshot, tmp_path)
    assert result["disposition"] == "qualified_complete_observed_population"
    assert result["qualified_counts"] == dict(
        played=82, did_not_play=0, same_game_other_side=0, unknown=0
    )
    assert result["missed_games"] == 0 and result["complete_requested_population"]
    assert result["collection_candidate_keys"] == []


def test_comparison_failure_still_retains_raw_report_and_bindings(snapshot, tmp_path, monkeypatch):
    original = build_report

    def wrong_date(**kwargs):
        result = original(**kwargs)
        result["games"][0]["game_date"] = "1999-01-01"
        return result

    monkeypatch.setattr(__name__ + ".build_report", wrong_date)
    with pytest.raises(AssertionError):
        capture(snapshot, tmp_path)
    saved = json.loads((tmp_path / "audit.json").read_bytes())
    assert saved["runtime_report"]["games"][0]["game_date"] == "1999-01-01"
    assert saved["raw_projection"]["games"][0]["game_date"] == "2025-10-21"
    assert saved["source_files"] and saved["audit_comparison_exception"]["type"] == "AssertionError"
    assert saved["disposition"] == "audit_oracle_mismatch_requires_investigation"
    assert not saved["capability_complete"] and saved["collection_candidate_keys"] == []


@pytest.mark.parametrize(
    "failure",
    [
        TypeError("unexpected programming error"),
        ValueError("unexpected value error"),
        OSError("access denied"),
    ],
    ids=["programming", "unexpected-value", "access"],
)
def test_unexpected_runtime_failures_are_persisted_then_propagated(
    snapshot, tmp_path, monkeypatch, failure
):
    def broken_runtime(**kwargs):
        raise failure

    monkeypatch.setattr(__name__ + ".build_report", broken_runtime)
    with pytest.raises(type(failure), match=str(failure)):
        capture(snapshot, tmp_path)
    saved = json.loads((tmp_path / "audit.json").read_bytes())
    assert saved["runtime_exception"] == dict(type=type(failure).__name__, message=str(failure))
    assert saved["disposition"] == "unexpected_runtime_failure"
    assert saved["audit_comparison_exception"] is None
    assert saved["runtime_report"] is None and saved["source_files"]
    assert saved["raw_projection"]["counts"]["did_not_play"] == 5
    assert saved["qualified_counts"] is None and saved["collection_candidate_keys"] == []
    assert not saved["capability_complete"] and not saved["complete_requested_population"]


def test_unfamiliar_report_qualification_error_is_persisted_then_fails(
    snapshot, tmp_path, monkeypatch
):
    original = build_report

    def unknown_qualification(**kwargs):
        report = original(**kwargs)
        report["games"][65]["qualification_error"] = "Unexpected source-access integrity failure"
        return report

    monkeypatch.setattr(__name__ + ".build_report", unknown_qualification)
    with pytest.raises(ValueError, match="Unexpected participation qualification errors"):
        capture(snapshot, tmp_path)
    saved = json.loads((tmp_path / "audit.json").read_bytes())
    assert (
        saved["runtime_report"]["games"][65]["qualification_error"]
        == "Unexpected source-access integrity failure"
    )
    assert saved["unexpected_qualification_errors"] == [
        "Unexpected source-access integrity failure"
    ]
    assert saved["qualification_exception"]["type"] == "ValueError"
    assert saved["disposition"] == "unexpected_runtime_qualification_failure"
    assert saved["audit_comparison_exception"] is None and saved["source_files"]
    assert saved["qualified_counts"] is None and saved["collection_candidate_keys"] == []
    assert not saved["capability_complete"] and not saved["complete_requested_population"]


def test_known_ambiguous_identity_report_remains_diagnostic_without_collection(snapshot, tmp_path):
    path = snapshot[0] / "raw/player_game_availability" / SUFFIX
    rows = pd.read_csv(path)
    same_name_other_id = rows.iloc[[0]].assign(player_id=999999)
    pd.concat([rows, same_name_other_id], ignore_index=True).to_csv(path, index=False)
    result = capture(snapshot, tmp_path)
    assert result["disposition"] == "existing_evidence_repair"
    assert result["runtime_report"]["counts"]["unknown"] == 82
    assert result["existing_evidence_errors"] == [
        "Unavailable or ambiguous participation identity for LeBron James"
    ]
    assert result["qualified_counts"] is None and result["collection_candidate_keys"] == []
