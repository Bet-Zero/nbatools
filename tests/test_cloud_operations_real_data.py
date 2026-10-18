"""Explicit, bounded setup operations. Only the existing read-only R2 runner.

Source failures are recorded as diagnostics, never relabeled source acceptance.
The full backup test is independently gated before durable release preservation.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools.cloud_backup import export_backup

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def test_full_generation_backup(capfd):
    root = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "cloud-backup"
    receipt = export_backup(root, os.environ["NBATOOLS_DATA_GENERATION"])
    assert receipt["files"] > 600 and receipt["data_bytes"] > 300_000_000
    assert receipt["r2_writes"] == 0 and receipt["production_pointer_unchanged"] is True
    with capfd.disabled():
        print("CLOUD_BACKUP_JSON " + json.dumps(receipt, sort_keys=True), flush=True)


def test_core_cloud_routes(tmp_path, capfd):
    from nba_api.live.nba.endpoints import boxscore

    # Actual existing core pipeline, with its normal 3 x 30-second request/retry
    # policy. Never weaken it to an eight-second diagnostic or mock NBA values.
    started = __import__("time").monotonic()
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from nbatools.commands.pipeline.pull_games import run; run('2025-26', 'Regular Season')",
        ],
        cwd=tmp_path,
        capture_output=True,
        timeout=120,
    )
    report = {
        "core_games": {
            "returned_canonical_csv": result.returncode == 0,
            "elapsed_seconds": round(__import__("time").monotonic() - started, 2),
            "normal_timeout_seconds": 30,
            "normal_attempts": 3,
        }
    }
    if result.returncode:
        report["core_games"]["error_category"] = (
            "read-timeout" if b"Read timed out" in result.stderr else "pipeline-acquisition-error"
        )
        report["core_games"]["failure"] = (
            "existing pipeline exhausted normal acquisition retries; no canonical data produced"
        )
    else:
        import pandas as pd

        games = pd.read_csv(tmp_path / "data/raw/games/2025-26_regular_season.csv")
        assert not games.empty and not games.game_id.duplicated().any()
        report["core_games"]["rows"] = len(games)
    try:
        game = boxscore.BoxScore("0022500003", timeout=20).get_dict()["game"]
        assert game["gameId"] == "0022500003" and game["gameStatus"] == 3
        report["official_live_boxscore"] = {
            "status": "returned-final-game",
            "home_points": game["homeTeam"]["score"],
            "away_points": game["awayTeam"]["score"],
        }
    except Exception as exc:
        report["official_live_boxscore"] = {
            "status": "unavailable",
            "error_type": type(exc).__name__,
        }

    # Recover the already qualified identity support from permanent Git, then
    # exercise the existing ESPN adapter rather than merely pinging scoreboard.
    bundle = tmp_path / "bundle.zip"
    import requests

    url = "https://raw.githubusercontent.com/Bet-Zero/nbatools/e4900f515bc2536859293599efdd7ba7889a7969/working/nba-tools-completion-program/cloud-staged/recovery-bundle.zip"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    bundle.write_bytes(response.content)
    assert (
        hashlib.sha256(response.content).hexdigest()
        == "1a482b76f7455dc6cefef89620e9e2d935f144b2c2765ce624080bf6e33ac9ea"
    )
    import zipfile

    with zipfile.ZipFile(bundle) as archive:
        # Exact reviewed hash above authenticates this fixed small inventory.
        assert sum(i.file_size for i in archive.infolist()) < 500_000
        archive.extractall(tmp_path / "identity")
    from nbatools.commands.pipeline.player_game_availability_espn import espn_boxscore_as_v3

    try:
        rows, event = espn_boxscore_as_v3(
            game_id=22500003,
            game_date="2025-10-22",
            season="2025-26",
            season_type="Regular Season",
            home_team_id=1610612752,
            away_team_id=1610612739,
            data_root=tmp_path / "identity/data",
        )
        assert len(rows) >= 21 and rows.personId.nunique() == len(rows)
        report["espn_participation"] = {
            "status": "qualified-adapter-returned",
            "rows": len(rows),
            "event_id": event,
            "scope": "participation only; canonical NBA identity support required",
        }
    except Exception as exc:
        report["espn_participation"] = {
            "status": "unavailable-or-unqualified",
            "error_type": type(exc).__name__,
        }
    report["classification"] = "source diagnostics, not universal core acquisition acceptance"
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "source-routes.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    with capfd.disabled():
        print("CLOUD_ROUTES_JSON " + json.dumps(report, sort_keys=True), flush=True)
