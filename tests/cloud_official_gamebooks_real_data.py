"""Explicit historical investigation: retain five new originals, never promote data.

This standalone capture has no application imports and is not a routine ingester.
The unchanged read-only Actions runner supplies transport and artifact custody.
"""

import hashlib
import io
import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

import pytest
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
REQUEST = (
    ROOT
    / "working/nba-tools-completion-program/collection-requests/official-gamebooks-20261105.json"
)
REQUEST_SHA = "edfa62ec7efeb239539eecfeb2cc765e0ecbb63272349699919112a7d409341d"
LIMIT = 1_500_000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def prepare():
    raw = REQUEST.read_bytes()
    assert sha(raw) == REQUEST_SHA
    request = json.loads(raw)
    assert request["limits"] == dict(
        sources=5,
        attempts_per_source=1,
        timeout_seconds=20,
        max_body_bytes=LIMIT,
        max_pages=64,
        redirects=0,
        retries=0,
        metered_overage_usd=0,
    )
    assert len(request["sources"]) == len({s["url"] for s in request["sources"]}) == 5
    for case in request["sources"]:
        binding = case["identity_source"]
        archive = (ROOT / binding["bundle_path"]).read_bytes()
        assert sha(archive) == binding["bundle_sha256"]
        with ZipFile(io.BytesIO(archive)) as z:
            summary = z.read(binding["member"])
        assert sha(summary) == binding["sha256"]
        box = json.loads(summary)["boxScoreSummary"]
        assert box["gameId"] == case["game_id"] and box["gameCode"] == case["game_code"]
        assert box["gameEt"][:10] == case["date"] and box["gameStatus"] == 3
        for side in ("away", "home"):
            team = box[side + "Team"]
            assert case["teams"][side] == dict(
                id=team["teamId"],
                city=team["teamCity"],
                name=team["teamName"],
                points=team["score"],
            )
        day, teams = case["game_code"].split("/")
        assert case["url"] == f"https://statsdmz.nba.com/pdfs/{day}/{day}_{teams}_book.pdf"
    return request


def capture(case, output, opener=None):
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(
        source_url=case["url"],
        game_id=case["game_id"],
        request_sha256=REQUEST_SHA,
        started_at=datetime.now(UTC).isoformat(),
        attempts=1,
        redirects_followed=0,
        original_retained=False,
        pdf_parsed=False,
        authoritative_correction_qualified=False,
        source_generation_independence="unestablished",
        canonical_writes=0,
        production_writes=0,
    )

    def retain(response):
        receipt["http_status"] = response.status
        receipt["response_url"] = response.geturl()
        receipt["response_headers"] = {
            name: response.headers.get(name)
            for name in (
                "Content-Type",
                "Content-Length",
                "Date",
                "ETag",
                "Last-Modified",
                "Location",
            )
            if response.headers.get(name) is not None
        }
        raw = response.read(LIMIT + 1)
        receipt.update(bytes_read=len(raw), sha256_of_bytes_read=sha(raw))
        if len(raw) > LIMIT:
            raise ValueError("Body exceeds capture bound; prefix hash is not an original checksum")
        name = sha(raw) + (".pdf" if raw.startswith(b"%PDF") else ".body")
        declared = receipt["response_headers"].get("Content-Length")
        if declared is not None and (not declared.isdigit() or int(declared) != len(raw)):
            partial = sha(raw) + ".partial"
            (output / partial).write_bytes(raw)
            receipt.update(received_file=partial, incomplete_or_invalid_content_length=True)
            raise ValueError("Declared Content-Length differs; received bytes are not an original")
        (output / name).write_bytes(raw)
        receipt.update(original_retained=True, raw_file=name, sha256=sha(raw), size_bytes=len(raw))
        return raw

    try:
        opener = opener or urllib.request.build_opener(NoRedirect())
        req = urllib.request.Request(
            case["url"],
            headers={
                "User-Agent": "Mozilla/5.0 (NBATools official box-score ingest)",
            },
        )
        try:
            with opener.open(req, timeout=20) as response:
                raw = retain(response)
        except urllib.error.HTTPError as exc:
            try:
                retain(exc)
            finally:
                exc.close()
            raise
        assert receipt["response_url"] == case["url"] and receipt["http_status"] == 200
        assert "application/pdf" in receipt["response_headers"].get("Content-Type", "").lower()
        assert raw.startswith(b"%PDF")
        reader = PdfReader(io.BytesIO(raw), strict=True)
        assert 1 <= len(reader.pages) <= 64
        for index, page in enumerate(reader.pages):
            (output / f"page-{index:02d}.txt").write_text(
                page.extract_text(extraction_mode="layout")
            )
        receipt.update(pdf_parsed=True, page_count=len(reader.pages))
    except Exception as exc:
        receipt["failure"] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        receipt["finished_at"] = datetime.now(UTC).isoformat()
        (output / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


@pytest.mark.needs_data
@pytest.mark.engine
def test_capture_five_new_official_gamebooks_without_canonical_promotion():
    request = prepare()  # All retained identity bindings precede every source request.
    assert os.environ["NBATOOLS_DATA_GENERATION"] == request["base_generation"]
    root = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "official-gamebooks-20261105"
    root.mkdir(parents=True, exist_ok=False)
    failures = []
    for case in request["sources"]:
        try:
            capture(case, root / case["game_id"])
        except Exception as exc:
            failures.append(dict(game_id=case["game_id"], error_type=type(exc).__name__))
    (root / "batch.json").write_text(
        json.dumps(
            dict(
                request_sha256=REQUEST_SHA,
                sources=5,
                attempts=5,
                failures=failures,
                source_qualification=False,
                canonical_writes=0,
                production_writes=0,
            ),
            indent=2,
        )
        + "\n"
    )
    assert not failures, failures
