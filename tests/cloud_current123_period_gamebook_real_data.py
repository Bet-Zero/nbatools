"""One newly justified scorer source, using the existing bounded gamebook capture."""

import hashlib
import io
import json
import os
from pathlib import Path
from zipfile import ZipFile

import pytest

from tests import cloud_official_gamebooks_real_data as existing

ROOT = Path(__file__).resolve().parents[1]
REQUEST = (
    ROOT
    / "working/nba-tools-completion-program/collection-requests/current123-game184-rebound-book-20261107.json"
)
REQUEST_SHA = "8ae14a5debf33fcdfbc99414d9a6efcc5a04501786cf922b379bcdd7966c771e"


def prepare():
    raw = REQUEST.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == REQUEST_SHA
    request = json.loads(raw)
    assert request["limits"] == dict(
        sources=1,
        attempts_per_source=1,
        timeout_seconds=20,
        max_body_bytes=1500000,
        max_pages=64,
        redirects=0,
        retries=0,
        metered_overage_usd=0,
    )
    case = request["source"]
    identity = case["identity_source"]
    body = (ROOT / identity["bundle_path"]).read_bytes()
    assert hashlib.sha256(body).hexdigest() == identity["bundle_sha256"]
    with ZipFile(io.BytesIO(body)) as z:
        raw = z.read(identity["member"])
    assert hashlib.sha256(raw).hexdigest() == identity["sha256"]
    box = json.loads(raw)["boxScoreSummary"]
    assert box["gameId"] == case["game_id"] == "0022600184"
    assert box["gameStatus"] == 3 and box["gameCode"] == case["game_code"] == "20261104/DALSAS"
    assert box["gameEt"][:10] == case["date"] == "2026-11-04"
    for side in ("away", "home"):
        team = box[side + "Team"]
        assert case["teams"][side] == dict(
            id=team["teamId"], city=team["teamCity"], name=team["teamName"], points=team["score"]
        )
    assert case["url"] == "https://statsdmz.nba.com/pdfs/20261104/20261104_DALSAS_book.pdf"
    return request


@pytest.mark.needs_data
@pytest.mark.engine
def test_capture_only_new_game184_rebound_scorer_book(monkeypatch):
    request = prepare()
    assert os.environ["NBATOOLS_DATA_GENERATION"] == request["base_generation"]
    # Reuse the proven transport unchanged; bind its receipt to this one-body request.
    monkeypatch.setattr(existing, "REQUEST_SHA", REQUEST_SHA)
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "current123-game184-book"
    receipt = existing.capture(request["source"], output)
    assert receipt["original_retained"] and receipt["pdf_parsed"]
    assert (
        receipt["attempts"] == 1
        and receipt["canonical_writes"] == receipt["production_writes"] == 0
    )
    assert receipt["authoritative_correction_qualified"] is False


@pytest.mark.needs_data
@pytest.mark.engine
def test_transfer_retained_game184_book_without_source_retry(capfd):
    """Existing bounded artifact-to-log custody route; makes zero NBA requests."""
    import base64

    import requests

    expected = "1a788f1f13a9a929d68e654c9a2e937f4e478377a8f22cfb0932f2e3c7a6cccc"
    url = "https://api.github.com/repos/Bet-Zero/nbatools/actions/artifacts/13573082492/zip"
    with requests.get(
        url, headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"]}, timeout=30, stream=True
    ) as response:
        response.raise_for_status()
        data = bytearray()
        for chunk in response.iter_content(8192):
            data.extend(chunk)
            assert len(data) <= 300_000
    raw = bytes(data)
    assert len(raw) == 167836 and hashlib.sha256(raw).hexdigest() == expected
    with ZipFile(io.BytesIO(raw)) as z:
        assert len(z.namelist()) <= 100
        assert sum(e.file_size for e in z.infolist()) <= 3_000_000
        assert all(not Path(n).is_absolute() and ".." not in Path(n).parts for n in z.namelist())
        assert all(
            n in {"summary.json", "junit.xml"}
            or n.startswith(
                (
                    "acquired_data/current123-game184-book/",
                    "acquired_data/current123-period-integration/",
                )
            )
            for n in z.namelist()
        )
        assert z.testzip() is None
        summary = json.loads(z.read("summary.json"))
        assert (
            summary["selected"],
            summary["executed"],
            summary["passed"],
            summary["failed"],
            summary["skipped"],
        ) == (2, 2, 2, 0, 0)
        assert summary["candidate_sha"] == "2c82a949825bf64905e1622f7638d6d48dbbc48b"
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "retained-current123-game184-book"
    output.mkdir(parents=True, exist_ok=False)
    (output / "original-artifact.zip").write_bytes(raw)
    encoded = base64.b64encode(raw).decode()
    with capfd.disabled():
        for index, offset in enumerate(range(0, len(encoded), 16000)):
            print(
                f"CURRENT184_ARTIFACT_CHUNK_{index:03d}=" + encoded[offset : offset + 16000],
                flush=True,
            )
        print("CURRENT184_ARTIFACT_SHA256=" + expected, flush=True)
