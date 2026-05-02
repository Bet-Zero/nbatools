"""Vercel function for POST /query."""

from __future__ import annotations

from nbatools.vercel_functions import query_response
from nbatools.vercel_http import JsonHandler


class handler(JsonHandler):
    """Execute a natural-language NBA query."""

    def do_GET(self) -> None:
        self.method_not_allowed("POST, OPTIONS")

    def do_POST(self) -> None:
        try:
            body = self.read_json_body()
            status, payload = query_response(body)
        except ValueError as exc:
            self.send_api_error(422, "validation_error", str(exc))
            return
        except Exception as exc:
            self.send_api_error(500, "query_error", str(exc))
            return
        self.send_json(payload, status=status)
