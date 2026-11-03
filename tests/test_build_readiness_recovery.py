"""Exact partial-capture recovery has no successful repeats or safety changes."""

import copy
import hashlib
import json
import os
import subprocess
import zipfile
from datetime import UTC, datetime, timedelta

import pytest

from tools import build_readiness_recovery as recovery
from tools import collect_rollover_readiness_laptop as collector
from tools.collection_bundle import create


@pytest.fixture
def partial(tmp_path):
    parent = json.loads(recovery.PARENT_PATH.read_bytes())
    source = tmp_path / "original"
    (source / "sources").mkdir(parents=True)
    started = datetime(2026, 11, 2, 5, 46, tzinfo=UTC)
    attempts = []
    for index, job in enumerate(parent["jobs"][:603]):
        failed = index == 602
        begin = started + timedelta(seconds=index * 2)
        end = begin + timedelta(seconds=30 if failed else 1)
        raw = b"" if failed else json.dumps({"controlled_test_source_index": index}).encode()
        if raw:
            (source / job["source_file"]).write_bytes(raw)
        attempt = dict(
            job=copy.deepcopy(job),
            endpoint=job["endpoint"],
            parameters=copy.deepcopy(job["parameters"]),
            url="https://stats.nba.com/stats/" + job["endpoint"],
            started_at=begin.isoformat(),
            finished_at=end.isoformat(),
            attempts=1,
            timeout_seconds=30,
            http_status=None if failed else 200,
            response_complete=not failed,
            transport_complete=not failed,
            response_bytes=len(raw),
            response_sha256=hashlib.sha256(raw).hexdigest(),
            source_file=None if failed else job["source_file"],
        )
        if failed:
            attempt["error_type"] = "ReadTimeout"
        attempts.append(attempt)
    metadata = dict(
        classification="unvalidated_laptop_source_capture_not_publication",
        source="NBA Stats",
        captured_at=started.isoformat(),
        parameters="per-job exact request",
        request=parent,
        request_sha256=recovery.PARENT_SHA256,
        nba_api_version="1.12.0",
        production_writes=0,
        canonical_period_accepted=False,
        transport_finished=False,
        attempts=attempts,
        unattempted_jobs=copy.deepcopy(parent["jobs"][603:]),
        finished_at=attempts[-1]["finished_at"],
    )
    return source, parent, metadata


def archive_partial(partial, path):
    source, parent, metadata = partial
    raw = json.dumps(metadata, indent=2).encode()
    (source / "acquisition.json").write_bytes(raw)
    (source / "sources/capture-attempt.json").write_bytes(raw)
    create(source, parent, path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exact_recovery_partition_keeps_every_successful_source(tmp_path, partial):
    source, parent, metadata = partial
    archive = tmp_path / "partial.zip"
    digest = archive_partial(partial, archive)
    request, ledger, proof = recovery.recovery_requirement(archive, parent, digest)
    assert request["jobs"] == parent["jobs"][602:]
    assert len(request["jobs"]) == request["maximum_requests"] == 459
    assert all(job not in request["jobs"] for job in parent["jobs"][:602])
    assert not any(job["endpoint"] == "leaguedashplayerstats" for job in request["jobs"])
    assert request["jobs"][0]["source_file"] == "sources/boxscoreadvancedv3_0022600116_q1.json"
    assert metadata["attempts"][601]["job"] not in request["jobs"]
    assert len(ledger["retained_successful_sources"]) == 602
    assert proof["repeated_successful_jobs"] == 0
    assert proof["parent_job_indices"] == list(range(602, 1061))
    assert (
        request["recovery"]["reuse_ledger_sha256"]
        == hashlib.sha256(recovery._json(ledger)).hexdigest()
    )
    assert request["recovery"]["original_zip_sha256"] == digest
    for field in [
        "attempts_per_job",
        "timeout_seconds",
        "response_limit_bytes",
        "minimum_interval_seconds",
        "maximum_elapsed_seconds",
        "fixed_cutoff",
        "base_generation",
        "base_manifest_sha256",
    ]:
        assert request[field] == parent[field]
    for row in ledger["retained_successful_sources"]:
        assert (
            hashlib.sha256((source / row["source_file"]).read_bytes()).hexdigest() == row["sha256"]
        )


@pytest.mark.parametrize(
    "damage",
    [
        "job_order",
        "already_success",
        "error_basis",
        "http",
        "failure_bytes",
        "unattempted",
        "source_hash",
        "time",
        "extra_file",
        "source_capture_mismatch",
    ],
)
def test_recovery_rejects_unproven_or_changed_partition(tmp_path, partial, damage):
    source, parent, metadata = partial
    if damage == "job_order":
        metadata["attempts"][1]["job"] = parent["jobs"][2]
    elif damage == "already_success":
        metadata["attempts"][-1]["transport_complete"] = True
    elif damage == "error_basis":
        metadata["attempts"][-1]["error_type"] = "InvalidStatistics"
    elif damage == "http":
        metadata["attempts"][-1]["http_status"] = 403
    elif damage == "failure_bytes":
        metadata["attempts"][-1]["response_bytes"] = 1
    elif damage == "unattempted":
        metadata["unattempted_jobs"].pop()
    elif damage == "source_hash":
        metadata["attempts"][0]["response_sha256"] = "0" * 64
    elif damage == "time":
        metadata["attempts"][2]["started_at"] = "2026-11-01T00:00:00+00:00"
    elif damage == "extra_file":
        (source / "sources/extra.json").write_text("{}")
    archive = tmp_path / "partial.zip"
    digest = archive_partial(partial, archive)
    if damage == "source_capture_mismatch":
        with zipfile.ZipFile(archive, "a") as handle:
            handle.writestr("unexpected.json", "{}")
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        recovery.recovery_requirement(archive, parent, digest)


def test_recovery_requires_original_zip_parent_request_and_cooldown(tmp_path, partial):
    _, parent, metadata = partial
    archive = tmp_path / "partial.zip"
    digest = archive_partial(partial, archive)
    with pytest.raises(ValueError, match="immutable bytes"):
        recovery.recovery_requirement(archive, parent, "0" * 64)
    changed = copy.deepcopy(parent)
    changed["jobs"] = changed["jobs"][1:]
    changed["maximum_requests"] -= 1
    with pytest.raises(ValueError, match="immutable reviewed"):
        recovery.recovery_requirement(archive, changed, digest)
    finished = datetime.fromisoformat(metadata["attempts"][-1]["finished_at"])
    with pytest.raises(ValueError, match="cooldown"):
        recovery.recovery_requirement(
            archive, parent, digest, checked_at=finished + timedelta(minutes=9)
        )
    recovery.recovery_requirement(
        archive, parent, digest, checked_at=finished + timedelta(minutes=10)
    )


def test_owner_package_reuses_unchanged_collector_and_preflights_all459_jobs(tmp_path, partial):
    archive = tmp_path / "partial.zip"
    digest = archive_partial(partial, archive)
    destination = tmp_path / "package"
    proof = recovery.build(archive, destination, expected_zip_sha256=digest)
    request = json.loads((destination / "readiness-recovery-request.json").read_bytes())
    original_script = tmp_path / "original-generated.py"
    collector.build_package(request, original_script)
    with zipfile.ZipFile(destination / "NBA-Tools-Readiness-Recovery.zip") as handle:
        assert handle.read("run_capture.py") == original_script.read_bytes()
        assert handle.getinfo("Run Capture.command").external_attr >> 16 == 0o100755
        assert b"pip" not in handle.read("Run Capture.command")
        assert b"pip" not in handle.read("Run Capture.bat")
        namespace = {"__name__": "preflight_only"}
        exec(compile(handle.read("run_capture.py"), "run_capture.py", "exec"), namespace)
    assert namespace["EMBEDDED_REQUEST"] == request
    for job in request["jobs"]:
        assert namespace["_client"](job)[1] == "https://stats.nba.com/stats/" + job["endpoint"]
    assert proof["collector_transport_policy_unchanged"] and proof["repeated_successful_jobs"] == 0
    assert (
        proof["owner_bundle_sha256"]
        == hashlib.sha256(
            (destination / "NBA-Tools-Readiness-Recovery.zip").read_bytes()
        ).hexdigest()
    )
    with pytest.raises(FileExistsError):
        recovery.build(archive, destination, expected_zip_sha256=digest)


@pytest.mark.parametrize("location", ["active", "sibling", "parent"])
def test_mac_launcher_finds_existing_isolated_python_without_install_or_home_search(
    tmp_path, location
):
    folder = tmp_path / "package with spaces"
    folder.mkdir()
    launcher = folder / "Run Capture.command"
    launcher.write_text(recovery.MAC_LAUNCHER)
    fake_path = tmp_path / "bin"
    fake_path.mkdir()
    for name in ["python3", "python"]:
        path = fake_path / name
        path.write_text("#!/bin/sh\nexit 1\n")
        path.chmod(0o755)
    environment = (
        folder / ".venv"
        if location == "sibling"
        else tmp_path / ".venv"
        if location == "parent"
        else tmp_path / "existing active env"
    )
    runtime = environment / "bin/python"
    runtime.parent.mkdir(parents=True)
    log = tmp_path / "calls.txt"
    runtime.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{log}"\nexit 0\n')
    runtime.chmod(0o755)
    env = {
        **os.environ,
        "PATH": str(fake_path) + ":/usr/bin:/bin",
        "VIRTUAL_ENV": str(environment) if location == "active" else "",
    }
    result = subprocess.run(
        ["sh", str(launcher)], env=env, input="\n", text=True, capture_output=True, timeout=5
    )
    assert result.returncode == 0 and "Return readiness-capture/collection.zip" in result.stdout
    assert log.read_text().splitlines() == ["-c import nba_api", "run_capture.py"]
    assert "find " not in recovery.MAC_LAUNCHER and "$HOME" not in recovery.MAC_LAUNCHER


@pytest.fixture
def extension(tmp_path):
    parent = json.loads(recovery.PARENT_PATH.read_bytes())
    scope = dict(
        checked_at="2026-11-03T09:30:00+00:00",
        fixed_cutoff="2026-11-01",
        schedule_sha256="a" * 64,
        due_game_ids=sorted(parent["game_ids"] + recovery.NEW_GAME_IDS),
        new_game_ids=recovery.NEW_GAME_IDS.copy(),
        new_overtime_game_ids=[],
        missing_summary_game_ids=["0022600154"],
        traditional_basis_game_ids=recovery.BASIS_GAME_IDS.copy(),
        independent_evidence="controlled exact-population test; not real NBA qualification",
    )
    path = tmp_path / "extension.json"
    path.write_text(json.dumps(scope))
    return path, scope


def test_bound_current_due_extension_is_exact515_without_snapshot_or_success_repeats(
    tmp_path, partial, extension
):
    archive = tmp_path / "partial.zip"
    digest = archive_partial(partial, archive)
    scope_path, scope = extension
    destination = tmp_path / "package"
    proof = recovery.build(
        archive, destination, expected_zip_sha256=digest, extension_scope=scope_path
    )
    request = json.loads((destination / "readiness-recovery-request.json").read_bytes())
    assert len(request["jobs"]) == request["maximum_requests"] == 515
    parent = partial[1]
    assert request["jobs"][:459] == parent["jobs"][602:]
    added = request["jobs"][459:]
    assert added[0]["endpoint"] == "boxscoresummaryv3" and added[0]["parameters"] == {
        "GameID": "0022600154"
    }
    assert len(added[1:-7]) == 48
    assert [job["parameters"]["GameID"] for job in added[-7:]] == recovery.BASIS_GAME_IDS
    assert all(job["parameters"]["RangeType"] == "0" for job in added[-7:])
    assert not any(job["endpoint"] == "leaguedashplayerstats" for job in request["jobs"])
    assert not any(job in request["jobs"] for job in parent["jobs"][:602])
    assert proof["added_first_time_jobs"] == 56 and proof["repeated_successful_jobs"] == 0
    assert request["fixed_cutoff"] == "2026-11-01" and len(request["game_ids"]) == 92
    assert (
        request["recovery_extension"]["scope_report_sha256"]
        == hashlib.sha256(scope_path.read_bytes()).hexdigest()
    )
    assert request["recovery_extension"]["traditional_basis_game_ids"] == recovery.BASIS_GAME_IDS
    assert request["recovery_extension"]["full_snapshot_acceptance"] is False
    with zipfile.ZipFile(destination / "NBA-Tools-Readiness-Recovery.zip") as handle:
        namespace = {"__name__": "preflight_only"}
        exec(compile(handle.read("run_capture.py"), "run_capture.py", "exec"), namespace)
        assert b"Exactly 515 requests" in handle.read("READ ME.txt")
    assert namespace["EMBEDDED_REQUEST"] == request
    for job in request["jobs"]:
        assert namespace["_client"](job)[1] == "https://stats.nba.com/stats/" + job["endpoint"]


@pytest.mark.parametrize(
    "damage",
    [
        "extra_game",
        "missing_game",
        "ot_extra",
        "duplicate_summary",
        "summary_old",
        "basis_extra",
        "basis_missing",
        "clock",
        "schedule_hash",
    ],
)
def test_extension_cannot_silently_expand_or_drop_bound_dependencies(
    tmp_path, partial, extension, damage
):
    archive = tmp_path / "partial.zip"
    digest = archive_partial(partial, archive)
    request, _, proof = recovery.recovery_requirement(archive, partial[1], digest)
    path, scope = extension
    if damage == "extra_game":
        scope["new_game_ids"] = scope["new_game_ids"] + ["0022600158"]
    elif damage == "missing_game":
        scope["due_game_ids"].pop()
    elif damage == "ot_extra":
        scope["new_overtime_game_ids"] = ["0022600144"]
    elif damage == "duplicate_summary":
        scope["missing_summary_game_ids"] *= 2
    elif damage == "summary_old":
        scope["missing_summary_game_ids"] = ["0022600001"]
    elif damage == "basis_extra":
        scope["traditional_basis_game_ids"] = scope["traditional_basis_game_ids"] + ["0022600158"]
    elif damage == "basis_missing":
        scope["traditional_basis_game_ids"] = scope["traditional_basis_game_ids"][1:]
    elif damage == "clock":
        scope["checked_at"] = "2026-10-31T09:30:00+00:00"
    elif damage == "schedule_hash":
        scope["schedule_sha256"] = "unverified"
    path.write_text(json.dumps(scope))
    with pytest.raises(ValueError, match="bounded current-due"):
        recovery.extend_requirement(request, proof, path)


def test_new_cutoff_clock_conflict_requests_two_distinct_snapshots_and_exact517(
    tmp_path, partial, extension
):
    archive = tmp_path / "partial.zip"
    digest = archive_partial(partial, archive)
    path, scope = extension
    scope["advanced_snapshot_endpoints"] = ["leaguedashplayerstats", "leaguedashteamstats"]
    scope["advanced_snapshot_reason"] = (
        "Controlled source-basis test: player/Team Advanced MIN contradict whole clock for 0154"
    )
    path.write_text(json.dumps(scope))
    destination = tmp_path / "package"
    proof = recovery.build(archive, destination, expected_zip_sha256=digest, extension_scope=path)
    request = json.loads((destination / "readiness-recovery-request.json").read_bytes())
    assert len(request["jobs"]) == request["maximum_requests"] == 517
    assert proof["date_filtered_snapshot_jobs"] == 2 and proof["added_first_time_jobs"] == 58
    snapshots = request["jobs"][-2:]
    assert [job["endpoint"] for job in snapshots] == scope["advanced_snapshot_endpoints"]
    assert all(job["parameters"]["DateTo"] == "11/01/2026" for job in snapshots)
    assert all(job["parameters"]["MeasureType"] == "Advanced" for job in snapshots)
    assert all(job["parameters"]["PerMode"] == "PerGame" for job in snapshots)
    assert all(job["parameters"]["ISTRound"] is None for job in snapshots)
    assert not any(job in request["jobs"] for job in partial[1]["jobs"][:602])
    assert all(job["parameters"].get("DateTo") != "10/31/2026" for job in request["jobs"])
    assert proof["repeated_successful_jobs"] == 0
    assert (
        request["recovery_extension"]["advanced_snapshot_reason"]
        == scope["advanced_snapshot_reason"]
    )
    with zipfile.ZipFile(destination / "NBA-Tools-Readiness-Recovery.zip") as handle:
        namespace = {"__name__": "preflight_only"}
        exec(compile(handle.read("run_capture.py"), "run_capture.py", "exec"), namespace)
        assert b"Exactly 517 requests" in handle.read("READ ME.txt")
    assert namespace["EMBEDDED_REQUEST"] == request
    for job in request["jobs"]:
        assert namespace["_client"](job)[1] == "https://stats.nba.com/stats/" + job["endpoint"]


@pytest.mark.parametrize("damage", ["duplicate_endpoint", "extra_endpoint", "missing_reason"])
def test_new_snapshot_scope_must_match_both_explicitly_justified_sources(
    tmp_path, partial, extension, damage
):
    archive = tmp_path / "partial.zip"
    digest = archive_partial(partial, archive)
    request, _, proof = recovery.recovery_requirement(archive, partial[1], digest)
    path, scope = extension
    scope["advanced_snapshot_endpoints"] = ["leaguedashplayerstats", "leaguedashteamstats"]
    scope["advanced_snapshot_reason"] = (
        "Verified clock-basis contradiction requires the two new-cutoff sources"
    )
    if damage == "duplicate_endpoint":
        scope["advanced_snapshot_endpoints"] = ["leaguedashplayerstats"] * 2
    elif damage == "extra_endpoint":
        scope["advanced_snapshot_endpoints"].append("leaguestandingsv3")
    else:
        scope["advanced_snapshot_reason"] = ""
    path.write_text(json.dumps(scope))
    with pytest.raises(ValueError, match="bounded current-due"):
        recovery.extend_requirement(request, proof, path)
