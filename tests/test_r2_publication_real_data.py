"""Bounded read-only rebuild of the reviewed package against the complete live base."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]


def test_reviewed_opening_package_complete_snapshot_prepare(tmp_path):
    policy = json.loads((ROOT / ".github/data-publication-packages.json").read_text())
    package = policy["packages"]["opening-availability-v1"]
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
    work = tmp_path / "prepared"
    audit = tmp_path / "audit"
    command = [sys.executable, str(ROOT / "tools/r2_publication.py")]
    subprocess.run(command + ["audit", "--work", str(audit)], check=True)
    try:
        subprocess.run(
            command + ["prepare", "--publisher", str(publisher), "--work", str(work)], check=True
        )
        receipt = json.loads((work / "prepared.json").read_text())
        assert receipt["publication_state"] == "prepared_no_writes"
        assert receipt["publisher_sha"] == package["publisher_sha"]
        assert receipt["file_count"] > 8
        assert receipt["total_bytes"] > 375400
        assert receipt["required_source_gate"]["executed"] > 0
        assert receipt["budget"]["conservative_projected_bytes"] <= policy["max_bucket_bytes"]
        assert not (work / "publication.json").exists()
    finally:
        output = os.environ.get("NBATOOLS_ACQUISITION_OUTPUT")
        if output:
            destination = Path(output) / "publication-preparation"
            destination.mkdir(parents=True, exist_ok=True)
            for source in (
                audit / "environment-audit.json",
                work / "prepared.json",
                work / "staging/local-validation.json",
                work / "staging/base-manifest.json",
                work
                / "staging/validation/generations"
                / package["generation_id"]
                / "metadata/generation_manifest.json",
            ):
                if source.exists():
                    shutil.copy2(source, destination / source.name)
