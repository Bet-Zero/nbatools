"""One bounded API check on the retained published snapshot; no acquisition.

Expected samples reuse the independent original-nine source oracle. The exact
Boston Final Box establishes Tatum's BOS DNP and opposite-side LAL nonmembership,
never a season interval. Davis's unqualified dates remain unknown.
"""

import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.data_source import data_generation_context
from tests.core1_k08_served_default_cases import assert_answer

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"


def test_published_membership_distinctions_and_original_blockers():
    with data_generation_context() as generation:
        assert generation == "availability-season-inactive-2024-v1-20261116"
    spec = json.loads((PROGRAM / "core1-acceptance-map.json").read_bytes())
    frozen = spec["independent_oracle"]
    archive = ROOT / frozen["path"]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == frozen["sha256"]
    with ZipFile(archive) as z:
        oracle = json.loads(z.read(frozen["member"]))
    cases = {case["ordinal"]: case for case in oracle["cases"]}
    client = TestClient(app)
    receipts = []

    def ask(ident, path, request):
        response = client.post(path, json=request)
        assert response.status_code == 200
        body = response.json()
        receipts.append(dict(id=ident, path=path, request=request, body=body))
        assert body["result"]["metadata"]["season"] == "2025-26"
        return body

    for ident, player, team, states in [
        ("member-dnp", 1628369, 1610612738, ("member", "did_not_play")),
        ("nonmember", 1628369, 1610612747, ("not_member", "not_member")),
        ("unknown", 203076, 1610612747, ("unknown", "unknown")),
    ]:
        body = ask(
            ident,
            "/structured-query",
            dict(
                route="player_membership",
                kwargs=dict(
                    player_id=player,
                    team_id=team,
                    game_id=22500338,
                    date="2025-12-05",
                    season="2025-26",
                ),
            ),
        )
        assert body["result_status"] == "ok"
        row = body["result"]["sections"]["summary"][0]
        assert (row["membership_state"], row["participation_state"]) == states
        assert row["requested_team_id"] == team and row["player_id"] == player
        assert row["game_id"] == 22500338 and row["date"] == "2025-12-05"

    for ordinal in (7, 24):
        case = cases[ordinal]
        body = ask(str(ordinal), "/query", {"query": case["query"]})
        assert_answer(body, case)

    for ident, query in [
        ("davis", "Lakers record without Davis"),
        ("davis-pair", "Lakers record with Davis and Reaves both out"),
        ("davis-with", "LeBron James 30 point games with Davis"),
        ("tatum-union", "Lakers record vs Celtics and Knicks without Tatum"),
    ]:
        body = ask(ident, "/query", {"query": query})
        assert body["query"] == query
        assert body["result_status"] == "no_result"
        assert body["result_reason"] in {"unsupported", "filter_not_supported"}
        assert not body["result"]["sections"]
        notes = " ".join(body["notes"])
        if ident.startswith("davis"):
            assert "Missing records establish neither a missed game nor nonmembership" in notes
        else:
            assert "Incomplete game-day participation coverage for Jayson Tatum" in notes

    # Owner-approved clarification changes meaning descriptions, not real-NBA
    # qualification or the denominator. ID39's WITH variant and current40 remain.
    assert {
        kind: sum(e["expect"] == kind for e in spec["k08"])
        for kind in ("pass", "missing_data", "live")
    } == {"pass": 16, "missing_data": 26, "live": 4}
    output = os.environ.get("NBATOOLS_ACQUISITION_OUTPUT")
    if output:
        path = Path(output) / "core1-limited-participation"
        path.mkdir(parents=True, exist_ok=True)
        (path / "api-checks.json").write_text(json.dumps(receipts, indent=2))
