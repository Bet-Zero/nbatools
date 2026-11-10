"""Required scorer-qualified ownership admission on the unchanged v6 source bytes."""

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from nbatools.data_source import data_generation_context, data_path
from nbatools.development_data import sha256

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_scorer_qualified_player_team_ownership(tmp_path):
    with data_generation_context() as generation:
        assert generation == "availability-lebron-season-v1-20261031"
        raw = data_path("metadata/generation_manifest.json").read_bytes()
        assert sha256(raw) == "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
        assert len(json.loads(raw)["files"]) == 775
    junit = tmp_path / "ownership.xml"
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-n",
            "0",
            "-q",
            "tests/test_player_team_ownership.py",
            f"--junitxml={junit}",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=dict(os.environ, DATA_SOURCE="local"),
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert run.returncode == 0, run.stdout[-18000:] + run.stderr[-2000:]
    suite = ET.parse(junit).getroot().find("testsuite")
    assert suite is not None and int(suite.attrib["tests"]) == 25
    assert all(int(suite.attrib[k]) == 0 for k in ("errors", "failures", "skipped"))
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "player-team-ownership"
    output.mkdir(parents=True, exist_ok=False)
    (output / "controls.xml").write_bytes(junit.read_bytes())
    (output / "acceptance.json").write_text(
        json.dumps(
            dict(
                candidate_sha=os.environ["VALIDATION_SHA"],
                generation=generation,
                controls=25,
                passed=25,
                skipped=0,
                failures=0,
                new_source_requests=0,
                production_writes=0,
                development_manifest_sha256="e46b6748887d263a342b44dd896e6f4cd2619fd824428f4842dda5be0ac380b7",
                original_question_rebounds=4,
                corrected_quarter_rebounds=1,
                source_values_changed=False,
                complete_current_snapshot_accepted=False,
            ),
            indent=2,
        )
        + "\n"
    )
