"""Offline environment admission, isolated setup and exact frozen Mac package."""

import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import build_mac_capture_repair as builder
from tools import mac_capture_environment as setup
from tools.collection_bundle import unpack

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "working/nba-tools-completion-program"
ORIGINAL = (
    EVIDENCE / "source-evidence/period-acquisition-20261107/NBA-Tools-Current123-Period-Capture.zip"
)
PLAN = json.loads(
    (EVIDENCE / "collection-requests/current123-new16-periods-20261107.json").read_bytes()
)


@pytest.fixture
def package(tmp_path):
    destination = tmp_path / "replacement.zip"
    builder.build(ORIGINAL, PLAN, destination)
    folder = tmp_path / "Mac capture with spaces"
    with zipfile.ZipFile(destination) as archive:
        archive.extractall(folder)
    return folder


def test_frozen_source_plan_and_full_offline_probe(package):
    assert (
        hashlib.sha256((package / "run_capture.py").read_bytes()).hexdigest()
        == builder.COLLECTOR_SHA
    )
    namespace = {"__name__": "independent_preflight"}
    exec(compile((package / "prepare_environment.py").read_text(), "helper", "exec"), namespace)
    assert namespace["REQUEST"] == PLAN
    assert len(PLAN["jobs"]) == 196
    assert setup.probe(sys.executable, package / "run_capture.py")["nba_api"]
    assert subprocess.run(["sh", "-n", str(package / "Run Capture.command")]).returncode == 0
    assert (
        "/opt/homebrew/opt/python@3.11/bin/python3.11"
        in (package / "Run Capture.command").read_text()
    )
    with zipfile.ZipFile(ORIGINAL) as archive:
        assert (package / "Run Capture.bat").read_bytes() == archive.read("Run Capture.bat")


def test_importable_namespace_without_distribution_is_rejected(package, tmp_path):
    # Reproduce the exact weak original admission without an NBA connection.
    namespace = tmp_path / "fake namespace"
    (namespace / "nba_api").mkdir(parents=True)
    old_probe = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "import nba_api; from importlib.metadata import version; version('nba_api')",
        ],
        env={**os.environ, "PYTHONPATH": str(namespace)},
        capture_output=True,
        text=True,
    )
    assert "PackageNotFoundError" in old_probe.stderr
    # A real empty isolated venv has no nba_api distribution: full probe refuses it.
    runtime = tmp_path / "empty environment"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(runtime)], check=True)
    assert setup.probe(str(runtime / "bin/python"), package / "run_capture.py") is None
    # Inherited namespace cannot contaminate healthy probe/collector (-I).
    contaminated = subprocess.run(
        [sys.executable, "-I", "-c", setup.PROBE, str(package / "run_capture.py")],
        env={**os.environ, "PYTHONPATH": str(namespace)},
        capture_output=True,
        text=True,
    )
    assert contaminated.returncode == 0, contaminated.stderr


def test_finite_existing_venv_discovery_and_preference(package, monkeypatch):
    retained = package.parent / "old capture/.venv/bin/python"
    retained.parent.mkdir(parents=True)
    retained.symlink_to(sys.executable)
    monkeypatch.setenv("VIRTUAL_ENV", str(retained.parent.parent))
    assert str(retained) in list(setup.candidates(package))
    monkeypatch.setattr(setup, "candidates", lambda root: iter(["broken", str(retained)]))
    monkeypatch.setattr(
        setup,
        "probe",
        lambda runtime, script: {"nba_api": "1.11.4"} if runtime == str(retained) else None,
    )
    monkeypatch.setattr(
        setup, "run", lambda *args: SimpleNamespace(returncode=1, stderr="controlled error")
    )
    assert setup.prepare(package, {}) == str(retained)
    assert not (package / ".nba-tools-env").exists()


@pytest.mark.parametrize("failure", [None, "venv", "pip", "probe"])
def test_private_setup_bounded_and_no_global_install(package, monkeypatch, failure):
    monkeypatch.setattr(setup, "candidates", lambda root: iter(["base311"]))
    calls = []

    def execute(arguments, timeout):
        calls.append((arguments, timeout))
        if "venv" in arguments and "-c" not in arguments and failure == "venv":
            return SimpleNamespace(returncode=1, stderr="controlled error")
        if "pip" in arguments and failure == "pip":
            return SimpleNamespace(returncode=1, stderr="controlled error")
        return SimpleNamespace(returncode=0)

    def probe(runtime, script):
        if runtime != "base311" and failure != "probe":
            return {"python": "3.11.9", "nba_api": "1.11.4"}
        return None

    monkeypatch.setattr(setup, "run", execute)
    monkeypatch.setattr(setup, "probe", probe)
    if failure:
        with pytest.raises(RuntimeError):
            setup.prepare(package, {})
    else:
        assert setup.prepare(package, {}) == str(package / ".nba-tools-env/bin/python")
    for arguments, timeout in calls:
        assert timeout <= 180
        if "pip" in arguments:
            assert arguments[0] == str(package / ".nba-tools-env/bin/python")
            assert "--isolated" in arguments and "--only-binary=:all:" in arguments
            assert "--no-cache-dir" in arguments
            assert arguments[arguments.index("--retries") + 1] == "0"
            assert arguments[-1] == "nba_api==1.11.4"
            assert "https://pypi.org/simple" in arguments


def test_setup_failure_portable_zero_attempt_receipt_and_existing_preserved(package, monkeypatch):
    monkeypatch.setattr(setup, "REQUEST", PLAN)
    setup.failure_receipt(package, {"error_type": "controlled_setup_failure"})
    archive = package / "readiness-capture/collection.zip"
    before = archive.read_bytes()
    restored = package.parent / "unpacked data"
    unpack(archive, PLAN, restored)
    report = json.loads((restored / "acquisition.json").read_bytes())
    assert report["attempts"] == [] and len(report["unattempted_jobs"]) == 196
    assert not report["transport_finished"] and report["production_writes"] == 0
    assert report["request_sha256"] == builder.REQUEST_SHA
    setup.failure_receipt(package, {"error_type": "second_failure"})
    assert archive.read_bytes() == before


def test_launcher_invokes_helper_once_without_commands_from_owner(package, tmp_path):
    scripts = tmp_path / "bin"
    scripts.mkdir()
    log = tmp_path / "calls.txt"
    fake = scripts / "python3.11"
    fake.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{log}"\nexit 0\n')
    fake.chmod(0o755)
    response = subprocess.run(
        ["sh", str(package / "Run Capture.command")],
        input="\n",
        text=True,
        capture_output=True,
        env={**os.environ, "PATH": str(scripts) + ":/usr/bin:/bin"},
        timeout=5,
    )
    assert response.returncode == 0
    assert log.read_text().splitlines() == [
        "-I -c import sys; assert sys.version_info >= (3, 8)",
        "-I prepare_environment.py",
    ]
    assert "Return readiness-capture/collection.zip" in response.stdout


def test_main_preserves_existing_failure_and_never_prepares_or_collects(package, monkeypatch):
    output = package / "readiness-capture"
    output.mkdir()
    (output / "collection.zip").write_bytes(b"custody evidence")
    monkeypatch.setattr(setup, "__file__", str(package / "prepare_environment.py"))
    monkeypatch.setattr(
        setup, "prepare", lambda *args: pytest.fail("Must not retry existing output")
    )
    assert setup.main() == 1
    assert (output / "collection.zip").read_bytes() == b"custody evidence"


def test_main_runs_exactly_one_verified_collector(package, monkeypatch):
    monkeypatch.setattr(setup, "__file__", str(package / "prepare_environment.py"))
    monkeypatch.setattr(setup, "prepare", lambda *args: "verified311")
    calls = []
    monkeypatch.setattr(
        setup.subprocess, "call", lambda *args, **kwargs: calls.append((args, kwargs)) or 1
    )
    assert setup.main() == 1
    assert calls == [
        ((["verified311", "-I", str(package / "run_capture.py")],), {"cwd": str(package)})
    ]
