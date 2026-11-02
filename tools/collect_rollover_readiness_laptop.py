"""Build/run a finite acquisition-only package with the laptop's existing nba_api.

Cloud usage: build_package(request, destination) embeds the reviewed request in
one standalone Python file. The generated file needs no NBA Tools checkout,
parameters, source selection, credentials or installation on the laptop.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import time
import zipfile
import zlib
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

# Replaced only by the cloud packaging function, never by laptop configuration.
EMBEDDED_REQUEST = None
EMBEDDED_SHA256 = None
MAX_BODY = 2_000_000
MAX_EXPANDED = 100_000_000
MAX_ZIP = 20_000_000
MAX_JOBS = 1200
ENDPOINTS = {
    "boxscoretraditionalv3",
    "boxscoreadvancedv3",
    "leaguedashplayerstats",
    "leaguedashteamstats",
}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_request(request):
    if (
        request.get("status") != "collection_requirement_not_publication_approval"
        or request.get("season") != "2026-27"
        or request.get("season_type") != "Regular Season"
        or not request.get("base_generation")
        or not re.fullmatch(r"[a-f0-9]{64}", request.get("base_manifest_sha256", ""))
        or len(_json(request)) > 250_000
    ):
        raise ValueError("Invalid fixed collection requirement")
    jobs = request["jobs"]
    if (
        not 1 <= len(jobs) <= MAX_JOBS
        or request["maximum_requests"] != len(jobs)
        or request["attempts_per_job"] != 1
        or request["timeout_seconds"] != 30
        or request["response_limit_bytes"] != MAX_BODY
        or request["minimum_interval_seconds"] < 1
        or not 1 <= request["maximum_elapsed_seconds"] <= 43_200
    ):
        raise ValueError("Collection bounds differ from reviewed finite protocol")
    names = set()
    requests_seen = set()
    for job in jobs:
        name = job["source_file"]
        if (
            job["endpoint"] not in ENDPOINTS
            or not re.fullmatch(r"sources/[a-zA-Z0-9_-]+\.json", name)
            or name in names
            or not isinstance(job["parameters"], dict)
        ):
            raise ValueError("Invalid/duplicate fixed source job")
        names.add(name)
        params = job["parameters"]
        identity = (job["endpoint"], _json(params))
        if identity in requests_seen:
            raise ValueError("Duplicate source request")
        requests_seen.add(identity)
        if job["endpoint"].startswith("boxscore"):
            if (
                set(params)
                != {"GameID", "StartPeriod", "EndPeriod", "RangeType", "StartRange", "EndRange"}
                or not re.fullmatch(r"00226\d{5}", params["GameID"])
                or type(params["StartPeriod"]) is not int
                or type(params["EndPeriod"]) is not int
                or (params["StartPeriod"], params["EndPeriod"])
                not in {(1, 1), (2, 2), (3, 3), (4, 4), (1, 2), (3, 4), (5, 14)}
                or params["RangeType"] != 1
                or params["StartRange"] != 0
                or params["EndRange"] != 28800
            ):
                raise ValueError("Invalid fixed box-score window")
        elif (
            params.get("Season") != "2026-27"
            or params.get("SeasonType") != "Regular Season"
            or params.get("MeasureType") != "Advanced"
            or params.get("PerMode") != "PerGame"
            or not re.fullmatch(r"\d{2}/\d{2}/2026", params.get("DateTo", ""))
        ):
            raise ValueError("Advanced snapshot must retain its explicit cutoff/basis")
    return _sha(_json(request))


def _client(job):
    from nba_api.stats.endpoints import (
        BoxScoreAdvancedV3,
        BoxScoreTraditionalV3,
        LeagueDashPlayerStats,
        LeagueDashTeamStats,
    )
    from nba_api.stats.library.http import NBAStatsHTTP

    name, params = job["endpoint"], job["parameters"]
    if name.startswith("boxscore"):
        cls = BoxScoreTraditionalV3 if name == "boxscoretraditionalv3" else BoxScoreAdvancedV3
        endpoint = cls(
            game_id=params["GameID"],
            start_period=params["StartPeriod"],
            end_period=params["EndPeriod"],
            range_type=1,
            start_range=0,
            end_range=28800,
            get_request=False,
        )
    else:
        cls = LeagueDashPlayerStats if name == "leaguedashplayerstats" else LeagueDashTeamStats
        endpoint = cls(
            season="2026-27",
            season_type_all_star="Regular Season",
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
            date_from_nullable=params.get("DateFrom", ""),
            date_to_nullable=params["DateTo"],
            get_request=False,
        )
    actual_parameters = endpoint.parameters.copy()
    planned_parameters = params.copy()
    # v1.12 adds only this optional default None to the player endpoint.
    # Requests omits None-valued query items; no statistical filter changes.
    if name == "leaguedashplayerstats":
        for parameters in [actual_parameters, planned_parameters]:
            if "ISTRound" in parameters:
                if parameters["ISTRound"] is not None:
                    raise ValueError("Unexpected tournament-round filter")
                parameters.pop("ISTRound")
    if endpoint.endpoint != name or actual_parameters != planned_parameters:
        raise ValueError("Installed SDK parameters differ from the fixed reviewed request")
    http = NBAStatsHTTP()
    url = http.base_url.format(endpoint=name)
    if url != f"https://stats.nba.com/stats/{name}":
        raise ValueError("Unexpected source transport host")
    return http, url


def _checkpoint(output, report):
    metadata = json.dumps(report, indent=2) + "\n"
    for name in ["acquisition.json", "sources/capture-attempt.json"]:
        temporary = output / "checkpoint.tmp"
        temporary.write_text(metadata)
        temporary.replace(output / name)


def _bundle(output, request, report):
    """Existing collection_bundle protocol; originals remain untouched on disk."""
    _checkpoint(output, report)
    paths = [output / "acquisition.json", *(output / "sources").glob("*.json")]
    files = {}
    total = 0
    for path in sorted(paths):
        if path.is_symlink():
            raise ValueError("Symlink not allowed")
        raw = path.read_bytes()
        total += len(raw)
        files[path.relative_to(output).as_posix()] = {"bytes": len(raw), "sha256": _sha(raw)}
    if len(files) > 2000 or total > MAX_EXPANDED:
        raise ValueError("Collection exceeds expanded data-only bound; loose originals preserved")
    manifest = dict(
        schema_version=1,
        classification="unvalidated_development_collection",
        request=request,
        request_sha256=_sha(_json(request)),
        files=files,
        production_writes=0,
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(output / name, name)
        archive.writestr("collection-manifest.json", json.dumps(manifest, indent=2) + "\n")
    payload = buffer.getvalue()
    if len(payload) > MAX_ZIP:
        raise ValueError("Collection exceeds ZIP bound; loose originals preserved")
    temporary = output / "collection.tmp"
    temporary.write_bytes(payload)
    temporary.replace(output / "collection.zip")


def _resume(output, request, request_sha):
    path = output / "acquisition.json"
    if not path.exists():
        output.mkdir(parents=True, exist_ok=False)
        (output / "sources").mkdir()
        return dict(
            classification="unvalidated_laptop_source_capture_not_publication",
            source="NBA Stats",
            captured_at=datetime.now(UTC).isoformat(),
            parameters="exact fixed per-job parameters in request and attempts",
            request=request,
            request_sha256=request_sha,
            nba_api_version=None,
            attempts=[],
            production_writes=0,
            canonical_period_accepted=False,
        )
    if output.is_symlink() or path.is_symlink() or (output / "sources").is_symlink():
        raise ValueError("Symlink not allowed")
    report = json.loads(path.read_bytes())
    if report["request"] != request or report["request_sha256"] != request_sha:
        raise ValueError("Existing output belongs to a different fixed package")
    attempts = report["attempts"]
    if len(attempts) > len(request["jobs"]):
        raise ValueError("Unexpected prior attempts")
    expected_names = {"capture-attempt.json"}
    for attempt, job in zip(attempts, request["jobs"], strict=False):
        if attempt["job"] != job:
            raise ValueError("Prior attempted request differs")
        if attempt.get("source_file"):
            if attempt["source_file"] != job["source_file"]:
                raise ValueError("Prior source path differs")
            source = output / attempt["source_file"]
            expected_names.add(source.name)
            if source.is_symlink():
                raise ValueError("Symlink not allowed")
            raw = source.read_bytes()
            if len(raw) != attempt["response_bytes"] or _sha(raw) != attempt["response_sha256"]:
                raise ValueError("Prior source bytes changed; no requests made")
    if {p.name for p in (output / "sources").iterdir()} != expected_names:
        raise ValueError("Unexpected source file; no requests made")
    return report


def collect(output: Path, request: dict):
    request_sha = validate_request(request)
    report = _resume(output, request, request_sha)
    attempts = report["attempts"]
    # A failure is never an implicit retry or permission to continue a batch.
    if any(not row.get("transport_complete", False) for row in attempts):
        report["stop_reason"] = "failure_return_output_do_not_retry"
        report["unattempted_jobs"] = request["jobs"][len(attempts) :]
        _bundle(output, request, report)
        return report
    started = time.monotonic()
    compressed_bytes = expanded_bytes = 0
    for row in attempts:
        if row.get("source_file"):
            raw = (output / row["source_file"]).read_bytes()
            compressed_bytes += len(zlib.compress(raw))
            expanded_bytes += len(raw)
    try:
        report["nba_api_version"] = version("nba_api")
        for job in request["jobs"][len(attempts) :]:
            # Reserve 2MB for next original and 4MB for bounded plan/diagnostics.
            if expanded_bytes > 94_000_000 or compressed_bytes > 14_000_000:
                report["stop_reason"] = "collection_size_limit"
                break
            if time.monotonic() - started + 31 > request["maximum_elapsed_seconds"]:
                report["stop_reason"] = "elapsed_limit"
                break
            if attempts:
                time.sleep(request["minimum_interval_seconds"])
            http, url = _client(job)
            attempt = dict(
                job=job,
                endpoint=job["endpoint"],
                url=url,
                parameters=job["parameters"],
                started_at=datetime.now(UTC).isoformat(),
                attempts=1,
                timeout_seconds=30,
                http_status=None,
                response_complete=False,
                transport_complete=False,
            )
            attempts.append(attempt)
            # Record intent before transport; interruption never causes a retry.
            _checkpoint(output, report)
            raw = bytearray()
            try:
                with http.get_session().get(
                    url=url,
                    params=sorted(job["parameters"].items()),
                    headers=http.headers,
                    timeout=30,
                    stream=True,
                    allow_redirects=False,
                ) as response:
                    attempt["http_status"] = response.status_code
                    for chunk in response.iter_content(65536):
                        remaining = MAX_BODY - len(raw)
                        raw.extend(chunk[:remaining])
                        if len(chunk) > remaining:
                            attempt["response_truncated"] = True
                            raise ValueError("Response exceeds2MB retained bound")
                        if time.monotonic() - started > request["maximum_elapsed_seconds"]:
                            raise TimeoutError("Fixed collection elapsed limit reached")
                    attempt["response_complete"] = True
                    response.raise_for_status()
                    if response.status_code != 200:
                        raise ValueError("Source transport did not return HTTP200")
                document = json.loads(raw)
                if not isinstance(document, dict):
                    raise ValueError("Expected JSON source object")
                attempt["transport_complete"] = True
            except BaseException as exc:
                attempt["error_type"] = type(exc).__name__
                raise
            finally:
                if raw:
                    destination = output / job["source_file"]
                    with destination.open("xb") as handle:
                        handle.write(raw)
                attempt.update(
                    finished_at=datetime.now(UTC).isoformat(),
                    response_bytes=len(raw),
                    response_sha256=_sha(raw),
                    source_file=job["source_file"] if raw else None,
                )
                compressed_bytes += len(zlib.compress(raw))
                expanded_bytes += len(raw)
                _checkpoint(output, report)
            print(
                f"Captured {len(attempts)}/{len(request['jobs'])}; originals retained.", flush=True
            )
    except BaseException as exc:
        report["error_type"] = type(exc).__name__
        report["stop_reason"] = "failure_return_output_do_not_retry"
    finally:
        report.update(
            finished_at=datetime.now(UTC).isoformat(),
            unattempted_jobs=request["jobs"][len(attempts) :],
            transport_finished=len(attempts) == len(request["jobs"])
            and all(row.get("transport_complete", False) for row in attempts),
        )
        _bundle(output, request, report)
    return report


def _package_source(request):
    request_sha = validate_request(request)
    source = Path(__file__).read_text()
    encoded = base64.b64encode(zlib.compress(_json(request))).decode()
    chunks = "\n".join(f"    {encoded[i : i + 76]!r}" for i in range(0, len(encoded), 76))
    replacement = (
        "EMBEDDED_REQUEST = json.loads(zlib.decompress(base64.b64decode(\n" + chunks + "\n)))"
    )
    source = source.replace("EMBEDDED_REQUEST = None", replacement, 1)
    source = source.replace("EMBEDDED_SHA256 = None", f"EMBEDDED_SHA256 = {request_sha!r}", 1)
    return source, {"request_sha256": request_sha, "package_sha256": _sha(source.encode())}


def build_package(request: dict, destination: Path):
    """Cloud-only builder; generated file has no repository imports or inputs."""
    source, binding = _package_source(request)
    with Path(destination).open("x") as handle:
        handle.write(source)
    return binding


def build_owner_bundle(request: dict, destination: Path):
    """One ZIP containing executable and existing-Python desktop launchers."""
    source, binding = _package_source(request)
    mac = """#!/bin/sh
cd -- "$(dirname -- "$0")" || exit 1
found=0
for runtime in python3 python; do
    if "$runtime" -c 'import nba_api' >/dev/null 2>&1; then
        "$runtime" run_capture.py
        found=1
        break
    fi
done
if [ "$found" -eq 0 ]; then
    python3 run_capture.py
fi
printf '\nReturn readiness-capture/collection.zip, including after a failure.\n'
printf 'Press Return to close.'
read -r ignored
"""
    windows = r"""@echo off
cd /d "%~dp0"
for %%P in (python python3) do (
    %%P -c "import nba_api" >nul 2>&1
    if not errorlevel 1 (
        %%P run_capture.py
        goto done
    )
)
py -3 -c "import nba_api" >nul 2>&1
if not errorlevel 1 (
    py -3 run_capture.py
    goto done
)
python run_capture.py
:done
echo.
echo Return readiness-capture\collection.zip, including after a failure.
pause
"""
    instructions = (
        "Unzip this package in a new folder. Open Run Capture.command on Mac "
        "or Run Capture.bat on Windows. Keep this folder open until it finishes.\n"
        "The launcher uses Python and nba_api already installed. It installs nothing.\n"
        f"Scope: {len(request['jobs'])} fixed requests; one attempt per request; "
        f"30-second timeout, {request['minimum_interval_seconds']}s minimum spacing, "
        f"finite {request['maximum_elapsed_seconds']}s ceiling.\n"
        "Return readiness-capture/collection.zip through the existing handoff, "
        "even if capture stops or fails. Keep the whole output folder until Codex "
        "confirms receipt. Do not delete it or restart to troubleshoot a failure.\n"
        "Every captured original and the exact request are preserved. "
        "The collection makes no production change and accepts no dataset.\n"
    )
    with Path(destination).open("xb") as output:
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("run_capture.py", source)
            command = zipfile.ZipInfo("Run Capture.command")
            command.create_system = 3
            command.external_attr = 0o100755 << 16
            archive.writestr(command, mac)
            archive.writestr("Run Capture.bat", windows.replace("\n", "\r\n"))
            archive.writestr("READ ME.txt", instructions)
    binding["owner_bundle_sha256"] = _sha(Path(destination).read_bytes())
    return binding


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).resolve().with_name("readiness-capture")
    )
    args = parser.parse_args()
    if EMBEDDED_REQUEST is None or validate_request(EMBEDDED_REQUEST) != EMBEDDED_SHA256:
        parser.error("Run the cloud-prepared standalone package; no request is embedded here")
    try:
        report = collect(args.output, EMBEDDED_REQUEST)
    except Exception as exc:
        print(f"Stopped safely ({type(exc).__name__}); preserve the output directory for Codex.")
        return 1
    print(
        f"Return {args.output / 'collection.zip'} to Codex, including after failure. "
        "No data published."
    )
    return 0 if report.get("transport_finished") else 1


if __name__ == "__main__":
    raise SystemExit(main())
