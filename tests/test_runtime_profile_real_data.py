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


def _profile(tmp_path, *queries: str, **env_overrides: str) -> dict:
    env = dict(os.environ, NBATOOLS_R2_CACHE_DIR=str(tmp_path / "r2-cache"), **env_overrides)
    completed = subprocess.run(
        [sys.executable, "-m", "nbatools.commands.ops.runtime_profile", *queries],
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
    return report


def test_cold_start_profile(tmp_path):
    _profile(tmp_path)


def test_career_query_with_a_frame_cache_that_holds_every_season(tmp_path):
    # Sizing evidence: the default frame cache (16 frames) cannot hold a
    # 30-season career, so every career query re-parses every season. Report
    # the time and memory with room for all of them.
    _profile(
        tmp_path,
        "LeBron James career stats",
        NBATOOLS_FRAME_CACHE_MAX_ENTRIES="256",
        NBATOOLS_FRAME_CACHE_MAX_BYTES=str(2 * 1024**3),
    )
