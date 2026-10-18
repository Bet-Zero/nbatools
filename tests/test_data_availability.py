import hashlib
from pathlib import Path

import pandas as pd
import pytest

from tools.data_availability import collection_request, profile_frame, scan_generation


def generation(tmp_path):
    files = {
        "raw/games/2025-26_regular_season.csv": "game_id,is_final,home_team_id,away_team_id,game_date\n0022500001,1,1,2,2025-10-21\n0022500002,1,3,4,2025-10-22\n",
        "raw/player_game_stats/2025-26_regular_season.csv": "game_id,team_id,player_id,pts\n22500001,1,42,20\n",
    }
    entries = []
    for name, value in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
        entries.append(
            {
                "path": name,
                "size_bytes": len(value.encode()),
                "sha256": hashlib.sha256(value.encode()).hexdigest(),
            }
        )
    manifest = {"generation_id": "test-generation", "files": entries}
    return manifest


def report(tmp_path):
    manifest = generation(tmp_path)
    return scan_generation(
        manifest,
        lambda path: tmp_path / path,
        origin="test_fixture_not_production",
        evidence={"manifest_sha256": "a" * 64},
    )


def test_observed_games_and_player_completeness_are_different(tmp_path):
    result = report(tmp_path)
    frame = next(f for f in result["files"] if f.get("dataset") == "raw/player_game_stats")
    assert frame["game_coverage"]["missing_game_ids"] == ["22500002"]
    assert frame["team_game_coverage"]["missing_keys"] == [
        ("22500001", "2"),
        ("22500002", "3"),
        ("22500002", "4"),
    ]
    assert "player denominator unknown" in frame["completeness"]
    assert frame["quality_state"] == "issues"
    assert "ast" in frame["missing_columns"]


def test_corrupt_generation_bytes_cannot_be_reported_as_production(tmp_path):
    manifest = generation(tmp_path)
    (tmp_path / manifest["files"][0]["path"]).write_text("changed")
    with pytest.raises(ValueError, match="integrity mismatch"):
        scan_generation(manifest, lambda path: tmp_path / path, origin="test", evidence={})


def test_quality_reports_duplicates_nulls_untrusted_rows_and_nonfinite_counts():
    frame = pd.DataFrame(
        {
            "game_id": [1, 1],
            "team_id": [2, 2],
            "player_id": [42, 42],
            "pts": [float("inf"), None],
            "role_source_trusted": [1, 0],
        }
    )
    result = profile_frame(frame, "raw/player_game_stats")
    assert result["duplicate_keys"] == 1
    assert result["null_counts"]["pts"] == 1
    assert result["trust"]["role_source_trusted"] == {"trusted_rows": 1, "other_rows": 1}
    assert "pts: nonfinite values" in result["quality_errors"]


def test_collection_request_preserves_base_and_exact_period_scope(tmp_path):
    request = collection_request(
        report(tmp_path),
        "raw/player_game_period_stats",
        "2025-26",
        "Regular Season",
        games=["0022500002"],
        fields=["ts_pct"],
    )
    assert request["missing_nba_game_ids"] == ["0022500002"]
    assert request["base_generation"] == "test-generation"
    assert request["base_manifest_sha256"] == "a" * 64
    assert len(request["period_windows"]) == 6
    assert "ts_pct" in request["required_columns"]
    assert "not_publication_approval" in request["status"]
    assert "no inference from absence" in request["completeness_requirement"]


def test_request_not_in_catalog_does_not_invent_a_game(tmp_path):
    request = collection_request(
        report(tmp_path), "raw/player_game_stats", "2026-27", "Regular Season", games=["0022600001"]
    )
    assert request["game_ids_not_in_production_catalog"] == ["22600001"]
    assert request["requested_nba_game_ids"] == ["0022600001"]


def test_request_rejects_noncontract_dataset(tmp_path):
    with pytest.raises(ValueError, match="existing canonical"):
        collection_request(report(tmp_path), "made_up_stats", "2025-26", "Regular Season")


def test_inventory_workflow_has_no_publication_or_cloud_acquisition_authority():
    workflow = Path(".github/workflows/r2-real-data-validation.yml").read_text()
    assert "from tools.cloud_refresh import prepare" not in workflow
    from yaml import safe_load

    jobs = safe_load(workflow)["jobs"]
    report = jobs["retain-data-inventory"]
    assert "environment" not in report and report["permissions"]["contents"] == "write"
    assert "test_generate_production_inventory" in report["if"]
    assert "needs.data-backed-tests.result == 'success'" in report["if"]
    assert not any("R2_" in str(step.get("env", {})) for step in report["steps"])
    restore = jobs["restore-backup"]
    assert "tools.data_availability from-backup" in str(restore)
    assert "restored/data-inventory/inventory.json" in str(jobs["retain-restore-receipt"])


def test_season_grain_does_not_invent_missing_games(tmp_path):
    manifest = generation(tmp_path)
    name = "raw/player_season_advanced/2025-26_regular_season.csv"
    raw = b"player_id,team_id,ts_pct\n42,1,0.6\n"
    target = tmp_path / name
    target.parent.mkdir(parents=True)
    target.write_bytes(raw)
    manifest["files"].append(
        {"path": name, "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    )
    result = scan_generation(manifest, lambda p: tmp_path / p, origin="test", evidence={})
    advanced = next(f for f in result["files"] if f.get("dataset") == "raw/player_season_advanced")
    assert "game_coverage" not in advanced


def test_missing_requested_identity_and_null_fields_never_report_ready(tmp_path):
    result = report(tmp_path)
    source = next(f for f in result["files"] if f.get("dataset") == "raw/player_game_stats")
    source["null_counts"]["pts"] = source["rows"]
    packet = collection_request(
        result,
        "raw/player_game_stats",
        "2025-26",
        "Regular Season",
        games=["0022500001"],
        player_ids=["999"],
    )
    assert packet["collection_needed"] and packet["quality_review_required"]
    assert packet["unusable_fields"] == ["pts"]
    assert packet["unobserved_requested_keys"] == [
        {"game_id": "22500001", "team_id": None, "player_id": "999"}
    ]
    assert "does not establish DNP" in packet["key_absence_note"]


def test_staging_inventory_retains_existing_path_variants_and_separation(tmp_path):
    import json
    import zipfile

    from tools.data_availability import staged_inventory

    for name, member, receipt_path in [
        (
            "core",
            "data/raw/player_game_stats/2025-26_regular_season.csv",
            "working/nba-tools-completion-program/cloud-operations/core.zip",
        ),
        ("lineup", "raw/league_lineup_viz/2025-26_regular_season.csv", "lineup.zip"),
        ("partial", "partial/rosters.csv", "partial.zip"),
    ]:
        path = tmp_path / f"{name}.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(member, "fixture")
        (tmp_path / f"{name}-receipt.json").write_text(
            json.dumps(
                {
                    "durable_bundle": {
                        "path": receipt_path,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                }
            )
        )
    result = staged_inventory(tmp_path)
    assert len(result) == 3 and all(len(b["dataset_paths"]) == 1 for b in result)
    assert all(b["location"] == "development_staging_in_git" for b in result)
