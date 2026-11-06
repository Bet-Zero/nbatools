"""One bounded original-source capture through the established read-only runner."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
URLS = {
    "tenure.html": "https://www.nba.com/raptors/news/raptors-extend-poeltl",
    "trade.html": "https://www.nba.com/raptors/news/raptors-acquire-poeltl-from-san-antonio",
    "return.html": "https://www.nba.com/raptors/news/raptors-re-sign-poeltl",
}


def test_capture_bounded_official_membership_originals():
    root = Path("acquired_data/poeltl-membership-originals")
    root.mkdir(parents=True, exist_ok=False)
    captures = []
    for name, url in URLS.items():
        # Existing direct public source path, one attempt per body, no retries,
        # credentials, alternate hosts, publication or data activation.
        with requests.get(url, timeout=30, stream=True, allow_redirects=False) as response:
            response.raise_for_status()
            assert response.status_code == 200
            raw = bytearray()
            for chunk in response.iter_content(65536):
                raw.extend(chunk)
                assert len(raw) <= 4_000_000
        body = bytes(raw)
        (root / name).write_bytes(body)
        captures.append(
            dict(
                url=url,
                file=name,
                sha256=hashlib.sha256(body).hexdigest(),
                size_bytes=len(body),
                captured_at=datetime.now(UTC).isoformat(),
            )
        )
        (root / "receipt.json").write_text(json.dumps(captures, indent=2) + "\n")
        assert "poeltl" in body.decode("utf-8").lower()
    assert len(captures) == 3
