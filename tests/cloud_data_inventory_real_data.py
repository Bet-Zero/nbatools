"""Explicit actual-R2 inventory generation; no backup export or production write."""

import json
import os
from pathlib import Path

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def test_generate_production_inventory(capfd):
    from tools.data_availability import collect_production, collection_request, write_report

    report = collect_production()
    assert report["generation_id"] == os.environ["NBATOOLS_DATA_GENERATION"]
    assert report["origin"] == "active_production_r2"
    assert report["file_count"] == len(report["files"]) > 0
    assert all(f["integrity"] == "verified" for f in report["files"])
    assert report["production_writes"] == 0
    paths = {f["path"]: f for f in report["files"]}
    current = paths["raw/player_game_stats/2025-26_regular_season.csv"]
    assert current["rows"] > 1000 and {"pts", "reb", "ast", "game_id"}.issubset(current["columns"])
    assert not current["game_coverage"]["missing_game_ids"]
    availability = paths["raw/player_game_availability/2025-26_regular_season.csv"]
    assert "listed_player_rows_only" in availability["source_labels"]["coverage_scope"]
    requirement = collection_request(
        report, "raw/player_game_period_stats", "2026-27", "Regular Season", games=["0022600001"]
    )
    assert requirement["missing_nba_game_ids"] == ["0022600001"]
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "data-inventory"
    write_report(report, output)
    (output / "example-collection-request.json").write_text(
        json.dumps(requirement, indent=2) + "\n"
    )
    with capfd.disabled():
        print(
            "DATA_INVENTORY_JSON "
            + json.dumps(
                {
                    "generation_id": report["generation_id"],
                    "manifest_sha256": report["evidence"]["manifest_sha256"],
                    "file_count": report["file_count"],
                    "total_bytes": report["total_bytes"],
                    "staged_bundles": len(report["staged_bundles"]),
                    "csv_quality_issues": sum(
                        f.get("quality_state") == "issues" for f in report["files"]
                    ),
                    "production_writes": 0,
                }
            ),
            flush=True,
        )
