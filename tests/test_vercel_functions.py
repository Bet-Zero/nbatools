"""Tests for Vercel function entrypoints and shared function handlers."""

from __future__ import annotations

import importlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from unittest.mock import patch

import pytest

from nbatools import api_ui, vercel_functions
from nbatools.vercel_http import JsonHandler

pytestmark = pytest.mark.api


def test_vercel_entrypoints_export_handlers():
    modules = [
        "api.index",
        "api.ui_fallback_asset",
        "api.assets",
        "api.health",
        "api.routes",
        "api.freshness",
        "api.query",
        "api.structured_query",
    ]

    for module_name in modules:
        module = importlib.import_module(module_name)
        assert issubclass(module.handler, JsonHandler)
        assert issubclass(module.handler, BaseHTTPRequestHandler)


def test_query_response_validates_body():
    status, payload = vercel_functions.query_response({})

    assert status == HTTPStatus.UNPROCESSABLE_ENTITY
    assert payload["ok"] is False
    assert payload["error"] == "validation_error"


def test_query_response_executes_shared_payload():
    expected = {"ok": True, "query": "test", "route": "player_game_summary"}
    with patch("nbatools.vercel_functions.natural_query_payload", return_value=expected) as mock:
        status, payload = vercel_functions.query_response({"query": "Jokic last 10"})

    assert status == HTTPStatus.OK
    assert payload == expected
    mock.assert_called_once_with("Jokic last 10")


def test_structured_query_response_defaults_kwargs():
    expected = {"ok": True, "query": "structured:season_leaders", "route": "season_leaders"}
    with patch("nbatools.vercel_functions.structured_query_payload", return_value=expected) as mock:
        status, payload = vercel_functions.structured_query_response({"route": "season_leaders"})

    assert status == HTTPStatus.OK
    assert payload == expected
    mock.assert_called_once_with("season_leaders", {})


def test_structured_query_response_rejects_non_object_kwargs():
    status, payload = vercel_functions.structured_query_response(
        {"route": "season_leaders", "kwargs": "bad"}
    )

    assert status == HTTPStatus.UNPROCESSABLE_ENTITY
    assert payload["error"] == "validation_error"


def test_ui_fallback_asset_response_serves_javascript():
    status, content, content_type = vercel_functions.ui_fallback_asset_response()

    assert status == HTTPStatus.OK
    assert "UI bundle not built" in content
    assert content_type == "application/javascript"


def test_ui_asset_response_serves_built_asset(tmp_path):
    asset = tmp_path / "assets" / "index-test.js"
    asset.parent.mkdir(parents=True)
    asset.write_text("console.log('ok');")

    status, content, content_type = api_ui.ui_asset_response(
        "assets/index-test.js",
        ui_dir=tmp_path,
    )

    assert status == HTTPStatus.OK
    assert content == b"console.log('ok');"
    assert content_type == "text/javascript; charset=utf-8"


def test_ui_asset_response_returns_404_for_missing_asset(tmp_path):
    status, content, content_type = api_ui.ui_asset_response(
        "assets/missing.js",
        ui_dir=tmp_path,
    )

    assert status == HTTPStatus.NOT_FOUND
    assert content == b"Not found"
    assert content_type == "text/plain; charset=utf-8"


def test_ui_asset_response_rejects_path_traversal(tmp_path):
    outside = tmp_path.parent / "outside.js"
    outside.write_text("bad")

    status, content, _ = api_ui.ui_asset_response("../outside.js", ui_dir=tmp_path)

    assert status == HTTPStatus.NOT_FOUND
    assert content == b"Not found"


def test_vercel_asset_path_parses_rewrite_query():
    from api.assets import _asset_path_from_request

    assert _asset_path_from_request("/api/assets?path=assets/index-test.js") == (
        "assets/index-test.js"
    )
    assert _asset_path_from_request("/assets/index-test.css") == "assets/index-test.css"
