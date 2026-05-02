"""Pure request handlers shared by Vercel function entrypoints and tests."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from nbatools.api_handlers import (
    freshness_payload,
    health_payload,
    natural_query_payload,
    routes_payload,
    structured_query_payload,
)
from nbatools.api_ui import UI_FALLBACK_SCRIPT, load_ui_html


def ui_response() -> tuple[int, str, str]:
    """Return the fallback/local UI shell response."""
    return HTTPStatus.OK, load_ui_html(), "text/html; charset=utf-8"


def ui_fallback_asset_response() -> tuple[int, str, str]:
    """Return the fallback UI JavaScript asset response."""
    return HTTPStatus.OK, UI_FALLBACK_SCRIPT, "application/javascript"


def ui_asset_response(asset_path: str) -> tuple[int, bytes, str]:
    """Return a bundled UI asset response."""
    from nbatools.api_ui import ui_asset_response as build_ui_asset_response

    return build_ui_asset_response(asset_path)


def health_response() -> tuple[int, dict[str, Any]]:
    """Return the health endpoint response."""
    return HTTPStatus.OK, health_payload()


def routes_response() -> tuple[int, dict[str, Any]]:
    """Return the routes endpoint response."""
    return HTTPStatus.OK, routes_payload()


def freshness_response() -> tuple[int, dict[str, Any]]:
    """Return the freshness endpoint response."""
    return HTTPStatus.OK, freshness_payload()


def query_response(body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Validate and execute a natural query request body."""
    query = body.get("query")
    if not isinstance(query, str) or not query.strip():
        return _validation_error("Field 'query' must be a non-empty string")
    return HTTPStatus.OK, natural_query_payload(query)


def structured_query_response(body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Validate and execute a structured query request body."""
    route = body.get("route")
    if not isinstance(route, str) or not route.strip():
        return _validation_error("Field 'route' must be a non-empty string")

    kwargs = body.get("kwargs", {})
    if kwargs is None:
        kwargs = {}
    if not isinstance(kwargs, dict):
        return _validation_error("Field 'kwargs' must be an object when provided")
    return HTTPStatus.OK, structured_query_payload(route, kwargs)


def _validation_error(detail: str) -> tuple[int, dict[str, Any]]:
    return HTTPStatus.UNPROCESSABLE_ENTITY, {
        "ok": False,
        "error": "validation_error",
        "detail": detail,
    }
