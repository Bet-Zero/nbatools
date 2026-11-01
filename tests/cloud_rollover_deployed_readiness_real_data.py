"""One public deployed readiness observation; never release acceptance or repair."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
BASE = "availability-lebron-season-v1-20261031"


def test_deployed_exact_coverage_preserves_missing_new_season_blocker():
    assert os.environ["NBATOOLS_DATA_GENERATION"] == BASE
    response = requests.get(
        "https://nbatools.vercel.app/readiness", timeout=30, allow_redirects=False
    )
    assert response.status_code == 503
    payload = response.json()
    assert payload["ready"] is False and payload["immutable_generation"] is True
    assert payload["active_generation"] == BASE
    assert payload["max_active_lag_hours"] == 24
    assert [item["code"] for item in payload["blockers"]] == ["new_season_not_loaded"]
    assert payload["exception"]["applied"] is False
    assert payload["slices"]
    assert all(
        item["trusted"] is True and item["missing_due_game_ids"] == [] for item in payload["slices"]
    )
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "deployed-readiness"
    output.mkdir(parents=True, exist_ok=True)
    (output / "receipt.json").write_text(
        json.dumps(
            dict(
                classification="single_public_readiness_diagnostic_not_release_acceptance",
                observed_at=datetime.now(UTC).isoformat(),
                public_http_requests=1,
                nba_source_requests=0,
                production_writes=0,
                operational_acceptance_complete=False,
                status_code=response.status_code,
                readiness=payload,
            ),
            indent=2,
        )
        + "\n"
    )
