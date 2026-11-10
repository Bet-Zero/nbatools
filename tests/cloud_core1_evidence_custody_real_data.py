"""Reuse the existing bounded artifact-to-log custody route; zero NBA requests."""

import base64
import hashlib
import io
import os
from pathlib import Path
from zipfile import ZipFile

import pytest
import requests

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _retain_exact(capfd, artifact_id, expected_size, expected_sha, label):
    url = f"https://api.github.com/repos/Bet-Zero/nbatools/actions/artifacts/{artifact_id}/zip"
    # requests removes Authorization on the cross-host artifact redirect.
    with requests.get(
        url,
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"]},
        timeout=30,
        stream=True,
    ) as response:
        response.raise_for_status()
        data = bytearray()
        for chunk in response.iter_content(8192):
            data.extend(chunk)
            assert len(data) <= expected_size
    raw = bytes(data)
    assert len(raw) == expected_size and hashlib.sha256(raw).hexdigest() == expected_sha
    with ZipFile(io.BytesIO(raw)) as archive:
        assert len(archive.infolist()) <= 10000
        assert sum(e.file_size for e in archive.infolist()) <= 100_000_000
        assert all(
            not Path(n).is_absolute() and ".." not in Path(n).parts for n in archive.namelist()
        )
        assert archive.testzip() is None
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / f"core1-existing-{label}-custody"
    output.mkdir(parents=True, exist_ok=False)
    (output / f"original-{label}-artifact.zip").write_bytes(raw)
    encoded = base64.b64encode(raw).decode("ascii")
    with capfd.disabled():
        for index, offset in enumerate(range(0, len(encoded), 16000)):
            print(
                f"CORE1_{label.upper()}_CHUNK_{index:03d}=" + encoded[offset : offset + 16000],
                flush=True,
            )
        print(f"CORE1_{label.upper()}_SHA256=" + expected_sha, flush=True)


def test_retain_exact_existing_raw_qa_artifact(capfd):
    _retain_exact(
        capfd,
        13749497897,
        1361179,
        "ccde9588c64de9953b8d24082fe81c0dc791f484162cc92105c1b7cf095197ff",
        "rawqa",
    )


def test_retain_exact_existing_filter_artifact(capfd):
    _retain_exact(
        capfd,
        13750270371,
        23326,
        "136479cac3f092cd81c314de7a46bd4da0c3a1255805c4025b2125bb49c97abd",
        "filter",
    )


def test_retain_exact_existing_nine_artifact(capfd):
    _retain_exact(
        capfd,
        13751751098,
        20489,
        "2837c571c1655468d23c8c8152584e58bd12c7b31a6981c697d312fa15f177b9",
        "nine",
    )
