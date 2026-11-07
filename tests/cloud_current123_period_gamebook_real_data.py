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
