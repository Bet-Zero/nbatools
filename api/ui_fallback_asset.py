"""Vercel function for the fallback UI JavaScript asset."""

from __future__ import annotations

from nbatools.vercel_functions import ui_fallback_asset_response
from nbatools.vercel_http import JsonHandler


class handler(JsonHandler):
    """Serve fallback JavaScript when the bundled UI is unavailable."""

    def do_GET(self) -> None:
        status, content, content_type = ui_fallback_asset_response()
        self.send_text(content, content_type=content_type, status=status)

    def do_POST(self) -> None:
        self.method_not_allowed("GET, OPTIONS")
