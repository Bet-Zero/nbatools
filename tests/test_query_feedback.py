from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.commands.structured_results import NoResult
from nbatools.query_feedback import (
    FeedbackStorageError,
    FeedbackStoreResult,
    FeedbackValidationError,
    build_feedback_record,
    handle_feedback_submission,
    load_feedback_store_config,
    maybe_log_query_diagnostic,
    sanitize_metadata,
    store_feedback_record,
)
from nbatools.query_service import QueryResult

pytestmark = pytest.mark.api


def base_payload(**overrides):
    payload = {
        "query": "Jokic last 10 games",
        "feedback_source": "user_submitted",
        "feedback_type": "wrong_answer",
        "source_page": "/",
        "route": "player_game_summary",
        "status": "ok",
        "reason": None,
        "metadata": {
            "route": "player_game_summary",
            "player": "Nikola Jokic",
            "email": "user@example.com",
            "unsupported_filters": ["rookie"],
            "applied_filters": [{"label": "Season", "value": "2025-26"}],
        },
        "result": {
            "query_class": "summary",
            "sections": {
                "summary": [{"player_name": "Nikola Jokic", "pts_avg": 25}],
                "game_log": [{"game_id": "1"}, {"game_id": "2"}],
            },
        },
    }
    payload.update(overrides)
    return payload


def test_feedback_payload_validation_success_sanitizes_record():
    record = build_feedback_record(
        base_payload(email="user@example.com", name="Test User"),
        now=datetime(2026, 5, 18, 12, 0, tzinfo=UTC),
        env={},
    )

    assert record["schema_version"] == 2
    assert record["retention_days"] == 90
    assert record["expires_at"] == "2026-08-16T12:00:00.000Z"
    assert record["feedback_source"] == "user_submitted"
    assert record["feedback_type"] == "wrong_answer"
    assert record["query_normalized_hash"]
    assert record["review_status"] == "new"
    assert record["triage_decision"] is None
    assert "email" not in record
    assert "name" not in record
    assert record["metadata"]["player"] == "Nikola Jokic"
    assert "email" not in record["metadata"]
    assert record["result_shape"]["section_row_counts"] == {
        "game_log": 2,
        "summary": 1,
    }


def test_invalid_feedback_type_rejected():
    with pytest.raises(FeedbackValidationError, match="feedback_type"):
        build_feedback_record(base_payload(feedback_type="bad_type"), env={})


def test_length_caps_are_applied():
    record = build_feedback_record(
        base_payload(
            query="q" * 700,
            user_note="n" * 1200,
            error_message="e" * 600,
            answer_text_preview="a" * 700,
        ),
        env={},
    )

    assert len(record["query"]) == 500
    assert len(record["user_note"]) == 1000
    assert len(record["error_message"]) == 500
    assert len(record["answer_text_preview"]) == 500


def test_metadata_sanitizer_excludes_raw_tables_and_pii_like_fields():
    metadata = sanitize_metadata(
        {
            "route": "player_game_summary",
            "name": "User Name",
            "ip": "127.0.0.1",
            "sections": {"summary": [{"pts": 1}]},
            "game_log": [{"game_id": "1"}],
            "team": "BOS",
        }
    )

    assert metadata == {"route": "player_game_summary", "team": "BOS"}


def test_disabled_store_behavior_when_env_missing():
    record = build_feedback_record(base_payload(), env={})

    result = store_feedback_record(record, env={})

    assert result.stored is False
    assert result.disabled is True


def test_r2_store_write_with_mock_client():
    record = build_feedback_record(
        base_payload(),
        now=datetime(2026, 5, 18, 12, 0, tzinfo=UTC),
        env={},
    )
    calls = []

    class FakeClient:
        def put_object(self, **kwargs):
            calls.append(kwargs)

    result = store_feedback_record(
        record,
        env={
            "QUERY_FEEDBACK_STORE": "r2",
            "QUERY_FEEDBACK_BUCKET_NAME": "nbatools-feedback",
            "QUERY_FEEDBACK_PREFIX": "query_feedback",
            "QUERY_FEEDBACK_R2_ACCOUNT_ID": "acct",
            "QUERY_FEEDBACK_R2_ACCESS_KEY_ID": "feedback-key",
            "QUERY_FEEDBACK_R2_SECRET_ACCESS_KEY": "feedback-secret",
        },
        client=FakeClient(),
    )

    assert result.stored is True
    assert result.key
    assert result.key == f"query_feedback/receipts/{record['id']}.json"
    assert calls[0]["Bucket"] == "nbatools-feedback"
    assert calls[0]["ContentType"] == "application/json"
    assert calls[0]["Metadata"] == {
        "expires-at": "2026-08-16T12:00:00.000Z",
        "retention-days": "90",
    }
    stored = json.loads(calls[0]["Body"].decode("utf-8"))
    assert stored["id"] == record["id"]
    assert "result" not in stored
    assert calls[0]["IfNoneMatch"] == "*"


def test_feedback_submission_id_uses_one_conditional_object_and_stable_receipt():
    submission_id = "00000000-0000-4000-8000-000000000001"
    record = build_feedback_record(
        base_payload(submission_id=submission_id),
        now=datetime(2026, 5, 18, 12, 0, tzinfo=UTC),
        env={},
    )
    calls = []

    class FakeClient:
        def put_object(self, **kwargs):
            calls.append(kwargs)

    result = store_feedback_record(
        record,
        env={
            "QUERY_FEEDBACK_STORE": "r2",
            "QUERY_FEEDBACK_BUCKET_NAME": "nbatools-feedback",
            "QUERY_FEEDBACK_PREFIX": "query_feedback",
            "QUERY_FEEDBACK_R2_ACCOUNT_ID": "acct",
            "QUERY_FEEDBACK_R2_ACCESS_KEY_ID": "feedback-key",
            "QUERY_FEEDBACK_R2_SECRET_ACCESS_KEY": "feedback-secret",
        },
        client=FakeClient(),
    )

    assert record["id"] == "qfb_00000000000040008000000000000001"
    assert result.key == f"query_feedback/submissions/{submission_id}.json"
    assert calls[0]["IfNoneMatch"] == "*"


def test_feedback_submission_retry_returns_same_receipt_without_new_write():
    submission_id = "00000000-0000-4000-8000-000000000001"

    class PreconditionFailed(Exception):
        response = {
            "Error": {"Code": "PreconditionFailed"},
            "ResponseMetadata": {"HTTPStatusCode": 412},
        }

    class FakeClient:
        def put_object(self, **_kwargs):
            raise PreconditionFailed("already stored")

    status, payload = handle_feedback_submission(
        base_payload(submission_id=submission_id),
        idempotency_key=submission_id,
        env={
            "QUERY_FEEDBACK_STORE": "r2",
            "QUERY_FEEDBACK_BUCKET_NAME": "nbatools-feedback",
            "QUERY_FEEDBACK_PREFIX": "query_feedback",
            "QUERY_FEEDBACK_R2_ACCOUNT_ID": "acct",
            "QUERY_FEEDBACK_R2_ACCESS_KEY_ID": "feedback-key",
            "QUERY_FEEDBACK_R2_SECRET_ACCESS_KEY": "feedback-secret",
        },
        client=FakeClient(),
    )

    assert status == 200
    assert payload["feedback_id"] == "qfb_00000000000040008000000000000001"
    assert payload["idempotent_replay"] is True


def test_feedback_idempotency_header_must_match_payload():
    status, payload = handle_feedback_submission(
        base_payload(submission_id="00000000-0000-4000-8000-000000000001"),
        idempotency_key="00000000-0000-4000-8000-000000000002",
        env={},
    )

    assert status == 422
    assert payload["error"] == "validation_error"
    assert "must match" in payload["detail"]


def test_feedback_store_uses_dedicated_credentials_and_preserves_read_only_data_client(
    monkeypatch,
):
    record = build_feedback_record(base_payload(), env={})
    created_configs = []

    class ReadOnlyDataClient:
        def put_object(self, **kwargs):
            raise AssertionError(f"canonical data client cannot write: {kwargs['Bucket']}")

    class BucketScopedFeedbackClient:
        def __init__(self):
            self.put_calls = []

        def put_object(self, **kwargs):
            if kwargs["Bucket"] != "nbatools-feedback":
                raise PermissionError("cross-bucket operation denied")
            self.put_calls.append(kwargs)

    data_client = ReadOnlyDataClient()
    feedback_client = BucketScopedFeedbackClient()

    def fake_create_r2_client(config):
        created_configs.append(config)
        if config.access_key_id == "data-read-only-key":
            return data_client
        return feedback_client

    monkeypatch.setattr("nbatools.query_feedback.create_r2_client", fake_create_r2_client)

    result = store_feedback_record(
        record,
        env={
            "QUERY_FEEDBACK_STORE": "r2",
            "QUERY_FEEDBACK_BUCKET_NAME": "nbatools-feedback",
            "QUERY_FEEDBACK_R2_ACCOUNT_ID": "acct",
            "QUERY_FEEDBACK_R2_ACCESS_KEY_ID": "feedback-write-key",
            "QUERY_FEEDBACK_R2_SECRET_ACCESS_KEY": "feedback-write-secret",
            "R2_ACCOUNT_ID": "acct",
            "R2_ACCESS_KEY_ID": "data-read-only-key",
            "R2_SECRET_ACCESS_KEY": "data-read-only-secret",
            "R2_BUCKET_NAME": "nbatools-data",
        },
    )

    assert result.stored is True
    assert created_configs[0].access_key_id == "feedback-write-key"
    assert created_configs[0].bucket_name == "nbatools-feedback"
    assert len(feedback_client.put_calls) == 1
    with pytest.raises(PermissionError, match="cross-bucket"):
        feedback_client.put_object(Bucket="nbatools-data", Key="forbidden", Body=b"")


def test_feedback_store_fails_closed_without_dedicated_credentials():
    with pytest.raises(FeedbackStorageError, match="QUERY_FEEDBACK_R2_ACCOUNT_ID"):
        load_feedback_store_config(
            env={
                "QUERY_FEEDBACK_STORE": "r2",
                "QUERY_FEEDBACK_BUCKET_NAME": "nbatools-feedback",
                "R2_ACCOUNT_ID": "acct",
                "R2_ACCESS_KEY_ID": "data-key",
                "R2_SECRET_ACCESS_KEY": "data-secret",
            },
            env_file=None,
        )


def test_feedback_store_fails_closed_when_credentials_alias_data_tuple():
    with pytest.raises(FeedbackStorageError, match="must not reuse"):
        load_feedback_store_config(
            env={
                "QUERY_FEEDBACK_STORE": "r2",
                "QUERY_FEEDBACK_BUCKET_NAME": "nbatools-feedback",
                "QUERY_FEEDBACK_R2_ACCOUNT_ID": "acct",
                "QUERY_FEEDBACK_R2_ACCESS_KEY_ID": "shared-key",
                "QUERY_FEEDBACK_R2_SECRET_ACCESS_KEY": "shared-secret",
                "R2_ACCOUNT_ID": "acct",
                "R2_ACCESS_KEY_ID": "shared-key",
                "R2_SECRET_ACCESS_KEY": "shared-secret",
            },
            env_file=None,
        )


def test_query_feedback_endpoint_success_and_validation_failure(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(
        "nbatools.query_feedback.store_feedback_record",
        lambda record, env=None, client=None: FeedbackStoreResult(stored=True),
    )

    response = client.post("/query-feedback", json=base_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["stored"] is True
    assert body["disabled"] is False
    assert body["feedback_id"]

    invalid = client.post(
        "/query-feedback",
        json=base_payload(feedback_type="bad_type"),
    )

    assert invalid.status_code == 422
    assert invalid.json()["error"] == "validation_error"


def test_query_feedback_endpoint_returns_json_storage_error(monkeypatch):
    client = TestClient(app)

    def fail_store(record, env=None, client=None):
        raise FeedbackStorageError("write failed")

    monkeypatch.setattr("nbatools.query_feedback.store_feedback_record", fail_store)

    response = client.post("/query-feedback", json=base_payload())

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["error"] == "feedback_storage_error"


def test_automatic_no_result_logging_is_best_effort_and_payload_unchanged(monkeypatch):
    payload = {
        "ok": False,
        "query": "unrecognized thing",
        "route": None,
        "result_status": "no_result",
        "result_reason": "unrouted",
        "current_through": None,
        "confidence": None,
        "intent": None,
        "notes": [],
        "caveats": [],
        "result": {
            "query_class": "unknown",
            "metadata": {},
            "notes": [],
            "caveats": [],
            "sections": {},
        },
    }
    original = json.loads(json.dumps(payload))

    def fail_store(record, env=None, client=None):
        raise FeedbackStorageError("store down")

    monkeypatch.setattr("nbatools.query_feedback.store_feedback_record", fail_store)

    assert maybe_log_query_diagnostic(payload, source_page="/") is False
    assert payload == original


def test_automatic_logging_failure_does_not_change_query_response(monkeypatch):
    client = TestClient(app)
    no_result = NoResult(
        query_class="unknown",
        reason="unrouted",
        result_status="no_result",
        result_reason="unrouted",
    )
    qr = QueryResult(
        result=no_result,
        metadata={"query_text": "gibberish"},
        query="gibberish",
        route=None,
    )

    def fail_store(record, env=None, client=None):
        raise FeedbackStorageError("store down")

    monkeypatch.setattr("nbatools.query_feedback.store_feedback_record", fail_store)
    with patch("nbatools.api.execute_natural_query", return_value=qr):
        response = client.post("/query", json={"query": "gibberish"})

    assert response.status_code == 200
    body = response.json()
    assert body["result_status"] == "no_result"
    assert body["result_reason"] == "unrouted"


def test_automatic_logging_suppressed_for_internal_pages(monkeypatch):
    calls = []

    def capture_store(record, env=None, client=None):
        calls.append(record)
        return FeedbackStoreResult(stored=True)

    monkeypatch.setattr("nbatools.query_feedback.store_feedback_record", capture_store)
    payload = {
        "query": "unsupported query",
        "result_status": "no_result",
        "result_reason": "unsupported",
        "result": {"metadata": {}, "sections": {}},
    }

    env = {"QUERY_AUTOMATIC_DIAGNOSTICS_ENABLED": "true"}
    assert maybe_log_query_diagnostic(payload, source_page="/review", env=env) is False
    assert maybe_log_query_diagnostic(payload, source_page="/visual-qa", env=env) is False
    assert calls == []
