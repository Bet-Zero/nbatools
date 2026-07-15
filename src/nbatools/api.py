"""Thin local HTTP API layer over the nbatools query service.

This module exposes the structured query engine through a small FastAPI
application so that a future UI or any HTTP client can call the engine
directly without going through the CLI.

Run locally with::

    uvicorn nbatools.api:app --reload
"""

from __future__ import annotations

import os
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from nbatools import __version__, api_ui
from nbatools.api_contracts import (
    NaturalQueryRequest,
    StructuredQueryRequest,
    validation_error_payload,
)
from nbatools.api_handlers import dev_fixtures_payload, query_result_to_payload
from nbatools.commands.freshness import build_freshness_info
from nbatools.query_feedback import (
    elapsed_ms_since,
    handle_feedback_submission,
    maybe_log_query_diagnostic,
)
from nbatools.query_feedback_review import (
    FeedbackReviewError,
    FeedbackReviewFilters,
    TriageOverlayValidationError,
    get_feedback_group_detail,
    list_feedback_groups,
    parse_datetime_filter,
    parse_multi_filter,
    read_triage_overlay,
    write_triage_overlay,
)
from nbatools.query_service import (
    VALID_ROUTES,
    QueryResult,
    execute_natural_query,
    execute_structured_query,
)
from nbatools.readiness import build_readiness_info

_UI_DIR = api_ui.UI_DIR
_UI_INDEX = api_ui.UI_INDEX
_UI_FALLBACK_ASSET = api_ui.UI_FALLBACK_ASSET
_UI_FALLBACK_SCRIPT = api_ui.UI_FALLBACK_SCRIPT

ADMIN_FEEDBACK_ENABLED_ENV = "NBATOOLS_ADMIN_FEEDBACK_ENABLED"
ADMIN_TOKEN_ENV = "NBATOOLS_ADMIN_TOKEN"

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="nbatools API",
    version=__version__,
    description="Local-first NBA analytics API — thin layer over the nbatools query service.",
)

# Allow local dev clients (file://, localhost variants) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local-only; no auth, no deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class QueryResponse(BaseModel):
    """Envelope returned by both query endpoints."""

    ok: bool
    query: str
    route: str | None = None
    result_status: str
    result_reason: str | None = None
    current_through: str | None = None
    confidence: float | None = None
    intent: str | None = None
    alternates: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)

    model_config = {"json_schema_extra": {"example": {"ok": True}}}


class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
    detail: str | None = None


@app.exception_handler(RequestValidationError)
async def request_validation_error(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Keep FastAPI request failures aligned with the Vercel envelope."""
    return JSONResponse(status_code=422, content=validation_error_payload(exc))


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


class RoutesResponse(BaseModel):
    routes: list[str]


class DevFixture(BaseModel):
    case_id: str
    query: str


class DevFixturesResponse(BaseModel):
    source_path: str
    fixtures: list[DevFixture] = Field(default_factory=list)


class SeasonFreshnessResponse(BaseModel):
    season: str
    season_type: str
    status: str
    current_through: str | None = None
    raw_complete: bool = False
    processed_complete: bool = False
    loaded_at: str | None = None
    validation_state: str = "unknown"
    generation_id: str | None = None
    validation_errors: list[str] = Field(default_factory=list)


class FreshnessResponse(BaseModel):
    """Structured freshness status for the API / UI."""

    status: str
    current_through: str | None = None
    checked_at: str | None = None
    seasons: list[SeasonFreshnessResponse] = Field(default_factory=list)
    last_refresh_ok: bool | None = None
    last_refresh_at: str | None = None
    last_refresh_error: str | None = None


class ReadinessResponse(BaseModel):
    """Fail-closed deployment readiness response."""

    ready: bool
    status: str
    checked_at: str
    season: str
    season_state: str
    max_active_lag_hours: int
    active_generation: str
    immutable_generation: bool
    release_exception_owner: str
    slices: list[dict[str, Any]] = Field(default_factory=list)
    blockers: list[dict[str, str]] = Field(default_factory=list)
    exception: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _query_result_to_response(qr: QueryResult) -> QueryResponse:
    """Convert a QueryResult envelope into a JSON-friendly response."""
    return QueryResponse(**query_result_to_payload(qr))


def _load_ui_html() -> str:
    """Return bundled UI HTML when present, else a minimal fallback shell."""
    return api_ui.load_ui_html(_UI_INDEX)


def _truthy_env(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _is_deployed_env(env: dict[str, str] | None = None) -> bool:
    values = os.environ if env is None else env
    if values.get("VERCEL") or values.get("VERCEL_ENV"):
        return True
    return values.get("ENVIRONMENT", "").strip().lower() in {"preview", "production", "prod"}


def _require_admin_feedback(request: Request) -> JSONResponse | None:
    if not _truthy_env(os.environ.get(ADMIN_FEEDBACK_ENABLED_ENV)):
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": "admin_feedback_disabled", "detail": None},
        )

    configured_token = os.environ.get(ADMIN_TOKEN_ENV, "").strip()
    if not configured_token:
        if _is_deployed_env():
            return JSONResponse(
                status_code=403,
                content={
                    "ok": False,
                    "error": "admin_token_not_configured",
                    "detail": "NBATOOLS_ADMIN_TOKEN is required for deployed admin feedback.",
                },
            )
        return None

    supplied_token = request.headers.get("X-NBATools-Admin-Token", "")
    if supplied_token != configured_token:
        return JSONResponse(
            status_code=401,
            content={"ok": False, "error": "admin_token_required", "detail": None},
        )
    return None


def _feedback_filters_from_request(request: Request) -> FeedbackReviewFilters:
    params = request.query_params
    limit_text = params.get("limit")
    limit = int(limit_text) if limit_text and limit_text.isdigit() else None
    return FeedbackReviewFilters(
        since=parse_datetime_filter(params.get("since"), is_until=False),
        until=parse_datetime_filter(params.get("until"), is_until=True),
        sources=parse_multi_filter(params.getlist("feedback_source") + params.getlist("source")),
        feedback_types=parse_multi_filter(params.getlist("feedback_type")),
        statuses=parse_multi_filter(params.getlist("status")),
        routes=parse_multi_filter(params.getlist("route")),
        reasons=parse_multi_filter(params.getlist("reason")),
        review_statuses=parse_multi_filter(params.getlist("review_status")),
        triage_decisions=parse_multi_filter(params.getlist("triage_decision")),
        include_smoke=_truthy_env(params.get("include_smoke")),
        limit=limit,
    )


def _feedback_review_error_response(exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": "feedback_review_error", "detail": str(exc)},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def ui() -> HTMLResponse:
    """Serve the single-page query UI (Vite build)."""
    return HTMLResponse(content=_load_ui_html())


@app.get("/review", response_class=HTMLResponse, include_in_schema=False)
@app.get("/visual-qa", response_class=HTMLResponse, include_in_schema=False)
@app.get("/admin/feedback", response_class=HTMLResponse, include_in_schema=False)
def internal_ui() -> HTMLResponse:
    """Serve internal UI shells."""
    return HTMLResponse(content=_load_ui_html())


@app.get(_UI_FALLBACK_ASSET, include_in_schema=False)
def ui_fallback_asset() -> Response:
    """Serve a minimal JS module when the frontend bundle is unavailable."""
    return Response(content=_UI_FALLBACK_SCRIPT, media_type="application/javascript")


# Mount Vite static assets (JS/CSS bundles) *after* explicit routes so
# they take priority over the catch-all static mount.
if _UI_DIR.is_dir():
    _assets = _UI_DIR / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="ui-assets")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Lightweight health / status check."""
    return HealthResponse(status="ok", version=__version__)


@app.get("/freshness", response_model=FreshnessResponse)
def freshness() -> FreshnessResponse:
    """Return structured data freshness status.

    Reports current_through, manifest state, per-season freshness
    classification (fresh / stale / unknown / failed), and last
    refresh outcome.
    """
    info = build_freshness_info()
    return FreshnessResponse(**info.to_dict())


@app.get("/readiness", response_model=ReadinessResponse)
def readiness() -> JSONResponse:
    """Return release readiness; non-ready states use HTTP 503."""
    info = build_readiness_info()
    return JSONResponse(status_code=200 if info.ready else 503, content=info.to_dict())


@app.get("/routes", response_model=RoutesResponse)
def routes() -> RoutesResponse:
    """List all supported structured query routes."""
    return RoutesResponse(routes=sorted(VALID_ROUTES))


@app.get("/api/dev/fixtures", response_model=DevFixturesResponse)
def dev_fixtures() -> DevFixturesResponse:
    """Return parser example fixtures for the internal review page."""
    return DevFixturesResponse(**dev_fixtures_payload())


@app.post("/query", response_model=QueryResponse)
def natural_query(body: NaturalQueryRequest, request: Request) -> QueryResponse:
    """Execute a natural-language NBA query.

    Calls ``execute_natural_query`` from the query service and returns
    the structured result as JSON.
    """
    start_time = time.monotonic()
    qr = execute_natural_query(body.query)
    payload = query_result_to_payload(qr)
    maybe_log_query_diagnostic(
        payload,
        elapsed_ms=elapsed_ms_since(start_time),
        source_page=request.headers.get("X-NBATools-Source-Page"),
    )
    return QueryResponse(**payload)


@app.post("/query-feedback")
def query_feedback(body: dict[str, Any], request: Request) -> JSONResponse:
    """Accept user-submitted or automatic query feedback."""
    status, payload = handle_feedback_submission(
        body,
        source_page=request.headers.get("X-NBATools-Source-Page"),
    )
    return JSONResponse(status_code=status, content=payload)


@app.get("/api/admin/feedback/groups")
def admin_feedback_groups(request: Request) -> JSONResponse:
    """List grouped immutable feedback with mutable triage overlays joined."""
    if response := _require_admin_feedback(request):
        return response
    try:
        payload = list_feedback_groups(filters=_feedback_filters_from_request(request))
    except ValueError as exc:
        return JSONResponse(
            status_code=422,
            content={"ok": False, "error": "validation_error", "detail": str(exc)},
        )
    except FeedbackReviewError as exc:
        return _feedback_review_error_response(exc)
    return JSONResponse(content=payload)


@app.get("/api/admin/feedback/groups/{group_id}")
def admin_feedback_group_detail(group_id: str, request: Request) -> JSONResponse:
    """Return one feedback group with normalized source records."""
    if response := _require_admin_feedback(request):
        return response
    try:
        payload = get_feedback_group_detail(
            group_id,
            filters=_feedback_filters_from_request(request),
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=422,
            content={"ok": False, "error": "validation_error", "detail": str(exc)},
        )
    except FeedbackReviewError as exc:
        return _feedback_review_error_response(exc)
    if payload is None:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": "feedback_group_not_found", "detail": group_id},
        )
    return JSONResponse(content=payload)


@app.get("/api/admin/feedback/groups/{group_id}/triage")
def admin_feedback_group_triage(group_id: str, request: Request) -> JSONResponse:
    """Return the mutable triage overlay for one feedback group."""
    if response := _require_admin_feedback(request):
        return response
    try:
        overlay = read_triage_overlay(group_id)
    except FeedbackReviewError as exc:
        return _feedback_review_error_response(exc)
    return JSONResponse(content={"ok": True, "triage_overlay": overlay})


@app.put("/api/admin/feedback/groups/{group_id}/triage")
def admin_feedback_group_triage_update(
    group_id: str,
    body: dict[str, Any],
    request: Request,
) -> JSONResponse:
    """Save the mutable triage overlay for one feedback group."""
    if response := _require_admin_feedback(request):
        return response
    try:
        detail = get_feedback_group_detail(
            group_id,
            filters=_feedback_filters_from_request(request),
        )
        if detail is None:
            return JSONResponse(
                status_code=404,
                content={"ok": False, "error": "feedback_group_not_found", "detail": group_id},
            )
        overlay = write_triage_overlay(group_id, body, existing_group=detail["group"])
    except TriageOverlayValidationError as exc:
        return JSONResponse(
            status_code=422,
            content={"ok": False, "error": "validation_error", "detail": str(exc)},
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=422,
            content={"ok": False, "error": "validation_error", "detail": str(exc)},
        )
    except FeedbackReviewError as exc:
        return _feedback_review_error_response(exc)
    return JSONResponse(content={"ok": True, "triage_overlay": overlay})


@app.post("/structured-query", response_model=QueryResponse)
def structured_query(body: StructuredQueryRequest) -> QueryResponse:
    """Execute a structured (route-based) query.

    Calls ``execute_structured_query`` from the query service and returns
    the structured result as JSON.
    """
    qr = execute_structured_query(body.route, **body.kwargs)
    return _query_result_to_response(qr)
