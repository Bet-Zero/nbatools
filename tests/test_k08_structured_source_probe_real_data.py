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


def test_transport_exact_three_retained_reports(tmp_path, capfd):
    """Transfer already acquired originals through existing Actions read access."""
    import base64
    import io
    import re
    import zipfile
    from urllib.parse import urlparse

    assert os.environ.get("SCOPE") == "targeted"
    assert os.environ.get("TESTS") == (
        "tests/test_k08_structured_source_probe_real_data.py::test_transport_exact_three_retained_reports"
    )
    artifact_id = 12750809462
    expected_zip_sha = "be00e2815bb2e66081fc2c247cdace2969bd25801f039762f8a0af75bc5a3b21"
    api_url = f"https://api.github.com/repos/Bet-Zero/nbatools/actions/artifacts/{artifact_id}/zip"
    # The existing job supplies an actions:read token. Never send it to the
    # storage redirect host or print headers, signed URLs, or exception strings.
    try:
        first = requests.get(
            api_url,
            headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}"},
            allow_redirects=False,
            timeout=20,
        )
        assert first.status_code == 302
        location = first.headers["Location"]
        host = urlparse(location)
        valid_host = (
            host.scheme == "https"
            and bool(host.hostname)
            and host.hostname.endswith(".blob.core.windows.net")
        )
        assert valid_host
        with requests.get(location, stream=True, timeout=20, allow_redirects=False) as response:
            assert response.status_code == 200
            raw = response.raw.read(2_000_001, decode_content=True)
    except requests.RequestException as error:
        raise AssertionError(type(error).__name__) from None
    assert len(raw) <= 2_000_000 and hashlib.sha256(raw).hexdigest() == expected_zip_sha
    names = ("20251024_MINLAL", "20251026_LALSAC", "20251027_PORLAL")
    prefix = "acquired_data/raw/player_game_availability_sources/"
    retained = []
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        assert len({m.filename for m in members}) == len(members)
        assert len(members) <= 100 and sum(m.file_size for m in members) <= 2_000_000
        for name in names:
            content = archive.read(prefix + name + ".json")
            receipt = json.loads(content)
            digest = receipt["sha256"]
            assert re.fullmatch(r"[0-9a-f]{64}", digest)
            assert receipt["raw_file"] == digest + ".pdf"
            assert receipt["source_url"] == (f"https://statsdmz.nba.com/pdfs/{name[:8]}/{name}.pdf")
            captured = datetime.fromisoformat(receipt["retrieved_at"])
            assert captured.tzinfo is not None
            pdf = archive.read(prefix + receipt["raw_file"])
            assert pdf.startswith(b"%PDF") and len(pdf) == receipt["size_bytes"]
            assert hashlib.sha256(pdf).hexdigest() == digest
            for filename, payload in ((name + ".json", content), (receipt["raw_file"], pdf)):
                retained.append(
                    dict(
                        name=filename,
                        bytes=len(payload),
                        sha256=hashlib.sha256(payload).hexdigest(),
                        data_base64=base64.b64encode(payload).decode("ascii"),
                    )
                )
    assert len(retained) == 6 and len({r["name"] for r in retained}) == 6
    with capfd.disabled():
        for item in retained:
            print("K08_RETAINED_FILE " + json.dumps(item, sort_keys=True), flush=True)
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", tmp_path))
    output.mkdir(parents=True, exist_ok=True)
    (output / "retained-transfer-receipt.json").write_text(
        json.dumps(
            dict(
                artifact_id=artifact_id,
                archive_sha256=expected_zip_sha,
                classification="existing_original_byte_transfer_no_new_NBA_acquisition",
                source_requests=0,
                production_writes=0,
                files=[{k: v for k, v in item.items() if k != "data_base64"} for item in retained],
            ),
            indent=2,
        )
        + "\n"
    )
