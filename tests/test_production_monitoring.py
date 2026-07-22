from __future__ import annotations

import json
from collections.abc import Mapping
from io import BytesIO
from urllib.error import HTTPError

from nbatools.production_monitoring import (
    AVAILABILITY_OBJECTIVE_PERCENT,
    MINIMUM_SUCCESSES_AT_FULL_WINDOW,
    NETWORK_TIMEOUT_GRACE_SECONDS,
    OBJECTIVE_WINDOW_DAYS,
    SCHEDULE_INTERVAL_MINUTES,
    ProductionMonitorCase,
    default_production_monitor_cases,
    run_production_monitor,
    synthetic_notification_failure,
)


def _response_for(slug: str) -> tuple[int, Mapping[str, str], bytes]:
    if slug == "health":
        return 200, {"x-request-id": "req-health"}, b'{"status":"ok"}'
    if slug == "readiness":
        return (
            200,
            {"x-request-id": "req-readiness"},
            b'{"ready":true,"status":"ready","immutable_generation":true,"blockers":[]}',
        )
    return (
        200,
        {"x-request-id": "req-query"},
        b'{"ok":true,"route":"season_leaders","result_status":"ok"}',
    )


def _slug_from_url(url: str) -> str:
    if url.endswith("/health"):
        return "health"
    if url.endswith("/readiness"):
        return "readiness"
    return "representative_query"


def test_default_monitor_cases_encode_approved_surface_and_thresholds() -> None:
    cases = default_production_monitor_cases()

    assert [case.smoke_case.slug for case in cases] == [
        "health",
        "readiness",
        "representative_query",
    ]
    assert [case.max_duration_ms for case in cases] == [2_000.0, 10_000.0, 15_000.0]
    assert cases[1].smoke_case.expected_json_fields["blockers.__len__"] == 0
    assert cases[2].smoke_case.body == {"query": "top 10 scorers 2025-26"}


def test_successful_monitor_report_contains_policy_and_no_request_body() -> None:
    timeouts: list[float] = []

    def fetcher(
        url: str,
        method: str,
        body: dict[str, object] | None,
        timeout: float,
    ) -> tuple[int, Mapping[str, str], bytes]:
        del method, body
        timeouts.append(timeout)
        return _response_for(_slug_from_url(url))

    payload = run_production_monitor("https://deploy.example/", fetcher=fetcher).to_dict()

    assert payload["ok"] is True
    assert payload["notification_required"] is False
    assert payload["policy"] == {
        "availability_objective_percent": AVAILABILITY_OBJECTIVE_PERCENT,
        "objective_window_days": OBJECTIVE_WINDOW_DAYS,
        "schedule_interval_minutes": SCHEDULE_INTERVAL_MINUTES,
        "expected_scheduled_runs_per_30_days": 360,
        "minimum_successes_at_full_30_day_window": MINIMUM_SUCCESSES_AT_FULL_WINDOW,
        "normal_requests_per_run": 3,
        "normal_requests_per_day": 36,
        "max_attempts_for_transport_or_latency": 2,
        "network_timeout_grace_seconds": NETWORK_TIMEOUT_GRACE_SECONDS,
    }
    assert timeouts == [12.0, 20.0, 25.0]
    assert [case["attempts"][0]["request_id"] for case in payload["cases"]] == [
        "req-health",
        "req-readiness",
        "req-query",
    ]
    rendered = json.dumps(payload)
    assert "top 10 scorers" not in rendered
    assert '"body"' not in rendered


def test_response_summary_redacts_raw_query_body_and_unsafe_request_id() -> None:
    private_query = "my private raw query"

    def fetcher(
        url: str,
        method: str,
        body: dict[str, object] | None,
        timeout: float,
    ) -> tuple[int, Mapping[str, str], bytes]:
        del url, method, body, timeout
        return (
            200,
            {"x-request-id": "secret request id with spaces"},
            json.dumps(
                {
                    "ok": True,
                    "route": "season_leaders",
                    "result_status": "ok",
                    "query": private_query,
                    "notes": ["private response note"],
                }
            ).encode(),
        )

    payload = run_production_monitor(
        "https://deploy.example",
        cases=[default_production_monitor_cases()[2]],
        fetcher=fetcher,
    ).to_dict()
    rendered = json.dumps(payload)

    assert payload["ok"] is True
    assert payload["cases"][0]["attempts"][0]["request_id"] is None
    assert private_query not in rendered
    assert "private response note" not in rendered


def test_monitor_rejects_base_url_credentials_without_echoing_them() -> None:
    try:
        run_production_monitor("https://secret-token@deploy.example")
    except ValueError as exc:
        assert "secret-token" not in str(exc)
    else:
        raise AssertionError("credential-bearing monitor URL was accepted")


def test_transport_failure_retries_once_and_redacts_exception() -> None:
    calls = 0

    def fetcher(
        url: str,
        method: str,
        body: dict[str, object] | None,
        timeout: float,
    ) -> tuple[int, Mapping[str, str], bytes]:
        nonlocal calls
        del url, method, body, timeout
        calls += 1
        raise TimeoutError("secret-token /private/provider/path")

    case = default_production_monitor_cases()[0]
    payload = run_production_monitor(
        "https://deploy.example",
        cases=[case],
        fetcher=fetcher,
    ).to_dict()

    assert calls == 2
    assert payload["ok"] is False
    assert payload["failures"] == ["health"]
    assert [attempt["failure_kind"] for attempt in payload["cases"][0]["attempts"]] == [
        "transport",
        "transport",
    ]
    assert "secret-token" not in json.dumps(payload)
    assert "/private/provider/path" not in json.dumps(payload)


def test_internal_monitor_error_fails_without_retry_and_redacts_exception() -> None:
    calls = 0

    def fetcher(
        url: str,
        method: str,
        body: dict[str, object] | None,
        timeout: float,
    ) -> tuple[int, Mapping[str, str], bytes]:
        nonlocal calls
        del url, method, body, timeout
        calls += 1
        raise RuntimeError("secret internal detail")

    report = run_production_monitor(
        "https://deploy.example",
        cases=[default_production_monitor_cases()[0]],
        fetcher=fetcher,
    )

    assert calls == 1
    assert report.ok is False
    assert report.cases[0].attempts[0].failure_kind == "internal"
    assert report.cases[0].attempts[0].error_code == "internal_monitor_error"
    assert "secret internal detail" not in json.dumps(report.to_dict())


def test_semantic_query_contract_mismatch_fails_without_retry() -> None:
    calls = 0

    def fetcher(
        url: str,
        method: str,
        body: dict[str, object] | None,
        timeout: float,
    ) -> tuple[int, Mapping[str, str], bytes]:
        nonlocal calls
        del url, method, body, timeout
        calls += 1
        return 200, {}, b'{"ok":true,"route":"wrong_route","result_status":"ok"}'

    report = run_production_monitor(
        "https://deploy.example",
        cases=[default_production_monitor_cases()[2]],
        fetcher=fetcher,
    )

    assert calls == 1
    assert report.ok is False
    assert report.cases[0].attempts[0].failure_kind == "response"
    assert report.cases[0].attempts[0].error_code == "response_contract_mismatch"


def test_transport_retry_can_recover_without_notification() -> None:
    calls = 0

    def fetcher(
        url: str,
        method: str,
        body: dict[str, object] | None,
        timeout: float,
    ) -> tuple[int, Mapping[str, str], bytes]:
        nonlocal calls
        del method, body, timeout
        calls += 1
        if calls == 1:
            raise TimeoutError("temporary")
        return _response_for(_slug_from_url(url))

    report = run_production_monitor(
        "https://deploy.example",
        cases=[default_production_monitor_cases()[0]],
        fetcher=fetcher,
    )

    assert report.ok is True
    assert report.notification_required is False
    assert report.cases[0].recovered_after_retry is True
    assert len(report.cases[0].attempts) == 2


def test_latency_failure_retries_once(monkeypatch) -> None:
    ticks = iter([0.0, 3.0, 3.0, 6.0])
    timeouts: list[float] = []
    monkeypatch.setattr("nbatools.production_monitoring.perf_counter", lambda: next(ticks))
    case = ProductionMonitorCase(
        default_production_monitor_cases()[0].smoke_case,
        max_duration_ms=2_000.0,
    )

    report = run_production_monitor(
        "https://deploy.example",
        cases=[case],
        fetcher=lambda url, method, body, timeout: (
            timeouts.append(timeout) or _response_for("health")
        ),
    )

    assert report.ok is False
    assert len(report.cases[0].attempts) == 2
    assert all(attempt.failure_kind == "latency" for attempt in report.cases[0].attempts)
    assert timeouts == [12.0, 12.0]


def test_readiness_contract_failure_alerts_without_retry() -> None:
    calls: list[str] = []

    def fetcher(
        url: str,
        method: str,
        body: dict[str, object] | None,
        timeout: float,
    ) -> tuple[int, Mapping[str, str], bytes]:
        del method, body, timeout
        calls.append(url)
        return (
            503,
            {"x-request-id": "req-blocked"},
            b'{"ready":false,"status":"not_ready","blockers":[{"code":"last_refresh_failed"}]}',
        )

    report = run_production_monitor(
        "https://deploy.example",
        cases=[default_production_monitor_cases()[1]],
        fetcher=fetcher,
    )

    assert calls == ["https://deploy.example/readiness"]
    assert report.ok is False
    attempt = report.cases[0].attempts[0]
    assert attempt.failure_kind == "response"
    assert attempt.error_code == "unexpected_http_status"
    assert attempt.request_id == "req-blocked"


def test_readiness_http_error_is_semantic_and_skips_query() -> None:
    calls: list[str] = []

    def fetcher(
        url: str,
        method: str,
        body: dict[str, object] | None,
        timeout: float,
    ) -> tuple[int, Mapping[str, str], bytes]:
        del method, body, timeout
        calls.append(url)
        if url.endswith("/health"):
            return _response_for("health")
        raise HTTPError(
            url,
            503,
            "Service Unavailable",
            {"x-request-id": "req-http-error"},
            BytesIO(
                b'{"ready":false,"status":"not_ready","blockers":[{"code":"last_refresh_failed"}]}'
            ),
        )

    report = run_production_monitor("https://deploy.example", fetcher=fetcher)

    assert report.ok is False
    assert calls == [
        "https://deploy.example/health",
        "https://deploy.example/readiness",
    ]
    readiness = report.cases[1].attempts[0]
    assert readiness.failure_kind == "response"
    assert readiness.status_code == 503
    assert readiness.request_id == "req-http-error"
    assert len(report.cases[1].attempts) == 1


def test_synthetic_failure_is_network_free_and_safe() -> None:
    payload = synthetic_notification_failure()

    assert payload["ok"] is False
    assert payload["notification_required"] is True
    assert payload["network_requests_made"] == 0
    assert payload["failure_code"] == "approved_synthetic_notification_test"
