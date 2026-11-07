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


def test_recover_retained_failed_capture_without_source_retry():
    """Recover one immutable artifact through the existing read-only runner.

    Cloud-local egress cannot reach GitHub's artifact CDN. This bounded custody
    replay transfers the already existing public-source failure package; no NBA
    reader, collection retry or new credential is involved. Not a completeness test.
    """
    import base64
    import io
    from zipfile import ZipFile

    import requests

    artifact = 13562477912
    expected = "f56d9c78c3df5c0c81c6d89e06ab99e147dfaa883b7f21a65ce5886bdfaefcfd"
    url = f"https://api.github.com/repos/Bet-Zero/nbatools/actions/artifacts/{artifact}/zip"
    # requests strips Authorization on a cross-host artifact redirect.
    with requests.get(
        url, headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"]}, timeout=30, stream=True
    ) as response:
        response.raise_for_status()
        raw = bytearray()
        for chunk in response.iter_content(8192):
            raw.extend(chunk)
            assert len(raw) <= 100_000
    raw = bytes(raw)
    assert len(raw) == 16637 and hashlib.sha256(raw).hexdigest() == expected
    with ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert all(not Path(n).is_absolute() and ".." not in Path(n).parts for n in names)
        assert all(
            n in {"summary.json", "junit.xml"}
            or n.startswith("acquired_data/current123-new16-periods/")
            for n in names
        )
        summary = json.loads(z.read("summary.json"))
        assert (
            summary["selected"],
            summary["executed"],
            summary["passed"],
            summary["failed"],
            summary["skipped"],
        ) == (1, 1, 0, 1, 0)
        assert summary["candidate_sha"] == "f6b576c3f2d44bf03de17d81bbb1d0af77301a3c"
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "retained-period-failure"
    output.mkdir(parents=True, exist_ok=False)
    (output / "original-artifact.zip").write_bytes(raw)
    # Exact bounded, non-secret public-source/request/JUnit bytes are retained in
    # the existing job log so this temporary artifact is not the sole handoff.
    print("RETAINED_PERIOD_ARTIFACT_BASE64=" + base64.b64encode(raw).decode())
    print("RETAINED_PERIOD_ARTIFACT_SHA256=" + expected)
