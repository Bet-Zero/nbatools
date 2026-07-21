"""Privacy and stability tests for public operational events."""

from __future__ import annotations

import json
import logging
from io import BytesIO
from time import perf_counter
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.operational_observability import (
    extract_request_outcome,
    log_request_complete,
    normalize_endpoint,
)
from nbatools.public_errors import REQUEST_ID_HEADER
from nbatools.vercel_http import JsonHandler

pytestmark = pytest.mark.api

SECRET_TEXT = "Jokic token=secret /srv/private.csv"


def test_endpoint_normalization_drops_queries_and_unknown_paths() -> None:
    assert normalize_endpoint("/query?query=secret") == "/query"
    assert normalize_endpoint("/private/secret") == "unknown"


def test_query_outcome_extracts_only_allowlisted_fields() -> None:
    outcome = extract_request_outcome(
        "/query",
        {
            "query": SECRET_TEXT,
            "route": "player_game_summary",
            "result_status": "no_result",
            "result_reason": "no_match",
            "notes": [SECRET_TEXT],
            "result": {"secret": SECRET_TEXT},
        },
    )

    assert outcome == {
        "route": "player_game_summary",
        "result_status": "no_result",
        "result_reason": "no_match",
    }
    assert SECRET_TEXT not in json.dumps(outcome)


def test_readiness_outcome_uses_codes_without_blocker_messages() -> None:
    outcome = extract_request_outcome(
        "/readiness",
        {
            "ready": False,
            "status": "not_ready",
            "season_state": "active",
            "active_generation": "generation-1",
            "blockers": [{"code": "active_season_lag", "message": SECRET_TEXT}],
        },
    )

    assert outcome == {
        "data_status": "not_ready",
        "season_state": "active",
        "active_generation": "generation-1",
        "ready": False,
        "blocker_codes": ["active_season_lag"],
    }
    assert SECRET_TEXT not in json.dumps(outcome)


def test_completion_event_is_bounded_and_excludes_payload_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="nbatools.operational")

    outcome = extract_request_outcome(
        "/query",
        {
            "query": SECRET_TEXT,
            "route": "player_game_summary",
            "result_status": "ok",
            "result_reason": None,
        },
    )
    log_request_complete(
        request_id="req_test",
        endpoint="/query",
        method="POST",
        status=200,
        duration_ms=12.34567,
        outcome=outcome,
    )

    assert SECRET_TEXT not in caplog.text
    event = json.loads(caplog.records[-1].message)
    assert event["event"] == "public_request_complete"
    assert event["request_id"] == "req_test"
    assert event["endpoint"] == "/query"
    assert event["method"] == "POST"
    assert event["status"] == 200
    assert event["status_class"] == "2xx"
    assert event["duration_ms"] == 12.346
    assert event["route"] == "player_game_summary"
    assert event["result_status"] == "ok"
    assert set(event) <= {
        "event",
        "request_id",
        "endpoint",
        "method",
        "status",
        "status_class",
        "duration_ms",
        "rss_peak_mb",
        "cache_hits",
        "cache_misses",
        "cache_entries",
        "cache_bytes",
        "cache_evictions",
        "result_status",
        "result_reason",
        "route",
        "data_status",
        "current_through",
        "season_state",
        "active_generation",
        "ready",
        "blocker_codes",
    }


def test_logging_failure_never_changes_request_path() -> None:
    with patch(
        "nbatools.operational_observability._LOGGER.info",
        side_effect=RuntimeError("delivery failed"),
    ):
        log_request_complete(
            request_id="req_test",
            endpoint="/health",
            method="GET",
            status=200,
            duration_ms=1,
        )


def test_fastapi_health_emits_correlated_completion_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="nbatools.operational")

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    events = [json.loads(record.message) for record in caplog.records]
    event = next(item for item in events if item.get("event") == "public_request_complete")
    assert event["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert event["endpoint"] == "/health"
    assert event["status"] == 200


def test_vercel_json_response_emits_correlated_completion_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="nbatools.operational")
    handler = object.__new__(JsonHandler)
    handler._nbatools_request_id = "req_test"
    handler._nbatools_request_started_at = perf_counter()
    handler.path = "/query"
    handler.command = "POST"
    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()
    handler.wfile = BytesIO()

    handler.send_json(
        {
            "ok": True,
            "query": SECRET_TEXT,
            "route": "player_game_summary",
            "result_status": "ok",
            "result_reason": None,
        }
    )

    assert SECRET_TEXT not in caplog.text
    event = json.loads(caplog.records[-1].message)
    assert event["request_id"] == "req_test"
    assert event["endpoint"] == "/query"
    assert event["result_status"] == "ok"
