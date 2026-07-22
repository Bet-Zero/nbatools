"""Policy-bound, privacy-safe monitoring for the deployed public service."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit

from nbatools.deployment_monitoring import (
    MAX_SMOKE_RESPONSE_BYTES,
    Fetcher,
    ResponseTooLargeError,
    SmokeCase,
    evaluate_smoke_response,
    fetch_http,
    normalize_base_url,
)

AVAILABILITY_OBJECTIVE_PERCENT = 99.0
OBJECTIVE_WINDOW_DAYS = 30
SCHEDULE_INTERVAL_MINUTES = 120
MAX_ATTEMPTS = 2
TRANSIENT_FAILURE_KINDS = frozenset({"latency", "transport"})
EXPECTED_SCHEDULED_RUNS_PER_WINDOW = OBJECTIVE_WINDOW_DAYS * 24 * 60 // SCHEDULE_INTERVAL_MINUTES
MINIMUM_SUCCESSES_AT_FULL_WINDOW = 357
NORMAL_REQUESTS_PER_RUN = 3
NORMAL_REQUESTS_PER_DAY = 24 * 60 // SCHEDULE_INTERVAL_MINUTES * NORMAL_REQUESTS_PER_RUN
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


@dataclass(frozen=True)
class ProductionMonitorCase:
    smoke_case: SmokeCase
    max_duration_ms: float


@dataclass(frozen=True)
class ProductionMonitorAttempt:
    attempt: int
    ok: bool
    status_code: int | None
    duration_ms: float
    request_id: str | None
    summary: dict[str, Any]
    failure_kind: str | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class ProductionMonitorCaseResult:
    slug: str
    method: str
    path: str
    max_duration_ms: float
    ok: bool
    recovered_after_retry: bool
    attempts: list[ProductionMonitorAttempt]


@dataclass(frozen=True)
class ProductionMonitorReport:
    base_url: str
    checked_at: str
    ok: bool
    notification_required: bool
    failure_count: int
    failures: list[str]
    cases: list[ProductionMonitorCaseResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "kind": "production_monitor",
            "base_url": self.base_url,
            "checked_at": self.checked_at,
            "ok": self.ok,
            "notification_required": self.notification_required,
            "failure_count": self.failure_count,
            "failures": self.failures,
            "policy": {
                "availability_objective_percent": AVAILABILITY_OBJECTIVE_PERCENT,
                "objective_window_days": OBJECTIVE_WINDOW_DAYS,
                "schedule_interval_minutes": SCHEDULE_INTERVAL_MINUTES,
                "expected_scheduled_runs_per_30_days": EXPECTED_SCHEDULED_RUNS_PER_WINDOW,
                "minimum_successes_at_full_30_day_window": MINIMUM_SUCCESSES_AT_FULL_WINDOW,
                "normal_requests_per_run": NORMAL_REQUESTS_PER_RUN,
                "normal_requests_per_day": NORMAL_REQUESTS_PER_DAY,
                "max_attempts_for_transport_or_latency": MAX_ATTEMPTS,
            },
            "cases": [asdict(case) for case in self.cases],
        }


def default_production_monitor_cases() -> list[ProductionMonitorCase]:
    """Return the approved three-request production monitoring surface."""

    return [
        ProductionMonitorCase(
            SmokeCase(
                slug="health",
                path="/health",
                expected_json_fields={"status": "ok"},
            ),
            max_duration_ms=2_000.0,
        ),
        ProductionMonitorCase(
            SmokeCase(
                slug="readiness",
                path="/readiness",
                expected_json_fields={
                    "ready": True,
                    "status": "ready",
                    "immutable_generation": True,
                    "blockers.__len__": 0,
                },
            ),
            max_duration_ms=10_000.0,
        ),
        ProductionMonitorCase(
            SmokeCase(
                slug="representative_query",
                path="/query",
                method="POST",
                body={"query": "top 10 scorers 2025-26"},
                expected_json_fields={
                    "ok": True,
                    "route": "season_leaders",
                    "result_status": "ok",
                },
            ),
            max_duration_ms=15_000.0,
        ),
    ]


def run_production_monitor(
    base_url: str,
    *,
    cases: list[ProductionMonitorCase] | None = None,
    fetcher: Fetcher = fetch_http,
) -> ProductionMonitorReport:
    """Run the approved monitor, retrying only transport and latency failures."""

    normalized_base_url = _normalize_monitor_base_url(base_url)
    case_results: list[ProductionMonitorCaseResult] = []
    for case in cases or default_production_monitor_cases():
        case_result = _run_monitor_case(normalized_base_url, case, fetcher)
        case_results.append(case_result)
        if not case_result.ok:
            break
    failures = [case.slug for case in case_results if not case.ok]
    checked_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return ProductionMonitorReport(
        base_url=normalized_base_url,
        checked_at=checked_at,
        ok=not failures,
        notification_required=bool(failures),
        failure_count=len(failures),
        failures=failures,
        cases=case_results,
    )


def synthetic_notification_failure() -> dict[str, Any]:
    """Return the safe receipt used to prove external failure notification delivery."""

    return {
        "schema_version": 1,
        "kind": "production_monitor_synthetic_notification_test",
        "checked_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "ok": False,
        "notification_required": True,
        "failure_code": "approved_synthetic_notification_test",
        "network_requests_made": 0,
    }


def _run_monitor_case(
    base_url: str,
    monitor_case: ProductionMonitorCase,
    fetcher: Fetcher,
) -> ProductionMonitorCaseResult:
    case = monitor_case.smoke_case
    attempts: list[ProductionMonitorAttempt] = []
    for attempt_number in range(1, MAX_ATTEMPTS + 1):
        attempt = _run_monitor_attempt(base_url, monitor_case, attempt_number, fetcher)
        attempts.append(attempt)
        if attempt.ok or attempt.failure_kind not in TRANSIENT_FAILURE_KINDS:
            break

    return ProductionMonitorCaseResult(
        slug=case.slug,
        method=case.method,
        path=case.path,
        max_duration_ms=monitor_case.max_duration_ms,
        ok=attempts[-1].ok,
        recovered_after_retry=len(attempts) > 1 and attempts[-1].ok,
        attempts=attempts,
    )


def _run_monitor_attempt(
    base_url: str,
    monitor_case: ProductionMonitorCase,
    attempt_number: int,
    fetcher: Fetcher,
) -> ProductionMonitorAttempt:
    case = monitor_case.smoke_case
    url = base_url + case.path
    started = perf_counter()
    try:
        status, headers, body = fetcher(
            url,
            case.method,
            case.body,
            monitor_case.max_duration_ms / 1_000,
        )
    except HTTPError as exc:
        duration_ms = round((perf_counter() - started) * 1_000, 3)
        status = int(exc.code)
        headers = dict(exc.headers.items()) if exc.headers is not None else {}
        body = exc.read(MAX_SMOKE_RESPONSE_BYTES + 1)
        if len(body) > MAX_SMOKE_RESPONSE_BYTES:
            return _failed_attempt(
                attempt_number,
                duration_ms,
                "response",
                "response_too_large",
                status_code=status,
            )
    except ResponseTooLargeError:
        duration_ms = round((perf_counter() - started) * 1_000, 3)
        return _failed_attempt(
            attempt_number,
            duration_ms,
            "response",
            "response_too_large",
        )
    except (ConnectionError, TimeoutError, URLError, OSError):
        duration_ms = round((perf_counter() - started) * 1_000, 3)
        return _failed_attempt(
            attempt_number,
            duration_ms,
            "transport",
            "transport_error",
        )
    except Exception:
        duration_ms = round((perf_counter() - started) * 1_000, 3)
        return _failed_attempt(
            attempt_number,
            duration_ms,
            "internal",
            "internal_monitor_error",
        )

    duration_ms = round((perf_counter() - started) * 1_000, 3)
    try:
        result = evaluate_smoke_response(case, url, status, headers, body, duration_ms)
        safe_summary = _safe_response_summary(case.slug, body)
    except Exception:
        return _failed_attempt(
            attempt_number,
            duration_ms,
            "internal",
            "internal_monitor_error",
        )

    request_id = _request_id(result.headers)
    if not result.ok:
        error_code = (
            "unexpected_http_status"
            if result.status_code != case.expected_status
            else "response_contract_mismatch"
        )
        return ProductionMonitorAttempt(
            attempt=attempt_number,
            ok=False,
            status_code=result.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
            summary=safe_summary,
            failure_kind="response",
            error_code=error_code,
        )
    if duration_ms > monitor_case.max_duration_ms:
        return ProductionMonitorAttempt(
            attempt=attempt_number,
            ok=False,
            status_code=result.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
            summary=safe_summary,
            failure_kind="latency",
            error_code="latency_threshold_exceeded",
        )
    return ProductionMonitorAttempt(
        attempt=attempt_number,
        ok=True,
        status_code=result.status_code,
        duration_ms=duration_ms,
        request_id=request_id,
        summary=safe_summary,
    )


def _failed_attempt(
    attempt_number: int,
    duration_ms: float,
    failure_kind: str,
    error_code: str,
    *,
    status_code: int | None = None,
) -> ProductionMonitorAttempt:
    return ProductionMonitorAttempt(
        attempt=attempt_number,
        ok=False,
        status_code=status_code,
        duration_ms=duration_ms,
        request_id=None,
        summary={},
        failure_kind=failure_kind,
        error_code=error_code,
    )


def _request_id(headers: Mapping[str, str]) -> str | None:
    value = headers.get("x-request-id")
    rendered = str(value) if value else ""
    return rendered if _SAFE_TOKEN.fullmatch(rendered) else None


def _normalize_monitor_base_url(base_url: str) -> str:
    normalized = normalize_base_url(base_url)
    parsed = urlsplit(normalized)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("base_url must be an HTTP(S) origin without credentials or query data")
    return normalized


def _safe_response_summary(slug: str, body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}

    if slug == "health":
        return _allowlisted_scalars(payload, ("status",))
    if slug == "readiness":
        summary = _allowlisted_scalars(payload, ("ready", "status", "immutable_generation"))
        blockers = payload.get("blockers")
        if isinstance(blockers, list):
            codes = []
            for blocker in blockers[:20]:
                if not isinstance(blocker, Mapping):
                    continue
                code = blocker.get("code")
                if isinstance(code, str) and _SAFE_TOKEN.fullmatch(code):
                    codes.append(code)
            summary["blocker_codes"] = codes
        return summary
    if slug == "representative_query":
        return _allowlisted_scalars(payload, ("ok", "route", "result_status"))
    return {}


def _allowlisted_scalars(payload: Mapping[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for field in fields:
        value = payload.get(field)
        if isinstance(value, bool):
            summary[field] = value
        elif isinstance(value, str) and _SAFE_TOKEN.fullmatch(value):
            summary[field] = value
    return summary
