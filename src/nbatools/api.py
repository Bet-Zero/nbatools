"""Thin local HTTP API layer over the nbatools query service.

This module exposes the structured query engine through a small FastAPI
application so that a future UI or any HTTP client can call the engine
directly without going through the CLI.

Run locally with::

    uvicorn nbatools.api:app --reload
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from nbatools import __version__
from nbatools.query_service import (
    VALID_ROUTES,
    QueryResult,
    execute_natural_query,
    execute_structured_query,
)

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

# Path to the bundled single-page UI.
_UI_DIR = Path(__file__).resolve().parent / "ui"

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class NaturalQueryRequest(BaseModel):
    query: str = Field(..., description="Natural-language NBA query text.")


class StructuredQueryRequest(BaseModel):
    route: str = Field(..., description="Named route (e.g. 'player_game_summary').")
    kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="Keyword arguments forwarded to the route's build_result function.",
    )


class QueryResponse(BaseModel):
    """Envelope returned by both query endpoints."""

    ok: bool
    query: str
    route: str | None = None
    result_status: str
    result_reason: str | None = None
    current_through: str | None = None
    notes: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)

    model_config = {"json_schema_extra": {"example": {"ok": True}}}


class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


class RoutesResponse(BaseModel):
    routes: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _query_result_to_response(qr: QueryResult) -> QueryResponse:
    """Convert a QueryResult envelope into a JSON-friendly response."""
    result_dict = qr.result.to_dict() if hasattr(qr.result, "to_dict") else {}

    notes: list[str] = getattr(qr.result, "notes", []) or []
    caveats: list[str] = getattr(qr.result, "caveats", []) or []

    return QueryResponse(
        ok=qr.is_ok,
        query=qr.query,
        route=qr.route,
        result_status=qr.result_status,
        result_reason=qr.result_reason,
        current_through=qr.current_through,
        notes=notes,
        caveats=caveats,
        result=result_dict,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def ui() -> HTMLResponse:
    """Serve the single-page query UI."""
    html = (_UI_DIR / "index.html").read_text()
    return HTMLResponse(content=html)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Lightweight health / status check."""
    return HealthResponse(status="ok", version=__version__)


@app.get("/routes", response_model=RoutesResponse)
def routes() -> RoutesResponse:
    """List all supported structured query routes."""
    return RoutesResponse(routes=sorted(VALID_ROUTES))


@app.post("/query", response_model=QueryResponse)
def natural_query(body: NaturalQueryRequest) -> QueryResponse:
    """Execute a natural-language NBA query.

    Calls ``execute_natural_query`` from the query service and returns
    the structured result as JSON.
    """
    qr = execute_natural_query(body.query)
    return _query_result_to_response(qr)


@app.post("/structured-query", response_model=QueryResponse)
def structured_query(body: StructuredQueryRequest) -> QueryResponse | JSONResponse:
    """Execute a structured (route-based) query.

    Calls ``execute_structured_query`` from the query service and returns
    the structured result as JSON.
    """
    try:
        qr = execute_structured_query(body.route, **body.kwargs)
    except ValueError as exc:
        return JSONResponse(
            content={"ok": False, "error": "invalid_route", "detail": str(exc)},
        )
    return _query_result_to_response(qr)
