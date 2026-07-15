from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from nbatools.query_feedback_review import (
    FeedbackReviewError,
    FeedbackReviewFilters,
    TriageOverlayValidationError,
    join_triage_overlays,
    list_feedback_groups,
    load_local_records,
    load_r2_records,
    normalize_records,
    prepare_review_records,
    read_triage_overlay,
    triage_overlay_key,
    validate_triage_overlay_payload,
    write_triage_overlay,
)

pytestmark = pytest.mark.api


def test_shared_grouping_matches_export_contract_and_excludes_overlay(tmp_path: Path):
    local_dir = tmp_path / "feedback"
    records = [
        feedback_record("a", query_normalized_hash="same_hash"),
        feedback_record("b", query_normalized_hash="same_hash"),
    ]
    write_fixture_records(local_dir, records)
    overlay_dir = local_dir / "_triage_overlay" / "groups"
    overlay_dir.mkdir(parents=True)
    (overlay_dir / "qfg_ignore.json").write_text(
        json.dumps({"group_id": "qfg_ignore", "review_status": "reviewed"})
    )

    loaded = load_local_records(local_dir)
    exported_records, groups, excluded_smoke = prepare_review_records(
        loaded,
        FeedbackReviewFilters(),
    )

    assert excluded_smoke == 0
    assert len(exported_records) == 2
    assert len(groups) == 1
    assert groups[0]["count"] == 2
    assert groups[0]["record_ids"] == ["a", "b"]
    assert all("_triage_overlay" not in record.object_key for record in loaded)


def test_triage_overlay_validation_enums_and_required_decision():
    with pytest.raises(TriageOverlayValidationError, match="review_status"):
        validate_triage_overlay_payload("qfg_test", {"review_status": "bad"})

    with pytest.raises(TriageOverlayValidationError, match="triage_decision"):
        validate_triage_overlay_payload(
            "qfg_test",
            {"review_status": "reviewed", "triage_decision": "bad"},
        )

    with pytest.raises(TriageOverlayValidationError, match="required"):
        validate_triage_overlay_payload("qfg_test", {"review_status": "reviewed"})

    overlay = validate_triage_overlay_payload(
        "qfg_test",
        {
            "review_status": "reviewed",
            "triage_decision": "bug",
            "review_notes": "Wrong answer.",
            "linked_case_or_issue": "raw_qa_case_1",
            "reviewer_source": "test",
        },
        existing_group={"record_ids": ["r1"]},
    )

    assert overlay["schema_version"] == 1
    assert overlay["group_id"] == "qfg_test"
    assert overlay["review_status"] == "reviewed"
    assert overlay["triage_decision"] == "bug"
    assert overlay["source_record_ids"] == ["r1"]


def test_triage_overlay_write_and_read_round_trip_without_mutating_sources():
    source_record = feedback_record("source")
    source_key = "query_feedback/preview/2026/05/18/source.json"
    client = FakeR2Client({source_key: json.dumps(source_record).encode("utf-8")})
    env = feedback_env()

    overlay = write_triage_overlay(
        "qfg_test",
        {
            "review_status": "reviewed",
            "triage_decision": "bug",
            "review_notes": "Investigate.",
        },
        existing_group={"record_ids": ["source"]},
        env=env,
        client=client,
    )
    loaded = read_triage_overlay("qfg_test", env=env, client=client)

    key = triage_overlay_key("query_feedback/preview", "qfg_test")
    assert client.put_calls == [key]
    assert json.loads(client.objects[source_key].decode("utf-8")) == source_record
    assert loaded["group_id"] == "qfg_test"
    assert loaded["review_status"] == "reviewed"
    assert loaded["triage_decision"] == "bug"
    assert overlay["source_record_ids"] == ["source"]


def test_list_feedback_groups_joins_overlays_and_supports_overlay_filters():
    source_record = feedback_record("source", query_normalized_hash="same_hash")
    normalized = normalize_records(
        [
            type("Loaded", (), {"record": source_record, "object_key": "ignored.json"})(),
        ]
    )[0]
    exported_records, groups, _ = prepare_review_records(
        [
            type("Loaded", (), {"record": source_record, "object_key": "ignored.json"})(),
        ],
        FeedbackReviewFilters(),
    )
    del normalized, exported_records
    group_id = groups[0]["group_id"]
    overlay_key = triage_overlay_key("query_feedback/preview", group_id)
    client = FakeR2Client(
        {
            "query_feedback/preview/2026/05/18/source.json": json.dumps(source_record).encode(
                "utf-8"
            ),
            overlay_key: json.dumps(
                {
                    "schema_version": 1,
                    "group_id": group_id,
                    "review_status": "reviewed",
                    "triage_decision": "bug",
                }
            ).encode("utf-8"),
        }
    )

    payload = list_feedback_groups(
        FeedbackReviewFilters(review_statuses={"reviewed"}, triage_decisions={"bug"}),
        env=feedback_env(),
        client=client,
    )

    assert payload["group_count"] == 1
    assert payload["groups"][0]["group_id"] == group_id
    assert payload["groups"][0]["triage_overlay"]["review_status"] == "reviewed"
    assert payload["groups"][0]["triage_overlay"]["triage_decision"] == "bug"


def test_r2_review_loader_uses_dedicated_feedback_credentials(monkeypatch):
    source_record = feedback_record("source")
    source_key = "query_feedback/preview/2026/05/18/source.json"
    created_configs = []

    class BucketScopedReviewClient(FakeR2Client):
        def _require_feedback_bucket(self, kwargs):
            if kwargs["Bucket"] != "nbatools-feedback":
                raise PermissionError("cross-bucket operation denied")

        def list_objects_v2(self, **kwargs):
            self._require_feedback_bucket(kwargs)
            return super().list_objects_v2(**kwargs)

        def get_object(self, **kwargs):
            self._require_feedback_bucket(kwargs)
            return super().get_object(**kwargs)

    client = BucketScopedReviewClient({source_key: json.dumps(source_record).encode("utf-8")})

    def fake_create_r2_client(config):
        created_configs.append(config)
        return client

    monkeypatch.setattr(
        "nbatools.query_feedback_review.data_source.create_r2_client",
        fake_create_r2_client,
    )

    records = load_r2_records(
        bucket="nbatools-feedback",
        prefix="query_feedback/preview",
        env={
            **feedback_env(),
            "R2_ACCOUNT_ID": "acct",
            "R2_ACCESS_KEY_ID": "data-read-only-key",
            "R2_SECRET_ACCESS_KEY": "data-read-only-secret",
            "R2_BUCKET_NAME": "nbatools-data",
        },
    )

    assert [record.record["id"] for record in records] == ["source"]
    assert created_configs[0].access_key_id == "feedback-key"
    assert created_configs[0].bucket_name == "nbatools-feedback"
    with pytest.raises(PermissionError, match="cross-bucket"):
        client.get_object(Bucket="nbatools-data", Key=source_key)


def test_feedback_review_fails_closed_without_dedicated_credentials():
    with pytest.raises(FeedbackReviewError, match="QUERY_FEEDBACK_R2_ACCOUNT_ID"):
        list_feedback_groups(
            env={
                "QUERY_FEEDBACK_STORE": "r2",
                "QUERY_FEEDBACK_BUCKET_NAME": "nbatools-feedback",
                "R2_ACCOUNT_ID": "acct",
                "R2_ACCESS_KEY_ID": "data-read-only-key",
                "R2_SECRET_ACCESS_KEY": "data-read-only-secret",
            }
        )


def test_join_triage_overlays_defaults_missing_overlay():
    groups = [{"group_id": "qfg_test", "count": 1}]

    joined = join_triage_overlays(groups, {})

    assert joined[0]["review_status"] == "new"
    assert joined[0]["triage_decision"] is None
    assert joined[0]["triage_overlay"]["group_id"] == "qfg_test"


def feedback_env() -> dict[str, str]:
    return {
        "QUERY_FEEDBACK_STORE": "r2",
        "QUERY_FEEDBACK_BUCKET_NAME": "nbatools-feedback",
        "QUERY_FEEDBACK_PREFIX": "query_feedback/preview",
        "QUERY_FEEDBACK_R2_ACCOUNT_ID": "acct",
        "QUERY_FEEDBACK_R2_ACCESS_KEY_ID": "feedback-key",
        "QUERY_FEEDBACK_R2_SECRET_ACCESS_KEY": "feedback-secret",
    }


def feedback_record(record_id: str, **overrides: Any) -> dict[str, Any]:
    record = {
        "id": record_id,
        "created_at": "2026-05-18T12:00:00.000Z",
        "schema_version": 1,
        "feedback_source": "user_submitted",
        "feedback_type": "wrong_answer",
        "query": f"Query for {record_id}",
        "query_normalized_hash": f"hash_{record_id}",
        "source_page": "/",
        "environment": "preview",
        "route": "season_leaders",
        "status": "ok",
        "reason": None,
        "metadata": {"route": "season_leaders", "unsupported_filters": []},
        "result_shape": {
            "query_class": "leaderboard",
            "section_keys": ["leaderboard"],
            "section_row_counts": {"leaderboard": 3},
        },
        "notes": [],
        "caveats": [],
        "user_note": None,
        "answer_text_preview": "Answer preview",
        "error_message": None,
        "elapsed_ms": 100,
        "review_status": "new",
        "triage_decision": None,
    }
    record.update(overrides)
    return record


def write_fixture_records(local_dir: Path, records: list[dict[str, Any]]) -> None:
    local_dir.mkdir(parents=True)
    for index, record in enumerate(records):
        (local_dir / f"{index:02d}_{record['id']}.json").write_text(json.dumps(record))


class FakeBody:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


class FakeR2Client:
    def __init__(self, objects: dict[str, bytes]):
        self.objects = objects
        self.put_calls: list[str] = []

    def list_objects_v2(self, **kwargs):
        prefix = kwargs.get("Prefix", "")
        return {
            "Contents": [{"Key": key} for key in sorted(self.objects) if key.startswith(prefix)],
            "IsTruncated": False,
        }

    def get_object(self, **kwargs):
        key = kwargs["Key"]
        if key not in self.objects:
            raise FileNotFoundError(key)
        return {"Body": FakeBody(self.objects[key])}

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs["Key"])
        self.objects[kwargs["Key"]] = kwargs["Body"]
