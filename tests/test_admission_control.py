from __future__ import annotations

import threading
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from nbatools import api as api_module
from nbatools.admission_control import (
    NATURAL_QUERY_BODY_MAX_BYTES,
    AdmissionController,
    AdmissionRejected,
    parse_and_validate_json_body,
    validate_json_budget,
    validate_season_span,
)
from nbatools.api import app
from nbatools.commands.structured_results import NoResult
from nbatools.query_service import QueryResult

pytestmark = pytest.mark.api


def test_body_byte_limit_is_inclusive_and_uses_encoded_bytes() -> None:
    payload = b'{"query":"Jokic"}'
    exact = payload + b" " * (NATURAL_QUERY_BODY_MAX_BYTES - len(payload))

    assert parse_and_validate_json_body(exact, "/query") == {"query": "Jokic"}

    with pytest.raises(AdmissionRejected) as caught:
        parse_and_validate_json_body(exact + b" ", "/query")
    assert caught.value.status == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert caught.value.error == "payload_too_large"


def test_json_depth_four_is_allowed_and_five_is_rejected() -> None:
    validate_json_budget({"a": {"b": {"c": {"d": {}}}}})

    with pytest.raises(AdmissionRejected, match="maximum depth"):
        validate_json_budget({"a": {"b": {"c": {"d": {"e": {}}}}}})


def test_existing_feedback_envelope_fits_depth_budget() -> None:
    validate_json_budget(
        {"result": {"sections": {"summary": [{"player_name": "Nikola Jokic", "pts_avg": 25}]}}}
    )


def test_json_aggregate_member_and_array_budgets() -> None:
    validate_json_budget({f"k{index}": index for index in range(64)})
    validate_json_budget({"values": list(range(20))})

    with pytest.raises(AdmissionRejected, match="64 total members"):
        validate_json_budget({f"k{index}": index for index in range(65)})
    with pytest.raises(AdmissionRejected, match="20 total elements"):
        validate_json_budget({"a": list(range(11)), "b": list(range(10))})


def test_full_supported_30_season_range_is_allowed() -> None:
    validate_season_span(
        "/structured-query",
        {
            "route": "season_leaders",
            "kwargs": {"start_season": "1996-97", "end_season": "2025-26"},
        },
    )
    validate_season_span(
        "/query",
        {"query": "top scorers from 1996-97 to 2025-26"},
    )


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        (
            "/structured-query",
            {
                "route": "season_leaders",
                "kwargs": {"start_season": "1995-96", "end_season": "2025-26"},
            },
        ),
        ("/query", {"query": "top scorers from 1995-96 to 2025-26"}),
        ("/query", {"query": "top scorers over the last 31 seasons"}),
    ],
)
def test_more_than_30_resolved_seasons_is_rejected(path, payload) -> None:
    with pytest.raises(AdmissionRejected) as caught:
        validate_season_span(path, payload)
    assert caught.value.status == HTTPStatus.UNPROCESSABLE_ENTITY
    assert caught.value.error == "season_span_exceeded"


def test_shared_query_rate_limit_returns_retry_after() -> None:
    controller = AdmissionController(
        query_limit=2,
        query_window_seconds=10,
        query_timeout_seconds=1,
    )

    assert controller.run_query("client", lambda: "one", now=0) == "one"
    assert controller.run_query("client", lambda: "two", now=1) == "two"
    with pytest.raises(AdmissionRejected) as caught:
        controller.run_query("client", lambda: "three", now=2)

    assert caught.value.status == HTTPStatus.TOO_MANY_REQUESTS
    assert caught.value.error == "rate_limited"
    assert caught.value.headers() == {"Retry-After": "8"}


def test_natural_and_structured_share_concurrency_slots() -> None:
    controller = AdmissionController(
        max_concurrent_queries=1,
        query_limit=10,
        query_timeout_seconds=2,
    )
    started = threading.Event()
    release = threading.Event()

    def blocking_query() -> str:
        started.set()
        release.wait(1)
        return "done"

    thread = threading.Thread(target=lambda: controller.run_query("natural-client", blocking_query))
    thread.start()
    assert started.wait(1)

    with pytest.raises(AdmissionRejected) as caught:
        controller.run_query("structured-client", lambda: "queued")
    assert caught.value.error == "concurrency_limited"
    assert caught.value.headers() == {"Retry-After": "1"}

    release.set()
    thread.join(2)
    assert not thread.is_alive()


def test_timeout_keeps_slot_reserved_until_worker_finishes() -> None:
    controller = AdmissionController(
        max_concurrent_queries=1,
        query_limit=10,
        query_timeout_seconds=0.01,
    )
    release = threading.Event()

    with pytest.raises(AdmissionRejected) as caught:
        controller.run_query("slow", lambda: release.wait(1))
    assert caught.value.status == HTTPStatus.GATEWAY_TIMEOUT
    assert caught.value.error == "execution_timeout"

    with pytest.raises(AdmissionRejected) as blocked:
        controller.run_query("next", lambda: "too soon")
    assert blocked.value.error == "concurrency_limited"
    release.set()


def test_feedback_quota_counts_only_committed_acceptances() -> None:
    controller = AdmissionController(feedback_limit=2, feedback_window_seconds=100)
    first = controller.reserve_feedback("client", now=0)
    first.commit()
    rolled_back = controller.reserve_feedback("client", now=1)
    rolled_back.rollback()
    second = controller.reserve_feedback("client", now=2)
    second.commit()

    assert controller.feedback_count("client") == 2
    with pytest.raises(AdmissionRejected) as caught:
        controller.reserve_feedback("client", now=3)
    assert caught.value.error == "feedback_rate_limited"
    assert caught.value.headers() == {"Retry-After": "97"}


def test_fastapi_rejects_body_before_json_parsing() -> None:
    client = TestClient(app)
    valid = b'{"query":"Jokic"}'
    oversized = valid + b" " * (NATURAL_QUERY_BODY_MAX_BYTES - len(valid) + 1)

    response = client.post(
        "/query",
        content=oversized,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert response.json()["error"] == "payload_too_large"


def test_fastapi_returns_429_and_retry_after_without_executing(monkeypatch) -> None:
    controller = AdmissionController(
        query_limit=1,
        query_window_seconds=60,
        query_timeout_seconds=1,
    )
    result = QueryResult(
        result=NoResult(
            query_class="unknown",
            reason="no_match",
            result_status="no_result",
            result_reason="no_match",
        ),
        metadata={},
        query="Jokic",
        route=None,
    )
    calls = []

    def execute(query):
        calls.append(query)
        return result

    monkeypatch.setenv("NBATOOLS_ADMISSION_CONTROLS", "true")
    monkeypatch.setattr(api_module, "ADMISSION_CONTROLLER", controller)
    monkeypatch.setattr(api_module, "execute_natural_query", execute)
    client = TestClient(app)

    first = client.post("/query", json={"query": "Jokic"})
    second = client.post("/query", json={"query": "Jokic"})

    assert first.status_code == 200
    assert second.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert second.headers["retry-after"] == "60"
    assert second.json()["error"] == "rate_limited"
    assert calls == ["Jokic"]
