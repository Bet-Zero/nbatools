"""Vercel function for built UI assets."""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

from nbatools.vercel_functions import ui_asset_response
from nbatools.vercel_http import JsonHandler


class handler(JsonHandler):
    """Serve Vite-built UI assets from the generated dist bundle."""

    def do_GET(self) -> None:
        asset_path = _asset_path_from_request(self.path)
        status, content, content_type = ui_asset_response(asset_path)
        self.send_bytes(content, content_type=content_type, status=status)

    def do_POST(self) -> None:
        self.method_not_allowed("GET, OPTIONS")


def _asset_path_from_request(path: str) -> str:
    parsed = urlparse(path)
    params = parse_qs(parsed.query)
    raw = params.get("path", [""])[0]
    if raw:
        return unquote(raw)

    request_path = unquote(parsed.path)
    if request_path.startswith("/assets/"):
        return "assets/" + request_path.removeprefix("/assets/")
    return request_path.lstrip("/")
