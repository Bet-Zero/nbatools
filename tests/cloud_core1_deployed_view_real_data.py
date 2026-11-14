"""Deployed Core-1 view: every original K08 question through the live API and UI.

The reviewed production deployment is bound to the candidate's exact build
inputs before and after. Each acceptance-map question is asked once per
viewport (desktop and mobile) through the real interface on the immutable
host. The answers must:
- verify against the same fixed expectations as ``tools/core1_acceptance_view.py``;
- equal, section for section, the answers this candidate gives in process on
  the same generation.
Missing-data questions must still refuse. Current readiness stays separate:
only the known ``new_season_not_loaded`` blocker (moved to Live) is accepted.
No data, pointer, protection or credential writes.
"""

import hashlib
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.cloud_core_historical_delivery_real_data import (
    LIVE,
    LIVE_MANIFEST,
    _assert_fixed_runtime,
    _readiness,
)
from tests.core1_k08_runtime_binding import deployed_runtime_binding
from tools.core1_acceptance_view import (
    FAIL,
    MAP,
    MISSING,
    PASS,
    _k08,
    _oracle_cases,
)
from tools.core1_acceptance_view import (
    LIVE as LIVE_ROW,
)

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"pass": PASS, "missing_data": MISSING, "live": LIVE_ROW}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


_TIMESTAMP = re.compile(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})")


def _canonical(value):
    # The deployed runtime writes timestamps as "YYYY-MM-DD HH:MM:SS" where the
    # test client writes "YYYY-MM-DDTHH:MM:SS": same value, two spellings.
    if isinstance(value, dict):
        return {k: _canonical(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_canonical(v) for v in value]
    if isinstance(value, str):
        return _TIMESTAMP.sub(r"\1T\2", value) if _TIMESTAMP.fullmatch(value) else value
    return value


def _answer(body):
    """The answer itself: route, status and every result section."""
    result = body.get("result") or {}
    return _canonical(
        dict(
            route=body.get("route"),
            status=body.get("result_status"),
            reason=body.get("result_reason"),
            sections=result.get("sections"),
            caveats=result.get("caveats"),
        )
    )


class _Replay:
    """Serve captured deployed payloads to the acceptance view's K08 checks."""

    def __init__(self, payloads):
        self.payloads, self.asked = payloads, set()

    def post(self, path, *, json):
        assert path == "/query"
        self.asked.add(json["query"])
        return SimpleNamespace(json=lambda: self.payloads[json["query"]])


def _deployed_entry(entry):
    # Synthetic unit nodes (IDs 44-46) run in the local view; here only
    # deployed answers count. IDs 45/46 have no natural-language question.
    check = {k: v for k, v in entry.get("check", {}).items() if k != "pytest"}
    return dict(entry, check=check)


def _cases(spec):
    queries = []
    for entry in spec["k08"]:
        queries += entry.get("queries", [])
        rest = entry.get("check", {}).get("rest_count_case")
        if rest:
            queries.append(rest["query"])
    unique = list(dict.fromkeys(queries))
    cases, ids = [], {}
    for entry in spec["k08"]:
        for n, query in enumerate(entry.get("queries", []), 1):
            if query in ids:
                continue
            ids[query] = f"core1-k08-{int(entry['id']):02d}-{n}"
        rest = entry.get("check", {}).get("rest_count_case")
        if rest and rest["query"] not in ids:
            ids[rest["query"]] = f"core1-k08-{int(entry['id']):02d}-{len(entry['queries']) + 1}"
    forbidden = ["NaN", "undefined", "Infinity"]
    for query in unique:
        cases.append(dict(id=ids[query], query=query, text=[], forbidden=forbidden))
    assert len({c["id"] for c in cases}) == len(cases) == len(unique)
    return cases


def test_core1_k08_deployed_view_matches_candidate():
    from fastapi.testclient import TestClient

    from nbatools.api import app
    from nbatools.data_source import data_generation_context, data_path

    with data_generation_context() as generation:
        assert generation == LIVE
        assert _sha(data_path("metadata/generation_manifest.json").read_bytes()) == LIVE_MANIFEST
        spec = json.loads(MAP.read_bytes())
        oracle = _oracle_cases(spec["independent_oracle"])
        cases = _cases(spec)
        local = TestClient(app)
        expected_answers = {
            c["query"]: _answer(local.post("/query", json={"query": c["query"]}).json())
            for c in cases
        }

    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "core1-deployed-view"
    output.mkdir(parents=True, exist_ok=False)
    inputs = output / "cases.json"
    inputs.write_text(json.dumps(cases) + "\n")
    receipt = dict(
        candidate_sha=os.environ.get("VALIDATION_SHA"),
        generation=LIVE,
        manifest_sha256=LIVE_MANIFEST,
        started_at=datetime.now(UTC).isoformat(),
        questions=len(cases),
        production_writes=0,
        source_requests=0,
        operational_readiness_accepted=False,
        consumer_acceptance="pending",
    )
    try:
        before = deployed_runtime_binding()
        receipt["runtime_before"] = {
            k: v for k, v in before.items() if k != "candidate_build_inputs"
        }
        allowed = {"PATH", "HOME", "TMPDIR", "CI", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"}
        allowed |= {"NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE"}
        env = {k: v for k, v in os.environ.items() if k in allowed}
        subprocess.run(
            ["npm", "ci", "--ignore-scripts", "--no-audit"],
            cwd=ROOT / "frontend",
            env=env,
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
            env=env,
            check=True,
            timeout=1800,
        )
        browser = json.loads((output / "browser-receipt.json").read_bytes())
        assert browser["base"] == before["base_url"] and not browser["failures"]
        receipts = browser["receipts"]
        seen = {(r["viewport"], r["id"]) for r in receipts}
        assert len(seen) == len(receipts)
        assert seen == {(v, c["id"]) for v in ("desktop", "mobile") for c in cases}
        by_query, mismatches = {}, []
        assets = receipts[0]["assets"]
        for item in receipts:
            assert item["http"] == 200 and item["payload"]["query"] == item["query"]
            assert not any(item[k] for k in ("errors", "missing", "forbidden", "grainErrors"))
            # The answer was rendered, not just fetched: a result surface with text,
            # and a table whenever the payload has row sections.
            assert item["text"].strip(), (item["viewport"], item["query"])
            if (item["payload"].get("result") or {}).get("sections"):
                assert item["tables"] or item["heroText"].strip(), item["query"]
            assert item["overflow"]["document"] <= item["overflow"]["viewport"]
            assert _sha((output / item["screenshot"]).read_bytes()) == item["screenshotSha256"]
            assert item["assets"] == assets and len(assets) == 1
            _readiness(item["readinessHttpBefore"], item["readinessBefore"], LIVE)
            _readiness(item["readinessHttpAfter"], item["readinessAfter"], LIVE)
            if _answer(item["payload"]) != expected_answers[item["query"]]:
                mismatches.append((item["viewport"], item["query"]))
            by_query.setdefault(item["query"], item["payload"])
        receipt["answer_mismatches"] = mismatches
        assert not mismatches, mismatches
        replay = _Replay(by_query)
        asked = [e for e in spec["k08"] if e.get("queries")]
        # IDs 45/46 are structured-route checks with no question to ask; they
        # stay with the local view and are never counted as deployed passes.
        receipt["local_only_ids"] = [e["id"] for e in spec["k08"] if not e.get("queries")]
        assert receipt["local_only_ids"] == [45, 46]
        # ID 44's deployed answers are checked here; its synthetic unit node
        # (franchise-identity) stays with the local view.
        receipt["local_unit_nodes_not_rerun"] = [
            n for e in spec["k08"] for n in e.get("check", {}).get("pytest", [])
        ]
        rows = [_k08(_deployed_entry(e), replay, oracle, []) for e in asked]
        assert replay.asked == set(by_query)
        verdicts = {row["id"]: row["verdict"] for row in rows}
        receipt["k08"] = [
            dict(id=r["id"], verdict=r["verdict"], problems=r["problems"]) for r in rows
        ]
        failed = [r for r in rows if r["verdict"] == FAIL]
        assert not failed, failed
        for entry in asked:
            assert verdicts[entry["id"]] == EXPECTED[entry["expect"]], entry["id"]
        after = deployed_runtime_binding()
        _assert_fixed_runtime(before, after)
        receipt["runtime_after"] = {k: v for k, v in after.items() if k != "candidate_build_inputs"}
        counts = {v: sum(x == v for x in verdicts.values()) for v in (PASS, MISSING, LIVE_ROW)}
        receipt.update(consumer_acceptance="passed", captures=len(receipts), counts=counts)
        print("Deployed K08:", counts, "captures:", len(receipts))
    except Exception as exc:
        receipt.update(consumer_acceptance="failed", failure=f"{type(exc).__name__}: {exc}"[:2000])
        raise
    finally:
        receipt["completed_at"] = datetime.now(UTC).isoformat()
        (output / "acceptance.json").write_text(json.dumps(receipt, indent=2, default=str) + "\n")
