"""Review helpers for immutable query feedback records.

This module owns read-only feedback review grouping plus the mutable triage
overlay. It is intentionally separate from ``query_feedback`` collection code:
source feedback records stay immutable, while review decisions are stored as
independent overlay objects.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, time
from pathlib import Path
from typing import Any

from nbatools import data_source
from nbatools.query_feedback import (
    DISALLOWED_FIELD_NAMES,
    METADATA_ALLOWLIST,
    SLOW_QUERY_WARNING_MS,
    FeedbackStorageError,
    load_feedback_r2_config,
    load_feedback_store_config,
)

SCHEMA_VERSION = 1
TRIAGE_OVERLAY_SCHEMA_VERSION = 1
TRIAGE_OVERLAY_PREFIX_PART = "_triage_overlay"
TRIAGE_OVERLAY_NOT_FOUND: dict[str, Any] = {
    "schema_version": TRIAGE_OVERLAY_SCHEMA_VERSION,
    "review_status": "new",
    "triage_decision": None,
    "review_notes": "",
    "linked_case_or_issue": "",
    "reviewer_source": None,
    "updated_at": None,
}

ALLOWED_REVIEW_STATUSES = {"new", "reviewed", "deferred", "closed"}
ALLOWED_TRIAGE_DECISIONS = {
    "bug",
    "support_candidate",
    "expected_unsupported",
    "duplicate",
    "no_action",
    "needs_more_data",
    "parser_routing_risk",
    "ui_copy_issue",
}
REVIEW_NOTES_MAX_LENGTH = 2000
LINKED_CASE_MAX_LENGTH = 240
REVIEWER_SOURCE_MAX_LENGTH = 120

TRIAGE_PRIORITY = [
    "parser_issue",
    "raw_qa_case",
    "data_issue",
    "unsupported_family",
    "visual_qa_case",
    "frontend_copy_case",
    "performance_review",
    "no_action",
]

RAW_OR_PII_KEYS = DISALLOWED_FIELD_NAMES | {
    "raw_rows",
    "row",
    "rows",
    "section_rows",
    "sections",
    "table",
    "tables",
}


class FeedbackReviewError(RuntimeError):
    """Raised when review storage cannot be read or written."""


class TriageOverlayValidationError(ValueError):
    """Raised when a mutable triage overlay payload is invalid."""


def _require_feedback_store_config(env: dict[str, str] | None):
    try:
        config = load_feedback_store_config(env=env)
    except FeedbackStorageError as exc:
        raise FeedbackReviewError(str(exc)) from exc
    if config is None:
        raise FeedbackReviewError("Query feedback store is not configured")
    return config


@dataclass(frozen=True)
class LoadedFeedbackRecord:
    record: dict[str, Any]
    object_key: str
    last_modified: datetime | None = None


@dataclass(frozen=True)
class FeedbackReviewFilters:
    since: datetime | None = None
    until: datetime | None = None
    sources: set[str] | None = None
    feedback_types: set[str] | None = None
    statuses: set[str] | None = None
    routes: set[str] | None = None
    reasons: set[str] | None = None
    review_statuses: set[str] | None = None
    triage_decisions: set[str] | None = None
    include_smoke: bool = False
    limit: int | None = None


def parse_multi_filter(values: list[str] | tuple[str, ...] | None) -> set[str]:
    result: set[str] = set()
    for value in values or []:
        for part in str(value).split(","):
            text = part.strip()
            if text:
                result.add(text)
    return result


def parse_datetime_filter(value: str | None, *, is_until: bool) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        date_value = datetime.strptime(text, "%Y-%m-%d").date()
        boundary_time = time.max if is_until else time.min
        return datetime.combine(date_value, boundary_time, tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid datetime filter: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def load_local_records(local_dir: Path) -> list[LoadedFeedbackRecord]:
    if not local_dir.exists():
        raise FileNotFoundError(f"Local feedback directory does not exist: {local_dir}")
    records: list[LoadedFeedbackRecord] = []
    for path in sorted(local_dir.rglob("*.json")):
        relative_key = path.relative_to(local_dir).as_posix()
        if _is_triage_overlay_key(relative_key):
            continue
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError(f"Feedback JSON must be an object: {path}")
        records.append(
            LoadedFeedbackRecord(
                record=data,
                object_key=relative_key,
                last_modified=datetime.fromtimestamp(path.stat().st_mtime, tz=UTC),
            )
        )
    return records


def load_r2_records(
    *,
    bucket: str,
    prefix: str,
    env: dict[str, str] | None = None,
    client: Any | None = None,
) -> list[LoadedFeedbackRecord]:
    if client is None:
        config = load_feedback_r2_config(env=env, bucket_name=bucket)
        r2_client = data_source.create_r2_client(config)
    else:
        r2_client = client
    records: list[LoadedFeedbackRecord] = []
    continuation_token: str | None = None
    prefix_value = prefix.strip("/")

    while True:
        kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix_value}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        response = r2_client.list_objects_v2(**kwargs)
        for item in response.get("Contents", []):
            key = str(item.get("Key") or "")
            if (
                not key
                or key.endswith("/")
                or not key.endswith(".json")
                or _is_triage_overlay_key(key)
            ):
                continue
            object_response = r2_client.get_object(Bucket=bucket, Key=key)
            data = json.loads(read_body_text(object_response.get("Body")))
            if not isinstance(data, dict):
                raise ValueError(f"Feedback JSON must be an object: {key}")
            last_modified = item.get("LastModified")
            records.append(
                LoadedFeedbackRecord(
                    record=data,
                    object_key=key,
                    last_modified=last_modified if isinstance(last_modified, datetime) else None,
                )
            )

        if not response.get("IsTruncated"):
            break
        continuation_token = response.get("NextContinuationToken")
        if not continuation_token:
            break

    return records


def read_body_text(body: Any) -> str:
    payload = body.read() if hasattr(body, "read") else body
    if isinstance(payload, bytes):
        return payload.decode("utf-8")
    return str(payload)


def normalize_record(loaded: LoadedFeedbackRecord) -> dict[str, Any]:
    record = loaded.record
    metadata = safe_metadata(record.get("metadata"))
    result_shape = (
        record.get("result_shape") if isinstance(record.get("result_shape"), dict) else {}
    )
    deployment = record.get("deployment") if isinstance(record.get("deployment"), dict) else {}
    query = clean_text(record.get("query"))
    unsupported_filters = normalize_string_list(
        metadata.get("unsupported_filters") or record.get("unsupported_filters")
    )
    section_row_counts = safe_section_counts(result_shape.get("section_row_counts"))
    section_keys = normalize_string_list(result_shape.get("section_keys")) or sorted(
        section_row_counts
    )

    normalized: dict[str, Any] = {
        "id": clean_text(record.get("id")),
        "created_at": clean_text(record.get("created_at")),
        "schema_version": record.get("schema_version"),
        "feedback_source": clean_text(record.get("feedback_source")),
        "feedback_type": clean_text(record.get("feedback_type")),
        "query": query,
        "query_normalized": normalize_query(query),
        "query_normalized_hash": clean_text(record.get("query_normalized_hash")),
        "source_page": clean_text(record.get("source_page")),
        "environment": clean_text(record.get("environment")),
        "deployment_vercel_url": clean_text(deployment.get("vercel_url")),
        "deployment_vercel_git_commit_sha": clean_text(deployment.get("vercel_git_commit_sha")),
        "route": clean_text(record.get("route")),
        "status": clean_text(record.get("status")),
        "reason": clean_text(record.get("reason")),
        "unsupported_filters": unsupported_filters,
        "metadata_summary": metadata,
        "result_query_class": clean_text(result_shape.get("query_class")),
        "result_section_keys": section_keys,
        "result_section_row_counts": section_row_counts,
        "notes": normalize_string_list(record.get("notes")),
        "caveats": normalize_string_list(record.get("caveats")),
        "user_note": clean_text(record.get("user_note")),
        "answer_text_preview": clean_text(record.get("answer_text_preview")),
        "error_message": clean_text(record.get("error_message")),
        "elapsed_ms": number_or_none(record.get("elapsed_ms")),
        "review_status": clean_text(record.get("review_status")),
        "triage_decision": clean_text(record.get("triage_decision")),
        "is_smoke": False,
        "group_id": "",
        "suggested_triage": "",
        "triage_modifiers": [],
        "object_key": loaded.object_key,
    }
    normalized["is_smoke"] = is_smoke_record(normalized)
    normalized["suggested_triage"] = suggest_triage(normalized)
    return normalized


def normalize_records(loaded_records: list[LoadedFeedbackRecord]) -> list[dict[str, Any]]:
    return [normalize_record(loaded) for loaded in loaded_records]


def prepare_review_records(
    loaded_records: list[LoadedFeedbackRecord],
    filters: FeedbackReviewFilters,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    normalized_records = normalize_records(loaded_records)
    records_after_filters = [
        record for record in normalized_records if record_matches_base_filters(record, filters)
    ]

    exported_records: list[dict[str, Any]] = []
    excluded_smoke_count = 0
    for record in records_after_filters:
        if record["is_smoke"] and not filters.include_smoke:
            excluded_smoke_count += 1
            continue
        exported_records.append(record)

    if filters.limit is not None:
        exported_records = exported_records[: filters.limit]

    groups = group_records(exported_records)
    return exported_records, groups, excluded_smoke_count


def group_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        key = grouping_key(record)
        buckets.setdefault(key, []).append(record)

    groups: list[dict[str, Any]] = []
    for key, group_records_value in buckets.items():
        group_id = deterministic_group_id(key)
        group = build_group(group_id, group_records_value)
        groups.append(group)
        for record in group_records_value:
            record["group_id"] = group_id
            record["triage_modifiers"] = list(group["triage_modifiers"])

    groups.sort(key=lambda group: (group["first_seen"], group["group_id"]))
    return groups


def join_triage_overlays(
    groups: list[dict[str, Any]],
    overlays: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    joined: list[dict[str, Any]] = []
    for group in groups:
        overlay = default_triage_overlay(group["group_id"])
        if group["group_id"] in overlays:
            overlay = {**overlay, **overlays[group["group_id"]]}
        joined_group = {**group, "triage_overlay": overlay}
        joined_group["review_status"] = overlay.get("review_status") or "new"
        joined_group["triage_decision"] = overlay.get("triage_decision")
        joined.append(joined_group)
    return joined


def filter_groups_with_overlay(
    groups: list[dict[str, Any]],
    filters: FeedbackReviewFilters,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    review_statuses = filters.review_statuses or set()
    triage_decisions = filters.triage_decisions or set()
    for group in groups:
        overlay = (
            group.get("triage_overlay") if isinstance(group.get("triage_overlay"), dict) else {}
        )
        review_status = overlay.get("review_status") or "new"
        triage_decision = overlay.get("triage_decision")
        if review_statuses and review_status not in review_statuses:
            continue
        if triage_decisions and (triage_decision or "") not in triage_decisions:
            continue
        result.append(group)
    return result


def record_matches_base_filters(record: dict[str, Any], filters: FeedbackReviewFilters) -> bool:
    created_at = parse_record_datetime(record.get("created_at"))
    if filters.since is not None and (created_at is None or created_at < filters.since):
        return False
    if filters.until is not None and (created_at is None or created_at > filters.until):
        return False
    if filters.sources and record.get("feedback_source") not in filters.sources:
        return False
    if filters.feedback_types and record.get("feedback_type") not in filters.feedback_types:
        return False
    if filters.statuses and record.get("status") not in filters.statuses:
        return False
    if filters.routes and record.get("route") not in filters.routes:
        return False
    return not (filters.reasons and record.get("reason") not in filters.reasons)


def record_matches_filters(record: dict[str, Any], filters: FeedbackReviewFilters) -> bool:
    """Compatibility alias used by the export workflow."""
    return record_matches_base_filters(record, filters)


def validate_triage_overlay_payload(
    group_id: str,
    payload: dict[str, Any],
    *,
    existing_group: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TriageOverlayValidationError("Triage overlay payload must be a JSON object")

    supplied_group_id = clean_text(payload.get("group_id"))
    if supplied_group_id and supplied_group_id != group_id:
        raise TriageOverlayValidationError("Overlay group_id must match request group_id")

    review_status = clean_text(payload.get("review_status")) or "new"
    if review_status not in ALLOWED_REVIEW_STATUSES:
        choices = ", ".join(sorted(ALLOWED_REVIEW_STATUSES))
        raise TriageOverlayValidationError(f"review_status must be one of: {choices}")

    triage_decision = clean_text(payload.get("triage_decision")) or None
    if triage_decision is not None and triage_decision not in ALLOWED_TRIAGE_DECISIONS:
        choices = ", ".join(sorted(ALLOWED_TRIAGE_DECISIONS))
        raise TriageOverlayValidationError(f"triage_decision must be one of: {choices}")
    if review_status in {"reviewed", "closed"} and triage_decision is None:
        raise TriageOverlayValidationError(
            "triage_decision is required when review_status is reviewed or closed"
        )

    updated_at = (
        (now or datetime.now(UTC))
        .astimezone(UTC)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )
    group_record_ids = existing_group.get("record_ids", []) if existing_group else []
    return {
        "schema_version": TRIAGE_OVERLAY_SCHEMA_VERSION,
        "group_id": group_id,
        "updated_at": updated_at,
        "review_status": review_status,
        "triage_decision": triage_decision,
        "review_notes": clean_text(payload.get("review_notes"))[:REVIEW_NOTES_MAX_LENGTH],
        "linked_case_or_issue": clean_text(payload.get("linked_case_or_issue"))[
            :LINKED_CASE_MAX_LENGTH
        ],
        "reviewer_source": clean_text(payload.get("reviewer_source"))[:REVIEWER_SOURCE_MAX_LENGTH]
        or None,
        "source_record_ids": normalize_string_list(
            payload.get("source_record_ids") or group_record_ids
        ),
    }


def default_triage_overlay(group_id: str) -> dict[str, Any]:
    return {**TRIAGE_OVERLAY_NOT_FOUND, "group_id": group_id}


def triage_overlay_key(prefix: str, group_id: str) -> str:
    safe_group_id = safe_key_token(group_id)
    return f"{prefix.strip('/')}/{TRIAGE_OVERLAY_PREFIX_PART}/groups/{safe_group_id}.json"


def read_triage_overlay(
    group_id: str,
    *,
    env: dict[str, str] | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    config = _require_feedback_store_config(env)
    r2_client = client or data_source.create_r2_client(config.r2)
    key = triage_overlay_key(config.prefix, group_id)
    try:
        response = r2_client.get_object(Bucket=config.bucket_name, Key=key)
    except Exception as exc:  # pragma: no cover - exact boto shape varies
        if _is_not_found(exc):
            return default_triage_overlay(group_id)
        raise FeedbackReviewError(f"Could not read triage overlay: {exc}") from exc
    data = json.loads(read_body_text(response.get("Body")))
    if not isinstance(data, dict):
        raise FeedbackReviewError(f"Triage overlay JSON must be an object: {key}")
    return {**default_triage_overlay(group_id), **data}


def write_triage_overlay(
    group_id: str,
    payload: dict[str, Any],
    *,
    existing_group: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    config = _require_feedback_store_config(env)
    overlay = validate_triage_overlay_payload(group_id, payload, existing_group=existing_group)
    key = triage_overlay_key(config.prefix, group_id)
    body = json.dumps(overlay, sort_keys=True, separators=(",", ":")).encode("utf-8")
    r2_client = client or data_source.create_r2_client(config.r2)
    try:
        r2_client.put_object(
            Bucket=config.bucket_name,
            Key=key,
            Body=body,
            ContentType="application/json",
        )
    except Exception as exc:  # pragma: no cover - exact boto shape varies
        raise FeedbackReviewError(f"Could not write triage overlay: {exc}") from exc
    return overlay


def list_triage_overlays(
    *,
    prefix: str,
    bucket: str,
    client: Any,
) -> dict[str, dict[str, Any]]:
    overlay_prefix = f"{prefix.strip('/')}/{TRIAGE_OVERLAY_PREFIX_PART}/groups"
    overlays: dict[str, dict[str, Any]] = {}
    continuation_token: str | None = None
    while True:
        kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": overlay_prefix}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        response = client.list_objects_v2(**kwargs)
        for item in response.get("Contents", []):
            key = str(item.get("Key") or "")
            if not key.endswith(".json"):
                continue
            object_response = client.get_object(Bucket=bucket, Key=key)
            data = json.loads(read_body_text(object_response.get("Body")))
            if isinstance(data, dict) and (group_id := clean_text(data.get("group_id"))):
                overlays[group_id] = {**default_triage_overlay(group_id), **data}
        if not response.get("IsTruncated"):
            break
        continuation_token = response.get("NextContinuationToken")
        if not continuation_token:
            break
    return overlays


def list_feedback_groups(
    filters: FeedbackReviewFilters | None = None,
    *,
    env: dict[str, str] | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    config = _require_feedback_store_config(env)
    r2_client = client or data_source.create_r2_client(config.r2)
    filters = filters or FeedbackReviewFilters()
    loaded_records = load_r2_records(
        bucket=config.bucket_name,
        prefix=config.prefix,
        client=r2_client,
    )
    records, groups, excluded_smoke_count = prepare_review_records(loaded_records, filters)
    overlays = list_triage_overlays(
        prefix=config.prefix,
        bucket=config.bucket_name,
        client=r2_client,
    )
    joined_groups = filter_groups_with_overlay(join_triage_overlays(groups, overlays), filters)
    return {
        "ok": True,
        "source_mode": "r2",
        "bucket": config.bucket_name,
        "prefix": config.prefix,
        "total_found": len(loaded_records),
        "total_exported": len(records),
        "excluded_smoke_count": excluded_smoke_count,
        "group_count": len(joined_groups),
        "groups": joined_groups,
    }


def get_feedback_group_detail(
    group_id: str,
    filters: FeedbackReviewFilters | None = None,
    *,
    env: dict[str, str] | None = None,
    client: Any | None = None,
) -> dict[str, Any] | None:
    payload = list_feedback_groups(filters=filters, env=env, client=client)
    group = next((item for item in payload["groups"] if item.get("group_id") == group_id), None)
    if group is None:
        return None
    record_ids = set(group.get("record_ids", []))
    config = _require_feedback_store_config(env)
    r2_client = client or data_source.create_r2_client(config.r2)
    loaded_records = load_r2_records(
        bucket=config.bucket_name,
        prefix=config.prefix,
        client=r2_client,
    )
    records = [
        record for record in normalize_records(loaded_records) if record.get("id") in record_ids
    ]
    return {
        "ok": True,
        "group": group,
        "records": records,
        "triage_overlay": group.get("triage_overlay") or default_triage_overlay(group_id),
        "handoff_summary": build_handoff_summary(group, records),
    }


def build_handoff_summary(group: dict[str, Any], records: list[dict[str, Any]]) -> str:
    lines = [
        f"Group: {group.get('group_id')}",
        f"Representative query: {group.get('representative_query')}",
        f"Count: {group.get('count')}",
        f"Sources: {', '.join(group.get('feedback_sources', [])) or 'none'}",
        f"Types: {', '.join(group.get('feedback_types', [])) or 'none'}",
        f"Routes: {', '.join(group.get('routes', [])) or 'none'}",
        f"Statuses: {', '.join(group.get('statuses', [])) or 'none'}",
        f"Reasons: {', '.join(group.get('reasons', [])) or 'none'}",
        f"Suggested triage: {group.get('suggested_triage') or 'none'}",
    ]
    user_notes = [record.get("user_note") for record in records if record.get("user_note")]
    if user_notes:
        lines.append("User notes:")
        lines.extend(f"- {note}" for note in user_notes[:5])
    return "\n".join(lines)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_query(query: str) -> str:
    return " ".join(query.lower().split())


def normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    result: list[str] = []
    for item in values:
        text = clean_text(item)
        if text and text not in result:
            result.append(text)
    return result


def number_or_none(value: Any) -> int | float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value
    try:
        return float(str(value))
    except ValueError:
        return None


def safe_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for key, raw_value in value.items():
        key_text = clean_text(key)
        if not key_text or key_text in RAW_OR_PII_KEYS or key_text not in METADATA_ALLOWLIST:
            continue
        clean_value = strip_disallowed_value(raw_value)
        if clean_value is not None:
            result[key_text] = clean_value
    return result


def strip_disallowed_value(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, list):
        return [clean for item in value if (clean := strip_disallowed_value(item)) is not None]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, raw_item in value.items():
            key_text = clean_text(key)
            if not key_text or key_text in RAW_OR_PII_KEYS:
                continue
            clean_item = strip_disallowed_value(raw_item)
            if clean_item is not None:
                result[key_text] = clean_item
        return result
    return clean_text(value)


def safe_section_counts(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    counts: dict[str, int] = {}
    for key, raw_count in value.items():
        key_text = clean_text(key)
        count = number_or_none(raw_count)
        if key_text and count is not None and count >= 0:
            counts[key_text] = int(count)
    return counts


def is_smoke_record(record: dict[str, Any]) -> bool:
    query = str(record.get("query", "")).lower()
    user_note = str(record.get("user_note", "")).lower()
    route = str(record.get("route", "")).lower()
    reason = str(record.get("reason", "")).lower()
    feedback_type = str(record.get("feedback_type", "")).lower()
    source_page = str(record.get("source_page", "")).lower()
    environment = str(record.get("environment", "")).lower()
    deployment_url = str(record.get("deployment_vercel_url", "")).lower()

    if "smoke" in query:
        return True
    if "smoke test" in user_note:
        return True
    if route == "smoke" or reason == "smoke":
        return True
    if feedback_type == "other" and "direct endpoint smoke" in query:
        return True
    return any(
        label in {"smoke", "smoke-test", "test", "testing"}
        or "smoke" in label
        or label.endswith("/smoke")
        or label.endswith("/test")
        for label in (source_page, environment, deployment_url)
        if label
    )


def suggest_triage(record: dict[str, Any]) -> str:
    if record.get("is_smoke"):
        return "no_action"
    status = record.get("status")
    reason = record.get("reason")
    feedback_type = record.get("feedback_type")
    feedback_source = record.get("feedback_source")
    elapsed_ms = record.get("elapsed_ms")

    if status == "error" and reason == "unrouted":
        return "parser_issue"
    if status == "no_result" and reason == "filter_not_supported":
        return "unsupported_family"
    if status == "no_result" and reason == "no_data":
        return "data_issue"
    if feedback_type == "wrong_answer":
        return "raw_qa_case"
    if feedback_type == "confusing_answer":
        return "frontend_copy_case"
    if feedback_type == "ui_issue":
        return "visual_qa_case"
    if (
        feedback_source == "automatic"
        and status == "ok"
        and isinstance(elapsed_ms, int | float)
        and elapsed_ms >= SLOW_QUERY_WARNING_MS
    ):
        return "performance_review"
    return "no_action"


def parse_record_datetime(value: Any) -> datetime | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def grouping_key(record: dict[str, Any]) -> str:
    query_hash = record.get("query_normalized_hash")
    if query_hash:
        return f"hash|{query_hash}"
    fallback_parts = [
        str(record.get("query_normalized") or ""),
        str(record.get("route") or ""),
        str(record.get("status") or ""),
        str(record.get("reason") or ""),
        json.dumps(sorted(record.get("unsupported_filters") or []), sort_keys=True),
        str(record.get("feedback_type") or ""),
    ]
    return "fallback|" + "|".join(fallback_parts)


def deterministic_group_id(key: str) -> str:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"qfg_{digest}"


def build_group(group_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    sorted_records = sorted(records, key=record_sort_key)
    user_submitted_count = sum(
        1 for record in sorted_records if record.get("feedback_source") == "user_submitted"
    )
    modifiers: list[str] = []
    if len(sorted_records) >= 3 or user_submitted_count >= 2:
        modifiers.append("prioritize_review")

    return {
        "group_id": group_id,
        "count": len(sorted_records),
        "first_seen": first_non_empty(record.get("created_at") for record in sorted_records),
        "last_seen": last_non_empty(record.get("created_at") for record in sorted_records),
        "representative_query": first_non_empty(record.get("query") for record in sorted_records),
        "feedback_sources": sorted(
            unique_values(record.get("feedback_source") for record in records)
        ),
        "feedback_types": sorted(unique_values(record.get("feedback_type") for record in records)),
        "routes": sorted(unique_values(record.get("route") for record in records)),
        "statuses": sorted(unique_values(record.get("status") for record in records)),
        "reasons": sorted(unique_values(record.get("reason") for record in records)),
        "unsupported_filters": sorted(
            {
                unsupported_filter
                for record in records
                for unsupported_filter in record.get("unsupported_filters", [])
                if unsupported_filter
            }
        ),
        "user_notes": unique_ordered(record.get("user_note") for record in sorted_records),
        "record_ids": unique_ordered(record.get("id") for record in sorted_records),
        "object_keys": unique_ordered(record.get("object_key") for record in sorted_records),
        "suggested_triage": group_suggested_triage(records),
        "triage_modifiers": modifiers,
    }


def record_sort_key(record: dict[str, Any]) -> tuple[str, str]:
    created_at = record.get("created_at") or ""
    return (str(created_at), str(record.get("id") or ""))


def first_non_empty(values: Any) -> str:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


def last_non_empty(values: Any) -> str:
    result = ""
    for value in values:
        text = clean_text(value)
        if text:
            result = text
    return result


def unique_values(values: Any) -> set[str]:
    return {text for value in values if (text := clean_text(value))}


def unique_ordered(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        text = clean_text(value)
        if text and text not in result:
            result.append(text)
    return result


def group_suggested_triage(records: list[dict[str, Any]]) -> str:
    suggestions = {record.get("suggested_triage") or "no_action" for record in records}
    for triage in TRIAGE_PRIORITY:
        if triage in suggestions:
            return triage
    return "no_action"


def safe_key_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._") or "unknown"


def _is_triage_overlay_key(key: str) -> bool:
    return f"/{TRIAGE_OVERLAY_PREFIX_PART}/" in f"/{key.strip('/')}/"


def _is_not_found(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        error = response.get("Error", {})
        code = str(error.get("Code", ""))
        if code in {"404", "NoSuchKey", "NotFound"}:
            return True
    return isinstance(exc, FileNotFoundError)
