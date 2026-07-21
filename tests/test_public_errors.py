"""Public error redaction and request-correlation regressions."""

from __future__ import annotations

import importlib
import json
import logging
import re
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.public_errors import (
    PUBLIC_INTERNAL_ERROR_CODE,
    PUBLIC_INTERNAL_ERROR_DETAIL,
    REQUEST_ID_HEADER,
    log_public_error,
    new_request_id,
)
from nbatools.vercel_http import JsonHandler

pytestmark = pytest.mark.api

REQUEST_ID_PATTERN = re.compile(r"^req_[0-9a-f]{32}$")
SECRET_EXCEPTION = "bucket=private-data token=secret /srv/internal/file.csv"


def test_request_ids_are_opaque_and_unique() -> None:
    first = new_request_id()
    second = new_request_id()

    assert REQUEST_ID_PATTERN.fullmatch(first)
    assert REQUEST_ID_PATTERN.fullmatch(second)
    assert first != second


def test_public_error_log_contains_only_allowlisted_metadata(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR, logger="nbatools.public_errors")

    log_public_error(
        request_id="req_test",
        endpoint="/query",
        status=500,
        error=PUBLIC_INTERNAL_ERROR_CODE,
        exc=RuntimeError(SECRET_EXCEPTION),
    )

    assert SECRET_EXCEPTION not in caplog.text
    event = json.loads(caplog.records[-1].message)
    assert event == {
        "endpoint": "/query",
        "error": "internal_error",
        "event": "public_request_error",
        "exception_type": "RuntimeError",
        "request_id": "req_test",
        "status": 500,
    }


def test_vercel_json_errors_include_matching_request_id_header() -> None:
    handler = object.__new__(JsonHandler)
    handler._nbatools_request_id = "req_test"
    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()
    handler.wfile = BytesIO()

    handler.send_json({"ok": False, "error": "validation_error"}, status=422)

    payload = json.loads(handler.wfile.getvalue())
    assert payload["request_id"] == "req_test"
    handler.send_header.assert_any_call(REQUEST_ID_HEADER, "req_test")


def test_vercel_method_rejections_include_request_id_header() -> None:
    handler = object.__new__(JsonHandler)
    handler._nbatools_request_id = "req_test"
    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()

    handler.method_not_allowed("POST, OPTIONS")

    handler.send_header.assert_any_call(REQUEST_ID_HEADER, "req_test")


@pytest.mark.parametrize(
    ("module_name", "response_name", "method_name", "expected_status"),
    [
        ("api.query", "query_response", "do_POST", 500),
        ("api.structured_query", "structured_query_response", "do_POST", 500),
        ("api.query_feedback", "query_feedback_response", "do_POST", 500),
        ("api.freshness", "freshness_response", "do_GET", 500),
        ("api.readiness", "readiness_response", "do_GET", 503),
    ],
)
def test_vercel_handlers_never_return_raw_unexpected_exception_text(
    module_name: str,
    response_name: str,
    method_name: str,
    expected_status: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    module = importlib.import_module(module_name)
    handler = object.__new__(module.handler)
    handler._nbatools_request_id = "req_test"
    handler.headers = {}
    handler.read_json_body = lambda _path: {"query": "test", "route": "season_leaders"}
    handler.client_identifier = lambda: "test-client"
    handler.send_api_error = Mock()
    caplog.set_level(logging.ERROR, logger="nbatools.public_errors")

    with patch.object(module, response_name, side_effect=RuntimeError(SECRET_EXCEPTION)):
        getattr(handler, method_name)()

    handler.send_api_error.assert_called_once_with(
        expected_status,
        PUBLIC_INTERNAL_ERROR_CODE,
        PUBLIC_INTERNAL_ERROR_DETAIL,
    )
    assert SECRET_EXCEPTION not in caplog.text
    assert json.loads(caplog.records[-1].message)["request_id"] == "req_test"


def test_fastapi_unexpected_error_is_redacted_and_correlated(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = TestClient(app, raise_server_exceptions=False)
    caplog.set_level(logging.ERROR, logger="nbatools.public_errors")

    with patch(
        "nbatools.api.build_freshness_info",
        side_effect=RuntimeError(SECRET_EXCEPTION),
    ):
        response = client.get("/freshness")

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"] == PUBLIC_INTERNAL_ERROR_CODE
    assert payload["detail"] == PUBLIC_INTERNAL_ERROR_DETAIL
    assert REQUEST_ID_PATTERN.fullmatch(payload["request_id"])
    assert response.headers[REQUEST_ID_HEADER] == payload["request_id"]
    assert SECRET_EXCEPTION not in response.text
    assert SECRET_EXCEPTION not in caplog.text
    event = json.loads(caplog.records[-1].message)
    assert event["endpoint"] == "/freshness"
    assert event["request_id"] == payload["request_id"]


def test_fastapi_success_response_has_request_id_header() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert REQUEST_ID_PATTERN.fullmatch(response.headers[REQUEST_ID_HEADER])
