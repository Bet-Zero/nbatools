"""Vercel function for POST /query-feedback."""

from __future__ import annotations

from nbatools.admission_control import AdmissionRejected
from nbatools.vercel_functions import query_feedback_response
from nbatools.vercel_http import JsonHandler


class handler(JsonHandler):
    """Persist query feedback and diagnostics."""

    def do_GET(self) -> None:
        self.method_not_allowed("POST, OPTIONS")

    def do_POST(self) -> None:
        try:
            body = self.read_json_body("/query-feedback")
            status, payload = query_feedback_response(
                body,
                source_page=self.headers.get("X-NBATools-Source-Page"),
                idempotency_key=self.headers.get("X-NBATools-Idempotency-Key"),
                client_id=self.client_identifier(),
            )
        except AdmissionRejected as exc:
            self.send_json(exc.payload(), status=exc.status, headers=exc.headers())
            return
        except ValueError as exc:
            self.send_api_error(422, "validation_error", str(exc))
            return
        except Exception as exc:
            self.send_api_error(500, "feedback_error", str(exc))
            return
        self.send_json(payload, status=status)
