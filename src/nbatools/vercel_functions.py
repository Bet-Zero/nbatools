"""Pure request handlers shared by Vercel function entrypoints and tests."""

from __future__ import annotations

import time
from http import HTTPStatus
from typing import Any

from pydantic import ValidationError

from nbatools.api_contracts import (
    NaturalQueryRequest,
    StructuredQueryRequest,
    validation_error_payload,
)
from nbatools.api_handlers import (
    dev_fixtures_payload,
    freshness_payload,
    health_payload,
    natural_query_payload,
    routes_payload,
    structured_query_payload,
)
from nbatools.api_ui import UI_FALLBACK_SCRIPT, load_ui_html
from nbatools.query_feedback import (
    elapsed_ms_since,
    handle_feedback_submission,
    maybe_log_query_diagnostic,
)


def ui_response() -> tuple[int, str, str]:
    """Return the fallback/local UI shell response."""
    return HTTPStatus.OK, load_ui_html(), "text/html; charset=utf-8"


def visual_qa_response(
    env: dict[str, str] | None = None,
) -> tuple[int, str | dict[str, Any], str]:
    """Serve the visual-QA shell only for explicit preview environments."""
    from nbatools.internal_routes import visual_qa_route_available

    if not visual_qa_route_available(env):
        return (
            HTTPStatus.NOT_FOUND,
            {"ok": False, "error": "internal_route_unavailable", "detail": None},
            "application/json",
        )
    return ui_response()


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


def readiness_response() -> tuple[int, dict[str, Any]]:
    """Return strict deployment readiness with a fail-closed status code."""
    from nbatools.readiness import build_readiness_info

    info = build_readiness_info()
    return (HTTPStatus.OK if info.ready else HTTPStatus.SERVICE_UNAVAILABLE), info.to_dict()


def dev_fixtures_response() -> tuple[int, dict[str, Any]]:
    """Return the parser example fixture list for the internal review UI."""
    return HTTPStatus.OK, dev_fixtures_payload()


def query_response(
    body: Any,
    *,
    source_page: str | None = None,
    client_id: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Validate and execute a natural query request body."""
    try:
        request = NaturalQueryRequest.model_validate(body)
    except ValidationError as exc:
        return HTTPStatus.UNPROCESSABLE_ENTITY, validation_error_payload(exc)
    start_time = time.monotonic()
    if client_id is not None:
        from nbatools.admission_control import ADMISSION_CONTROLLER

        payload = ADMISSION_CONTROLLER.run_query(
            client_id,
            lambda: natural_query_payload(request.query),
        )
    else:
        payload = natural_query_payload(request.query)
    maybe_log_query_diagnostic(
        payload,
        elapsed_ms=elapsed_ms_since(start_time),
        source_page=source_page,
    )
    return HTTPStatus.OK, payload


def query_feedback_response(
    body: dict[str, Any],
    *,
    source_page: str | None = None,
    idempotency_key: str | None = None,
    client_id: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Validate and persist a query feedback request body."""
    from nbatools.admission_control import ADMISSION_CONTROLLER

    reservation = ADMISSION_CONTROLLER.reserve_feedback(client_id) if client_id else None
    feedback_kwargs: dict[str, Any] = {"source_page": source_page}
    if idempotency_key is not None:
        feedback_kwargs["idempotency_key"] = idempotency_key
    try:
        status, payload = handle_feedback_submission(body, **feedback_kwargs)
    except Exception:
        if reservation is not None:
            reservation.rollback()
        raise
    if reservation is not None:
        if payload.get("stored") and not payload.get("idempotent_replay"):
            reservation.commit()
        else:
            reservation.rollback()
    return status, payload


def structured_query_response(
    body: Any,
    *,
    client_id: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """Validate and execute a structured query request body."""
    try:
        request = StructuredQueryRequest.model_validate(body)
    except ValidationError as exc:
        return HTTPStatus.UNPROCESSABLE_ENTITY, validation_error_payload(exc)
    if client_id is not None:
        from nbatools.admission_control import ADMISSION_CONTROLLER

        payload = ADMISSION_CONTROLLER.run_query(
            client_id,
            lambda: structured_query_payload(request.route, request.kwargs),
        )
    else:
        payload = structured_query_payload(request.route, request.kwargs)
    return HTTPStatus.OK, payload
