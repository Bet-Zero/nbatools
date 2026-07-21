"""Vercel function for the root UI shell route."""

from __future__ import annotations

from nbatools.vercel_functions import ui_response
from nbatools.vercel_http import JsonHandler


class handler(JsonHandler):
    """Serve the local fallback UI shell in Vercel preview."""

    allowed_method = "GET"

    def do_GET(self) -> None:
        try:
            status, content, content_type = ui_response()
        except Exception as exc:
            self.send_unexpected_error(exc, endpoint="/")
            return
        self.send_text(content, content_type=content_type, status=status)

    def do_POST(self) -> None:
        self.method_not_allowed("GET, OPTIONS")
