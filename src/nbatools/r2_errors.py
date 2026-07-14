"""Shared classification and formatting for S3-compatible R2 client errors."""

from __future__ import annotations

from typing import Any


def client_error_code_and_status(exc: Exception) -> tuple[str | None, int | None]:
    """Extract provider error code and HTTP status when available."""
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return None, None
    error: dict[str, Any] = response.get("Error") or {}
    metadata: dict[str, Any] = response.get("ResponseMetadata") or {}
    code = str(error.get("Code")) if error.get("Code") is not None else None
    status = metadata.get("HTTPStatusCode")
    return code, int(status) if status is not None else None


def is_not_found(exc: Exception) -> bool:
    """Return whether an R2/S3 client error represents a missing object/bucket."""
    code, status = client_error_code_and_status(exc)
    return status == 404 or code in {"404", "NoSuchKey", "NotFound", "NoSuchBucket"}


def is_auth_error(exc: Exception) -> bool:
    """Return whether an R2/S3 client error represents denied authentication."""
    code, status = client_error_code_and_status(exc)
    return status in {401, 403} or code in {"401", "403", "AccessDenied", "InvalidAccessKeyId"}


def is_precondition_failed(exc: Exception) -> bool:
    """Return whether an R2/S3 conditional write lost ownership."""
    code, status = client_error_code_and_status(exc)
    return status == 412 or code in {
        "412",
        "PreconditionFailed",
        "ConditionalRequestConflict",
    }


def format_client_error(exc: Exception) -> str:
    """Return stable provider detail without requiring botocore exception types."""
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        error = response.get("Error") or {}
        code = error.get("Code")
        message = error.get("Message")
        if code and message:
            return f"{code}: {message}"
        if code:
            return str(code)
    return f"{type(exc).__name__}: {exc}"
