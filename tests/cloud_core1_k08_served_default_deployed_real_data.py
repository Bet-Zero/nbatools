"""Actual new-runtime D for nine original K08 cases; no data/protection writes."""

import json
import os
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests

from tests.core1_k08_runtime_binding import deployed_runtime_binding
from tests.core1_k08_served_default_cases import (
    BASE,
    ROOT,
    SEASON,
    assert_answer,
    assert_ownership_answer,
    sha,
    source_oracle,
)

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _table(item, label):
    matches = [t for t in item["tables"] if t["label"] == label]
    assert len(matches) == 1
    table = matches[0]
    return [dict(zip(table["headers"], row, strict=True)) for row in table["rows"]]


def _rendered(item, case):
    assert item["query"] == case["query"] and item["http"] == 200
    assert_answer(item["payload"], case)
    text, expected = item["text"], case["expected"]
    assert SEASON in text and "Data Not Available" not in text
    assert not any(t in text for t in ("NaN", "undefined", "Infinity"))
    assert "provisional" not in text.lower()
    if not expected["games"]:
        assert "No Matching Results" in text and "120" in text
        assert "Lakers" in text and ("Celtics" in text or "BOS" in text)
        assert "Tatum" in text and not item["tables"]
        return
    assert "No Matching Results" not in text
    if case["kind"] in {"missed", "home_missed"}:
        assert "LeBron James" in text and "missed" in text.lower()
        assert str(expected["games"]) in item["heroText"]
        if case["kind"] == "home_missed":
            assert "home" in item["heroText"].lower()
    elif case["kind"] == "record":
        (shown,) = _table(item, "Team record")
        assert shown["Team"].endswith("Los Angeles Lakers")
        assert shown["W-L"] == f"{expected['wins']}-{expected['losses']}"
        assert int(shown["Games"]) == expected["games"]
        assert float(shown["PPG"]) == pytest.approx(expected["means"]["pts"], abs=0.051)
    elif case["kind"] == "player":
        assert "LeBron James" in item["heroText"]
        for stat, noun in (("pts", "points"), ("reb", "rebounds"), ("ast", "assists")):
            shown = re.search(rf"\b(\d+(?:\.\d+)?) {noun}\b", item["heroText"])
            assert shown, (stat, item["heroText"])
            assert float(shown.group(1)) == pytest.approx(expected["means"][stat], abs=0.051)
    else:
        assert case["kind"] == "summary"
        rows = _table(item, "Game log")
        assert len(rows) == expected["games"]
        assert sum(float(row["PTS"]) for row in rows) == expected["sums"]["pts"]
        assert f"{expected['means']['pts']:.1f}" in text
    if case["kind"] not in {"missed", "home_missed"}:
        assert "Tatum" in text and ("Celtics" in text or "BOS" in text)


def test_actual_new_runtime_original_nine_desktop_and_mobile():
    oracle = source_oracle()
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "core1-k08-served-default-live"
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(
        candidate_sha=os.environ["VALIDATION_SHA"],
        started_at=datetime.now(UTC).isoformat(),
        generation=BASE,
        manifest_sha256=oracle["manifest_sha256"],
        original_ids=[c["ordinal"] for c in oracle["cases"]],
        source_requests=0,
        production_writes=0,
        protection_changes=0,
        all46_accepted=False,
        full_core1_accepted=False,
        current_readiness_accepted=False,
        cold_performance_accepted=False,
        consumer_acceptance="pending",
    )
    (output / "independent-raw-oracle.json").write_text(json.dumps(oracle, indent=2) + "\n")
    try:
        before = deployed_runtime_binding()
        receipt["runtime_before"] = before
        cases = [
            dict(
                id=c["id"],
                query=c["query"],
                text=[],
                forbidden=["NaN", "undefined", "Infinity", "Data Not Available"],
            )
            for c in oracle["cases"]
        ]
        inputs = output / "cases.json"
        inputs.write_text(json.dumps(cases) + "\n")
        allowed = {
            "PATH",
            "HOME",
            "TMPDIR",
            "CI",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "NO_PROXY",
            "NODE_EXTRA_CA_CERTS",
            "SSL_CERT_FILE",
        }
        clean = {k: v for k, v in os.environ.items() if k in allowed}
        subprocess.run(
            ["npm", "ci", "--ignore-scripts", "--no-audit"],
            cwd=ROOT / "frontend",
            env=clean,
            check=True,
            timeout=180,
        )
        subprocess.run(
            [
                "node",
                str(ROOT / "frontend/tools/captureCoreIdentityFindCount.mjs"),
                str(inputs),
                str(output),
                before["base_url"],
            ],
            cwd=ROOT,
            env=clean,
            check=True,
            timeout=900,
        )
        browser = json.loads((output / "browser-receipt.json").read_bytes())
        assert browser["base"] == before["base_url"] and not browser["failures"]
        assert len(browser["receipts"]) == 18
        case_by_id = {c["id"]: c for c in oracle["cases"]}
        seen, asset_hashes = set(), set()
        for item in browser["receipts"]:
            assert (item["viewport"], item["id"]) not in seen
            seen.add((item["viewport"], item["id"]))
            assert not item["errors"] and not item["missing"] and not item["forbidden"]
            assert item["overflow"]["document"] <= item["overflow"]["viewport"]
            assert sha((output / item["screenshot"]).read_bytes()) == item["screenshotSha256"]
            for when in ("Before", "After"):
                ready = item["readiness" + when]
                assert item["readinessHttp" + when] == 503
                assert ready["active_generation"] == BASE and ready["immutable_generation"] is True
                assert ready["ready"] is False
                assert [b["code"] for b in ready["blockers"]] == ["new_season_not_loaded"]
                assert not ready["exception"]["applied"]
            assert (
                item["freshness"]["status"] == "stale"
                and item["freshness"]["current_through"] == "2026-06-13"
            )
            assert "Data through 2026-06-13" in item["freshnessText"]
            asset_hashes.add(item["servedAssetSha256"])
            _rendered(item, case_by_id[item["id"]])
        assert seen == {(view, c["id"]) for view in ("desktop", "mobile") for c in oracle["cases"]}
        assert (
            len(asset_hashes) == 1
            and sha((output / "served-application.js").read_bytes()) in asset_hashes
        )
        # A separate public positive exercises the changed name-ownership path;
        # it is not a tenth original K08 ID or a cold-performance observation.
        time.sleep(7)
        control = oracle["supplemental_ownership"]
        response = requests.post(
            before["base_url"] + "/query",
            json={"query": control["query"]},
            timeout=60,
            allow_redirects=False,
        )
        assert response.status_code == 200
        assert_ownership_answer(response.json(), control)
        receipt["supplemental_ownership"] = dict(
            original46_case=False,
            http=response.status_code,
            query=control["query"],
            actual=response.json(),
            rendered_acceptance="separate local six-capture ownership proof; public supplement is HTTP only",
        )
        after = deployed_runtime_binding()
        receipt["runtime_after"] = after
        assert after["deployment"]["id"] == before["deployment"]["id"]
        assert (
            after["deployed_sha"] == before["deployed_sha"]
            and after["build_input_tree_sha256"] == before["build_input_tree_sha256"]
        )
        receipt.update(
            consumer_acceptance="passed",
            actual_original_cases=9,
            actual_captures=18,
            fresh_deployment_accepted=True,
            served_asset_sha256=next(iter(asset_hashes)),
        )
    except Exception as exc:
        receipt.update(
            consumer_acceptance="failed",
            error_type=type(exc).__name__,
            error=str(exc),
            fresh_deployment_accepted=False,
        )
        raise
    finally:
        receipt["completed_at"] = datetime.now(UTC).isoformat()
        (output / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
