"""Small HTTP helpers for Vercel Python function handlers."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from time import monotonic, perf_counter
from typing import Any

from nbatools.admission_control import (
    BODY_LIMITS,
    parse_and_validate_json_body,
    query_timeout,
    validate_body_size,
)
from nbatools.operational_observability import (
    extract_request_outcome,
    log_request_complete,
    normalize_endpoint,
)
from nbatools.public_errors import (
    PUBLIC_INTERNAL_ERROR_CODE,
    PUBLIC_INTERNAL_ERROR_DETAIL,
    PUBLIC_METHOD_NOT_ALLOWED_CODE,
    PUBLIC_METHOD_NOT_ALLOWED_DETAIL,
    REQUEST_ID_HEADER,
    log_public_error,
    new_request_id,
)

# Provisional application budget pending effective host qualification. Start at
# native handler entry. Leave 3 s outside the handler against the declared 20 s
# (retained cold sample: 2.647 s outside the handler), plus 0.5 s for the reply.
NATIVE_QUERY_RESPONSE_SECONDS = 17.0
NATIVE_QUERY_REPLY_RESERVE_SECONDS = 0.5


class JsonHandler(BaseHTTPRequestHandler):
    """Base handler with JSON/text response helpers and CORS headers."""

    server_version = "nbatools-vercel"
    allowed_method: str | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._nbatools_request_started_at = perf_counter()
        self._request_started_at = monotonic()
        super().__init__(*args, **kwargs)

    @property
    def request_id(self) -> str:
        value = getattr(self, "_nbatools_request_id", None)
        if value is None:
            value = new_request_id()
            self._nbatools_request_id = value
        return value

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.send_header(REQUEST_ID_HEADER, self.request_id)
        self.end_headers()

    def query_work_deadline(self) -> float:
        return self.query_response_deadline() - NATIVE_QUERY_REPLY_RESERVE_SECONDS

    def query_response_deadline(self) -> float:
        return self._request_started_at + NATIVE_QUERY_RESPONSE_SECONDS

    def send_json(
        self,
        payload: dict[str, Any],
        status: int = HTTPStatus.OK,
        *,
        headers: dict[str, str] | None = None,
        deadline: float | None = None,
    ) -> None:
        response_payload = dict(payload)
        if response_payload.get("ok") is False:
            response_payload.setdefault("request_id", self.request_id)
        body = json.dumps(response_payload, separators=(",", ":"), default=str).encode("utf-8")
        if deadline is not None:
            now = monotonic()
            if now >= deadline:
                # Headers are still unsent. Try to deliver a small typed error
                # within the host allowance if setup or encoding used the budget.
                if status < HTTPStatus.BAD_REQUEST:
                    rejected = query_timeout()
                    return self.send_json(
                        rejected.payload(),
                        status=rejected.status,
                        deadline=now + NATIVE_QUERY_REPLY_RESERVE_SECONDS,
                    )
                deadline = now + NATIVE_QUERY_REPLY_RESERVE_SECONDS
            self.connection.settimeout(deadline - now)
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header(REQUEST_ID_HEADER, self.request_id)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if getattr(self, "command", "") != "HEAD":
            if deadline is not None:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise TimeoutError("Query response deadline expired after headers")
                self.connection.settimeout(remaining)
            self.wfile.write(body)
        endpoint = normalize_endpoint(getattr(self, "path", ""))
        log_request_complete(
            request_id=self.request_id,
            endpoint=endpoint,
            method=getattr(self, "command", ""),
            status=status,
            duration_ms=(
                perf_counter() - getattr(self, "_nbatools_request_started_at", perf_counter())
            )
            * 1000,
            outcome=extract_request_outcome(endpoint, response_payload),
        )

    def send_text(
        self,
        content: str,
        *,
        content_type: str,
        status: int = HTTPStatus.OK,
    ) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header(REQUEST_ID_HEADER, self.request_id)
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(
        self,
        content: bytes,
        *,
        content_type: str,
        status: int = HTTPStatus.OK,
    ) -> None:
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header(REQUEST_ID_HEADER, self.request_id)
        self.end_headers()
        self.wfile.write(content)

    def send_api_error(
        self,
        status: int,
        error: str,
        detail: str | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"ok": False, "error": error}
        if detail:
            payload["detail"] = detail
        self.send_json(payload, status=status, headers=headers)

    def send_unexpected_error(
        self,
        exc: Exception,
        *,
        endpoint: str,
        status: int = HTTPStatus.INTERNAL_SERVER_ERROR,
    ) -> None:
        """Log safe correlation metadata and hide the internal exception."""
        log_public_error(
            request_id=self.request_id,
            endpoint=endpoint,
            status=status,
            error=PUBLIC_INTERNAL_ERROR_CODE,
            exc=exc,
        )
        self.send_api_error(
            status,
            PUBLIC_INTERNAL_ERROR_CODE,
            PUBLIC_INTERNAL_ERROR_DETAIL,
        )

    def read_json_body(self, path: str, *, deadline: float | None = None) -> dict[str, Any]:
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) > 1:
            raise ValueError("Expected a single Content-Length header")
        declared = lengths[0].strip() if lengths else ""
        if not declared:
            raise ValueError("Request body must be a JSON object")
        if not declared.isascii() or not declared.isdecimal():
            raise ValueError("Invalid Content-Length header")
        digits = declared.lstrip("0")
        if not digits:
            raise ValueError("Request body must be a JSON object")
        limit = BODY_LIMITS.get(path)
        if limit is None:
            raise ValueError(f"No body budget is defined for {path}")
        # Compare decimal width first so arbitrarily long digit strings never reach int().
        if len(digits) > len(str(limit)):
            validate_body_size(limit + 1, path)
        length = int(digits)
        validate_body_size(length, path)
        if deadline is None:
            raw_body = self.rfile.read(length)
        else:
            chunks = bytearray()
            try:
                while len(chunks) < length:
                    remaining = deadline - monotonic()
                    if remaining <= 0:
                        raise query_timeout()
                    self.connection.settimeout(remaining)
                    chunk = self.rfile.read1(length - len(chunks))
                    if not chunk:
                        break
                    chunks.extend(chunk)
            except TimeoutError as exc:
                raise query_timeout() from exc
            finally:
                # Return the socket to the server's normal mode for the reply,
                # including typed errors after a request body timed out.
                self.connection.settimeout(self.timeout)
            raw_body = bytes(chunks)
        validate_body_size(len(raw_body), path)
        if len(raw_body) != length:
            raise ValueError("Request body length does not match Content-Length")
        return parse_and_validate_json_body(raw_body, path)

    def client_identifier(self) -> str:
        from nbatools.admission_control import client_identifier

        fallback = self.client_address[0] if self.client_address else None
        return client_identifier(self.headers, fallback)

    def method_not_allowed(self, allowed: str | None = None) -> None:
        allowed_methods = allowed or self._allowed_methods()
        self.send_api_error(
            HTTPStatus.METHOD_NOT_ALLOWED,
            PUBLIC_METHOD_NOT_ALLOWED_CODE,
            PUBLIC_METHOD_NOT_ALLOWED_DETAIL,
            headers={"Allow": allowed_methods},
        )

    def _allowed_methods(self) -> str:
        if self.allowed_method is not None:
            return f"{self.allowed_method}, OPTIONS"
        return "GET, POST, OPTIONS"

    def do_HEAD(self) -> None:
        self.method_not_allowed()

    def do_PUT(self) -> None:
        self.method_not_allowed()

    def do_PATCH(self) -> None:
        self.method_not_allowed()

    def do_DELETE(self) -> None:
        self.method_not_allowed()

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Expose-Headers", REQUEST_ID_HEADER)
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, X-NBATools-Source-Page, X-NBATools-Idempotency-Key",
        )
