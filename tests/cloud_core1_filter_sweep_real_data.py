"""Execute the unchanged complete P3 filter tool through the existing R2 route.

This avoids replaying unrelated public-browser suites merely to select the
workflow's existing sweep. It does not substitute for full release validation.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from nbatools.data_source import data_generation_context, data_path
from nbatools.development_data import selected_snapshot

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ROOT = Path(__file__).resolve().parents[1]


def test_existing_complete_filter_execution_sweep():
    assert selected_snapshot() is None
    with data_generation_context() as generation:
        assert generation == "availability-lebron-season-v1-20261031"
        assert hashlib.sha256(
            data_path("metadata/generation_manifest.json").read_bytes()
        ).hexdigest() == ("3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3")
    tool = ROOT / "tools/filter_execution_sweep.py"
    config = ROOT / "qa/filter_execution_sweep.yaml"
    assert hashlib.sha256(tool.read_bytes()).hexdigest() == (
        "7bc9b605d169c973117d681c149e7ff6df3a5bfa126d9f189491a50024e57052"
    )
    config_sha = hashlib.sha256(config.read_bytes()).hexdigest()
    assert config_sha == "4201f3875a8dfc551a2c307e7058903c3f9b0926253d67d8535f6a8b3ada0653"
    inputs = yaml.safe_load(config.read_bytes())
    expected = {
        (seed["id"], flt["id"])
        for seed in inputs["seeds"]
        for flt in inputs["filters"]
        if seed["id"] not in (flt.get("skip_seeds") or [])
    }
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "core1-existing-filter-sweep"
    output.mkdir(parents=True, exist_ok=False)
    report = output / "complete-existing-sweep.json"
    command = [sys.executable, str(tool), "--json", str(report)]
    try:
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=3300)
    except subprocess.TimeoutExpired as exc:
        (output / "partial-tool-output.log").write_bytes((exc.stdout or b"") + (exc.stderr or b""))
        raise
    (output / "tool-output.log").write_text(run.stdout + run.stderr)
    assert report.is_file(), run.stdout[-4000:] + run.stderr[-2000:]
    result = json.loads(report.read_bytes())
    summary, rows = result["summary"], result["rows"]
    assert summary["data_generation"] == generation
    assert summary["config_sha256"] == config_sha and summary["only"] is None
    assert summary["configured_comparisons"] == len(rows) == len(expected)
    assert {(r["seed"], r["filter"]) for r in rows} == expected
    print("EXISTING_COMPLETE_FILTER_SWEEP " + json.dumps(summary, sort_keys=True))
    assert run.returncode == summary["exit_code"] == 0, run.stdout[-16000:] + run.stderr[-2000:]
