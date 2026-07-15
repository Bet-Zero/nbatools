"""Vercel function for GET /readiness."""

from __future__ import annotations

from nbatools.vercel_functions import readiness_response
from nbatools.vercel_http import JsonHandler


class handler(JsonHandler):
    """Return strict data and release readiness."""

    def do_GET(self) -> None:
        try:
            status, payload = readiness_response()
        except Exception as exc:
            self.send_api_error(503, "readiness_error", str(exc))
            return
        self.send_json(payload, status=status)

    def do_POST(self) -> None:
        self.method_not_allowed("GET, OPTIONS")
