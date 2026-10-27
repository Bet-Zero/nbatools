"""Bounded source-reachability research, never NBA feature acceptance.

This task-branch-only selector must not be merged as an unattended acquisition
entry point. The owner authorized a representative source investigation; a
recorded timeout establishes unavailable access, never an empty NBA population.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests
from nba_api.stats.library.http import STATS_HEADERS

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
SAMPLES = (
    ("2025-26", "0022500002"),
    ("1997-98", "0029700001"),
    ("2004-05", "0020400001"),
    ("2014-15", "0021400001"),
)
ENDPOINTS = ("boxscoretraditionalv3", "boxscoresummaryv3")


def test_bounded_structured_source_research(tmp_path, capfd):
    assert os.environ.get("SCOPE") == "targeted"
    assert os.environ.get("TESTS") == (
        "tests/test_k08_structured_source_probe_real_data.py::test_bounded_structured_source_research"
    )
    output = (
        Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", tmp_path)) / "structured-source-research"
    )
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for endpoint in ENDPOINTS:
        for index, (season, game_id) in enumerate(SAMPLES):
            canonical = data_read_csv(f"raw/games/{season}_regular_season.csv")
            game = canonical.loc[canonical.game_id.astype(int).eq(int(game_id))]
            assert len(game) == 1 and str(game.iloc[0].is_final).lower() in {"true", "1"}
            params = {"GameID": game_id}
            if endpoint == "boxscoretraditionalv3":
                params.update(EndPeriod=0, EndRange=0, RangeType=0, StartPeriod=0, StartRange=0)
            started = time.monotonic()
            receipt = dict(
                endpoint=endpoint,
                game_id=game_id,
                season=season,
                url=f"https://stats.nba.com/stats/{endpoint}",
                parameters=params,
                captured_at=datetime.now(UTC).isoformat(),
                attempts=1,
                timeout_seconds=12,
                classification="diagnostic_only_not_feature_acceptance",
                historical_coverage="unknown",
            )
            reachable = False
            try:
                with requests.get(
                    receipt["url"],
                    params=params,
                    headers=STATS_HEADERS,
                    timeout=12,
                    stream=True,
                ) as response:
                    raw = response.raw.read(1_500_001, decode_content=True)
                    receipt["http_status"] = response.status_code
                digest = hashlib.sha256(raw).hexdigest()
                name = f"{endpoint}_{game_id}.response"
                (output / name).write_bytes(raw)
                receipt.update(raw_file=name, bytes=len(raw), sha256=digest)
                if len(raw) > 1_500_000:
                    receipt["status"] = "oversized_response_rejected"
                elif receipt["http_status"] != 200:
                    receipt["status"] = "http_failure"
                else:
                    payload = json.loads(raw)
                    key = "boxScoreTraditional" if endpoint == ENDPOINTS[0] else "boxScoreSummary"
                    body = payload.get(key, {})
                    reachable = body.get("gameId") == game_id
                    receipt["status"] = (
                        "matching_game_response" if reachable else "unmatched_response"
                    )
                    if reachable:
                        receipt["historical_coverage"] = (
                            "one_matching_game_only_unqualified_player_states"
                        )
                        receipt["side_player_rows"] = {
                            side: len(body.get(side, {}).get("players", []))
                            for side in ("homeTeam", "awayTeam")
                        }
                        receipt["side_inactive_rows"] = {
                            side: len(body.get(side, {}).get("inactives", []))
                            for side in ("homeTeam", "awayTeam")
                        }
            except Exception as error:
                receipt.update(status="request_or_parse_failure", error_type=type(error).__name__)
            receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
            results.append(receipt)
            # A recent failure leaves this endpoint's historical reachability
            # unknown. Do not spend three more attempts on the same access block.
            if index == 0 and not reachable:
                break
    report = dict(
        classification="bounded_source_diagnostic_not_feature_acceptance",
        candidate_sha=os.environ.get("VALIDATION_SHA"),
        generation=os.environ.get("NBATOOLS_DATA_GENERATION"),
        no_bulk_acquisition=True,
        production_writes=0,
        results=results,
    )
    (output / "live-source-probe.json").write_text(json.dumps(report, indent=2) + "\n")
    assert 2 <= len(results) <= 8
    with capfd.disabled():
        print("K08_STRUCTURED_SOURCE_DIAGNOSTIC " + json.dumps(report, sort_keys=True), flush=True)
