"""Vercel function for GET /freshness."""

from __future__ import annotations

from nbatools.vercel_functions import freshness_response
from nbatools.vercel_http import JsonHandler


class handler(JsonHandler):
    """Return structured data freshness status."""

    def do_GET(self) -> None:
        try:
            status, payload = freshness_response()
        except Exception as exc:
            self.send_api_error(500, "freshness_error", str(exc))
            return
        self.send_json(payload, status=status)

    def do_POST(self) -> None:
        self.method_not_allowed("GET, OPTIONS")
