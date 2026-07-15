"""Vercel function for the preview-only /visual-qa UI shell."""

from __future__ import annotations

from nbatools.vercel_functions import visual_qa_response
from nbatools.vercel_http import JsonHandler


class handler(JsonHandler):
    """Serve visual QA in preview and return 404 in production."""

    def do_GET(self) -> None:
        status, content, content_type = visual_qa_response()
        if isinstance(content, dict):
            self.send_json(content, status=status)
            return
        self.send_text(content, content_type=content_type, status=status)

    def do_POST(self) -> None:
        self.method_not_allowed("GET, OPTIONS")
