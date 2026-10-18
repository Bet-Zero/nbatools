"""Explicit reviewed real-source selectors; excluded from ordinary test discovery."""

import hashlib
import io
import json
import os
import zipfile
from pathlib import Path

import pandas as pd
import pytest
import requests

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "working/nba-tools-completion-program/cloud-operations"


def test_season_inputs_collection(tmp_path, capfd):
    from tools.cloud_season_sources import qualify

    receipt = qualify(tmp_path / "collected")
    assert receipt["canonical_rows"] == {
        "player_season_advanced": 582,
        "team_season_advanced": 30,
        "standings_snapshots": 30,
    }
    assert receipt["roster_snapshot"]["missing_team_ids"] == [1610612752]
    assert receipt["roster_snapshot"]["teams"] == 29
    assert receipt["rollover"]["regular_games"] == 1206
    assert receipt["rollover"]["final_regular_games"] == 0
    assert receipt["rollover"]["advanced_player_rows"] == 0
    assert receipt["automatic_refresh"] is False and receipt["production_writes"] == 0
    reference = json.loads((EVIDENCE / "season-inputs-receipt.json").read_text())
    assert receipt["files"] == reference["files"]
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "season-inputs-collection.json").write_text(json.dumps(receipt, indent=2) + "\n")
    with capfd.disabled():
        print("SEASON_INPUTS_COLLECTION_JSON " + json.dumps(receipt), flush=True)


def test_durable_season_inputs_recovery(capfd):
    reference = json.loads((EVIDENCE / "season-inputs-receipt.json").read_text())
    payload = (EVIDENCE / "season-inputs-staging.zip").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == reference["durable_bundle"]["sha256"]
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert sum(i.file_size for i in archive.infolist()) < 10_000_000
        assert set(archive.namelist()) == set(reference["files"]) | {"receipt.json"}
        for name, item in reference["files"].items():
            data = archive.read(name)
            assert hashlib.sha256(data).hexdigest() == item["sha256"] and len(data) == item["bytes"]
        players = pd.read_csv(
            io.BytesIO(archive.read("data/raw/player_season_advanced/2025-26_regular_season.csv"))
        )
        teams = pd.read_csv(
            io.BytesIO(archive.read("data/raw/team_season_advanced/2025-26_regular_season.csv"))
        )
        standings = pd.read_csv(
            io.BytesIO(archive.read("data/raw/standings_snapshots/2025-26_regular_season.csv"))
        )
        assert len(players) == players.player_id.nunique() == 582
        assert len(teams) == 30 and teams.games_played.eq(82).all()
        assert standings.wins.sum() == standings.losses.sum() == 1230
        assert "data/raw/rosters/2025-26.csv" not in archive.namelist()
    with capfd.disabled():
        print(
            "SEASON_INPUTS_RECOVERY_JSON "
            + json.dumps(
                {
                    "state": "verified",
                    "player_rows": 582,
                    "team_rows": 30,
                    "standings_rows": 30,
                    "production_writes": 0,
                }
            ),
            flush=True,
        )


def test_public_nba_web_route_diagnostic(capfd):
    # New public source route, one ordinary request per URL. No browser
    # impersonation, cookies, proxy rotation or retries of blocked Stats APIs.
    results = []
    for url in [
        "https://www.nba.com/game/cle-vs-nyk-0022500003/box-score",
        "https://www.nba.com/stats/players/traditional",
        "https://www.nba.com/stats/teams/traditional",
    ]:
        record = {"url": url, "attempts": 1, "timeout_seconds": 12}
        try:
            with requests.get(url, timeout=12, stream=True) as response:
                payload = bytearray()
                for chunk in response.iter_content(65536):
                    payload.extend(chunk)
                    if len(payload) > 8_000_000:
                        raise ValueError("Response limit")
                record.update(
                    http_status=response.status_code,
                    bytes=len(payload),
                    sha256=hashlib.sha256(payload).hexdigest(),
                )
                record["embedded_next_data"] = b"__NEXT_DATA__" in payload
                record["classification"] = (
                    "retrieved; content qualification required" if response.ok else "unavailable"
                )
        except Exception as exc:
            record.update(classification="unavailable", error_type=type(exc).__name__)
        results.append(record)
    report = {"classification": "diagnostic only, not source acceptance", "results": results}
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "public-web-route.json").write_text(json.dumps(report, indent=2) + "\n")
    with capfd.disabled():
        print("PUBLIC_WEB_ROUTE_JSON " + json.dumps(report), flush=True)
