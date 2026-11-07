"""Bounded196new-window source reads through the established acquisition collector."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from nbatools.data_source import data_generation_context, data_path
from tools.collect_rollover_readiness_laptop import collect, validate_request

ROOT = Path(__file__).resolve().parents[1]
REQUEST = (
    ROOT
    / "working/nba-tools-completion-program/collection-requests/current123-new16-periods-20261107.json"
)
DENOMINATOR = (
    ROOT
    / "working/nba-tools-completion-program/source-evidence/core-live-current-20261107/new16-window-denominator.json"
)
REQUEST_SHA = "e06682b8da8eb4b4b5c1a627566b617ae9e0e4fffa70d69f675c4b6f71868268"
pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def prepare_request():
    raw = REQUEST.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == REQUEST_SHA
    request = json.loads(raw)
    validate_request(request)
    original = DENOMINATOR.read_bytes()
    assert hashlib.sha256(original).hexdigest() == request["denominator_sha256"]
    source = json.loads(original)
    games = {r["game_id"]: r for r in source["new16"]}
    assert set(games) == {f"00226{n:05d}" for n in range(173, 189)}
    assert sum(r["required_quarter_half_windows"] for r in games.values()) == 98
    assert request["source_period_windows"] == 745
    expected = set()
    for gid, game in games.items():
        windows = [(1, 1), (2, 2), (3, 3), (4, 4), (1, 2), (3, 4)]
        if game["ot"]:
            windows.append((5, 14))
        for start, end in windows:
            for ep in ["boxscoretraditionalv3", "boxscoreadvancedv3"]:
                expected.add((gid, ep, start, end))
    jobs = request["jobs"]
    actual = {
        (
            j["parameters"]["GameID"],
            j["endpoint"],
            j["parameters"]["StartPeriod"],
            j["parameters"]["EndPeriod"],
        )
        for j in jobs
    }
    assert len(jobs) == len(actual) == len(expected) == 196
    assert actual == expected
    assert request["attempts_per_job"] == 1 and request["maximum_elapsed_seconds"] == 1050
    assert request["minimum_interval_seconds"] == 1
    return request


def test_capture_only_actual_new16_required_period_sources():
    request = prepare_request()
    with data_generation_context() as generation:
        assert generation == request["base_generation"]
        raw = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == request["base_manifest_sha256"]
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "current123-new16-periods"
    report = collect(output, request)
    assert report["production_writes"] == 0 and report["canonical_period_accepted"] is False
    assert report["transport_finished"], report.get("stop_reason")
    assert len(report["attempts"]) == 196 and not report["unattempted_jobs"]
    assert all(r["transport_complete"] for r in report["attempts"])
