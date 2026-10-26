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


def test_first_request_shared_team_comparison_profile(tmp_path):
    # Reproduce PR534's first query in a fresh process/cache. The default
    # profile reaches comparisons after other queries have warmed identity.
    report = _profile(
        tmp_path,
        "Compare Luka Doncic and Anthony Davis for the Lakers against the Warriors in 2024-25",
    )
    queries = [stage for stage in report["stages"] if "status" in stage]
    assert len(queries) == 2
    assert all(stage["route"] == "player_compare" for stage in queries)


@pytest.mark.parametrize("group", ["common", "historical"])
def test_k12_controlled_delivery_budgets(tmp_path, group):
    """Declared controlled cold/warm sample; production cold remains separate."""
    import hashlib
    import math
    import time
    from pathlib import Path
    from types import SimpleNamespace

    from tests.test_k12_delivery_real_data import _assert_case, _bindings, _qualified_sources

    oracle, sources = _qualified_sources()
    bindings = _bindings(oracle)
    common = ("K12-S1", "K12-R1", "K12-B1", "K12-M1")
    selected = common if group == "common" else ("K12-H1",)
    expected_cold = 2 * len(selected)
    expected_warm = 40 if group == "common" else 0
    samples, problems = [], []
    for ident in selected:
        for repetition in (1, 2):
            case = bindings[ident]
            cache = tmp_path / f"{ident}-{repetition}"
            env = dict(os.environ, NBATOOLS_R2_CACHE_DIR=str(cache))
            # An enlarged diagnostic cache is not production-equivalent evidence.
            for key in ("NBATOOLS_FRAME_CACHE_MAX_ENTRIES", "NBATOOLS_FRAME_CACHE_MAX_BYTES"):
                assert not env.get(key), f"Unexpected performance override: {key}"
            started = time.monotonic_ns()
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "nbatools.commands.ops.runtime_profile",
                        "--delivery-sample",
                        "--warm-repeats",
                        "5",
                        case["query"],
                    ],
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=180,
                )
                finished = time.monotonic_ns()
                assert result.returncode == 0, result.stderr[-4000:]
                measured = json.loads(result.stdout)
                cold = (measured["first_answer_monotonic_ns"] - started) / 1e9
                assert 0 < cold <= (finished - started) / 1e9
                assert measured["generation"] == oracle["generation_id"]
                assert measured["data_source"] == "r2"
                assert measured["initial_cache_files"] == 0
                assert measured["frame_cache_max_entries"] == 16
                assert measured["frame_cache_max_bytes"] == 128 * 1024**2
                payload = measured["first_payload"]
                body = payload["result"]
                _assert_case(
                    SimpleNamespace(
                        route=payload["route"],
                        metadata=body["metadata"],
                        result_status=payload["result_status"],
                        result_reason=payload["result_reason"],
                        result=SimpleNamespace(to_dict=lambda: body),
                    ),
                    case,
                    sources,
                )
                fingerprint = hashlib.sha256(
                    json.dumps(payload, sort_keys=True, allow_nan=False).encode()
                ).hexdigest()
                assert fingerprint == measured["first_fingerprint"]
                assert [item["index"] for item in measured["warm"]] == [1, 2, 3, 4, 5]
                for item in measured["warm"]:
                    assert item["fingerprint"] == fingerprint
                    assert item["status"] == "ok" and item["route"] == payload["route"]
                    assert item["seconds"] >= 0
                samples.append(
                    dict(
                        id=ident,
                        repetition=repetition,
                        cold_seconds=cold,
                        warm_seconds=[item["seconds"] for item in measured["warm"]],
                    )
                )
            except (AssertionError, ValueError, subprocess.TimeoutExpired) as error:
                problems.append(dict(id=ident, repetition=repetition, error=str(error)))
    warm = sorted(
        value for sample in samples if sample["id"] in common for value in sample["warm_seconds"]
    )
    report = dict(
        generation=oracle["generation_id"],
        scope="Controlled GitHub fresh-process R2; not Vercel cold-start acceptance",
        group=group,
        cold_expected=expected_cold,
        samples=samples,
        problems=problems,
        common_warm_expected=expected_warm,
        common_warm_executed=len(warm),
        common_warm_p95=warm[math.ceil(0.95 * len(warm)) - 1] if warm else None,
        common_by_case={
            ident: {
                "count": len(
                    values := sorted(
                        value
                        for sample in samples
                        if sample["id"] == ident
                        for value in sample["warm_seconds"]
                    )
                ),
                "p95": values[math.ceil(0.95 * len(values)) - 1] if values else None,
            }
            for ident in common
        },
    )
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / "k12-profile"
    output.mkdir(parents=True, exist_ok=True)
    (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    warnings.warn(RuntimeProfileReport("K12_MEASUREMENTS " + json.dumps(report)), stacklevel=1)
    assert not problems and len(samples) == expected_cold and len(warm) == expected_warm
    if expected_warm:
        assert report["common_warm_p95"] <= 3
    for sample in samples:
        assert sample["cold_seconds"] <= (10 if sample["id"] in common else 20), sample
        if sample["id"] == "K12-H1":
            assert max(sample["warm_seconds"]) <= 20
