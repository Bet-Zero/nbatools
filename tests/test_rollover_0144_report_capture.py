"""Offline contracts only; synthetic bytes are never NBA source evidence."""

import io
import json
import urllib.error

import pytest
from pypdf import PdfWriter

from tests import cloud_rollover_0144_report_capture_real_data as capture


class Response(io.BytesIO):
    status = 200
    headers = {"Content-Type": "application/pdf"}

    def geturl(self):
        return capture.URL


def envelope(*, date="Thursday, October 29, 2026", away="Cleveland Cavaliers", score=111):
    return f"{date}\nVISITOR: {away} (0-0)\n240:00 0 {score}\nHOME: Atlanta Hawks (0-0)\n240:00 0 114\nSCORE BY PERIOD\n"


def run_synthetic(tmp_path, monkeypatch, *, text=None, raw=b"%PDF synthetic", failure=None):
    calls = []

    def reader():
        calls.append(capture.URL)
        if failure:
            raise failure
        return Response(raw)

    monkeypatch.setattr(capture, "_open_report", reader)
    if text is not None:
        monkeypatch.setattr(capture.report, "_report_text", lambda content: text)
    output = tmp_path / "capture"
    case = capture._prepare()["game"]
    return calls, output, lambda: capture._capture(case, output)


def test_retained_identity_preflight_and_single_capture_does_not_qualify_positions(
    tmp_path, monkeypatch
):
    calls, output, invoke = run_synthetic(tmp_path, monkeypatch, text=envelope())
    result = invoke()
    assert calls == [capture.URL] and result["source_reader_invocations"] == 1
    assert result["envelope_verified"] and result["capture_complete"]
    assert not result["starter_positions_qualified"] and not result["full_slice_accepted"]
    assert result["production_writes"] == 0
    stored = result["returned_body"]
    assert (output / stored["raw_file"]).read_bytes() == b"%PDF synthetic"
    assert json.loads((output / "20261029_CLEATL.json").read_bytes())["source_url"] == capture.URL


@pytest.mark.parametrize(
    "text",
    [
        envelope(date="Friday, October 30, 2026"),
        envelope(away="Atlanta Hawks"),
        envelope(score=112),
    ],
)
def test_wrong_envelope_retains_original_and_failure_once(tmp_path, monkeypatch, text):
    calls, output, invoke = run_synthetic(tmp_path, monkeypatch, text=text)
    with pytest.raises((ValueError, AssertionError)):
        invoke()
    result = json.loads((output / "capture.json").read_bytes())
    assert calls == [capture.URL] and result["failure"]
    assert result["returned_body"]["retained"]
    assert not result["capture_complete"] and not result["starter_positions_qualified"]


def test_strict_original_pdf_header_guard_runs_after_retention(tmp_path, monkeypatch):
    pdf = PdfWriter()
    pdf.add_blank_page(width=100, height=100)
    body = io.BytesIO()
    pdf.write(body)
    calls, output, invoke = run_synthetic(tmp_path, monkeypatch, raw=body.getvalue())
    with pytest.raises(ValueError, match="not an NBA Final Box"):
        invoke()
    result = json.loads((output / "capture.json").read_bytes())
    assert calls == [capture.URL] and result["returned_body"]["retained"]
    assert (output / result["returned_body"]["raw_file"]).read_bytes() == body.getvalue()


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("synthetic timeout"),
        urllib.error.HTTPError(
            capture.URL, 403, "synthetic forbidden", {}, io.BytesIO(b"synthetic denied")
        ),
    ],
)
def test_failed_reader_is_one_attempt_and_retains_diagnostic(tmp_path, monkeypatch, error):
    calls, output, invoke = run_synthetic(tmp_path, monkeypatch, failure=error)
    with pytest.raises(type(error)):
        invoke()
    result = json.loads((output / "capture.json").read_bytes())
    assert calls == [capture.URL] and result["source_reader_invocations"] == 1
    assert result["failure"]["error_type"] == type(error).__name__
    assert not result["capture_complete"]
    if isinstance(error, urllib.error.HTTPError):
        assert result["http_status"] == 403
        assert (output / result["returned_body"]["raw_file"]).read_bytes() == b"synthetic denied"


def test_oversize_does_not_archive_over_cap(tmp_path, monkeypatch):
    calls, output, invoke = run_synthetic(tmp_path, monkeypatch, raw=b"%PDF" + b"x" * capture.LIMIT)
    with pytest.raises(ValueError, match="Invalid NBA official"):
        invoke()
    result = json.loads((output / "capture.json").read_bytes())
    assert calls == [capture.URL]
    assert result["returned_body"]["bytes_read"] == capture.LIMIT + 1
    assert result["returned_body"]["read_limit_exceeded"]
    assert not result["returned_body"]["retained"] and list(output.glob("*.pdf")) == []


def test_reader_keeps_existing_header_timeout_and_disables_redirects(monkeypatch):
    calls = []

    class Opener:
        def open(self, request, timeout):
            calls.append((request.full_url, request.get_header("User-agent"), timeout))
            return "synthetic response"

    def build(handler):
        assert isinstance(handler, capture._NoRedirect)
        assert (
            handler.redirect_request(None, None, 302, "redirect", {}, "https://other.invalid")
            is None
        )
        return Opener()

    monkeypatch.setattr(capture.urllib.request, "build_opener", build)
    assert capture._open_report() == "synthetic response"
    assert calls == [(capture.URL, "Mozilla/5.0 (NBATools official box-score ingest)", 20)]
