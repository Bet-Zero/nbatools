"""Temporary, bounded post-merge role-boundary smoke; existing read-only R2 route only."""

import hashlib
import json
import os
import re
from pathlib import Path

import pytest
import requests

from tests.cloud_core_historical_delivery_real_data import _readiness
from tests.core1_k08_runtime_binding import ROOT, _github, _local_build_tree, non_build

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
CURRENT = "availability-season-inactive-2024-v1-20261116"


def _binding():
    # Current Vercel bot links identify the same existing project under its
    # renamed zeros-projects slug. Accept only this exact immutable host family;
    # do not change the legacy capture helper, protection, aliases or access.
    (deployment,) = _github("deployments?environment=Production&per_page=1")
    assert deployment["creator"]["login"] == "vercel[bot]"
    (status,) = _github(f"deployments/{deployment['id']}/statuses?per_page=1")
    assert status["state"] == "success" and status["creator"]["login"] == "vercel[bot]"
    url = status["environment_url"].rstrip("/")
    assert re.fullmatch(r"https://nbatools-[a-z0-9]+-zeros-projects-686e97fc\.vercel\.app", url)
    tree = _github(f"git/trees/{deployment['sha']}?recursive=1")
    assert not tree["truncated"]
    remote = {
        e["path"]: dict(mode=e["mode"], sha=e["sha"])
        for e in tree["tree"]
        if e["type"] == "blob" and not non_build(e["path"])
    }
    assert remote == _local_build_tree(), "Production build inputs differ from the reviewed app"
    return dict(
        id=deployment["id"],
        sha=deployment["sha"],
        url=url,
        build_sha256=hashlib.sha256(json.dumps(remote, sort_keys=True).encode()).hexdigest(),
    )


def test_post_merge_scalar_role_boundary():
    assert os.environ["NBATOOLS_DATA_GENERATION"] == CURRENT
    before = _binding()
    response = requests.get(before["url"] + "/readiness", timeout=30, allow_redirects=False)
    _readiness(response.status_code, response.json(), CURRENT)
    receipts = []
    for clause, valid in [
        ("without Caris LeVert when opponent Stephen Curry plays", False),
        ("not when opponent Stephen Curry plays", False),
        ("when opponent Stephen Curry plays", True),
    ]:
        query = f"Cavaliers record {clause} vs Warriors in 2024-25"
        response = requests.post(before["url"] + "/query", json={"query": query}, timeout=30, allow_redirects=False)
        assert response.status_code == 200
        body = response.json()
        metadata = body["result"]["metadata"]
        assert body["query"] == query and metadata["team"] == "CLE"
        assert metadata["season"] == "2024-25" and metadata["season_type"] == "Regular Season"
        if valid:
            assert body["result_status"] == "ok" and metadata["participation_scope"] == "opponent"
            summary = body["result"]["sections"]["summary"][0]
            assert summary["team_name"] == "Cleveland Cavaliers"
            assert (summary["games"], summary["wins"], summary["losses"], summary["pts_avg"]) == (2, 2, 0, 124.5)
            assert {int(r["game_id"]) for r in body["result"]["sections"]["game_log"]} == {22400188, 22400446}
        else:
            assert body["result_status"] == "no_result" and body["result_reason"] in {"unsupported", "filter_not_supported"}
            assert "mixed_participation_roles" in metadata["unsupported_filters"]
            assert not body["result"]["sections"]
        receipts.append(dict(query=query, body=body))
    assert len(receipts) == 3 and _binding() == before
    response = requests.get(before["url"] + "/readiness", timeout=30, allow_redirects=False)
    _readiness(response.status_code, response.json(), CURRENT)
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]).resolve() / "team-role-boundary-hosted"
    output.mkdir(parents=True)
    (output / "receipt.json").write_text(json.dumps(dict(binding=before, checks=receipts), indent=2))
