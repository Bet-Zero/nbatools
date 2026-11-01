"""Explicit-only public regression: published counts and unpublished Rest reasons."""

import hashlib
import json
import os
import re
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
ROOT = Path(__file__).resolve().parents[1]
BASE = "availability-lebron-season-v1-20261031"
MANIFEST = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"
URL = "https://nbatools.vercel.app"
QUALIFICATION = (
    ROOT
    / "working/nba-tools-completion-program/source-evidence/k08-lebron-remaining"
    / "qualification.json"
)
QUALIFICATION_SHA = "772db656d061d8b459e62c24aa939a9cae13479492eb5c1d7f1b1a6973fb9c1c"
REST_QUERY = "Lakers record when Luka Doncic rests from 2025-10-24 to 2025-10-27 in 2025-26"
QUERIES = (
    "How many games did LeBron James miss in 2025-26?",
    "How many home games did LeBron James miss in 2025-26?",
    REST_QUERY,
)


def _fold(value):
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()


def _parser_scope():
    """Record local parser intent; public API has no top-level query metadata."""
    from nbatools.commands.natural_query import parse_query

    parsed = parse_query(REST_QUERY)
    options = parsed["route_kwargs"]
    assert parsed["route"] == "team_record"
    assert options["team"] == "LAL" and options["season"] == "2025-26"
    assert _fold(options["without_player"]) == "luka doncic"
    assert options["without_player_reason"] == "reported_rest"
    assert options["start_date"] == "2025-10-24" and options["end_date"] == "2025-10-27"
    assert not options.get("unsupported_filters")
    return options


def _assert_count(answer, query, expected_ids):
    assert answer["query"] == query and answer["route"] == "game_finder"
    assert answer["result_status"] == "ok" and answer["result_reason"] is None
    sections = answer["result"]["sections"]
    assert sections["count"] == [{"count": len(expected_ids)}]
    assert len(sections["finder"]) == len(expected_ids)
    assert {int(row["game_id"]) for row in sections["finder"]} == set(expected_ids)
    assert all(
        row["season"] == "2025-26" and row["team_abbr"] == "LAL" for row in sections["finder"]
    )


def _assert_unpublished_reason(answer):
    assert answer["query"] == REST_QUERY and answer["route"] == "team_record"
    assert answer["result_status"] == "no_result" and answer["result_reason"] == "no_data"
    result = answer["result"]
    assert not result["sections"]
    assert result["metadata"]["reported_reason_basis"] == "officially reported Rest"
    assert result["metadata"]["reported_reason_coverage"] == dict(
        basis="officially reported Rest",
        complete=False,
        requested_games=3,
        qualified_nonparticipations=2,
        reported_rest=0,
        reported_other=0,
        unknown=2,
    )
    notes = [_fold(note) for note in answer["notes"]]
    assert any(
        "incomplete officially reported rest reason coverage for luka doncic" in n for n in notes
    )
    assert any("no rest total is established" in n for n in notes)


def test_deployed_rest_keeps_unpublished_reasons_unknown():
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "reported-rest-deployed"
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(
        classification="bounded_public_regression_not_reason_publication_or_operational_readiness",
        candidate_sha=os.environ.get("VALIDATION_SHA"),
        expected_generation=BASE,
        expected_manifest_sha256=MANIFEST,
        expected_public_readiness=503,
        status="pending",
        failure=None,
        operational_acceptance_complete=False,
        public_readiness_requests=0,
        public_query_requests=0,
        attempts_per_request=1,
        minimum_query_start_spacing_seconds=7,
        request_timeout_seconds=30,
        redirects_allowed=False,
        requests=[],
        nba_source_requests=0,
        production_data_writes=0,
    )
    receipt_path = output / "receipt.json"

    def persist():
        receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")

    def request(method, path, query=None):
        item = dict(
            method=method,
            url=URL + path,
            query=query,
            started_at=datetime.now(UTC).isoformat(),
            monotonic_start_seconds=time.monotonic(),
            attempts=1,
            response=None,
            failure=None,
        )
        receipt["requests"].append(item)
        receipt["public_readiness_requests" if method == "GET" else "public_query_requests"] += 1
        persist()
        try:
            kwargs = dict(timeout=30, allow_redirects=False)
            response = (
                requests.get(item["url"], **kwargs)
                if method == "GET"
                else requests.post(item["url"], json={"query": query}, **kwargs)
            )
            raw = response.content
            filename = f"response-{len(receipt['requests']):02d}.body"
            (output / filename).write_bytes(raw)
            item["response"] = dict(
                status=response.status_code,
                headers=dict(response.headers),
                body_file=filename,
                body_size_bytes=len(raw),
                body_sha256=hashlib.sha256(raw).hexdigest(),
            )
            persist()  # Original response survives JSON/contract assertion failures.
            body = response.json()
            item["response"]["body"] = body
            persist()
            return response.status_code, body
        except Exception as exc:
            item["failure"] = dict(type=type(exc).__name__, message=str(exc))
            persist()
            raise

    persist()
    try:
        assert os.environ["NBATOOLS_DATA_GENERATION"] == BASE
        assert re.fullmatch(r"[a-f0-9]{40}", receipt["candidate_sha"] or "")
        raw = QUALIFICATION.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == QUALIFICATION_SHA
        source = json.loads(raw)
        assert source["observed_counts"] == dict(
            played=60, did_not_play=22, same_game_other_side=0, unknown=0
        )
        expected = [source["missed_game_ids"], source["home_missed_game_ids"]]
        assert [len(ids) for ids in expected] == [22, 11]
        assert set(expected[1]) <= set(expected[0])
        receipt["qualification_sha256"] = QUALIFICATION_SHA
        receipt["local_parser_scope"] = _parser_scope()
        persist()
        code, state = request("GET", "/readiness")
        assert code == 503 and state["active_generation"] == BASE and state["ready"] is False
        assert [block["code"] for block in state["blockers"]] == ["new_season_not_loaded"]
        assert state["exception"]["applied"] is False
        receipt["readiness"] = state
        next_start = time.monotonic()
        for index, query in enumerate(QUERIES):
            delay = max(0, next_start - time.monotonic())
            if delay:
                time.sleep(delay)
            next_start = time.monotonic() + 7.0
            code, answer = request("POST", "/query", query)
            assert code == 200
            if index < 2:
                _assert_count(answer, query, expected[index])
            else:
                _assert_unpublished_reason(answer)
        assert receipt["public_readiness_requests"] == 1 and receipt["public_query_requests"] == 3
        receipt["status"] = "passed"
    except Exception as exc:
        receipt.update(status="failed", failure=dict(type=type(exc).__name__, message=str(exc)))
        raise
    finally:
        persist()
