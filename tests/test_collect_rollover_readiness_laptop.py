"""Finite standalone package preserves original responses and fails closed."""

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import requests

from tools import collect_rollover_readiness_laptop as collector
from tools.collection_bundle import unpack

ROOT = Path(__file__).resolve().parents[1]


def request():
    jobs = [
        dict(
            endpoint=name,
            source_file=f"sources/{name}_0022600001_q1.json",
            parameters=dict(
                GameID="0022600001",
                StartPeriod=1,
                EndPeriod=1,
                RangeType=1,
                StartRange=0,
                EndRange=28800,
            ),
        )
        for name in ["boxscoretraditionalv3", "boxscoreadvancedv3"]
    ]
    return dict(
        status="collection_requirement_not_publication_approval",
        season="2026-27",
        season_type="Regular Season",
        base_generation="availability-lebron-season-v1-20261031",
        base_manifest_sha256="3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3",
        jobs=jobs,
        maximum_requests=2,
        attempts_per_job=1,
        timeout_seconds=30,
        response_limit_bytes=2_000_000,
        minimum_interval_seconds=1,
        maximum_elapsed_seconds=90,
    )


def originals():
    archive = ROOT / "work/period-milestone/collection.zip"
    if not archive.exists():
        archive = (
            ROOT
            / "working/nba-tools-completion-program/source-evidence/rollover-2026-27/q1-laptop-capture/collection.zip"
        )
    with zipfile.ZipFile(archive) as handle:
        return [handle.read(job["source_file"]) for job in request()["jobs"]]


class Response:
    def __init__(self, raw, status=200):
        self.raw, self.status_code = raw, status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def iter_content(self, size):
        yield self.raw

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("controlled failure")


def fake_client(monkeypatch, payloads, failure=None):
    calls = []
    sleeps = []

    class HTTP:
        headers = {"User-Agent": "standard existing SDK fixture"}

        def get_session(self):
            return self

        def get(self, **kwargs):
            index = len(calls)
            calls.append(kwargs)
            if index == 1 and failure in {"timeout", "interrupt"}:
                if failure == "interrupt":
                    raise KeyboardInterrupt()
                raise requests.ReadTimeout("controlled")
            raw = payloads[index]
            if index == 1 and failure == "invalid_json":
                raw = b"original invalid JSON body"
            if index == 1 and failure == "oversized":
                raw = b"x" * 2_000_001
            status = (
                302
                if index == 1 and failure == "redirect"
                else 403
                if index == 1 and failure == "403"
                else 200
            )
            return Response(raw, status)

    monkeypatch.setattr(
        collector, "_client", lambda job: (HTTP(), "https://stats.nba.com/stats/" + job["endpoint"])
    )
    monkeypatch.setattr(collector.time, "sleep", sleeps.append)
    return calls, sleeps


def test_actual_original_q1_replay_through_standalone_data_bundle(tmp_path, monkeypatch):
    raw = originals()
    assert [hashlib.sha256(item).hexdigest() for item in raw] == [
        "613712a1703f8ad393e0c4a48ab782013bb3322a74234a8d514baac35c03c35b",
        "3f692a446ec0ed1f3cb622353bd1c28c87268f65e73f63dce1c0b879819666ab",
    ]
    calls, sleeps = fake_client(monkeypatch, raw)
    output = tmp_path / "capture"
    plan = request()
    report = collector.collect(output, plan)
    assert report["transport_finished"] and not report["canonical_period_accepted"]
    assert report["production_writes"] == 0 and len(calls) == 2 and sleeps == [1]
    for index, call in enumerate(calls):
        assert call == dict(
            url="https://stats.nba.com/stats/" + plan["jobs"][index]["endpoint"],
            params=sorted(plan["jobs"][index]["parameters"].items()),
            headers={"User-Agent": "standard existing SDK fixture"},
            timeout=30,
            stream=True,
            allow_redirects=False,
        )
    unpack(output / "collection.zip", plan, tmp_path / "unpacked")
    for job, body in zip(plan["jobs"], raw, strict=True):
        assert (tmp_path / "unpacked" / job["source_file"]).read_bytes() == body
    # Completed rerun does not touch network or create new attempts.
    assert collector.collect(output, plan)["transport_finished"]
    assert len(calls) == 2
    assert "headers" not in (output / "acquisition.json").read_text()


@pytest.mark.parametrize(
    "failure", ["timeout", "interrupt", "403", "redirect", "invalid_json", "oversized"]
)
def test_failure_preserves_success_and_failed_body_and_forbids_implicit_retry(
    tmp_path, monkeypatch, failure
):
    raw = originals()
    calls, _ = fake_client(monkeypatch, raw, failure)
    plan = request()
    plan["jobs"].append(
        dict(
            endpoint="boxscoretraditionalv3",
            source_file="sources/unattempted.json",
            parameters={**plan["jobs"][0]["parameters"], "StartPeriod": 2, "EndPeriod": 2},
        )
    )
    plan["maximum_requests"] = 3
    output = tmp_path / "capture"
    report = collector.collect(output, plan)
    assert not report["transport_finished"] and len(calls) == 2
    assert report["unattempted_jobs"] == plan["jobs"][2:]
    assert (output / plan["jobs"][0]["source_file"]).read_bytes() == raw[0]
    unpack(output / "collection.zip", plan, tmp_path / "unpacked")
    failed = report["attempts"][1]
    assert failed["error_type"] and failed["response_bytes"] <= 2_000_000
    if failure in {"403", "redirect", "invalid_json", "oversized"}:
        assert (output / failed["source_file"]).read_bytes()
    collector.collect(output, plan)
    assert len(calls) == 2


@pytest.mark.parametrize("damage", ["hash", "plan", "extra", "symlink"])
def test_existing_capture_must_match_exact_request_and_bytes_before_any_network(
    tmp_path, monkeypatch, damage
):
    calls, _ = fake_client(monkeypatch, originals())
    plan = request()
    output = tmp_path / "capture"
    collector.collect(output, plan)
    path = output / plan["jobs"][0]["source_file"]
    if damage == "hash":
        path.write_bytes(b"changed")
    elif damage == "plan":
        plan["jobs"][0]["parameters"]["EndPeriod"] = 2
    elif damage == "extra":
        (output / "sources/extra.json").write_text("{}")
    elif damage == "symlink":
        path.unlink()
        path.symlink_to(tmp_path / "elsewhere")
    with pytest.raises(ValueError):
        collector.collect(output, plan)
    assert len(calls) == 2


@pytest.mark.parametrize(
    "damage", ["host", "name", "count", "range", "attempts", "timeout", "deadline", "jobs"]
)
def test_finite_request_rejects_scope_expansion(damage):
    plan = request()
    if damage == "host":
        plan["jobs"][0]["endpoint"] = "https://elsewhere"
    elif damage == "name":
        plan["jobs"][0]["source_file"] = "sources/../credentials.json"
    elif damage == "count":
        plan["maximum_requests"] = 3
    elif damage == "range":
        plan["jobs"][0]["parameters"]["EndRange"] = 0
    elif damage == "attempts":
        plan["attempts_per_job"] = 2
    elif damage == "timeout":
        plan["timeout_seconds"] = 60
    elif damage == "deadline":
        plan["maximum_elapsed_seconds"] = 99999
    elif damage == "jobs":
        plan["jobs"] *= 601
        plan["maximum_requests"] = len(plan["jobs"])
    with pytest.raises(ValueError):
        collector.validate_request(plan)


def test_installed_sdk_creates_exact_fixed_parameters_without_request():
    for job in request()["jobs"]:
        http, url = collector._client(job)
        assert url == "https://stats.nba.com/stats/" + job["endpoint"]
        assert http.headers
    from nba_api.stats.endpoints import LeagueDashPlayerStats, LeagueDashTeamStats

    for cls in [LeagueDashPlayerStats, LeagueDashTeamStats]:
        obj = cls(
            season="2026-27",
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
            date_to_nullable="10/31/2026",
            get_request=False,
        )
        job = dict(
            endpoint=obj.endpoint, source_file="sources/snapshot.json", parameters=obj.parameters
        )
        plan = request()
        plan["jobs"] = [job]
        plan["maximum_requests"] = 1
        collector.validate_request(plan)
        assert collector._client(job)[1].endswith(obj.endpoint)
        job["parameters"] = {**obj.parameters, "TeamID": 1610612747}
        with pytest.raises(ValueError, match="SDK parameters differ"):
            collector._client(job)


def test_generated_single_file_needs_no_repo_or_source_selection(tmp_path):
    path = tmp_path / "run_readiness_capture.py"
    plan = request()
    binding = collector.build_package(plan, path)
    assert binding["request_sha256"] == collector.validate_request(plan)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == binding["package_sha256"]
    outcome = subprocess.run(
        [sys.executable, "-S", str(path), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert outcome.returncode == 0 and "--output" in outcome.stdout
    assert "from tools" not in path.read_text() and "from nbatools" not in path.read_text()
    namespace = {"__name__": "reviewed_package"}
    exec(compile(path.read_text(), str(path), "exec"), namespace)
    assert namespace["EMBEDDED_REQUEST"] == plan
    assert namespace["EMBEDDED_SHA256"] == collector.validate_request(plan)
    with pytest.raises(FileExistsError):
        collector.build_package(plan, path)


def test_elapsed_and_size_limits_stop_without_extra_requests(tmp_path, monkeypatch):
    calls, _ = fake_client(monkeypatch, originals())
    plan = request()
    plan["maximum_elapsed_seconds"] = 1
    report = collector.collect(tmp_path / "elapsed", plan)
    assert report["stop_reason"] == "elapsed_limit" and not calls
    assert report["unattempted_jobs"] == plan["jobs"]
    unpack(tmp_path / "elapsed/collection.zip", plan, tmp_path / "unpacked")


def test_proven_v112_unset_round_parameter_is_transport_equivalent():
    from nba_api.stats.endpoints import LeagueDashPlayerStats

    endpoint = LeagueDashPlayerStats(
        season="2026-27",
        measure_type_detailed_defense="Advanced",
        per_mode_detailed="PerGame",
        date_to_nullable="10/31/2026",
        get_request=False,
    )
    parameters = {**endpoint.parameters, "ISTRound": None}
    job = dict(
        endpoint=endpoint.endpoint, source_file="sources/advanced.json", parameters=parameters
    )
    assert collector._client(job)[1].endswith("leaguedashplayerstats")
    prepared = requests.Request(
        "GET",
        "https://stats.nba.com/stats/leaguedashplayerstats",
        params=sorted(parameters.items()),
    ).prepare()
    assert "ISTRound" not in prepared.url
    job["parameters"]["ISTRound"] = "Finals"
    with pytest.raises(ValueError, match="tournament-round"):
        collector._client(job)


def test_owner_zip_launchers_select_existing_python_and_need_no_arguments(tmp_path):
    output = tmp_path / "capture package.zip"
    plan = request()
    binding = collector.build_owner_bundle(plan, output)
    assert binding["owner_bundle_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    unpacked = tmp_path / "unpacked with spaces"
    unpacked.mkdir()
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == {
            "run_capture.py",
            "Run Capture.command",
            "Run Capture.bat",
            "READ ME.txt",
        }
        assert archive.getinfo("Run Capture.command").external_attr >> 16 == 0o100755
        archive.extractall(unpacked)
    response = subprocess.run(
        ["sh", "-n", str(unpacked / "Run Capture.command")], capture_output=True, timeout=5
    )
    assert response.returncode == 0
    scripts = tmp_path / "bin"
    scripts.mkdir()
    log = tmp_path / "arguments.txt"
    fake_python = scripts / "python3"
    fake_python.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{log}"\nexit 0\n')
    fake_python.chmod(0o755)
    # A fake interpreter proves launcher control flow without executing downloads/network.
    import os

    response = subprocess.run(
        ["sh", str(unpacked / "Run Capture.command")],
        env={**os.environ, "PATH": str(scripts) + ":/usr/bin:/bin"},
        input="\n",
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert response.returncode == 0
    assert log.read_text().splitlines() == ["-c import nba_api", "run_capture.py"]
    assert "pip" not in (unpacked / "Run Capture.bat").read_text()
    assert "py -3" in (unpacked / "Run Capture.bat").read_text()
    assert "Return readiness-capture" in response.stdout


def test_exact_1061_job_package_preflights_every_sdk_request_and_self_contains_plan(tmp_path):
    path = (
        ROOT
        / "working/nba-tools-completion-program/collection-requests/rollover-period-readiness-2026-27.json"
    )
    plan = json.loads(path.read_bytes())
    assert (
        collector.validate_request(plan)
        == "4a30c59cc6753fb060359b09d12b9b24c49e65851fb880d57e7154079959f1e0"
    )
    assert len(plan["jobs"]) == plan["maximum_requests"] == 1061
    for job in plan["jobs"]:
        assert collector._client(job)[1] == "https://stats.nba.com/stats/" + job["endpoint"]
    package = tmp_path / "run_capture.py"
    collector.build_package(plan, package)
    namespace = {"__name__": "preflight_only"}
    exec(compile(package.read_text(), str(package), "exec"), namespace)
    assert namespace["EMBEDDED_REQUEST"] == plan
    assert (
        namespace["validate_request"](namespace["EMBEDDED_REQUEST"]) == namespace["EMBEDDED_SHA256"]
    )
    # Preflight every embedded job too; none sends a network request.
    for job in namespace["EMBEDDED_REQUEST"]["jobs"]:
        assert namespace["_client"](job)[1] == "https://stats.nba.com/stats/" + job["endpoint"]
