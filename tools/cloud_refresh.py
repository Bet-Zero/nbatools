"""Manual isolated freshness preparation; never uploads, publishes or prunes.

Default planning is offline. Execution requires an authenticated cloud backup,
uses existing acquisition/orchestration unchanged, and retains the input archive
on every failure. Production authorization and scheduling are separate.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from nbatools.commands.pipeline.generation_publication import (
    _build_staged_generation,
    validate_staged_generation,
)
from nbatools.commands.pipeline.orchestrator import current_refresh_season, refresh_season
from tools.cloud_backup import restore_backup

ROOT = Path(__file__).resolve().parents[1]


def plan(season=None):
    season = season or current_refresh_season()
    if (
        not re.fullmatch(r"20[0-9]{2}-[0-9]{2}", season)
        or int(season[5:]) != (int(season[:4]) + 1) % 100
    ):
        raise ValueError("Invalid bounded NBA season")
    result = refresh_season(season, "Regular Season", dry_run=True)
    return {
        "season": season,
        "season_type": "Regular Season",
        "stages": [stage.name for stage in result.stages],
        "automatic_refresh": False,
        "production_publication": False,
        "required_route": "NBA Stats core pipelines; participation alternatives are narrower",
        "readiness": "plan-only; acquisition and validation required before candidate preparation",
    }


def prepare(archive, receipt, work, *, season=None, timeout=150):
    configuration = plan(season)
    if not 1 <= timeout <= 600:
        raise ValueError("Manual acquisition timeout must be between 1 and 600 seconds")
    work = Path(work).resolve()
    if work.exists():
        raise ValueError("Refresh work directory must not exist")
    work.mkdir(parents=True)
    backup_receipt = json.loads(Path(receipt).read_text())
    restore_backup(archive, backup_receipt, work / "data")
    outcome = {
        **configuration,
        "base_generation": backup_receipt["generation_id"],
        "base_manifest_sha256": backup_receipt["manifest_sha256"],
        "production_writes": 0,
        "state": "failed",
        "candidate": None,
    }
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("R2_")
        and key not in {"NBATOOLS_DATA_GENERATION", "GH_TOKEN", "GITHUB_TOKEN"}
    }
    env.update(DATA_SOURCE="local", NBATOOLS_DATA_ROOT=str(work), PYTHONPATH=str(ROOT / "src"))
    # Fresh interpreter/CWD: old modules must not retain a production data root.
    script = """import json, sys
from dataclasses import asdict
from pathlib import Path
from nbatools.commands.pipeline.orchestrator import refresh_season
result = refresh_season(sys.argv[1], 'Regular Season', allow_no_data_skip=False)
Path('pipeline-result.json').write_text(json.dumps(asdict(result), default=str))
"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", script, configuration["season"]],
            cwd=work,
            env=env,
            timeout=timeout,
            capture_output=True,
        )
        evidence = work / "pipeline-result.json"
        if result.returncode or not evidence.is_file():
            outcome["failure"] = "Pipeline process failed without a complete stage receipt"
        else:
            pipeline = json.loads(evidence.read_text())
            stages = pipeline.get("stages", [])
            # Never mistake a dry run, skipped future season or partial stage set
            # for a successfully refreshed season.
            complete = [s.get("name") for s in stages] == configuration["stages"] and all(
                s.get("status") == "success" for s in stages
            )
            outcome["stages"] = [
                {
                    "name": s.get("name"),
                    "status": s.get("status"),
                    "duration_ms": s.get("duration_ms"),
                }
                for s in stages
            ]
            if not complete:
                outcome["failure"] = (
                    "Acquisition/build/receipt stages incomplete; no candidate prepared"
                )
            else:
                candidate = "manual-refresh-" + datetime.now(UTC).strftime("%Y%m%d%H%M%S")
                _build_staged_generation(work / "data", work / "candidate", candidate)
                manifest = validate_staged_generation(work / "candidate", candidate)
                outcome.update(
                    state="prepared_no_writes",
                    candidate=candidate,
                    current_through=pipeline.get("current_through"),
                    files=len(manifest["files"]),
                )
    except subprocess.TimeoutExpired:
        outcome["failure"] = (
            "Manual acquisition exceeded its bounded timeout; no candidate prepared"
        )
    finally:
        (work / "refresh-attempt.json").write_text(json.dumps(outcome, indent=2) + "\n")
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    planning = sub.add_parser("plan")
    planning.add_argument("--output", type=Path, required=True)
    planning.add_argument("--season")
    run = sub.add_parser("run")
    run.add_argument("archive", type=Path)
    run.add_argument("receipt", type=Path)
    run.add_argument("--work", type=Path, required=True)
    run.add_argument("--season")
    run.add_argument("--timeout", type=int, default=150)
    args = parser.parse_args()
    if args.command == "plan":
        args.output.write_text(json.dumps(plan(args.season), indent=2) + "\n")
        return
    outcome = prepare(
        args.archive, args.receipt, args.work, season=args.season, timeout=args.timeout
    )
    print(json.dumps(outcome, sort_keys=True))
    if outcome["state"] != "prepared_no_writes":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
