"""Explicit-only numerical audit; failed operational publication remains failed."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.audit_lebron_publication import (
    ARTIFACT,
    GENERATION,
    MANIFEST_SHA,
    PACKAGE,
    SOURCE_RUN,
    SOURCE_SHA,
)

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]


def test_audit_published_lebron_generation_without_readiness_waiver(tmp_path):
    assert os.environ["NBATOOLS_DATA_GENERATION"] == GENERATION
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
    work = tmp_path / "diagnostic"
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.audit_lebron_publication",
                "--publisher",
                str(publisher),
                "--work",
                str(work),
            ],
            cwd=ROOT,
            check=True,
        )
        result = json.loads((work / "diagnostic.json").read_text())
        assert result["evidence_type"] == "read_only_publication_numeric_diagnostic"
        assert result["diagnostic_complete"] and result["numeric_checks_complete"]
        assert (
            result["operational_acceptance_complete"] is False and result["production_writes"] == 0
        )
        assert result["source_publication_state"] == "published_verification_failed"
        source = result["source"]
        assert source["workflow_run_id"] == SOURCE_RUN and source["workflow_sha"] == SOURCE_SHA
        assert source["artifact_id"] == ARTIFACT and source["generation_id"] == GENERATION
        assert source["manifest_sha256"] == MANIFEST_SHA and source["verified_object_count"] == 775
        assert source["verified_object_bytes"] == 403814381
        assert result["pointer_before"] == result["pointer_after"]
        assert result["pointer_before"]["generation_id"] == GENERATION
        assert result["pointer_before"]["manifest_sha256"] == MANIFEST_SHA
        assert len(result["deployed_answers"]) == len(package["deployed_checks"]) == 16
        assert {
            row["index"] for row in result["deployed_query_attempts"] if row["status"] == 200
        } == set(range(1, 17))
        for key in ["readiness_before", "readiness_after"]:
            assert result[key]["classification"] in {"ready_observed", "new_season_not_loaded"}
            assert result[key]["body"]["active_generation"] == GENERATION
    finally:
        if (work / "diagnostic.json").exists():
            output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "lebron-publication-audit"
            output.mkdir(parents=True, exist_ok=True)
            shutil.copy2(work / "diagnostic.json", output / "diagnostic.json")
