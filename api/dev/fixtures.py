"""Vercel function for GET /api/dev/fixtures."""

from __future__ import annotations

from nbatools.vercel_functions import dev_fixtures_response
from nbatools.vercel_http import JsonHandler


class handler(JsonHandler):
    """Return parser example fixtures for the internal review UI."""

    def do_GET(self) -> None:
        status, payload = dev_fixtures_response()
        self.send_json(payload, status=status)

    def do_POST(self) -> None:
        self.method_not_allowed("GET, OPTIONS")
