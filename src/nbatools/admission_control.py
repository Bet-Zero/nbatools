"""Public request admission budgets shared by FastAPI and Vercel."""

from __future__ import annotations

import json
import math
import os
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable, Mapping
from concurrent.futures import (
    Future,
    ThreadPoolExecutor,
)
from concurrent.futures import (
    TimeoutError as FutureTimeout,
)
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, TypeVar

from nbatools.commands._seasons import LATEST_REGULAR_SEASON, season_to_int

NATURAL_QUERY_BODY_MAX_BYTES = 4 * 1024
STRUCTURED_QUERY_BODY_MAX_BYTES = 8 * 1024
QUERY_FEEDBACK_BODY_MAX_BYTES = 8 * 1024
MAX_JSON_DEPTH = 4
MAX_JSON_OBJECT_MEMBERS = 64
MAX_JSON_ARRAY_ELEMENTS = 20
MAX_RESOLVED_SEASONS = 30
MAX_CONCURRENT_QUERIES = 3
QUERY_REQUESTS_PER_MINUTE = 10
QUERY_RATE_WINDOW_SECONDS = 60
QUERY_EXECUTION_TIMEOUT_SECONDS = 20
FEEDBACK_SUBMISSIONS_PER_DAY = 20
FEEDBACK_RATE_WINDOW_SECONDS = 24 * 60 * 60

BODY_LIMITS = {
    "/query": NATURAL_QUERY_BODY_MAX_BYTES,
    "/structured-query": STRUCTURED_QUERY_BODY_MAX_BYTES,
    "/query-feedback": QUERY_FEEDBACK_BODY_MAX_BYTES,
}

T = TypeVar("T")


@dataclass(frozen=True)
class AdmissionRejected(Exception):
    """Structured public rejection with an optional retry delay."""

    status: int
    error: str
    detail: str
    retry_after: int | None = None

    def payload(self) -> dict[str, Any]:
        return {"ok": False, "error": self.error, "detail": self.detail}

    def headers(self) -> dict[str, str]:
        return {"Retry-After": str(self.retry_after)} if self.retry_after is not None else {}


def parse_and_validate_json_body(raw: bytes, path: str) -> dict[str, Any]:
    """Parse one endpoint body after enforcing its exact byte and JSON budgets."""
    limit = BODY_LIMITS.get(path)
    if limit is None:
        raise ValueError(f"No body budget is defined for {path}")
    if len(raw) > limit:
        raise AdmissionRejected(
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            "payload_too_large",
            f"Request body exceeds the {limit}-byte limit for {path}.",
        )
    if not raw:
        raise ValueError("Request body must be a JSON object")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Request body must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object")
    validate_json_budget(payload)
    validate_season_span(path, payload)
    return payload


def validate_json_budget(payload: Any) -> None:
    """Enforce aggregate JSON nesting, object-member, and array-element limits."""
    members = 0
    array_elements = 0

    def visit(value: Any, depth: int) -> None:
        nonlocal members, array_elements
        if isinstance(value, dict):
            if depth > MAX_JSON_DEPTH:
                _budget_error("JSON nesting exceeds the maximum depth of 4.")
            members += len(value)
            if members > MAX_JSON_OBJECT_MEMBERS:
                _budget_error("JSON objects exceed 64 total members.")
            for nested in value.values():
                visit(nested, depth + 1 if isinstance(nested, dict | list) else depth)
        elif isinstance(value, list):
            if depth > MAX_JSON_DEPTH:
                _budget_error("JSON nesting exceeds the maximum depth of 4.")
            array_elements += len(value)
            if array_elements > MAX_JSON_ARRAY_ELEMENTS:
                _budget_error("JSON arrays exceed 20 total elements.")
            for nested in value:
                visit(nested, depth + 1 if isinstance(nested, dict | list) else depth)

    # The root request object is depth zero. This keeps the documented depth-4
    # budget compatible with the existing feedback envelope, whose result rows
    # sit four container edges below that root.
    visit(payload, 0)


def validate_season_span(path: str, payload: Mapping[str, Any]) -> None:
    """Reject requests resolving more than the 30-season supported surface."""
    spans: list[int] = []
    if path == "/structured-query":
        kwargs = payload.get("kwargs")
        if isinstance(kwargs, dict):
            seasons = kwargs.get("seasons")
            if isinstance(seasons, list):
                spans.append(len(seasons))
            start = kwargs.get("start_season")
            end = kwargs.get("end_season")
            span = _season_range_size(start, end)
            if span is not None:
                spans.append(span)
    elif path == "/query":
        query = payload.get("query")
        if isinstance(query, str):
            span = _natural_query_season_span(query)
            if span is not None:
                spans.append(span)

    if spans and max(spans) > MAX_RESOLVED_SEASONS:
        raise AdmissionRejected(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "season_span_exceeded",
            "Request resolves more than the supported 30-season range.",
        )


def admission_controls_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Enable runtime quotas for deployed environments or an explicit override."""
    values = os.environ if env is None else env
    override = values.get("NBATOOLS_ADMISSION_CONTROLS", "").strip().lower()
    if override:
        return override in {"1", "true", "yes", "on"}
    return bool(values.get("VERCEL") or values.get("VERCEL_ENV")) or values.get(
        "ENVIRONMENT", ""
    ).strip().lower() in {"preview", "production", "prod"}


def client_identifier(
    headers: Mapping[str, str] | None,
    fallback: str | None,
) -> str:
    """Resolve the platform-provided client/IP key used by local limiters."""
    lowered = {str(key).lower(): str(value) for key, value in (headers or {}).items()}
    for key in ("x-vercel-forwarded-for", "x-real-ip", "x-forwarded-for"):
        value = lowered.get(key, "").split(",", 1)[0].strip()
        if value:
            return value[:128]
    return (fallback or "unknown-client")[:128]


class AdmissionController:
    """Thread-safe process-local rate, concurrency, timeout, and feedback quotas."""

    def __init__(
        self,
        *,
        max_concurrent_queries: int = MAX_CONCURRENT_QUERIES,
        query_limit: int = QUERY_REQUESTS_PER_MINUTE,
        query_window_seconds: float = QUERY_RATE_WINDOW_SECONDS,
        query_timeout_seconds: float = QUERY_EXECUTION_TIMEOUT_SECONDS,
        feedback_limit: int = FEEDBACK_SUBMISSIONS_PER_DAY,
        feedback_window_seconds: float = FEEDBACK_RATE_WINDOW_SECONDS,
    ) -> None:
        self.max_concurrent_queries = max_concurrent_queries
        self.query_limit = query_limit
        self.query_window_seconds = query_window_seconds
        self.query_timeout_seconds = query_timeout_seconds
        self.feedback_limit = feedback_limit
        self.feedback_window_seconds = feedback_window_seconds
        self._lock = threading.Lock()
        self._active_queries = 0
        self._query_events: dict[str, deque[float]] = defaultdict(deque)
        self._feedback_events: dict[str, deque[tuple[float, str]]] = defaultdict(deque)
        self._executor = ThreadPoolExecutor(
            max_workers=max_concurrent_queries,
            thread_name_prefix="nbatools-query",
        )

    def run_query(
        self,
        client_id: str,
        callback: Callable[[], T],
        *,
        now: float | None = None,
    ) -> T:
        """Admit and execute one natural/structured query under shared budgets."""
        admitted_at = time.monotonic() if now is None else now
        with self._lock:
            events = self._query_events[client_id]
            _prune_timestamps(events, admitted_at - self.query_window_seconds)
            if len(events) >= self.query_limit:
                retry = max(1, math.ceil(events[0] + self.query_window_seconds - admitted_at))
                raise AdmissionRejected(
                    HTTPStatus.TOO_MANY_REQUESTS,
                    "rate_limited",
                    "Query request limit exceeded. Retry after the indicated delay.",
                    retry,
                )
            if self._active_queries >= self.max_concurrent_queries:
                raise AdmissionRejected(
                    HTTPStatus.TOO_MANY_REQUESTS,
                    "concurrency_limited",
                    "All query execution slots are in use.",
                    1,
                )
            events.append(admitted_at)
            self._active_queries += 1

        try:
            future = self._executor.submit(callback)
        except Exception:
            self._release_query()
            raise
        future.add_done_callback(self._query_finished)
        try:
            return future.result(timeout=self.query_timeout_seconds)
        except FutureTimeout as exc:
            future.cancel()
            raise AdmissionRejected(
                HTTPStatus.GATEWAY_TIMEOUT,
                "execution_timeout",
                "Query execution exceeded the 20-second response budget.",
            ) from exc

    def reserve_feedback(
        self,
        client_id: str,
        *,
        now: float | None = None,
    ) -> FeedbackReservation:
        """Reserve one rolling-24-hour accepted-feedback slot."""
        admitted_at = time.time() if now is None else now
        token = uuid.uuid4().hex
        with self._lock:
            events = self._feedback_events[client_id]
            cutoff = admitted_at - self.feedback_window_seconds
            while events and events[0][0] <= cutoff:
                events.popleft()
            if len(events) >= self.feedback_limit:
                retry = max(1, math.ceil(events[0][0] + self.feedback_window_seconds - admitted_at))
                raise AdmissionRejected(
                    HTTPStatus.TOO_MANY_REQUESTS,
                    "feedback_rate_limited",
                    "Feedback submission limit exceeded. Retry after the indicated delay.",
                    retry,
                )
            events.append((admitted_at, token))
        return FeedbackReservation(self, client_id, token)

    def feedback_count(self, client_id: str) -> int:
        with self._lock:
            return len(self._feedback_events.get(client_id, ()))

    def _query_finished(self, _future: Future[Any]) -> None:
        self._release_query()

    def _release_query(self) -> None:
        with self._lock:
            self._active_queries = max(0, self._active_queries - 1)

    def _rollback_feedback(self, client_id: str, token: str) -> None:
        with self._lock:
            events = self._feedback_events.get(client_id)
            if not events:
                return
            retained = deque(item for item in events if item[1] != token)
            if retained:
                self._feedback_events[client_id] = retained
            else:
                self._feedback_events.pop(client_id, None)


class FeedbackReservation:
    """Feedback quota reservation committed only for a new stored record."""

    def __init__(self, controller: AdmissionController, client_id: str, token: str) -> None:
        self._controller = controller
        self._client_id = client_id
        self._token = token
        self._committed = False

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        if not self._committed:
            self._controller._rollback_feedback(self._client_id, self._token)
            self._committed = True


ADMISSION_CONTROLLER = AdmissionController()


class RequestBodyBudgetMiddleware:
    """ASGI pre-parser enforcing whole-body and structural JSON budgets."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        path = scope.get("path", "")
        if scope.get("type") != "http" or scope.get("method") != "POST" or path not in BODY_LIMITS:
            await self.app(scope, receive, send)
            return

        limit = BODY_LIMITS[path]
        content_length = _content_length(scope)
        if content_length is not None and content_length > limit:
            await _send_asgi_rejection(
                send,
                AdmissionRejected(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    "payload_too_large",
                    f"Request body exceeds the {limit}-byte limit for {path}.",
                ),
            )
            return

        body = bytearray()
        more_body = True
        while more_body:
            message = await receive()
            if message.get("type") == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            more_body = bool(message.get("more_body", False))
            if len(body) > limit:
                await _send_asgi_rejection(
                    send,
                    AdmissionRejected(
                        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                        "payload_too_large",
                        f"Request body exceeds the {limit}-byte limit for {path}.",
                    ),
                )
                return

        try:
            parse_and_validate_json_body(bytes(body), path)
        except AdmissionRejected as exc:
            await _send_asgi_rejection(send, exc)
            return
        except ValueError:
            pass  # Preserve each transport's existing malformed-JSON envelope.

        sent = False

        async def replay() -> dict[str, Any]:
            nonlocal sent
            if sent:
                return {"type": "http.request", "body": b"", "more_body": False}
            sent = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay, send)


def _budget_error(detail: str) -> None:
    raise AdmissionRejected(
        HTTPStatus.UNPROCESSABLE_ENTITY,
        "json_budget_exceeded",
        detail,
    )


def _season_range_size(start: Any, end: Any) -> int | None:
    if not isinstance(start, str) or not isinstance(end, str):
        return None
    try:
        start_year = season_to_int(start)
        end_year = season_to_int(end)
    except (ValueError, IndexError):
        return None
    return end_year - start_year + 1 if end_year >= start_year else None


def _natural_query_season_span(query: str) -> int | None:
    explicit = re.search(
        r"\bfrom\s+((?:19|20)\d{2}-\d{2})\s+to\s+((?:19|20)\d{2}-\d{2})\b",
        query,
        flags=re.IGNORECASE,
    )
    if explicit:
        return _season_range_size(explicit.group(1), explicit.group(2))
    since = re.search(r"\bsince\s+((?:19|20)\d{2})(?:-\d{2})?\b", query, flags=re.IGNORECASE)
    if since:
        return season_to_int(LATEST_REGULAR_SEASON) - int(since.group(1)) + 1
    last_n = re.search(r"\blast\s+(\d+)\s+seasons?\b", query, flags=re.IGNORECASE)
    if last_n:
        return int(last_n.group(1))
    return None


def _prune_timestamps(events: deque[float], cutoff: float) -> None:
    while events and events[0] <= cutoff:
        events.popleft()


def _content_length(scope: Mapping[str, Any]) -> int | None:
    for raw_key, raw_value in scope.get("headers", []):
        if raw_key.lower() == b"content-length":
            try:
                return int(raw_value.decode("ascii"))
            except (UnicodeDecodeError, ValueError):
                return None
    return None


async def _send_asgi_rejection(send: Any, rejection: AdmissionRejected) -> None:
    body = json.dumps(rejection.payload(), separators=(",", ":")).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    headers.extend(
        (key.lower().encode("ascii"), value.encode("ascii"))
        for key, value in rejection.headers().items()
    )
    await send({"type": "http.response.start", "status": rejection.status, "headers": headers})
    await send({"type": "http.response.body", "body": body})
