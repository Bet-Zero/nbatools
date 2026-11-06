"""Bounded DQ-005 originals only; transport is not statistical qualification."""

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
URLS = {
    "0022200138.pdf": "https://statsdmz.nba.com/pdfs/20221105/20221105_SASDEN.pdf",
    "0022200749.pdf": "https://statsdmz.nba.com/pdfs/20230128/20230128_LALBOS.pdf",
}


def test_capture_two_official_final_boxes():
    root = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", "acquired_data")) / "dq005"
    root.mkdir(parents=True, exist_ok=False)
    captures = []
    for name, url in URLS.items():
        record = dict(url=url, file=name, attempted_at=datetime.now(UTC).isoformat())
        captures.append(record)
        try:
            # Existing approved public scorer-report route. One attempt, no
            # redirects, credential use, retry, data activation or publication.
            with requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (NBATools official box-score ingest)"},
                timeout=20,
                stream=True,
                allow_redirects=False,
            ) as response:
                record["http_status"] = response.status_code
                record["content_type"] = response.headers.get("Content-Type")
                response.raise_for_status()
                assert response.status_code == 200
                raw = bytearray()
                for chunk in response.iter_content(65536):
                    assert len(raw) + len(chunk) <= 1_500_000
                    raw.extend(chunk)
            body = bytes(raw)
            (root / name).write_bytes(body)
            record.update(
                sha256=hashlib.sha256(body).hexdigest(),
                bytes=len(body),
                captured_at=datetime.now(UTC).isoformat(),
            )
            assert body.startswith(b"%PDF"), "Non-PDF original retained but unqualified"
            record["capture_complete"] = True
        except Exception as exc:
            record.update(capture_complete=False, error=f"{type(exc).__name__}: {exc}")
        finally:
            (root / "receipt.json").write_text(json.dumps(captures, indent=2) + "\n")
    assert len(captures) == 2 and all(r["capture_complete"] for r in captures), captures
