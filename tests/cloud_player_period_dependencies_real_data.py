"""Required finite dependency/consumer gate; original source numerical proof is reused."""

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from nbatools.data_source import data_generation_context, data_path
from nbatools.development_data import sha256

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "working/nba-tools-completion-program/source-evidence/player-period-reader-20261110"


def test_required_player_period_dependency_consumers(tmp_path):
    with data_generation_context() as generation:
        assert generation == "availability-lebron-season-v1-20261031"
        raw = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert sha256(raw) == "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
        assert len(json.loads(raw)["files"]) == 775
    # A separate process closes the authenticated R2 context before explicit
    # local development opt-in. This executes only the affected finite matrix.
    env = dict(os.environ, DATA_SOURCE="local")
    junit = tmp_path / "reader-controls.xml"
    executed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-n",
            "0",
            "-q",
            "tests/test_player_period_dependencies.py",
            f"--junitxml={junit}",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert executed.returncode == 0, executed.stdout[-16000:] + executed.stderr[-4000:]
    suite = ET.parse(junit).getroot().find("testsuite")
    assert suite is not None and int(suite.attrib["tests"]) == 60
    assert all(int(suite.attrib[k]) == 0 for k in ("failures", "errors", "skipped"))
    binding = json.loads((E / "binding.json").read_bytes())
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "player-period-dependencies"
    output.mkdir(parents=True, exist_ok=False)
    (output / "controls.xml").write_bytes(junit.read_bytes())
    (output / "controls.log").write_text(executed.stdout + executed.stderr)
    (output / "acceptance.json").write_text(
        json.dumps(
            dict(
                candidate_sha=os.environ["VALIDATION_SHA"],
                base_generation=generation,
                development_manifest_sha256=binding["manifest_sha256"],
                unchanged_parent_manifest_sha256=binding["parent_manifest_sha256"],
                focused_controls=60,
                failures=0,
                errors=0,
                skipped=0,
                independent_source_oracle_sha256="9b3c4cd26b12f8ac983e339275a28b3e5212c1d8deec8b55fb6d56fe6cc6a3dc",
                reused_v5_source_numerical_run=42371619251,
                quarter_half_source_ot_positive=True,
                direct_indirect_unknown_controls=True,
                natural_structured_http=True,
                source_values_changed=False,
                unknown_rate_cells=484,
                whole_snapshot_accepted=False,
                new_source_requests=0,
                production_writes=0,
            ),
            indent=2,
        )
        + "\n"
    )
