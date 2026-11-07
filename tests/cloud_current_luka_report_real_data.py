"""One bounded official final report fallback for an original Rest obligation."""

import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

import pytest

from tests.cloud_rollover_0144_report_capture_real_data import LIMIT, _NoRedirect

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "working/nba-tools-completion-program/source-evidence/core-live-current-20261107"
URL = "https://statsdmz.nba.com/pdfs/20261028/20261028_LALLAC.pdf"


def test_capture_one_original_luka_reported_rest_dependency():
    archive = (EVIDENCE / "current-originals.zip").read_bytes()
    assert (
        hashlib.sha256(archive).hexdigest()
        == "411435a52ba299441e06cc0af50bfd4e31da7e853d0dc2cd03fe197e13a695dd"
    )
    with ZipFile(EVIDENCE / "current-originals.zip") as z:
        schedule = json.loads(z.read("schedule-current.json"))["leagueSchedule"]
        (game,) = [
            g for day in schedule["gameDates"] for g in day["games"] if g["gameId"] == "0022600143"
        ]
        assert schedule["seasonYear"] == "2026-27" and game["gameStatus"] == 3
        assert game["gameDateEst"][:10] == "2026-10-28"
        assert game["gameCode"] == "20261028/LALLAC"
        assert [
            (game[s + "Team"]["teamId"], game[s + "Team"]["score"]) for s in ("away", "home")
        ] == [(1610612747, 103), (1610612746, 87)]
        summary = json.loads(z.read("retained-pairs/sources/boxscoresummaryv3_0022600143.json"))[
            "boxScoreSummary"
        ]
        assert summary["gameId"] == game["gameId"] and summary["gameStatus"] == 3
        assert any(p["personId"] == 1629029 for p in summary["awayTeam"]["inactives"])
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "current-luka-reason-report"
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(
        candidate_sha=os.environ["VALIDATION_SHA"],
        base_generation=os.environ["NBATOOLS_DATA_GENERATION"],
        source_url=URL,
        game_id="0022600143",
        started_at=datetime.now(UTC).isoformat(),
        limits=dict(readers=1, retries=0, redirects=0, seconds=20, bytes=LIMIT),
        reader_invocations=0,
        capture_complete=False,
        rest_qualified=False,
        production_writes=0,
        failure=None,
    )

    def retain(raw):
        receipt["bytes_read"] = len(raw)
        receipt["sha256_of_bytes_read"] = hashlib.sha256(raw).hexdigest()
        if len(raw) <= LIMIT:
            name = "original.pdf" if raw.startswith(b"%PDF") else "original.body"
            (output / name).write_bytes(raw)
            receipt["raw_file"] = name

    try:
        request = urllib.request.Request(
            URL, headers={"User-Agent": "Mozilla/5.0 (NBATools official box-score ingest)"}
        )
        receipt["reader_invocations"] = 1
        try:
            with urllib.request.build_opener(_NoRedirect()).open(request, timeout=20) as response:
                raw = response.read(LIMIT + 1)
                retain(raw)
                receipt["http"] = response.status
                assert response.geturl() == URL and response.status == 200
                assert len(raw) <= LIMIT and raw.startswith(b"%PDF")
                assert "application/pdf" in response.headers.get("Content-Type", "").lower()
        except urllib.error.HTTPError as exc:
            receipt["http"] = exc.code
            try:
                retain(exc.read(LIMIT + 1))
            finally:
                exc.close()
            raise
        receipt["capture_complete"] = True
        # Capture is not reason/identity qualification. Independent original-body
        # review determines whether this report actually states a Rest reason.
    except Exception as exc:
        receipt["failure"] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        receipt["finished_at"] = datetime.now(UTC).isoformat()
        (output / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
