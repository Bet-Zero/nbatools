"""One explicit two-report capture through the existing read-only runner."""

import base64
import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from nbatools.data_source import data_path
from tests import cloud_official_gamebooks_real_data as existing

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = (
    ROOT
    / "working/nba-tools-completion-program/source-evidence/cleveland-full-boxscore-2024/originals.zip"
)
CASES = [
    {"game_id": "0022400199", "game_code": "20241109/BKNCLE", "scores": [100, 105]},
    {"game_id": "0022400893", "game_code": "20250305/MIACLE", "scores": [107, 112]},
]


def test_capture_only_two_official_final_boxes(monkeypatch, capfd):
    assert os.environ["NBATOOLS_DATA_GENERATION"] == "availability-season-inactive-2024-v1-20261116"
    assert (
        hashlib.sha256(data_path("data/metadata/generation_manifest.json").read_bytes()).hexdigest()
        == "0abce6f8261957df6cffc19ce24a4ed408a548e1292a33456ce55c0481903ecc"
    )
    assert (
        hashlib.sha256(ORIGINALS.read_bytes()).hexdigest()
        == "594bab365fa2eda59a217c2137bda901dd0d55b7c8e60268a7ba9f2da2ab66d6"
    )
    cases = []
    with ZipFile(ORIGINALS) as archive:
        for case in CASES:
            source = json.loads(archive.read(f"sources/boxscoresummaryv3_{case['game_id']}.json"))[
                "boxScoreSummary"
            ]
            day, clubs = case["game_code"].split("/")
            assert source["gameId"] == case["game_id"] and source["gameCode"] == case["game_code"]
            assert source["gameStatus"] == 3 and source["gameEt"][:10].replace("-", "") == day
            assert [source[s]["score"] for s in ("awayTeam", "homeTeam")] == case["scores"]
            cases.append(dict(case, url=f"https://statsdmz.nba.com/pdfs/{day}/{day}_{clubs}.pdf"))
    request_sha = hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest()
    monkeypatch.setattr(existing, "REQUEST_SHA", request_sha)
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "cleveland-two-game-source"
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for case in cases:
        try:
            receipt = existing.capture(case, output / case["game_id"])
            results.append(dict(game_id=case["game_id"], capture=receipt))
        except Exception as exc:
            results.append(
                dict(game_id=case["game_id"], unavailable=type(exc).__name__, error=str(exc))
            )
    report = dict(
        classification="bounded_source_capture_not_membership_or_participation_acceptance",
        cases=results,
        attempts=2,
        production_writes=0,
    )
    (output / "batch.json").write_text(json.dumps(report, indent=2) + "\n")
    with capfd.disabled():
        print("CLEVELAND_TWO_SOURCE_CAPTURE " + json.dumps(report), flush=True)
    assert not any("unavailable" in r for r in results), report


def test_read_only_retained_two_report_artifact(capfd):
    """Transfer already captured public originals; no NBA fetch or data writes."""
    from tools.r2_publication import api

    payload = api("/actions/artifacts/14743399780/zip", binary=True)
    assert len(payload) == 55441
    assert (
        hashlib.sha256(payload).hexdigest()
        == "df954fe55ca067859dfa0cd76571b76cb8af7439eef27e037820665e131c535d"
    )
    encoded = base64.b64encode(payload).decode("ascii")
    with capfd.disabled():
        for index, start in enumerate(range(0, len(encoded), 4096)):
            print(
                f"CLEVELAND_RETAINED_CHUNK {index:02d} {encoded[start : start + 4096]}", flush=True
            )
