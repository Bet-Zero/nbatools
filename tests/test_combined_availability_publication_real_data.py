"""No-write complete-snapshot gate for the fixed combined availability package."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "opening-s4-availability-v1"


def test_combined_availability_complete_snapshot_prepare(tmp_path, monkeypatch):
    policy = json.loads((ROOT / ".github/data-publication-packages.json").read_text())
    package = policy["packages"][PACKAGE]
    publisher = tmp_path / "publisher"
    subprocess.run(
        [
            "git",
            "clone",
            "--no-checkout",
            "--filter=blob:none",
            "https://github.com/Bet-Zero/nbatools.git",
            str(publisher),
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(publisher), "checkout", "--detach", package["publisher_sha"]], check=True
    )
    inventory = json.loads((publisher / package["inventory"]).read_text())
    work, audit = tmp_path / "prepared", tmp_path / "audit"
    command = [sys.executable, str(ROOT / "tools/r2_publication.py")]
    subprocess.run(command + ["audit", "--work", str(audit)], check=True)
    try:
        subprocess.run(
            command
            + ["prepare", "--package", PACKAGE, "--publisher", str(publisher), "--work", str(work)],
            check=True,
        )
        receipt = json.loads((work / "prepared.json").read_text())
        assert receipt["publication_state"] == "prepared_no_writes"
        assert receipt["publisher_sha"] == package["publisher_sha"]
        assert (
            receipt["required_source_gate"]["selected"]
            == receipt["required_source_gate"]["executed"]
            == receipt["required_source_gate"]["passed"]
            == 1
        )
        assert receipt["budget"]["conservative_projected_bytes"] <= policy["max_bucket_bytes"]
        assert not (work / "publication.json").exists()
        snapshot = work / "staging/validation/generations" / package["generation_id"]
        manifest_path = snapshot / "metadata/generation_manifest.json"
        assert (
            hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            == receipt["prepared_manifest_sha256"]
        )
        manifest = json.loads(manifest_path.read_text())
        base = json.loads((work / "staging/base-manifest.json").read_text())
        files = {item["path"]: item for item in manifest["files"]}
        original = {item["path"]: item for item in base["files"]}
        overlay = {
            item["path"]: item for item in inventory["files"] if item["path"].startswith("raw/")
        }
        assert len(original) == 684
        assert len(overlay) == 18
        assert files.keys() == original.keys() | overlay.keys() | {"metadata/player_names.csv"}
        assert len(files) == receipt["file_count"] == 703
        for name, item in original.items():
            assert files[name] == item, f"Base object changed: {name}"
        for name, item in overlay.items():
            assert files[name] == item, f"Reviewed overlay changed: {name}"
        for name, item in files.items():
            raw = (snapshot / name).read_bytes()
            assert len(raw) == item["size_bytes"]
            assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        assert sum(item["size_bytes"] for item in files.values()) == receipt["total_bytes"]
        consumer_root = tmp_path / "consumer-root"
        consumer_root.mkdir()
        (consumer_root / "data").symlink_to(work / "staging/validation", target_is_directory=True)
        monkeypatch.setenv("DATA_SOURCE", "local")
        monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(consumer_root))
        monkeypatch.setenv("NBATOOLS_DATA_GENERATION", package["generation_id"])
        reset_data_source_cache()
        answers = []
        for case in package["deployed_checks"]:
            result = execute_natural_query(case["query"])
            assert result.result_status == "ok", (case["query"], result.result_reason)
            rows = result.result.to_dict()["sections"]["summary"]
            assert len(rows) == 1
            for key, value in case["summary"].items():
                assert rows[0][key] == value, (case["query"], key, rows[0])
            answer = {"query": case["query"], "summary": rows[0]}
            if rows[0].get("player_name") == "Jaylen Brown":
                games = result.result.to_dict()["sections"]["game_log"]
                expected_ids = (
                    {22300403, 22300684}
                    if rows[0]["season_start"] == "2023-24"
                    else {22500338, 22500823}
                )
                assert len(games) == 2
                assert {int(row["game_id"]) for row in games} == expected_ids
                assert all(int(row["player_id"]) == 1627759 for row in games)
                answer["game_ids"] = sorted(expected_ids)
            answers.append(answer)
        assert len(answers) == 6
        (work / "consumer-checks.json").write_text(json.dumps(answers, indent=2) + "\n")
    finally:
        reset_data_source_cache()
        output = os.environ.get("NBATOOLS_ACQUISITION_OUTPUT")
        if output:
            destination = Path(output) / "combined-publication-preparation"
            destination.mkdir(parents=True, exist_ok=True)
            for source in (
                audit / "environment-audit.json",
                work / "prepared.json",
                work / "consumer-checks.json",
                work / "staging/local-validation.json",
                work / "staging/base-manifest.json",
                work
                / "staging/validation/generations"
                / package["generation_id"]
                / "metadata/generation_manifest.json",
            ):
                if source.exists():
                    shutil.copy2(source, destination / source.name)
