"""Fixed thirteen gamebooks after qualified representative; capture is not reason acceptance."""

import io
import json
import os
from datetime import date
from pathlib import Path
from zipfile import ZipFile

import pytest

from nbatools.commands.pipeline import player_game_availability_report as report
from tests import cloud_luka_reported_reason_capture_real_data as first

pytestmark = pytest.mark.engine
REQUEST = first.PROGRAM / "collection-requests/luka-reported-reasons-remaining-2025-26.json"
REQUEST_SHA = "dc4f8dbbebeb3c73fc9229c98d42e78a8f44bd40db0e9f2459a292ce131568b1"
QUALIFICATION_SHA = "020b022dba9b4443480b334d0d8c1ae3b9868ab630267a26ed919f2e0b2abbd0"
ARTIFACT_SHA = "cd11f240eee112254af862af6e1bfb278a5ded351d2cd1e5b085561237b7d8e4"
PDF_SHA = "b7880804f7fa95830c85a6e5f468e5ba3a02cd3ac59b5061136dfeb78901ef55"
RECEIPT_SHA = "b47c8cff76e0eea33a1fd28e54ab803340da7acf11b9120a40462e76b2a78486"
REMAINING_IDS = first.GAME_IDS - {int(first.REPRESENTATIVE)}


def _prepare_remaining():
    assert first._sha(REQUEST.read_bytes()) == REQUEST_SHA
    request = json.loads(REQUEST.read_bytes())
    assert (request["base_generation"], request["base_manifest_sha256"]) == (
        first.BASE,
        first.MANIFEST,
    )
    assert request["parent_request"]["sha256"] == first.REQUEST_SHA
    assert request["reason_coverage_audit"]["sha256"] == first.AUDIT_SHA
    assert request["limits"] == dict(
        source_files=13,
        reader_invocations=13,
        attempts_per_file=1,
        timeout_seconds=20,
        pdf_max_bytes=first.PDF_LIMIT,
        aggregate_max_new_pdf_bytes=19_500_000,
        retained_representative_pdf_bytes=26_433,
        aggregate_max_with_representative_pdf_bytes=21_000_000,
        metered_overage_usd=0,
    )
    assert {int(r["game_id"]) for r in request["games"]} == REMAINING_IDS and len(
        request["games"]
    ) == 13
    assert set(request["never_refetch_game_ids"]) == {
        first.REPRESENTATIVE,
        "0022500113",
        "0022500122",
        "0022500338",
        "0022501098",
    }
    proof_path = first.PROGRAM.parent.parent / request["representative_qualification"]["path"]
    proof_raw = proof_path.read_bytes()
    assert (
        first._sha(proof_raw)
        == request["representative_qualification"]["sha256"]
        == QUALIFICATION_SHA
    )
    proof = json.loads(proof_raw)
    assert proof["continuation"]["same_existing_source_format_justified"]
    assert set(proof["continuation"]["remaining_fixed_games"]) == {
        r["game_id"] for r in request["games"]
    }
    assert (
        proof["source_fact"]["reported_reason_qualified"] and not proof["clinical_status_qualified"]
    )
    artifact_path = (
        first.PROGRAM.parent.parent / request["retained_representative"]["artifact_path"]
    )
    artifact = artifact_path.read_bytes()
    assert (
        first._sha(artifact)
        == request["retained_representative"]["artifact_sha256"]
        == ARTIFACT_SHA
    )
    assert len(artifact) == request["retained_representative"]["artifact_size_bytes"] == 26926
    with ZipFile(io.BytesIO(artifact)) as archive:
        pdf = archive.read(proof["raw_pdf"]["artifact_member"])
        receipt_raw = archive.read(proof["raw_pdf"]["source_receipt_member"])
    assert first._sha(pdf) == proof["raw_pdf"]["sha256"] == PDF_SHA and len(pdf) == 26433
    assert first._sha(receipt_raw) == proof["raw_pdf"]["source_receipt_sha256"] == RECEIPT_SHA
    receipt = json.loads(receipt_raw)
    assert receipt["sha256"] == PDF_SHA and receipt["size_bytes"] == len(pdf)
    assert receipt["source_url"] == proof["raw_pdf"]["source_url"]
    assert receipt["raw_file"] == PDF_SHA + ".pdf"
    # Reuse the existing complete fourteen-envelope preflight; it makes no NBA calls.
    prepared = first._prepare(all_cases=True)
    parent = json.loads(first.REQUEST.read_bytes())
    assert request["games"] == [r for r in parent["games"] if r["game_id"] != first.REPRESENTATIVE]
    cases = [prepared[r["game_id"]] for r in request["games"]]
    return cases, dict(pdf=pdf, receipt=receipt_raw)


def _capture_case(case, cache, monkeypatch):
    original_parser = report._report_text
    observed = {}

    def preserve_then_parse(content):
        observed.update(size_bytes=len(content), sha256=first._sha(content), retained=False)
        # Retain bounded returned PDFs before strict content/header parsing.
        # The unchanged parser still rejects invalid reports; oversize bodies
        # are diagnosed without writing past the approved per-file limit.
        if content.startswith(b"%PDF") and len(content) <= first.PDF_LIMIT:
            report._archive_report(content, case["source_url"], cache)
            observed["retained"] = True
        return original_parser(content)

    with monkeypatch.context() as scoped:
        scoped.setattr(report, "_report_text", preserve_then_parse)
        try:
            first._capture_one(
                case,
                cache,
                request_sha=REQUEST_SHA,
                classification="remaining_source_envelope_capture_not_reported_reason_acceptance",
            )
        finally:
            path = cache / "capture.json"
            if path.exists():
                receipt = json.loads(path.read_bytes())
                receipt["returned_body_diagnostic"] = observed or None
                receipt["representative_qualification_sha256"] = QUALIFICATION_SHA
                receipt["representative_pdf_sha256"] = PDF_SHA
                path.write_text(json.dumps(receipt, indent=2) + "\n")


def _capture_batch(cases, output, reused, monkeypatch):
    assert len(cases) == 13 and {int(r["game_id"]) for r in cases} == REMAINING_IDS
    output.mkdir(parents=True, exist_ok=False)
    cache = output / "reused-representative"
    cache.mkdir()
    (cache / (PDF_SHA + ".pdf")).write_bytes(reused["pdf"])
    (cache / "20251029_LALMIN.json").write_bytes(reused["receipt"])
    receipts, failures = [], []
    for case in cases:
        cache = output / case["game_id"]
        failure = None
        try:
            _capture_case(case, cache, monkeypatch)
        except Exception as exc:
            failure = dict(
                game_id=case["game_id"], error_type=type(exc).__name__, error_message=str(exc)
            )
            failures.append(failure)
        finally:
            path = cache / "capture.json"
            receipt = (
                json.loads(path.read_bytes())
                if path.exists()
                else dict(
                    game_id=case["game_id"],
                    source_reader_invocations=0,
                    capture_complete=False,
                    failure=failure,
                )
            )
            receipts.append(receipt)
            # Count all physically retained PDFs, including failed envelopes.
            new_bytes = sum(p.stat().st_size for p in output.glob("[0-9]*/**/*.pdf"))
            summary = dict(
                classification="thirteen_fixed_source_captures_not_reason_or_feature_acceptance",
                base_generation=first.BASE,
                base_manifest_sha256=first.MANIFEST,
                request_sha256=REQUEST_SHA,
                representative_qualification_sha256=QUALIFICATION_SHA,
                representative_artifact_sha256=ARTIFACT_SHA,
                representative_pdf_sha256=PDF_SHA,
                source_reader_invocations=sum(r["source_reader_invocations"] for r in receipts),
                new_pdf_bytes_retained=new_bytes,
                reused_pdf_bytes_retained=len(reused["pdf"]),
                combined_pdf_bytes_retained=new_bytes + len(reused["pdf"]),
                capture_receipts=receipts,
                failures=failures,
                reported_reason_qualified=False,
                clinical_status_qualified=False,
                full_slice_accepted=False,
                production_writes=0,
            )
            (output / "capture-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    assert (
        summary["new_pdf_bytes_retained"] <= 19_500_000
        and summary["combined_pdf_bytes_retained"] <= 21_000_000
    )
    assert summary["source_reader_invocations"] == 13
    assert not failures, failures
    return summary


@pytest.mark.needs_data
def test_capture_thirteen_remaining_luka_reason_gamebooks_only(monkeypatch):
    cases, reused = _prepare_remaining()
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "luka-reason-remaining"
    _capture_batch(cases, output, reused, monkeypatch)


def test_synthetic_batch_attempts_all_once_and_retains_bad_header_bytes(tmp_path, monkeypatch):
    cases = json.loads(REQUEST.read_bytes())["games"]
    cases = [dict(r, away_name=r["away_abbr"], home_name=r["home_abbr"]) for r in cases]
    calls = []

    def fetch(url, *, archive):
        calls.append(url)
        case = next(r for r in cases if r["source_url"] == url)
        raw = b"%PDF synthetic unit bytes; not NBA evidence"
        report._archive_report(raw, url, archive)
        date_text = date.fromisoformat(case["game_date"]).strftime("%A, %B %d, %Y")
        away = "WRONG TEAM" if case is cases[0] else case["away_name"]
        return f"{date_text}\nVISITOR: {away} (0-0)\n240:00 0 {case['away_points']}\nHOME: {case['home_name']} (0-0)\n240:00 0 {case['home_points']}\nSCORE BY PERIOD\n"

    monkeypatch.setattr(report, "_fetch_report_text", fetch)
    reused = dict(pdf=b"%PDF synthetic reused", receipt=b"{}")
    with pytest.raises(AssertionError):
        _capture_batch(cases, tmp_path / "batch", reused, monkeypatch)
    summary = json.loads((tmp_path / "batch/capture-summary.json").read_bytes())
    assert len(calls) == len(set(calls)) == summary["source_reader_invocations"] == 13
    assert len(summary["failures"]) == 1 and len(summary["capture_receipts"]) == 13
    assert summary["new_pdf_bytes_retained"] == 13 * len(
        b"%PDF synthetic unit bytes; not NBA evidence"
    )
    assert not summary["reported_reason_qualified"]


def test_synthetic_invalid_pdf_content_is_retained_before_original_guard(tmp_path, monkeypatch):
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    stream = io.BytesIO()
    writer.write(stream)
    raw = stream.getvalue()
    response = io.BytesIO(raw)
    response.headers = {"Content-Type": "application/pdf"}
    calls = []

    def open_response(*args, **kwargs):
        calls.append(1)
        return response

    monkeypatch.setattr(report.urllib.request, "urlopen", open_response)
    case = dict(json.loads(REQUEST.read_bytes())["games"][0], away_name="LAL", home_name="NOP")
    with pytest.raises(ValueError, match="not an NBA Final Box"):
        _capture_case(case, tmp_path / "case", monkeypatch)
    receipt = json.loads((tmp_path / "case/capture.json").read_bytes())
    assert calls == [1] and receipt["source_reader_invocations"] == 1
    assert receipt["retained_pdf_bytes"] == len(raw) and not receipt["capture_complete"]
    assert receipt["returned_body_diagnostic"]["retained"]
    assert receipt["returned_body_diagnostic"]["sha256"] == first._sha(raw)
