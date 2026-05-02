"""Vercel function for GET /routes."""

from __future__ import annotations

from nbatools.vercel_functions import routes_response
from nbatools.vercel_http import JsonHandler


class handler(JsonHandler):
    """Return supported structured routes."""

    def do_GET(self) -> None:
        status, payload = routes_response()
        self.send_json(payload, status=status)

    def do_POST(self) -> None:
        self.method_not_allowed("GET, OPTIONS")
