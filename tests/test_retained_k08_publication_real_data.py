"""Complete prepared snapshot, consumer and backup gate; no production writes."""

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

from nbatools.data_source import reset_data_source_cache
from tools.availability_overlay import verify_append
from tools.cloud_backup import export_backup, restore_backup
from tools.r2_publication import verify_answer

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "retained-k08-availability-v1"


def test_retained_k08_complete_snapshot_prepare(tmp_path, monkeypatch):
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
    work = tmp_path / "prepared"
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
    try:
        receipt = json.loads((work / "prepared.json").read_text())
        assert receipt["publication_state"] == "prepared_no_writes"
        assert receipt["base_manifest_sha256"] == inventory["base_manifest_sha256"]
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
        assert len(original) == 703
        assert files.keys() == original.keys() | overlay.keys()
        assert len(files) == receipt["file_count"] == 724
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
        # Reuse the authenticated base downloaded by the producer for byte-exact
        # append assertions; no second source acquisition or remote write.
        from nbatools.data_source import data_path

        for relative, binding in inventory["append_only"].items():
            verify_append(
                relative,
                data_path("data/" + relative).read_bytes(),
                (snapshot / relative).read_bytes(),
                binding,
            )
        ledgers = sorted((snapshot / "raw/player_game_availability").glob("*.csv"))
        assert len(ledgers) == 5
        assert sum(len(pd.read_csv(path)) for path in ledgers) == 352
        consumer_root = tmp_path / "consumer-root"
        consumer_root.mkdir()
        (consumer_root / "data").symlink_to(work / "staging/validation", target_is_directory=True)
        monkeypatch.setenv("DATA_SOURCE", "local")
        monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(consumer_root))
        monkeypatch.setenv("NBATOOLS_DATA_GENERATION", package["generation_id"])
        reset_data_source_cache()
        from fastapi.testclient import TestClient

        from nbatools.api import app

        client = TestClient(app)
        answers = []
        for case in package["deployed_checks"]:
            response = client.post("/query", json={"query": case["query"]})
            assert response.status_code == 200
            answers.append(verify_answer(case, response.json()))
        assert len(answers) == 13
        # Broader season completeness is still unknown after these six games.
        unknown = client.post(
            "/query", json={"query": "Lakers record without LeBron James in 2025-26"}
        ).json()
        assert unknown["result_status"] == "no_result"
        (work / "consumer-checks.json").write_text(json.dumps(answers, indent=2) + "\n")

        # Exercise the unchanged backup exporter/restore against this exact local
        # full snapshot through a read-only file-backed store, never a live writer.
        class SnapshotStore:
            def get_object(self, *, Bucket, Key):
                if Key == "metadata/active_generation.json":
                    return {
                        "Body": io.BytesIO(
                            json.dumps(
                                {
                                    "generation_id": package["generation_id"],
                                    "manifest_sha256": receipt["prepared_manifest_sha256"],
                                }
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
        assert result["production_writes"] == 0
        assert backup["files"] == receipt["file_count"]
        assert backup["data_bytes"] == receipt["total_bytes"]
        for name, item in files.items():
            assert hashlib.sha256((restored / name).read_bytes()).hexdigest() == item["sha256"]
        (work / "backup-compatibility.json").write_text(
            json.dumps(dict(backup=backup, restore=result), indent=2) + "\n"
        )
    finally:
        reset_data_source_cache()
        target = os.environ.get("NBATOOLS_ACQUISITION_OUTPUT")
        if target:
            destination = Path(target) / "retained-k08-publication-preparation"
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
