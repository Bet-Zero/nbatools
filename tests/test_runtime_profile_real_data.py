"""Cold-start time profile against the served data (informational).

Runs ``nbatools.commands.ops.runtime_profile`` in a fresh process with an
empty data cache, as a deployed function starts, and reports the stage timings
in the warnings summary of the run log. It asserts only that the queries
answered; the timings are evidence for performance work, not a gate.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import warnings

import pytest

pytestmark = [pytest.mark.needs_data]


class RuntimeProfileReport(UserWarning):
    """Carries the profile into the pytest warnings summary."""


def test_cold_start_profile(tmp_path):
    env = dict(os.environ, NBATOOLS_R2_CACHE_DIR=str(tmp_path / "r2-cache"))
    completed = subprocess.run(
        [sys.executable, "-m", "nbatools.commands.ops.runtime_profile"],
        capture_output=True,
        text=True,
        env=env,
        timeout=900,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-4000:]
    report = json.loads(completed.stdout)
    warnings.warn(RuntimeProfileReport("\n" + json.dumps(report, indent=1)), stacklevel=1)
    assert all(item.get("status", "ok") == "ok" for item in report["stages"]), report
