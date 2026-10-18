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
