"""Policy-bound, privacy-safe monitoring for the deployed public service."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from http.client import HTTPException
from math import isfinite
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
    snapshot_live_gap_matches,
)

AVAILABILITY_OBJECTIVE_PERCENT = 99.0
OBJECTIVE_WINDOW_DAYS = 30
SCHEDULE_INTERVAL_MINUTES = 120
MAX_ATTEMPTS = 2
NETWORK_TIMEOUT_GRACE_SECONDS = 10.0
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
    known_live_gap: bool = False


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
    live_readiness: str
    snapshot_status: str
    expected_generation: str | None

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
            "live_readiness": self.live_readiness,
            "snapshot_status": self.snapshot_status,
            "expected_generation": self.expected_generation,
            "policy": {
                "availability_objective_percent": AVAILABILITY_OBJECTIVE_PERCENT,
                "objective_window_days": OBJECTIVE_WINDOW_DAYS,
                "schedule_interval_minutes": SCHEDULE_INTERVAL_MINUTES,
                "expected_scheduled_runs_per_30_days": EXPECTED_SCHEDULED_RUNS_PER_WINDOW,
                "minimum_successes_at_full_30_day_window": MINIMUM_SUCCESSES_AT_FULL_WINDOW,
                "normal_requests_per_run": NORMAL_REQUESTS_PER_RUN,
                "normal_requests_per_day": NORMAL_REQUESTS_PER_DAY,
                "max_attempts_for_transport_or_latency": MAX_ATTEMPTS,
                "network_timeout_grace_seconds": NETWORK_TIMEOUT_GRACE_SECONDS,
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
                    "result.metadata.season": "2025-26",
                    "result.metadata.season_type": "Regular Season",
                    "result.metadata.stat": "pts",
                    "result.sections.leaderboard.__len__": 10,
                },
            ),
            max_duration_ms=15_000.0,
        ),
    ]


def run_production_monitor(
    base_url: str,
    *,
    expected_generation: str | None = None,
    cases: list[ProductionMonitorCase] | None = None,
    fetcher: Fetcher = fetch_http,
) -> ProductionMonitorReport:
    """Run every probe and apply the scoped snapshot alert policy."""

    normalized_base_url = _normalize_monitor_base_url(base_url)
    if expected_generation is not None and not _SAFE_TOKEN.fullmatch(expected_generation):
        raise ValueError("expected_generation must be a safe immutable generation ID")
    case_results = [
        _run_monitor_case(normalized_base_url, case, fetcher, expected_generation)
        for case in cases or default_production_monitor_cases()
    ]
    failures = [case.slug for case in case_results if not case.ok]
    readiness = next((case for case in case_results if case.slug == "readiness"), None)
    snapshot_status = _snapshot_status(case_results, expected_generation)
    if (
        snapshot_status == "passed"
        and failures == ["readiness"]
        and readiness
        and readiness.attempts[-1].known_live_gap
    ):
        failures.clear()
    if (
        readiness is not None
        and readiness.ok
        and expected_generation is not None
        and readiness.attempts[-1].summary.get("active_generation") != expected_generation
    ):
        failures.append("unexpected_active_generation")
    checked_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return ProductionMonitorReport(
        base_url=normalized_base_url,
        checked_at=checked_at,
        ok=not failures,
        notification_required=bool(failures),
        failure_count=len(failures),
        failures=failures,
        cases=case_results,
        live_readiness=(
            "not_checked" if readiness is None else "passed" if readiness.ok else "failed"
        ),
        snapshot_status=snapshot_status,
        expected_generation=expected_generation,
    )


def _snapshot_status(
    cases: list[ProductionMonitorCaseResult], expected_generation: str | None
) -> str:
    probes = {case.slug: case for case in cases}
    if not {"health", "readiness", "representative_query"} <= probes.keys():
        return "not_checked"
    if not probes["health"].ok or not probes["representative_query"].ok:
        return "failed"
    readiness = probes["readiness"]
    attempt = readiness.attempts[-1]
    if attempt.known_live_gap:
        return "passed"
    if not readiness.ok:
        return "failed"
    if expected_generation is None:
        return "not_checked"
    return "passed" if attempt.summary.get("active_generation") == expected_generation else "failed"


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
    expected_generation: str | None,
) -> ProductionMonitorCaseResult:
    case = monitor_case.smoke_case
    attempts: list[ProductionMonitorAttempt] = []
    for attempt_number in range(1, MAX_ATTEMPTS + 1):
        attempt = _run_monitor_attempt(
            base_url, monitor_case, attempt_number, fetcher, expected_generation
        )
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
    expected_generation: str | None,
) -> ProductionMonitorAttempt:
    case = monitor_case.smoke_case
    url = base_url + case.path
    started = perf_counter()
    try:
        status, headers, body = fetcher(
            url,
            case.method,
            case.body,
            monitor_case.max_duration_ms / 1_000 + NETWORK_TIMEOUT_GRACE_SECONDS,
        )
    except HTTPError as exc:
        status = int(exc.code)
        headers = dict(exc.headers.items()) if exc.headers is not None else {}
        try:
            with exc:
                body = exc.read(MAX_SMOKE_RESPONSE_BYTES + 1)
        except (HTTPException, OSError):
            return _failed_attempt(
                attempt_number,
                round((perf_counter() - started) * 1_000, 3),
                "transport",
                "transport_error",
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
    except (HTTPException, URLError, OSError):
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
    if len(body) > MAX_SMOKE_RESPONSE_BYTES:
        return _failed_attempt(
            attempt_number, duration_ms, "response", "response_too_large", status_code=status
        )
    try:
        result = evaluate_smoke_response(case, url, status, headers, body, duration_ms)
        payload = _decode_payload(body)
        safe_summary = _safe_response_summary(case.slug, payload)
    except Exception:
        return _failed_attempt(
            attempt_number,
            duration_ms,
            "internal",
            "internal_monitor_error",
        )

    request_id = _request_id(result.headers)
    shape_ok = result.ok
    if shape_ok and case.slug == "readiness":
        shape_ok = payload.get("ready") is True and payload.get("immutable_generation") is True
    if shape_ok and case.slug == "representative_query":
        shape_ok = _scoring_rows_are_valid(payload)
    known_live_gap = (
        case.slug == "readiness"
        and status == 503
        and snapshot_live_gap_matches(payload, expected_generation)
    )
    too_slow = duration_ms > monitor_case.max_duration_ms
    if not shape_ok and not (known_live_gap and too_slow):
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
            known_live_gap=known_live_gap,
        )
    if too_slow:
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


def _decode_payload(body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _scoring_rows_are_valid(payload: dict[str, Any]) -> bool:
    # The smoke case already checks the season, metric and leaderboard length.
    if payload.get("ok") is not True:
        return False
    result = payload.get("result")
    sections = result.get("sections") if isinstance(result, dict) else None
    rows = sections.get("leaderboard") if isinstance(sections, dict) else None
    if not isinstance(rows, list) or len(rows) != 10:
        return False
    seen: set[int] = set()
    previous_points = float("inf")
    for rank, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            return False
        player_id, games, points = (
            row.get("player_id"),
            row.get("games_played"),
            row.get("pts_per_game"),
        )
        if (
            type(row.get("rank")) is not int
            or row["rank"] != rank
            or type(player_id) is not int
            or player_id <= 0
            or player_id in seen
            or type(games) is not int
            or games <= 0
            or type(points) not in {int, float}
            or (type(points) is float and not isfinite(points))
            or not 0 < points <= previous_points
        ):
            return False
        seen.add(player_id)
        previous_points = points
    return True


def _safe_response_summary(slug: str, payload: dict[str, Any]) -> dict[str, Any]:
    if slug == "health":
        return _allowlisted_scalars(payload, ("status",))
    if slug == "readiness":
        summary = _allowlisted_scalars(
            payload, ("ready", "status", "immutable_generation", "active_generation")
        )
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
