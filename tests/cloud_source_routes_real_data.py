"""Explicit setup diagnostics: real public sources, no production writes.

An outer pass means the bounded diagnostic completed, NOT source acceptance.
Only the separate archive qualification test asserts usable canonical records.
"""

import hashlib
import json
import os
import time
from pathlib import Path

import pytest
import requests

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def test_official_cloud_alternatives(capfd):
    from nba_api.stats.endpoints import LeagueGameLog, PlayerGameLogs, TeamGameLogs

    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "official-alternatives"
    output.mkdir(parents=True, exist_ok=False)
    results = []
    # Public documented endpoints, normal nba_api headers. No alternate IP,
    # relay, cookie, token, spoofed origin, or source restriction bypass.
    endpoints = [
        ("leaguegamelog", LeagueGameLog, {"season": "2025-26"}),
        ("playergamelogs", PlayerGameLogs, {"season_nullable": "2025-26"}),
        ("teamgamelogs", TeamGameLogs, {"season_nullable": "2025-26"}),
    ]
    for name, cls, kwargs in endpoints:
        start = time.monotonic()
        result = {"source": name, "timeout_seconds": 12, "attempts": 1}
        try:
            endpoint = cls(timeout=12, **kwargs)
            frames = endpoint.get_data_frames()
            result.update(status="received", rows=[len(f) for f in frames])
            (output / f"{name}.json").write_text(json.dumps(endpoint.get_dict()))
        except Exception as exc:
            result.update(status="unavailable", error_type=type(exc).__name__)
        result["elapsed_seconds"] = round(time.monotonic() - start, 2)
        results.append(result)

    base = "https://cdn.nba.com/static/json/"
    urls = [
        base + "staticData/scheduleLeagueV2.json",
        base + "staticData/scheduleLeagueV2_2.json",
        base + "liveData/scoreboard/todaysScoreboard_00.json",
        base + "liveData/boxscore/boxscore_0022400001.json",
        base + "liveData/playbyplay/playbyplay_0022400001.json",
    ]
    for index, url in enumerate(urls):
        result = {"url": url, "attempts": 1, "timeout_seconds": 12}
        try:
            with requests.get(url, timeout=12, stream=True) as response:
                payload = bytearray()
                for chunk in response.iter_content(65536):
                    payload.extend(chunk)
                    if len(payload) > 8_000_000:
                        raise ValueError("bounded response exceeded 8MB")
                result.update(
                    http_status=response.status_code,
                    bytes=len(payload),
                    sha256=hashlib.sha256(payload).hexdigest(),
                )
                if response.ok:
                    data = json.loads(payload)
                    result.update(status="received-json", keys=list(data)[:10])
                    (output / f"cdn-{index}.json").write_bytes(payload)
                else:
                    result["status"] = "http-failure"
        except Exception as exc:
            result.update(status="unavailable", error_type=type(exc).__name__)
        results.append(result)
    report = {"classification": "diagnostic only; no acquisition acceptance", "results": results}
    (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    with capfd.disabled():
        print("OFFICIAL_ALTERNATIVES_JSON " + json.dumps(report), flush=True)


def test_archived_core_collection(tmp_path, capfd):
    from tools.cloud_nba_archive import prepare

    receipt = prepare(tmp_path / "collected")
    assert receipt["canonical_rows"] == {
        "games": 1,
        "team_game_stats": 2,
        "player_game_stats": 21,
        "player_game_starter_roles": 21,
        "play_by_play_events": 0,
    }
    assert receipt["team_scores"] == {"CLE": 111, "NYK": 119}
    # Retained PBP is not usable canonical PBP. Keep its actual incompatibility.
    assert receipt["play_by_play"]["status"] == "canonical-rejected"
    assert receipt["play_by_play"]["raw_actions"] == 521
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "archive-collection.json").write_text(json.dumps(receipt, indent=2) + "\n")
    with capfd.disabled():
        print("ARCHIVE_COLLECTION_JSON " + json.dumps(receipt), flush=True)


def test_durable_archive_recovery(capfd):
    import io
    import zipfile

    import pandas as pd

    root = (
        Path(__file__).resolve().parents[1]
        / "working/nba-tools-completion-program/cloud-operations"
    )
    reference = json.loads((root / "core-archive-receipt.json").read_text())
    payload = (root / "core-archive-staging.zip").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == reference["durable_bundle"]["sha256"]
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        receipt = json.loads(archive.read("receipt.json"))
        assert set(archive.namelist()) == set(receipt["files"]) | {"receipt.json"}
        for name, record in receipt["files"].items():
            data = archive.read(name)
            assert len(data) == record["bytes"]
            assert hashlib.sha256(data).hexdigest() == record["sha256"]
        frame = pd.read_csv(
            io.BytesIO(archive.read("data/raw/player_game_stats/2025-26_regular_season.csv"))
        )
        assert len(frame) == 21 and frame.pts.sum() == 230
        assert frame.player_id.nunique() == 21
    with capfd.disabled():
        print(
            "ARCHIVE_RECOVERY_JSON "
            + json.dumps(
                {
                    "state": "verified",
                    "rows": 21,
                    "points": 230,
                    "bundle_sha256": reference["durable_bundle"]["sha256"],
                    "r2_writes": 0,
                }
            ),
            flush=True,
        )
