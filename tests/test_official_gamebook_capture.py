"""Transport and retention regressions; synthetic PDFs are never NBA evidence."""

import io
import json
import urllib.error
from email.message import Message

import pytest
from pypdf import PdfWriter

from tests import cloud_official_gamebooks_real_data as capture

URL = "https://statsdmz.nba.com/pdfs/20261028/20261028_OKCDAL_book.pdf"
CASE = dict(url=URL, game_id="0022600142")


class Response(io.BytesIO):
    status = 200
    headers = {"Content-Type": "application/pdf", "Set-Cookie": "not-retained"}

    def geturl(self):
        return URL


class Opener:
    def __init__(self, body=None, error=None):
        self.body, self.error, self.calls = body, error, 0

    def open(self, req, timeout):
        self.calls += 1
        assert req.full_url == URL and timeout == 20
        if self.error:
            raise self.error
        return Response(self.body)


def test_retained_bindings_and_success_do_not_qualify_source(tmp_path):
    assert len(capture.prepare()["sources"]) == 5
    pdf = PdfWriter()
    pdf.add_blank_page(width=100, height=100)
    out = io.BytesIO()
    pdf.write(out)
    raw = out.getvalue()
    opener = Opener(body=raw)
    receipt = capture.capture(CASE, tmp_path / "capture", opener)
    assert opener.calls == 1 and receipt["pdf_parsed"]
    assert (tmp_path / "capture" / receipt["raw_file"]).read_bytes() == raw
    assert receipt["sha256"] == capture.sha(raw)
    assert not receipt["authoritative_correction_qualified"]
    assert receipt["source_generation_independence"] == "unestablished"
    assert "Set-Cookie" not in receipt["response_headers"]


def test_invalid_pdf_is_retained_before_parse_failure(tmp_path):
    raw = b"%PDF-invalid"
    opener = Opener(body=raw)
    with pytest.raises(Exception):
        capture.capture(CASE, tmp_path / "capture", opener)
    receipt = json.loads((tmp_path / "capture/capture.json").read_text())
    assert opener.calls == 1 and receipt["original_retained"]
    assert not receipt["pdf_parsed"]
    assert (tmp_path / "capture" / receipt["raw_file"]).read_bytes() == raw


def test_redirect_is_rejected_and_error_body_is_retained_once(tmp_path):
    assert capture.NoRedirect().redirect_request(None, None, 302, "", {}, URL) is None
    headers = Message()
    headers["Location"] = "https://example.com/other.pdf"
    error = urllib.error.HTTPError(URL, 302, "Found", headers, io.BytesIO(b"redirect"))
    opener = Opener(error=error)
    with pytest.raises(urllib.error.HTTPError):
        capture.capture(CASE, tmp_path / "capture", opener)
    receipt = json.loads((tmp_path / "capture/capture.json").read_text())
    assert opener.calls == 1 and receipt["http_status"] == 302
    assert receipt["redirects_followed"] == 0 and receipt["original_retained"]


def test_oversize_body_never_gets_an_original_checksum(tmp_path):
    opener = Opener(body=b"%PDF" + b"x" * capture.LIMIT)
    with pytest.raises(ValueError, match="capture bound"):
        capture.capture(CASE, tmp_path / "capture", opener)
    receipt = json.loads((tmp_path / "capture/capture.json").read_text())
    assert opener.calls == 1 and not receipt["original_retained"]
    assert "sha256" not in receipt and "raw_file" not in receipt


def test_short_body_is_preserved_without_original_custody(tmp_path):
    class ShortResponse(Response):
        headers = {"Content-Type": "application/pdf", "Content-Length": "999"}

    class ShortOpener:
        def open(self, req, timeout):
            return ShortResponse(b"%PDF-short")

    with pytest.raises(ValueError, match="Content-Length"):
        capture.capture(CASE, tmp_path / "capture", ShortOpener())
    receipt = json.loads((tmp_path / "capture/capture.json").read_text())
    assert not receipt["original_retained"] and not receipt["pdf_parsed"]
    assert "sha256" not in receipt and "raw_file" not in receipt
    assert (tmp_path / "capture" / receipt["received_file"]).read_bytes() == b"%PDF-short"
