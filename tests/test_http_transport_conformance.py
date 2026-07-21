"""Machine-readable public HTTP contract conformance across transports."""

from __future__ import annotations

import importlib
import json
import logging
import time
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from nbatools.admission_control import BODY_LIMITS
from nbatools.api import app
from nbatools.public_errors import PUBLIC_METHOD_NOT_ALLOWED_DETAIL, REQUEST_ID_HEADER

pytestmark = pytest.mark.api

CONTRACT = json.loads(Path("contracts/public_http_routes.json").read_text())
PUBLIC_ROUTES = CONTRACT["public_routes"]
CLIENT = TestClient(app, raise_server_exceptions=False)


def _module_name(path: str) -> str:
    return "api." + path.removeprefix("/").replace("-", "_")


def _new_vercel_handler(path: str, *, method: str):
    handler_type = importlib.import_module(_module_name(path)).handler
    handler = object.__new__(handler_type)
    handler.path = path
    handler.command = method
    handler._nbatools_request_id = "req_contract"
    handler._nbatools_request_started_at = time.perf_counter()
    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()
    handler.wfile = BytesIO()
    return handler


def _header_values(handler) -> dict[str, str]:
    return {call.args[0]: call.args[1] for call in handler.send_header.call_args_list}


def _matches_pattern(path: str, pattern: str) -> bool:
    return path.startswith(pattern.removesuffix("*")) if pattern.endswith("*") else path == pattern


def test_contract_body_budgets_match_shared_admission_control() -> None:
    contracted = {
        route["path"]: route["body_max_bytes"]
        for route in PUBLIC_ROUTES
        if route["body_max_bytes"] is not None
    }
    assert contracted == BODY_LIMITS


def test_contract_routes_match_fastapi_vercel_and_vercel_rewrites() -> None:
    expected = {route["path"]: route["method"] for route in PUBLIC_ROUTES}
    fastapi_methods = {
        route.path: next(iter(route.methods))
        for route in app.routes
        if getattr(route, "path", None) in expected
    }
    assert fastapi_methods == expected

    config = json.loads(Path("vercel.json").read_text())
    rewrites = {item["source"]: item["destination"] for item in config["rewrites"]}
    for path, method in expected.items():
        assert rewrites[path] == f"/api/{path.removeprefix('/').replace('-', '_')}"
        handler_type = importlib.import_module(_module_name(path)).handler
        assert handler_type.allowed_method == method
        assert hasattr(handler_type, f"do_{method}")
        assert hasattr(handler_type, "do_OPTIONS")


@pytest.mark.parametrize("route", PUBLIC_ROUTES, ids=lambda route: route["path"])
def test_wrong_methods_use_correlated_json_errors_across_transports(route) -> None:
    path = route["path"]
    expected_method = route["method"]
    wrong_method = "POST" if expected_method == "GET" else "GET"
    error_contract = CONTRACT["errors"]["method_not_allowed"]
    expected_allow = f"{expected_method}, OPTIONS"

    response = CLIENT.request(wrong_method, path)
    assert response.status_code == error_contract["status"]
    assert response.headers["content-type"].startswith(error_contract["content_type"])
    assert response.headers[REQUEST_ID_HEADER] == response.json()["request_id"]
    assert response.headers["allow"] == expected_allow
    assert response.json()["error"] == error_contract["code"]
    assert response.json()["detail"] == PUBLIC_METHOD_NOT_ALLOWED_DETAIL

    handler = _new_vercel_handler(path, method=wrong_method)
    getattr(handler, f"do_{wrong_method}")()
    headers = _header_values(handler)
    payload = json.loads(handler.wfile.getvalue())
    handler.send_response.assert_called_once_with(error_contract["status"])
    assert headers["Content-Type"] == error_contract["content_type"]
    assert headers[REQUEST_ID_HEADER] == payload["request_id"] == "req_contract"
    assert headers["Allow"] == response.headers["allow"] == expected_allow
    assert payload["error"] == error_contract["code"]
    assert payload["detail"] == PUBLIC_METHOD_NOT_ALLOWED_DETAIL


@pytest.mark.parametrize("method", ["HEAD", "PUT", "PATCH", "DELETE"])
def test_other_unsupported_verbs_use_precise_json_errors(method: str) -> None:
    error_contract = CONTRACT["errors"]["method_not_allowed"]
    response = CLIENT.request(method, "/query")
    assert response.status_code == error_contract["status"]
    assert response.headers["content-type"].startswith(error_contract["content_type"])
    assert response.headers["allow"] == "POST, OPTIONS"

    handler = _new_vercel_handler("/query", method=method)
    getattr(handler, f"do_{method}")()
    headers = _header_values(handler)
    handler.send_response.assert_called_once_with(error_contract["status"])
    assert headers["Content-Type"] == error_contract["content_type"]
    assert headers["Allow"] == response.headers["allow"]
    if method == "HEAD":
        assert response.content == handler.wfile.getvalue() == b""
    else:
        assert json.loads(handler.wfile.getvalue())["error"] == error_contract["code"]


@pytest.mark.parametrize("route", PUBLIC_ROUTES, ids=lambda route: route["path"])
def test_cors_preflight_meets_contract_across_transports(route) -> None:
    path = route["path"]
    cors = CONTRACT["cors"]
    response = CLIENT.options(
        path,
        headers={
            "Origin": "https://client.example",
            "Access-Control-Request-Method": route["method"],
            "Access-Control-Request-Headers": ", ".join(cors["required_request_headers"]),
        },
    )
    assert response.status_code == CONTRACT["intentional_differences"]["fastapi_options_status"]
    assert response.headers["access-control-allow-origin"] == cors["allow_origin"]
    for method in cors["required_methods"]:
        assert method in response.headers["access-control-allow-methods"]
    for header in cors["required_request_headers"]:
        assert header.lower() in response.headers["access-control-allow-headers"].lower()

    handler = _new_vercel_handler(path, method="OPTIONS")
    handler.do_OPTIONS()
    headers = _header_values(handler)
    handler.send_response.assert_called_once_with(
        CONTRACT["intentional_differences"]["vercel_options_status"]
    )
    assert headers["Access-Control-Allow-Origin"] == cors["allow_origin"]
    for method in cors["required_methods"]:
        assert method in headers["Access-Control-Allow-Methods"]
    for header in cors["required_request_headers"]:
        assert header in headers["Access-Control-Allow-Headers"]
    for header in cors["required_exposed_headers"]:
        assert header in headers["Access-Control-Expose-Headers"]


@pytest.mark.parametrize("path", ["/query", "/structured-query", "/query-feedback"])
@pytest.mark.parametrize(
    ("raw_body", "detail"),
    [
        (b"", "Request body must be a JSON object"),
        (b"{", "Request body must be valid JSON"),
        (b"[]", "Request body must be a JSON object"),
    ],
)
def test_malformed_bodies_share_json_validation_errors(
    path: str, raw_body: bytes, detail: str
) -> None:
    error_contract = CONTRACT["errors"]["validation_error"]
    response = CLIENT.post(
        path,
        content=raw_body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == error_contract["status"]
    assert response.headers["content-type"].startswith(error_contract["content_type"])
    assert response.json()["error"] == error_contract["code"]
    assert response.json()["detail"] == detail
    assert response.headers[REQUEST_ID_HEADER] == response.json()["request_id"]

    handler = _new_vercel_handler(path, method="POST")
    handler.headers = {"Content-Length": str(len(raw_body))}
    handler.rfile = BytesIO(raw_body)
    getattr(handler, "do_POST")()
    payload = json.loads(handler.wfile.getvalue())
    handler.send_response.assert_called_once_with(error_contract["status"])
    assert payload["error"] == error_contract["code"]
    assert payload["detail"] == detail
    assert _header_values(handler)[REQUEST_ID_HEADER] == payload["request_id"]


def test_endpoint_validation_errors_are_correlated_across_transports() -> None:
    error_contract = CONTRACT["errors"]["validation_error"]
    raw_body = b"{}"
    response = CLIENT.post(
        "/query-feedback",
        content=raw_body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == error_contract["status"]
    assert response.json()["error"] == error_contract["code"]
    assert response.headers[REQUEST_ID_HEADER] == response.json()["request_id"]

    handler = _new_vercel_handler("/query-feedback", method="POST")
    handler.headers = {"Content-Length": str(len(raw_body))}
    handler.rfile = BytesIO(raw_body)
    handler.client_address = ("127.0.0.1", 1234)
    handler.do_POST()
    payload = json.loads(handler.wfile.getvalue())
    headers = _header_values(handler)
    assert payload["error"] == response.json()["error"]
    assert payload["detail"] == response.json()["detail"]
    assert headers[REQUEST_ID_HEADER] == payload["request_id"]


def test_early_body_rejections_keep_cors_headers() -> None:
    response = CLIENT.post(
        "/query",
        content=b"x" * (BODY_LIMITS["/query"] + 1),
        headers={"Content-Type": "application/json", "Origin": "https://client.example"},
    )
    assert response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert response.headers["access-control-allow-origin"] == "*"
    assert response.headers[REQUEST_ID_HEADER] == response.json()["request_id"]


@pytest.mark.parametrize(
    ("path", "fastapi_target", "vercel_target", "error_name"),
    [
        (
            "/freshness",
            "nbatools.api.build_freshness_info",
            "api.freshness.freshness_response",
            "unexpected_error",
        ),
        (
            "/readiness",
            "nbatools.api.build_readiness_info",
            "api.readiness.readiness_response",
            "readiness_unavailable",
        ),
    ],
)
def test_unexpected_errors_follow_contract_and_keep_cors(
    path: str,
    fastapi_target: str,
    vercel_target: str,
    error_name: str,
) -> None:
    error_contract = CONTRACT["errors"][error_name]
    with patch(fastapi_target, side_effect=RuntimeError("private failure")):
        response = CLIENT.get(path, headers={"Origin": "https://client.example"})
    assert response.status_code == error_contract["status"]
    assert response.headers["content-type"].startswith(error_contract["content_type"])
    assert response.headers["access-control-allow-origin"] == CONTRACT["cors"]["allow_origin"]
    assert response.headers[REQUEST_ID_HEADER] == response.json()["request_id"]
    assert response.json()["error"] == error_contract["code"]

    handler = _new_vercel_handler(path, method="GET")
    with patch(vercel_target, side_effect=RuntimeError("private failure")):
        handler.do_GET()
    payload = json.loads(handler.wfile.getvalue())
    headers = _header_values(handler)
    handler.send_response.assert_called_once_with(error_contract["status"])
    assert headers["Content-Type"] == error_contract["content_type"]
    assert headers["Access-Control-Allow-Origin"] == CONTRACT["cors"]["allow_origin"]
    assert headers[REQUEST_ID_HEADER] == payload["request_id"]
    assert payload["error"] == error_contract["code"]


def test_early_and_unexpected_fastapi_failures_emit_one_completion_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="nbatools.operational")
    malformed = CLIENT.post(
        "/query",
        content=b"{",
        headers={"Content-Type": "application/json"},
    )
    with patch("nbatools.api.build_freshness_info", side_effect=RuntimeError("private")):
        unexpected = CLIENT.get("/freshness")

    events = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "nbatools.operational"
        and json.loads(record.message).get("event") == "public_request_complete"
    ]
    assert [(event["endpoint"], event["status"]) for event in events] == [
        ("/query", malformed.status_code),
        ("/freshness", unexpected.status_code),
    ]
    assert [event["request_id"] for event in events] == [
        malformed.headers[REQUEST_ID_HEADER],
        unexpected.headers[REQUEST_ID_HEADER],
    ]


def test_contract_records_intentional_local_only_route_differences() -> None:
    differences = CONTRACT["intentional_differences"]
    config = json.loads(Path("vercel.json").read_text())
    sources = [item["source"] for item in config["rewrites"]]
    fastapi_paths = [getattr(route, "path", "") for route in app.routes]

    for pattern in differences["fastapi_local_only_routes"]:
        assert any(_matches_pattern(path, pattern) for path in fastapi_paths)
    for pattern in differences["production_absent_routes"]:
        assert not any(_matches_pattern(source, pattern) for source in sources)

    extensions = differences["fastapi_local_cors_extensions"]
    response = CLIENT.options(
        "/api/admin/feedback/groups/example/triage",
        headers={
            "Origin": "https://client.example",
            "Access-Control-Request-Method": extensions["methods"][0],
            "Access-Control-Request-Headers": extensions["request_headers"][0],
        },
    )
    assert response.status_code == differences["fastapi_options_status"]
    for method in extensions["methods"]:
        assert method in response.headers["access-control-allow-methods"]
    for header in extensions["request_headers"]:
        assert header.lower() in response.headers["access-control-allow-headers"].lower()
