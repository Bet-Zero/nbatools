"""Vercel function for POST /structured-query."""

from __future__ import annotations

from nbatools.admission_control import AdmissionRejected
from nbatools.vercel_functions import structured_query_response
from nbatools.vercel_http import JsonHandler


class handler(JsonHandler):
    """Execute a structured NBA query route."""

    allowed_method = "POST"

    def do_GET(self) -> None:
        self.method_not_allowed("POST, OPTIONS")

    def do_POST(self) -> None:
        try:
            body = self.read_json_body("/structured-query")
            status, payload = structured_query_response(
                body,
                client_id=self.client_identifier(),
            )
        except AdmissionRejected as exc:
            self.send_json(exc.payload(), status=exc.status, headers=exc.headers())
            return
        except ValueError as exc:
            self.send_api_error(422, "validation_error", str(exc))
            return
        except Exception as exc:
            self.send_unexpected_error(exc, endpoint="/structured-query")
            return
        self.send_json(payload, status=status)
