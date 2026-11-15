"""Finite public-source diagnostic, not membership or publication acceptance.

Existing read-only R2 runner is the acquisition route. No source retries,
redirects, inferred membership, credentials to source hosts, or auto-expansion.
"""

import hashlib
import html
import io
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests
from pypdf import PdfReader
from pypdf.errors import PdfReadError

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
SOURCES = (
    (
        "opening-2023.pdf",
        "https://bloximages.chicago2.vip.townnews.com/tucson.com/content/tncms/assets/v3/editorial/b/52/b52fd976-71ff-11ee-8fbf-d7479459d4aa/653708216e38d.pdf.pdf",
        2_000_000,
    ),
    ("opening-2009.html", "https://pr.nba.com/opening-day-rosters-set/", 1_000_000),
    (
        "rockets-2016-guide.pdf",
        "https://ak-static-int.nba.com/wp-content/uploads/sites/3/2016/10/2016-17-Media-Guide-Rockets.pdf",
        12_000_000,
    ),
    (
        "gleague-2023.html",
        "https://gleague.nba.com/2023-24-nba-g-league-transactions",
        2_000_000,
    ),
    (
        "player-movement.json",
        "https://stats.nba.com/js/data/playermovement/NBA_Player_Movement.json",
        4_000_000,
    ),
)


def test_capture_fixed_bulk_membership_source_sample(capfd):
    def emit(label, document):
        with capfd.disabled():
            print(label + " " + json.dumps(document), flush=True)

    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "membership-source-sample"
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(
        classification="bounded_source_diagnostic_not_membership_acceptance",
        candidate_sha=os.environ["VALIDATION_SHA"],
        source_count=5,
        max_total_body_bytes=21_000_000,
        attempts_per_source=1,
        redirects=0,
        timeout_seconds=20,
        production_writes=0,
        membership_accepted=False,
        captures=[],
    )
    for name, url, limit in SOURCES:
        raw = bytearray()
        item = dict(
            file=name,
            url=url,
            started_at=datetime.now(UTC).isoformat(),
            complete=False,
            limit_bytes=limit,
        )
        try:
            with requests.get(url, stream=True, timeout=20, allow_redirects=False) as response:
                item["http_status"] = response.status_code
                for chunk in response.iter_content(65536):
                    remaining = limit - len(raw)
                    raw.extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        raise ValueError("body_limit_exceeded")
                item["complete"] = response.status_code == 200
        except (requests.RequestException, ValueError) as error:
            item["error_type"] = type(error).__name__
        if raw:
            (output / name).write_bytes(raw)
        item.update(
            size_bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            retrieved_at=datetime.now(UTC).isoformat(),
            original_nba_capture_time=None,
        )
        receipt["captures"].append(item)
        (output / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
        # Selected native text is a diagnostic derivative, bound to the body hash.
        # Originals remain in the artifact; the runner can replay them offline.
        if item["complete"] and name.endswith(".pdf") and raw.startswith(b"%PDF-"):
            try:
                pdf = PdfReader(io.BytesIO(raw))
                pages = (
                    range(min(3, len(pdf.pages))) if name.startswith("opening") else range(156, 162)
                )
                native = dict(
                    file=name,
                    original_sha256=item["sha256"],
                    pages={
                        str(i): pdf.pages[i].extract_text() for i in pages if i < len(pdf.pages)
                    },
                )
                (output / (name + ".pages.json")).write_text(json.dumps(native) + "\n")
                emit("MEMBERSHIP_NATIVE_TEXT", native)
            except (ValueError, IndexError, PdfReadError) as error:
                item["pdf_diagnostic_error"] = type(error).__name__
        if item["complete"] and name.endswith(".html"):
            text = raw.decode("utf-8", errors="replace")
            text = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", text, flags=re.S | re.I)
            text = html.unescape(re.sub(r"<[^>]+>", "\n", text))
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            native = dict(file=name, original_sha256=item["sha256"], text="\n".join(lines)[:180000])
            (output / (name + ".text.json")).write_text(json.dumps(native) + "\n")
            emit("MEMBERSHIP_NATIVE_TEXT", native)
        if item["complete"] and name.endswith(".json"):
            try:
                document = json.loads(raw)
                emit(
                    "MEMBERSHIP_JSON_SCHEMA",
                    dict(file=name, keys=list(document), preview=str(document)[:2000]),
                )
            except (ValueError, TypeError):
                item["json_diagnostic_error"] = True
    (output / "capture.json").write_text(json.dumps(receipt, indent=2) + "\n")
    emit("MEMBERSHIP_CAPTURE_DIAGNOSTIC", receipt)
    assert len(receipt["captures"]) == 5
    assert sum(item["size_bytes"] for item in receipt["captures"]) <= 21_000_000
