"""Read-only complete-snapshot, consumer and backup gate for the fixed 17-game overlay."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_path, reset_data_source_cache
from tools.availability_overlay import verify_append
from tools.cloud_backup import export_backup, restore_backup
from tools.participation_coverage import build_report
from tools.r2_publication import verify_answer

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "lebron-season-participation-v1"
QUALIFICATION = (
    ROOT
    / "working/nba-tools-completion-program/source-evidence/k08-lebron-remaining/qualification.json"
)


def test_lebron_participation_complete_snapshot_prepare(tmp_path, monkeypatch):
    policy = json.loads((ROOT / ".github/data-publication-packages.json").read_text())
    package = policy["packages"][PACKAGE]
    qualification = json.loads(QUALIFICATION.read_text())
    expected_ids = set(qualification["missed_game_ids"])
    expected_home = set(qualification["home_missed_game_ids"])
    assert len(expected_ids) == 22 and len(expected_home) == 11
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
    assert inventory["run_id"] == qualification["required_run_id"] == 41254371768
    work = tmp_path / "prepared"
    try:
        # A fresh child imports only the pinned publisher. This read-only command
        # needs no main/manual authorization bypass and invokes no R2 writer.
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/r2_publication.py"),
                "prepare",
                "--package",
                PACKAGE,
                "--publisher",
                str(publisher),
                "--work",
                str(work),
            ],
            check=True,
        )
        receipt = json.loads((work / "prepared.json").read_text())
        assert receipt["publication_state"] == "prepared_no_writes"
        assert receipt["publisher_sha"] == package["publisher_sha"]
        assert receipt["base_manifest_sha256"] == inventory["base_manifest_sha256"]
        source = receipt["required_source_gate"]
        assert source["selected"] == source["executed"] == source["passed"] == 1
        assert all(source[key] == 0 for key in ["skipped", "failed", "errors", "xfailed"])
        assert receipt["budget"]["conservative_projected_bytes"] <= policy["max_bucket_bytes"]
        assert not (work / "publication.json").exists()
        snapshot = work / "staging/validation/generations" / package["generation_id"]
        manifest_path = snapshot / "metadata/generation_manifest.json"
        manifest_raw = manifest_path.read_bytes()
        assert hashlib.sha256(manifest_raw).hexdigest() == receipt["prepared_manifest_sha256"]
        manifest = json.loads(manifest_raw)
        assert manifest["generation_id"] == package["generation_id"]
        base = json.loads((work / "staging/base-manifest.json").read_text())
        files = {item["path"]: item for item in manifest["files"]}
        original = {item["path"]: item for item in base["files"]}
        overlay = {
            item["path"]: item for item in inventory["files"] if item["path"].startswith("raw/")
        }
        assert len(original) == 724 and len(overlay) == 53
        assert files.keys() == original.keys() | overlay.keys()
        assert len(files) == receipt["file_count"] == 775
        assert receipt["total_bytes"] == 403814381
        for name, item in original.items():
            if name not in inventory["append_only"]:
                assert files[name] == item, f"Existing snapshot object changed: {name}"
        for name, item in overlay.items():
            assert files[name] == item, f"Qualified overlay changed: {name}"
        for name, item in files.items():
            raw = (snapshot / name).read_bytes()
            assert len(raw) == item["size_bytes"]
            assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        assert sum(item["size_bytes"] for item in files.values()) == receipt["total_bytes"]
        # Use the pinned authenticated base, before changing to the local
        # consumer source; do not perform another NBA acquisition.
        for relative, binding in inventory["append_only"].items():
            verify_append(
                relative,
                data_path("data/" + relative).read_bytes(),
                (snapshot / relative).read_bytes(),
                binding,
            )
        ledgers = sorted((snapshot / "raw/player_game_availability").glob("*.csv"))
        assert len(ledgers) == 5
        assert sum(len(pd.read_csv(path)) for path in ledgers) == 950
        consumer_root = tmp_path / "consumer-root"
        consumer_root.mkdir()
        (consumer_root / "data").symlink_to(work / "staging/validation", target_is_directory=True)
        monkeypatch.setenv("DATA_SOURCE", "local")
        monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(consumer_root))
        monkeypatch.setenv("NBATOOLS_DATA_GENERATION", package["generation_id"])
        reset_data_source_cache()
        coverage = build_report(
            generation=package["generation_id"],
            manifest_sha256=receipt["prepared_manifest_sha256"],
            season="2025-26",
            team_id=1610612747,
            player_id=2544,
        )
        assert coverage["requested_games"] == coverage["observed_team_games"] == 82
        assert coverage["counts"] == qualification["observed_counts"]
        assert coverage["complete_requested_population"] and not coverage["missing_keys"]
        assert coverage["missed_games"] == 22
        from fastapi.testclient import TestClient

        from nbatools.api import app

        client = TestClient(app)
        answers = []
        assert len(package["deployed_checks"]) == 16
        for case in package["deployed_checks"]:
            response = client.post("/query", json={"query": case["query"]})
            assert response.status_code == 200
            answers.append(verify_answer(case, response.json()))
        count_answers = []
        for question, expected in [
            ("how many games did LeBron James miss in 2025-26", expected_ids),
            ("how many home games did LeBron James miss in 2025-26", expected_home),
        ]:
            payload = client.post("/query", json={"query": question}).json()
            assert payload["result_status"] == "ok" and payload["route"] == "game_finder"
            sections = payload["result"]["sections"]
            assert sections["count"] == [{"count": len(expected)}]
            assert len(sections["finder"]) == len(expected)
            assert {int(row["game_id"]) for row in sections["finder"]} == expected
            count_answers.append(
                dict(query=question, count=len(expected), game_ids=sorted(expected))
            )
        # The new 2025-26 positive does not qualify another season by omission.
        unknown = client.post(
            "/query", json={"query": "Lakers record without LeBron James in 2024-25"}
        ).json()
        assert unknown["result_status"] == "no_result"
        (work / "consumer-checks.json").write_text(
            json.dumps(
                dict(
                    classification="prepared_local_consumers_not_deployed",
                    registered_answers=answers,
                    exact_counts=count_answers,
                    unknown_season="2024-25",
                    coverage=coverage,
                ),
                indent=2,
            )
            + "\n"
        )

        # Unchanged backup/restore operates against a local file-backed store.
        # This does not read a live generation or expose a writer.
        class SnapshotStore:
            def get_object(self, *, Bucket, Key):
                if Key == "metadata/active_generation.json":
                    return {
                        "Body": io.BytesIO(
                            json.dumps(
                                dict(
                                    generation_id=package["generation_id"],
                                    manifest_sha256=receipt["prepared_manifest_sha256"],
                                )
                            ).encode()
                        )
                    }
                relative = Key.removeprefix(f"generations/{package['generation_id']}/")
                assert relative != Key and relative in {*files, "metadata/generation_manifest.json"}
                return {"Body": (snapshot / relative).open("rb")}

        backup_dir = tmp_path / "backup"
        backup = export_backup(
            backup_dir,
            package["generation_id"],
            client=SnapshotStore(),
            bucket="offline-prepared-snapshot",
        )
        restored = tmp_path / "restored"
        result = restore_backup(backup_dir / "generation.zip", backup, restored)
        assert result["production_writes"] == 0 and not result["r2_credentials_used"]
        assert backup["r2_writes"] == 0
        assert backup["files"] == receipt["file_count"] == 775
        assert backup["data_bytes"] == receipt["total_bytes"] == 403814381
        for name, item in files.items():
            assert hashlib.sha256((restored / name).read_bytes()).hexdigest() == item["sha256"]
        (work / "backup-compatibility.json").write_text(
            json.dumps(
                dict(
                    classification="local_prepared_snapshot_backup_only",
                    backup=backup,
                    restore=result,
                ),
                indent=2,
            )
            + "\n"
        )
    finally:
        reset_data_source_cache()
        target = os.environ.get("NBATOOLS_ACQUISITION_OUTPUT")
        if target:
            destination = Path(target) / "lebron-publication-preparation"
            destination.mkdir(parents=True, exist_ok=True)
            for source in [
                work / "prepared.json",
                work / "consumer-checks.json",
                work / "backup-compatibility.json",
                work / "staging/local-validation.json",
                work / "staging/base-manifest.json",
                work
                / "staging/validation/generations"
                / package["generation_id"]
                / "metadata/generation_manifest.json",
            ]:
                if source.exists():
                    shutil.copy2(source, destination / source.name)
