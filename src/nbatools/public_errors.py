"""Privacy-safe public error envelopes and request correlation."""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from uuid import uuid4

REQUEST_ID_HEADER = "X-Request-ID"
PUBLIC_INTERNAL_ERROR_CODE = "internal_error"
PUBLIC_INTERNAL_ERROR_DETAIL = "The request could not be completed. Try again later."
PUBLIC_METHOD_NOT_ALLOWED_CODE = "method_not_allowed"
PUBLIC_METHOD_NOT_ALLOWED_DETAIL = "The requested method is not allowed for this endpoint."

_SAFE_LABEL = re.compile(r"^[a-zA-Z0-9_./{}:-]{1,120}$")
_LOGGER = logging.getLogger("nbatools.public_errors")


def new_request_id() -> str:
    """Return an opaque server-generated correlation ID."""
    return f"req_{uuid4().hex}"


def public_error_payload(
    request_id: str,
    *,
    error: str = PUBLIC_INTERNAL_ERROR_CODE,
    detail: str = PUBLIC_INTERNAL_ERROR_DETAIL,
) -> dict[str, Any]:
    """Build the stable client-safe envelope for an unexpected failure."""
    return {
        "ok": False,
        "error": error,
        "detail": detail,
        "request_id": request_id,
    }


def log_public_error(
    *,
    request_id: str,
    endpoint: str,
    status: int,
    error: str,
    exc: Exception,
) -> None:
    """Emit allowlisted correlation metadata without exception or request text."""
    event = {
        "event": "public_request_error",
        "request_id": request_id,
        "endpoint": _safe_label(endpoint),
        "status": int(status),
        "error": _safe_label(error),
        "exception_type": type(exc).__name__,
    }
    _LOGGER.error(json.dumps(event, sort_keys=True, separators=(",", ":")))


def _safe_label(value: str) -> str:
    cleaned = str(value or "").strip()
    return cleaned if _SAFE_LABEL.fullmatch(cleaned) else "unknown"
