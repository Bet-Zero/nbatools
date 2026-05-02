"""Shared API payload helpers for local FastAPI and Vercel handlers."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nbatools.query_service import QueryResult


try:
    _VERSION = version("nbatools")
except PackageNotFoundError:
    _VERSION = "0.7.0"


def query_result_to_payload(qr: QueryResult) -> dict[str, Any]:
    """Convert a QueryResult envelope into a JSON-friendly payload."""
    result_dict = qr.to_dict()

    notes: list[str] = getattr(qr.result, "notes", []) or []
    caveats: list[str] = getattr(qr.result, "caveats", []) or []

    return {
        "ok": qr.is_ok,
        "query": qr.query,
        "route": qr.route,
        "result_status": qr.result_status,
        "result_reason": qr.result_reason,
        "current_through": qr.current_through,
        "confidence": qr.metadata.get("confidence"),
        "intent": qr.metadata.get("intent"),
        "alternates": qr.metadata.get("alternates", []),
        "notes": notes,
        "caveats": caveats,
        "result": result_dict,
    }


def health_payload() -> dict[str, str]:
    """Return the health-check payload."""
    return {"status": "ok", "version": _VERSION}


def routes_payload() -> dict[str, list[str]]:
    """Return the supported structured routes payload."""
    from nbatools.query_service import VALID_ROUTES

    return {"routes": sorted(VALID_ROUTES)}


def freshness_payload() -> dict[str, Any]:
    """Return the structured freshness payload."""
    from nbatools.commands.freshness import build_freshness_info

    return build_freshness_info().to_dict()


def natural_query_payload(query: str) -> dict[str, Any]:
    """Execute a natural query and return the API payload."""
    from nbatools.query_service import execute_natural_query

    return query_result_to_payload(execute_natural_query(query))


def structured_query_payload(route: str, kwargs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a structured query and return the API payload."""
    from nbatools.query_service import execute_structured_query

    kwargs = kwargs or {}
    return query_result_to_payload(execute_structured_query(route, **kwargs))
