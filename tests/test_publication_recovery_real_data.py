"""Focused live verification of the owner-published package; no data writes."""

import json
import os
from pathlib import Path

import pytest
import requests

from tools.r2_publication import verify_answer

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "retained-k08-availability-v1"
GENERATION = "availability-k08-retained-v1-20261031"


def test_diagnose_published_live_queries():
    """Retain each exact response; failure is diagnostic, never acceptance."""
    assert os.environ["NBATOOLS_DATA_GENERATION"] == GENERATION
    package = json.loads((ROOT / ".github/data-publication-packages.json").read_text())["packages"][
        PACKAGE
    ]
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "publication-recovery"
    output.mkdir(parents=True, exist_ok=True)
    report = {"package": PACKAGE, "generation": GENERATION, "production_writes": 0, "responses": []}
    try:
        for index, case in enumerate(package["deployed_checks"], 1):
            response = requests.post(
                "https://nbatools.vercel.app/query", json={"query": case["query"]}, timeout=30
            )
            record = dict(
                index=index,
                query=case["query"],
                status=response.status_code,
                headers={
                    key: response.headers[key]
                    for key in ["Content-Type", "Retry-After", "X-Request-Id", "X-Vercel-Id"]
                    if key in response.headers
                },
                body=response.text,
            )
            report["responses"].append(record)
            assert response.status_code == 200, record
            verify_answer(case, response.json())
        assert len(report["responses"]) == 13
    finally:
        (output / "live-diagnosis.json").write_text(json.dumps(report, indent=2) + "\n")
