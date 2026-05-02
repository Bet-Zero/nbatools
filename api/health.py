"""Vercel function for GET /health."""

from __future__ import annotations

from nbatools.vercel_functions import health_response
from nbatools.vercel_http import JsonHandler


class handler(JsonHandler):
    """Return API health status."""

    def do_GET(self) -> None:
        status, payload = health_response()
        self.send_json(payload, status=status)

    def do_POST(self) -> None:
        self.method_not_allowed("GET, OPTIONS")
