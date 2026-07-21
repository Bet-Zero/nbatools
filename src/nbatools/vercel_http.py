"""Small HTTP helpers for Vercel Python function handlers."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any

from nbatools.admission_control import parse_and_validate_json_body
from nbatools.public_errors import (
    PUBLIC_INTERNAL_ERROR_CODE,
    PUBLIC_INTERNAL_ERROR_DETAIL,
    REQUEST_ID_HEADER,
    log_public_error,
    new_request_id,
)


class JsonHandler(BaseHTTPRequestHandler):
    """Base handler with JSON/text response helpers and CORS headers."""

    server_version = "nbatools-vercel"

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

    def send_json(
        self,
        payload: dict[str, Any],
        status: int = HTTPStatus.OK,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        response_payload = dict(payload)
        if response_payload.get("ok") is False:
            response_payload.setdefault("request_id", self.request_id)
        body = json.dumps(response_payload, separators=(",", ":"), default=str).encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header(REQUEST_ID_HEADER, self.request_id)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

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
    ) -> None:
        payload: dict[str, Any] = {"ok": False, "error": error}
        if detail:
            payload["detail"] = detail
        self.send_json(payload, status=status)

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

    def read_json_body(self, path: str | None = None) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid Content-Length header") from exc
        if length <= 0:
            raise ValueError("Request body must be a JSON object")

        raw_body = self.rfile.read(length)
        if path is not None:
            return parse_and_validate_json_body(raw_body, path)
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON") from exc
        if not isinstance(body, dict):
            raise ValueError("Request body must be a JSON object")
        return body

    def client_identifier(self) -> str:
        from nbatools.admission_control import client_identifier

        fallback = self.client_address[0] if self.client_address else None
        return client_identifier(self.headers, fallback)

    def method_not_allowed(self, allowed: str) -> None:
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self._send_cors_headers()
        self.send_header("Allow", allowed)
        self.send_header(REQUEST_ID_HEADER, self.request_id)
        self.end_headers()

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Expose-Headers", REQUEST_ID_HEADER)
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, X-NBATools-Source-Page, X-NBATools-Idempotency-Key",
        )
