from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nbatools.query_feedback import (
    FeedbackStoreResult,
    automatic_diagnostics_enabled,
    build_feedback_record,
    feedback_persistence_gate,
    handle_feedback_submission,
    load_feedback_store_config,
    maybe_log_query_diagnostic,
    store_feedback_record,
)
from nbatools.query_feedback_privacy import (
    FeedbackPrivacyError,
    delete_feedback_by_receipt,
    feedback_key_from_receipt,
    verify_feedback_lifecycle,
)

pytestmark = pytest.mark.api


def payload(**overrides):
    value = {
        "submission_id": "00000000-0000-4000-8000-000000000001",
        "query": "Jokic last 10 games",
        "feedback_source": "user_submitted",
        "feedback_type": "wrong_answer",
        "source_page": "/",
    }
    value.update(overrides)
    return value


def deployed_store_env(**overrides):
    values = {
        "VERCEL": "1",
        "VERCEL_ENV": "production",
        "QUERY_FEEDBACK_STORE": "r2",
        "QUERY_FEEDBACK_BUCKET_NAME": "nbatools-feedback",
        "QUERY_FEEDBACK_R2_ACCOUNT_ID": "acct",
        "QUERY_FEEDBACK_R2_ACCESS_KEY_ID": "feedback-key",
        "QUERY_FEEDBACK_R2_SECRET_ACCESS_KEY": "feedback-secret",
    }
    values.update(overrides)
    return values


def test_deployed_persistence_fails_closed_until_every_external_gate_is_set():
    environment = deployed_store_env()
    gate = feedback_persistence_gate(env=environment, env_file=None)

    assert gate.enabled is False
    assert gate.missing_requirements == (
        "QUERY_FEEDBACK_PUBLIC_PERSISTENCE_ENABLED",
        "QUERY_FEEDBACK_LEGAL_BASIS_APPROVED",
        "QUERY_FEEDBACK_PUBLIC_NOTICE_APPROVED",
        "QUERY_FEEDBACK_DELETION_CONTACT",
        "QUERY_FEEDBACK_LIFECYCLE_VERIFIED",
    )

    class NoWriteClient:
        def put_object(self, **_kwargs):
            raise AssertionError("deployed store must remain disabled")

    result = store_feedback_record(
        build_feedback_record(payload(), env=environment),
        env=environment,
        client=NoWriteClient(),
    )
    assert result.stored is False
    assert result.disabled is True

    # The gate blocks new writes, not authorized review/deletion of existing
    # records while public persistence is disabled.
    assert load_feedback_store_config(env=environment, env_file=None) is not None

    enabled = feedback_persistence_gate(
        env=deployed_store_env(
            QUERY_FEEDBACK_PUBLIC_PERSISTENCE_ENABLED="true",
            QUERY_FEEDBACK_LEGAL_BASIS_APPROVED="true",
            QUERY_FEEDBACK_PUBLIC_NOTICE_APPROVED="true",
            QUERY_FEEDBACK_DELETION_CONTACT="privacy@example.test",
            QUERY_FEEDBACK_LIFECYCLE_VERIFIED="true",
        ),
        env_file=None,
    )
    assert enabled.enabled is True


def test_automatic_diagnostics_require_local_opt_in_and_never_run_deployed(monkeypatch):
    local_env = {"QUERY_AUTOMATIC_DIAGNOSTICS_ENABLED": "true"}
    production_env = {
        "QUERY_AUTOMATIC_DIAGNOSTICS_ENABLED": "true",
        "VERCEL": "1",
        "VERCEL_ENV": "production",
    }
    assert automatic_diagnostics_enabled(env={}) is False
    assert automatic_diagnostics_enabled(env=local_env) is True
    assert automatic_diagnostics_enabled(env=production_env) is False

    calls = []
    monkeypatch.setattr(
        "nbatools.query_feedback.store_feedback_record",
        lambda record, env=None, client=None: (
            calls.append(record) or FeedbackStoreResult(stored=True)
        ),
    )
    query_result = {
        "query": "unsupported query",
        "result_status": "no_result",
        "result_reason": "unsupported",
        "result": {"metadata": {}, "sections": {}},
    }

    assert maybe_log_query_diagnostic(query_result, env=production_env) is False
    assert calls == []
    assert maybe_log_query_diagnostic(query_result, env=local_env) is True
    assert len(calls) == 1


def test_public_endpoint_rejects_automatic_submission():
    status, response = handle_feedback_submission(
        payload(feedback_source="automatic"),
        env={},
    )

    assert status == 422
    assert response["error"] == "validation_error"
    assert "explicitly user_submitted" in response["detail"]


def test_free_text_is_redacted_and_unknown_fields_are_dropped():
    record = build_feedback_record(
        payload(
            query=(
                "Jokic user@example.com 313-555-0199 192.0.2.10 "
                "2001:db8::1 password=hunter2 Bearer abcdefghijklmnop"
            ),
            source_page="/results?token=secret-value",
            user_note="Card 4111-1111-1111-1111, api_key=super-secret",
            error_message="Contact admin@example.com with secret=abcd1234",
            metadata={
                "route": "player_game_summary",
                "player": "Nikola Jokic",
                "email": "private@example.com",
                "unknown": "must not persist",
            },
            unexpected_private_field="must not persist",
        ),
        now=datetime(2026, 5, 18, 12, 0, tzinfo=UTC),
        env={},
    )
    serialized = str(record)

    for secret in (
        "user@example.com",
        "313-555-0199",
        "192.0.2.10",
        "2001:db8::1",
        "hunter2",
        "abcdefghijklmnop",
        "4111-1111-1111-1111",
        "super-secret",
        "admin@example.com",
        "abcd1234",
        "private@example.com",
        "must not persist",
    ):
        assert secret not in serialized
    assert "[redacted-email]" in record["query"]
    assert "[redacted-phone]" in record["query"]
    assert "[redacted-ip]" in record["query"]
    assert "[redacted-secret]" in record["query"]
    assert record["source_page"] == "/results"
    assert record["metadata"] == {
        "route": "player_game_summary",
        "player": "Nikola Jokic",
    }


def test_receipt_maps_to_one_key_and_deletion_is_verified():
    feedback_id = "qfb_00000000000040008000000000000001"
    expected_key = "query_feedback/submissions/00000000-0000-4000-8000-000000000001.json"

    class NotFound(Exception):
        response = {
            "Error": {"Code": "NoSuchKey"},
            "ResponseMetadata": {"HTTPStatusCode": 404},
        }

    class FakeClient:
        def __init__(self):
            self.exists = True
            self.deleted = []

        def head_object(self, **kwargs):
            if not self.exists:
                raise NotFound("missing")
            return kwargs

        def delete_object(self, **kwargs):
            self.deleted.append(kwargs)
            self.exists = False

    client = FakeClient()
    receipt = delete_feedback_by_receipt(
        client,
        bucket_name="nbatools-feedback",
        prefix="query_feedback",
        feedback_id=feedback_id,
        now=datetime(2026, 7, 15, 12, 0, tzinfo=UTC),
    )

    assert feedback_key_from_receipt(feedback_id, prefix="query_feedback") == expected_key
    assert client.deleted == [{"Bucket": "nbatools-feedback", "Key": expected_key}]
    assert receipt.result == "deleted"
    assert receipt.feedback_id == feedback_id
    assert receipt.deletion_receipt_id.startswith("qfd_")

    repeated = delete_feedback_by_receipt(
        client,
        bucket_name="nbatools-feedback",
        prefix="query_feedback",
        feedback_id=feedback_id,
        now=datetime(2026, 7, 15, 12, 0, tzinfo=UTC),
    )
    assert repeated.result == "already_absent"
    assert repeated.deletion_receipt_id == receipt.deletion_receipt_id
    assert len(client.deleted) == 1


def test_schema_v2_server_receipt_maps_to_receipts_prefix():
    assert (
        feedback_key_from_receipt(
            "qfb_20260518T120000000000Z_abcd1234",
            prefix="query_feedback",
        )
        == "query_feedback/receipts/qfb_20260518T120000000000Z_abcd1234.json"
    )


def test_invalid_receipt_is_rejected_without_bucket_access():
    with pytest.raises(FeedbackPrivacyError, match="invalid format"):
        feedback_key_from_receipt("../../other-object", prefix="query_feedback")


def test_lifecycle_verification_requires_enabled_rule_at_or_below_90_days():
    class FakeClient:
        def __init__(self, rules):
            self.rules = rules

        def get_bucket_lifecycle_configuration(self, **_kwargs):
            return {"Rules": self.rules}

    verified = verify_feedback_lifecycle(
        FakeClient(
            [
                {
                    "ID": "feedback-90-day-delete",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "query_feedback/"},
                    "Expiration": {"Days": 90},
                }
            ]
        ),
        bucket_name="nbatools-feedback",
        prefix="query_feedback",
    )
    assert verified.expiration_days == 90

    with pytest.raises(FeedbackPrivacyError, match="at or below 90 days"):
        verify_feedback_lifecycle(
            FakeClient(
                [
                    {
                        "ID": "too-long",
                        "Status": "Enabled",
                        "Prefix": "query_feedback/",
                        "Expiration": {"Days": 91},
                    }
                ]
            ),
            bucket_name="nbatools-feedback",
            prefix="query_feedback",
        )
