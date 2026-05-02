"""Small HTTP helpers for Vercel Python function handlers."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any


class JsonHandler(BaseHTTPRequestHandler):
    """Base handler with JSON/text response helpers and CORS headers."""

    server_version = "nbatools-vercel"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def send_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
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

    def read_json_body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid Content-Length header") from exc
        if length <= 0:
            raise ValueError("Request body must be a JSON object")

        raw_body = self.rfile.read(length)
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON") from exc
        if not isinstance(body, dict):
            raise ValueError("Request body must be a JSON object")
        return body

    def method_not_allowed(self, allowed: str) -> None:
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self._send_cors_headers()
        self.send_header("Allow", allowed)
        self.end_headers()

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
