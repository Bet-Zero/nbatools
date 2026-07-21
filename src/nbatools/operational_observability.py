"""Privacy-safe operational events for public HTTP request monitoring."""

from __future__ import annotations

import json
import logging
import resource
import sys
from typing import Any
from urllib.parse import urlsplit

from nbatools.dataframe_cache import frame_cache_info

PUBLIC_OBSERVED_ENDPOINTS = frozenset(
    {
        "/health",
        "/freshness",
        "/readiness",
        "/query",
        "/structured-query",
        "/query-feedback",
    }
)

_LOGGER = logging.getLogger("nbatools.operational")
_LOGGER.setLevel(logging.INFO)
_OUTCOME_FIELDS = (
    "result_status",
    "result_reason",
    "route",
    "data_status",
    "current_through",
    "season_state",
    "active_generation",
    "ready",
)


def normalize_endpoint(value: str) -> str:
    """Return an allowlisted public endpoint without query-string data."""
    path = urlsplit(str(value or "")).path
    return path if path in PUBLIC_OBSERVED_ENDPOINTS else "unknown"


def extract_request_outcome(endpoint: str, payload: Any) -> dict[str, Any]:
    """Extract only explicitly approved status fields from a response payload."""
    normalized = normalize_endpoint(endpoint)
    if normalized == "unknown" or not isinstance(payload, dict):
        return {}

    outcome: dict[str, Any] = {}
    if normalized in {"/query", "/structured-query"}:
        for key in ("result_status", "result_reason", "route"):
            value = _safe_label(payload.get(key))
            if value is not None:
                outcome[key] = value
    elif normalized == "/freshness":
        status = _safe_label(payload.get("status"))
        current_through = _safe_label(payload.get("current_through"))
        if status is not None:
            outcome["data_status"] = status
        if current_through is not None:
            outcome["current_through"] = current_through
    elif normalized == "/readiness":
        for source, target in (
            ("status", "data_status"),
            ("season_state", "season_state"),
            ("active_generation", "active_generation"),
        ):
            value = _safe_label(payload.get(source))
            if value is not None:
                outcome[target] = value
        if isinstance(payload.get("ready"), bool):
            outcome["ready"] = payload["ready"]
        blockers = payload.get("blockers")
        if isinstance(blockers, list):
            codes = [
                value
                for blocker in blockers[:10]
                if isinstance(blocker, dict)
                if (value := _safe_label(blocker.get("code"))) is not None
            ]
            if codes:
                outcome["blocker_codes"] = codes
    return outcome


def log_request_complete(
    *,
    request_id: str,
    endpoint: str,
    method: str,
    status: int,
    duration_ms: float,
    outcome: dict[str, Any] | None = None,
) -> None:
    """Emit one bounded operational event and never affect the response path."""
    normalized = normalize_endpoint(endpoint)
    if normalized == "unknown":
        return

    cache = frame_cache_info()
    event: dict[str, Any] = {
        "event": "public_request_complete",
        "request_id": str(request_id),
        "endpoint": normalized,
        "method": _safe_method(method),
        "status": int(status),
        "status_class": f"{max(0, int(status)) // 100}xx",
        "duration_ms": round(max(0.0, float(duration_ms)), 3),
        "rss_peak_mb": _rss_peak_mb(),
        "cache_hits": cache.hits,
        "cache_misses": cache.misses,
        "cache_entries": cache.current_entries,
        "cache_bytes": cache.current_bytes,
        "cache_evictions": cache.evictions,
    }
    for key in _OUTCOME_FIELDS:
        if outcome is not None and key in outcome:
            event[key] = outcome[key]
    if outcome is not None and "blocker_codes" in outcome:
        event["blocker_codes"] = list(outcome["blocker_codes"][:10])

    try:
        _LOGGER.info(json.dumps(event, sort_keys=True, separators=(",", ":")))
    except Exception:
        # Monitoring must never change the public response path.
        return


def _safe_label(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 120:
        return None
    if not all(character.isalnum() or character in "_./:-" for character in cleaned):
        return None
    return cleaned


def _safe_method(value: str) -> str:
    cleaned = str(value or "").strip().upper()
    return cleaned if cleaned in {"GET", "POST", "OPTIONS"} else "UNKNOWN"


def _rss_peak_mb() -> float:
    raw = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    return round(raw / divisor, 3)
