"""Cloud-only, offline packaging of the exact uncompleted readiness request tail.

Original successful sources are verified and listed for reuse, never reacquired.
The reviewed standalone collector and its fail-fast/no-retry behavior are reused.
Only finite launcher selection is extended to existing nearby virtual environments.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import tempfile
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tools.collect_rollover_readiness_laptop import build_owner_bundle, validate_request
from tools.collection_bundle import unpack

PARENT_SHA256 = "4a30c59cc6753fb060359b09d12b9b24c49e65851fb880d57e7154079959f1e0"
ORIGINAL_ZIP_SHA256 = "03ee634189d3f245badbd0baadc60ddaeac4b9efd978c5d2bd62d02aa7d4ceb3"
PARENT_PATH = (
    Path(__file__).resolve().parents[1]
    / "working/nba-tools-completion-program/collection-requests"
    / "rollover-period-readiness-2026-27.json"
)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _instant(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("Original capture time lacks timezone")
    return result.astimezone(UTC)


def recovery_requirement(original_zip, parent_request, expected_zip_sha256, *, checked_at=None):
    """Check byte provenance and exact parent partition before generating any package."""
    checked_at = checked_at or datetime.now(UTC)
    if checked_at.tzinfo is None:
        raise ValueError("Recovery check time lacks timezone")
    parent = copy.deepcopy(parent_request)
    if validate_request(parent) != PARENT_SHA256 or len(parent["jobs"]) != 1061:
        raise ValueError("Recovery requires the immutable reviewed 1061-job request")
    original_zip = Path(original_zip)
    if original_zip.is_symlink() or _sha(original_zip.read_bytes()) != expected_zip_sha256:
        raise ValueError("Original partial ZIP differs from expected immutable bytes")
    with tempfile.TemporaryDirectory(prefix="readiness-recovery-") as temporary:
        source = Path(temporary) / "original"
        unpack(original_zip, parent, source)
        acquisition_raw = (source / "acquisition.json").read_bytes()
        report = json.loads(acquisition_raw)
        if (
            report["request"] != parent
            or report["request_sha256"] != PARENT_SHA256
            or report["production_writes"] != 0
            or report["canonical_period_accepted"] is not False
            or report["transport_finished"] is not False
            or (source / "sources/capture-attempt.json").read_bytes() != acquisition_raw
        ):
            raise ValueError("Original partial capture metadata differs")
        attempts = report["attempts"]
        if len(attempts) != 603 or report["unattempted_jobs"] != parent["jobs"][603:]:
            raise ValueError("Original capture does not partition the reviewed request")
        previous = _instant(report["captured_at"])
        retained = []
        expected_files = {"acquisition.json", "sources/capture-attempt.json"}
        for index, (attempt, job) in enumerate(zip(attempts, parent["jobs"], strict=False)):
            started, finished = _instant(attempt["started_at"]), _instant(attempt["finished_at"])
            if (
                attempt["job"] != job
                or attempt["parameters"] != job["parameters"]
                or attempt["endpoint"] != job["endpoint"]
                or attempt["url"] != f"https://stats.nba.com/stats/{job['endpoint']}"
                or attempt["attempts"] != 1
                or attempt["timeout_seconds"] != 30
                or not previous <= started <= finished
            ):
                raise ValueError("Original attempt identity, order or clock differs")
            previous = finished
            if index == 602:
                if (
                    attempt.get("error_type") != "ReadTimeout"
                    or attempt["http_status"] is not None
                    or attempt["response_bytes"] != 0
                    or attempt["response_sha256"] != _sha(b"")
                    or attempt["source_file"] is not None
                    or attempt["response_complete"] is not False
                    or attempt["transport_complete"] is not False
                    or job["endpoint"] != "boxscoreadvancedv3"
                    or job["parameters"]["GameID"] != "0022600116"
                    or job["parameters"]["StartPeriod"] != 1
                    or job["parameters"]["EndPeriod"] != 1
                ):
                    raise ValueError(
                        "Failed attempt is not the diagnosed zero-byte transport timeout"
                    )
                failed = copy.deepcopy(attempt)
                continue
            if (
                attempt["http_status"] != 200
                or attempt["response_complete"] is not True
                or attempt["transport_complete"] is not True
                or attempt["source_file"] != job["source_file"]
                or not 0 < attempt["response_bytes"] <= 2_000_000
                or "error_type" in attempt
            ):
                raise ValueError("Previously completed source lacks successful transport evidence")
            raw = (source / job["source_file"]).read_bytes()
            if len(raw) != attempt["response_bytes"] or _sha(raw) != attempt["response_sha256"]:
                raise ValueError("Previously completed source bytes differ")
            if not isinstance(json.loads(raw), dict):
                raise ValueError("Previously completed source is not a JSON object")
            expected_files.add(job["source_file"])
            retained.append(
                dict(
                    parent_job_index=index,
                    source_file=job["source_file"],
                    bytes=len(raw),
                    sha256=_sha(raw),
                    captured_at=attempt["finished_at"],
                )
            )
        actual_files = {
            path.relative_to(source).as_posix()
            for path in source.rglob("*")
            if path.is_file() and path.name != "collection-manifest.json"
        }
        if actual_files != expected_files:
            raise ValueError("Original source set is not the exact retained successful population")
        if _instant(report["finished_at"]) < previous:
            raise ValueError("Original capture finish precedes final attempt")
        not_before = _instant(failed["finished_at"]) + timedelta(minutes=10)
        if checked_at < not_before:
            raise ValueError("Diagnosed transient timeout recovery requires cooldown")
    ledger = dict(
        classification="byte_verified_retained_sources_not_full_statistical_acceptance",
        original_zip_sha256=expected_zip_sha256,
        parent_request_sha256=PARENT_SHA256,
        acquisition_sha256=_sha(acquisition_raw),
        retained_successful_sources=retained,
        retained_source_count=602,
        failed_attempt=failed,
        unattempted_job_count=458,
        no_successful_source_reacquisition=True,
        player_advanced_reacquisition=False,
        statistical_qualification="Separate source/statistical review remains mandatory",
        production_writes=0,
    )
    ledger_sha = _sha(_json(ledger))
    request = copy.deepcopy(parent)
    request["jobs"] = copy.deepcopy(parent["jobs"][602:])
    request["maximum_requests"] = 459
    request["recovery"] = dict(
        original_zip_sha256=expected_zip_sha256,
        parent_request_sha256=PARENT_SHA256,
        reuse_ledger_sha256=ledger_sha,
        retained_successful_sources=602,
        failed_job_parent_index=602,
        unattempted_parent_job_indices=[603, 1060],
        exact_scope=(
            "failed zero-byte request plus 458 never-attempted jobs; zero successful repeats"
        ),
        retry_reason=(
            "One ReadTimeout after 602 successful responses; no HTTP/error body or "
            "invalid-statistics "
            "evidence. A separate one-attempt retry after cooldown does not relax fail-fast policy."
        ),
        retry_not_before=not_before.isoformat(),
        recovery_checked_at=checked_at.astimezone(UTC).isoformat(),
    )
    if len(request["jobs"]) != 459 or any(job in request["jobs"] for job in parent["jobs"][:602]):
        raise ValueError("Recovery would repeat a successful source or omit unfinished work")
    request["scope"] = (
        "459 unfinished period requests;602successful originals retained for separate "
        "qualification; no successful source repeats or snapshot recapture; staging only"
    )
    request_sha = validate_request(request)
    proof = dict(
        original_zip_sha256=expected_zip_sha256,
        parent_request_sha256=PARENT_SHA256,
        recovery_request_sha256=request_sha,
        reuse_ledger_sha256=ledger_sha,
        original_jobs=1061,
        parent_recovery_jobs=459,
        added_first_time_jobs=0,
        verified_successful_jobs=602,
        failed_jobs=1,
        never_attempted_jobs=458,
        recovery_jobs=459,
        repeated_successful_jobs=0,
        parent_job_indices=list(range(602, 1061)),
        first_recovery_job=request["jobs"][0],
        fixed_cutoff=request["fixed_cutoff"],
        nba_api_version=report["nba_api_version"],
        checked_at=checked_at.astimezone(UTC).isoformat(),
        production_writes=0,
    )
    return request, ledger, proof


NEW_GAME_IDS = [f"0022600{value}" for value in range(154, 158)]
BASIS_GAME_IDS = [
    "0022600091",
    "0022600109",
    "0022600118",
    "0022600121",
    "0022600138",
    "0022600142",
    "0022600144",
]
PERIOD_WINDOWS = [
    ("q1", 1, 1),
    ("q2", 2, 2),
    ("q3", 3, 3),
    ("q4", 4, 4),
    ("h1", 1, 2),
    ("h2", 3, 4),
]


def extend_requirement(request, proof, scope_path):
    """Append only the explicitly recorded four-game and seven-game source gaps."""
    scope_path = Path(scope_path)
    if scope_path.is_symlink():
        raise ValueError("Extension scope cannot be a symlink")
    raw = scope_path.read_bytes()
    scope = json.loads(raw)
    new_ids = scope["new_game_ids"]
    ot_ids = scope["new_overtime_game_ids"]
    summary_ids = scope["missing_summary_game_ids"]
    snapshot_endpoints = scope.get("advanced_snapshot_endpoints", [])
    snapshot_reason = scope.get("advanced_snapshot_reason", "")
    if (
        new_ids != NEW_GAME_IDS
        or scope["fixed_cutoff"] != "2026-11-01"
        or set(scope["due_game_ids"]) != set(request["game_ids"]) | set(NEW_GAME_IDS)
        or len(scope["due_game_ids"]) != 92
        or ot_ids != sorted(set(ot_ids))
        or not set(ot_ids).issubset(NEW_GAME_IDS)
        or summary_ids != sorted(set(summary_ids))
        or not set(summary_ids).issubset(NEW_GAME_IDS)
        or scope["traditional_basis_game_ids"] != BASIS_GAME_IDS
        or snapshot_endpoints not in [[], ["leaguedashplayerstats", "leaguedashteamstats"]]
        or (snapshot_endpoints and len(snapshot_reason) < 20)
        or not re.fullmatch(r"[a-f0-9]{64}", scope["schedule_sha256"])
        or _instant(scope["checked_at"]) < _instant(request["cutoff_checked_at"])
    ):
        raise ValueError(
            "Extension differs from the bounded current-due and source-basis dependency"
        )
    additional = [
        dict(
            endpoint="boxscoresummaryv3",
            parameters={"GameID": gid},
            source_file=f"sources/boxscoresummaryv3_{gid}.json",
        )
        for gid in summary_ids
    ]
    for gid in new_ids:
        windows = PERIOD_WINDOWS + ([("ot", 5, 14)] if gid in ot_ids else [])
        for label, start, end in windows:
            for name in ["boxscoretraditionalv3", "boxscoreadvancedv3"]:
                additional.append(
                    dict(
                        endpoint=name,
                        parameters=dict(
                            GameID=gid,
                            StartPeriod=start,
                            EndPeriod=end,
                            RangeType=1,
                            StartRange=0,
                            EndRange=28800,
                        ),
                        source_file=f"sources/{name}_{gid}_{label}.json",
                    )
                )
    for gid in BASIS_GAME_IDS:
        additional.append(
            dict(
                endpoint="boxscoretraditionalv3",
                parameters=dict(
                    GameID=gid,
                    StartPeriod="0",
                    EndPeriod="0",
                    RangeType="0",
                    StartRange="0",
                    EndRange="0",
                ),
                source_file=f"sources/boxscoretraditionalv3_{gid}_full.json",
            )
        )
    if snapshot_endpoints:
        from nba_api.stats.endpoints import LeagueDashPlayerStats, LeagueDashTeamStats

        for cls in [LeagueDashPlayerStats, LeagueDashTeamStats]:
            endpoint = cls(
                season="2026-27",
                season_type_all_star="Regular Season",
                measure_type_detailed_defense="Advanced",
                per_mode_detailed="PerGame",
                date_to_nullable="11/01/2026",
                get_request=False,
            )
            # Both v1.12 endpoint declarations add an unset optional ISTRound.
            parameters = {**endpoint.parameters, "ISTRound": None}
            additional.append(
                dict(
                    endpoint=endpoint.endpoint,
                    parameters=parameters,
                    source_file=f"sources/{endpoint.endpoint}_advanced_through_20261101.json",
                )
            )
    result = copy.deepcopy(request)
    result["jobs"].extend(additional)
    result["maximum_requests"] = len(result["jobs"])
    result["fixed_cutoff"] = scope["fixed_cutoff"]
    result["cutoff_checked_at"] = scope["checked_at"]
    result["due_cutoff"] = (_instant(scope["checked_at"]) - timedelta(hours=24)).isoformat()
    result["game_ids"] = sorted(scope["due_game_ids"])
    result["overtime_game_ids"] = sorted(set(result["overtime_game_ids"]) | set(ot_ids))
    result["schedule_sha256"] = scope["schedule_sha256"]
    result["scope"] = (
        "459 unfinished period requests plus explicitly bound first-time inputs for92duegames "
        "and seven prior Advanced/core basis conflicts; no successful source or snapshot repeats; "
        "staging only, full acceptance remains unproven"
    )
    result["recovery_extension"] = dict(
        scope_report_sha256=_sha(raw),
        additional_jobs_sha256=_sha(_json(additional)),
        new_game_ids=new_ids,
        new_overtime_game_ids=ot_ids,
        missing_summary_game_ids=summary_ids,
        traditional_basis_game_ids=BASIS_GAME_IDS,
        first_time_jobs=len(additional),
        advanced_snapshot_endpoints=snapshot_endpoints,
        advanced_snapshot_reason=snapshot_reason,
        advanced_snapshot_date_to="11/01/2026" if snapshot_endpoints else None,
        reconstruction="Direct source windows only; no quarter-to-half or Advanced reconstruction",
        quality_failures=(
            "Previously captured malformed clocks remain quarantined; no corresponding "
            "period recapture or silent statistic replacement is requested"
        ),
        full_snapshot_acceptance=False,
    )
    request_sha = validate_request(result)
    parent = json.loads(PARENT_PATH.read_bytes())
    successful = {_json(job) for job in parent["jobs"][:602]}
    if any(_json(job) in successful for job in result["jobs"]):
        raise ValueError("Extension repeats an already successful source job")
    updated = copy.deepcopy(proof)
    updated.update(
        recovery_request_sha256=request_sha,
        recovery_jobs=len(result["jobs"]),
        added_first_time_jobs=len(additional),
        new_game_period_pairs=24 + len(ot_ids),
        summary_jobs=len(summary_ids),
        whole_traditional_basis_jobs=7,
        date_filtered_snapshot_jobs=len(snapshot_endpoints),
        advanced_snapshot_date_to="11/01/2026" if snapshot_endpoints else None,
        fixed_cutoff=scope["fixed_cutoff"],
        extension_scope_sha256=_sha(raw),
        extension_jobs_sha256=_sha(_json(additional)),
        current_due_game_ids=sorted(scope["due_game_ids"]),
        full_snapshot_acceptance=False,
    )
    return result, updated


MAC_LAUNCHER = """#!/bin/sh
cd -- "$(dirname -- "$0")" || exit 1
found=0
# Preserve the proven PATH route first, then check only finite existing environments.
set -- python3 python
if [ -n "${VIRTUAL_ENV:-}" ]; then
    set -- "$@" "$VIRTUAL_ENV/bin/python"
fi
for runtime in "$@" ".venv/bin/python" "venv/bin/python" \
    "../.venv/bin/python" "../venv/bin/python"; do
    if "$runtime" -c 'import nba_api' >/dev/null 2>&1; then
        "$runtime" run_capture.py
        found=1
        break
    fi
done
if [ "$found" -eq 0 ]; then
    python3 run_capture.py
fi
printf '\\nReturn readiness-capture/collection.zip, including after a failure.\\n'
printf 'Press Return to close.'
read -r ignored
"""

WINDOWS_LAUNCHER = r"""@echo off
cd /d "%~dp0"
call :try_python python3 && goto done
call :try_python python && goto done
py -3 -c "import nba_api" >nul 2>&1
if not errorlevel 1 (
    py -3 run_capture.py
    goto done
)
if defined VIRTUAL_ENV call :try_python "%VIRTUAL_ENV%\Scripts\python.exe" && goto done
call :try_python "%~dp0.venv\Scripts\python.exe" && goto done
call :try_python "%~dp0venv\Scripts\python.exe" && goto done
call :try_python "%~dp0..\.venv\Scripts\python.exe" && goto done
call :try_python "%~dp0..\venv\Scripts\python.exe" && goto done
python3 run_capture.py
goto done
:try_python
"%~1" -c "import nba_api" >nul 2>&1
if errorlevel 1 exit /b 1
"%~1" run_capture.py
exit /b 0
:done
echo.
echo Return readiness-capture\collection.zip, including after a failure.
pause
"""


def build(
    original_zip,
    output,
    *,
    expected_zip_sha256=ORIGINAL_ZIP_SHA256,
    checked_at=None,
    extension_scope=None,
):
    """Build the owner package offline; no endpoint invocation or source publication."""
    parent = json.loads(PARENT_PATH.read_bytes())
    request, ledger, proof = recovery_requirement(
        original_zip, parent, expected_zip_sha256, checked_at=checked_at
    )
    if extension_scope is not None:
        request, proof = extend_requirement(request, proof, extension_scope)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "readiness-recovery-request.json").write_text(json.dumps(request, indent=2) + "\n")
    (output / "reuse-ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")
    package = output / "NBA-Tools-Readiness-Recovery.zip"
    binding = build_owner_bundle(request, package)
    # Keep the existing collector executable byte-for-byte; replace wrappers only.
    with zipfile.ZipFile(package) as original:
        members = [(entry, original.read(entry)) for entry in original.infolist()]
    temporary = output / "package.tmp"
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
        for entry, raw in members:
            if entry.filename == "Run Capture.command":
                raw = MAC_LAUNCHER.encode()
            elif entry.filename == "Run Capture.bat":
                raw = WINDOWS_LAUNCHER.replace("\n", "\r\n").encode()
            elif entry.filename == "READ ME.txt":
                raw = (
                    "Unzip this recovery package in a new folder beside your previous "
                    "capture folder.\n"
                    "Open Run Capture.command on Mac or Run Capture.bat on Windows.\n"
                    "It uses Python/nba_api already installed: PATH, active environment, then "
                    "existing sibling/parent .venv or venv. It installs nothing.\n"
                    f"Exactly {len(request['jobs'])} requests: one explicit retry of the zero-byte "
                    "timeout and 458 previously unattempted jobs"
                    f" plus {proof['added_first_time_jobs']} first-time source requests. "
                    "All 602 successful originals, including Player "
                    "Advanced through 10/31 and 0116 Q1 Traditional, are retained in the cloud.\n"
                    "Any new dated Advanced requests use 11/01; 10/31 is not repeated.\n"
                    "One attempt per job, 30-second timeout, 1-second minimum spacing, "
                    "12-hour ceiling.\n"
                    "Return readiness-capture/collection.zip even on failure. "
                    "Keep all prior outputs. "
                    "Do not rerun the original 1061-job package, delete outputs, "
                    "or troubleshoot.\n"
                    "This does not accept a snapshot or publish production data.\n"
                ).encode()
            archive.writestr(entry, raw)
    temporary.replace(package)
    proof.update(binding)
    proof["owner_bundle_sha256"] = _sha(package.read_bytes())
    proof["collector_transport_policy_unchanged"] = True
    proof["collector_source_sha256"] = _sha(
        Path(__file__).with_name("collect_rollover_readiness_laptop.py").read_bytes()
    )
    proof["collector_policy"] = (
        "Unchanged fail-fast transport loop and all request/size/time safeguards; "
        "narrow full-Traditional and Summary source forms, no automatic retry"
    )
    (output / "build-report.json").write_text(json.dumps(proof, indent=2) + "\n")
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_zip", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--extension-scope", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            build(args.original_zip, args.output, extension_scope=args.extension_scope), indent=2
        )
    )


if __name__ == "__main__":
    main()
