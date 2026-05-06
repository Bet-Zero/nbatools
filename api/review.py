"""Vercel function for the internal /review UI shell."""

from __future__ import annotations

from nbatools.vercel_functions import ui_response
from nbatools.vercel_http import JsonHandler


class handler(JsonHandler):
    """Serve the internal review UI route in Vercel preview."""

    def do_GET(self) -> None:
        status, content, content_type = ui_response()
        self.send_text(content, content_type=content_type, status=status)

    def do_POST(self) -> None:
        self.method_not_allowed("GET, OPTIONS")
