"""Explicit-only read-only recovery; ordinary suites must not invoke operations."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.recover_k08_publication import PACKAGE, SOURCE_RUN, SOURCE_SHA

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]


def test_recover_published_k08_generation(tmp_path):
    generation = "availability-k08-retained-v1-20261031"
    assert os.environ["NBATOOLS_DATA_GENERATION"] == generation
    package = json.loads((ROOT / ".github/data-publication-packages.json").read_text())["packages"][
        PACKAGE
    ]
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
    work = tmp_path / "verified"
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.recover_k08_publication",
                "--publisher",
                str(publisher),
                "--work",
                str(work),
            ],
            cwd=ROOT,
            check=True,
        )
        receipt = json.loads((work / "receipt.json").read_text())
        assert receipt["publication_state"] == "published_and_verified"
        assert receipt["workflow_sha"] == SOURCE_SHA
        assert receipt["workflow_run_id"] == str(SOURCE_RUN)
        assert receipt["recovery"]["workflow_sha"] == os.environ["VALIDATION_SHA"]
        assert receipt["recovery"]["production_writes"] == 0
        assert receipt["generation_id"] == generation
        assert (
            receipt["prepared_manifest_sha256"]
            == "de83522f37f6bd7f26b51c1bf869deb05bbe242d3249d685997a979c050d16a9"
        )
        assert len(receipt["verified_objects"]) == receipt["file_count"] == 724
        assert receipt["total_bytes"] == 402948225
        assert receipt["deployed_readiness"]["active_generation"] == generation
        assert len(receipt["deployed_answers"]) == len(package["deployed_checks"]) == 13
        assert {
            row["index"] for row in receipt["deployed_query_attempts"] if row["status"] == 200
        } == set(range(1, 14))
    finally:
        if (work / "receipt.json").exists():
            output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "publication-recovery"
            output.mkdir(parents=True, exist_ok=True)
            shutil.copy2(work / "receipt.json", output / "recovery-receipt.json")
