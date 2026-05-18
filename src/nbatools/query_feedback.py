"""Query feedback validation, sanitization, and durable storage helpers.

This module is intentionally API-adjacent rather than query-engine-adjacent:
feedback writes are side effects for HTTP surfaces and must not affect core
query behavior.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any

from nbatools.data_source import R2Config, create_r2_client

SCHEMA_VERSION = 1

ALLOWED_FEEDBACK_SOURCES = {"automatic", "user_submitted"}
ALLOWED_FEEDBACK_TYPES = {
    "wrong_answer",
    "expected_supported",
    "confusing_answer",
    "no_result",
    "unsupported",
    "error",
    "ui_issue",
    "other",
}

QUERY_MAX_LENGTH = 500
USER_NOTE_MAX_LENGTH = 1000
ERROR_MESSAGE_MAX_LENGTH = 500
ANSWER_TEXT_PREVIEW_MAX_LENGTH = 500
METADATA_TEXT_MAX_LENGTH = 240
NOTES_MAX_ITEMS = 8
LIST_MAX_ITEMS = 20
DICT_MAX_ITEMS = 30
SLOW_QUERY_WARNING_MS = 8000

QUERY_FEEDBACK_STORE_ENV = "QUERY_FEEDBACK_STORE"
QUERY_FEEDBACK_BUCKET_ENV = "QUERY_FEEDBACK_BUCKET_NAME"
QUERY_FEEDBACK_PREFIX_ENV = "QUERY_FEEDBACK_PREFIX"
DEFAULT_QUERY_FEEDBACK_PREFIX = "query_feedback"

SUPPRESSED_SOURCE_PAGES = {"/review", "/visual-qa"}
AUTOMATIC_DIAGNOSTIC_REASONS = {
    "filter_not_supported",
    "unsupported",
    "no_data",
    "unrouted",
}

DISALLOWED_FIELD_NAMES = {
    "account",
    "email",
    "full_raw_result",
    "full_result",
    "ip",
    "ip_address",
    "name",
    "phone",
    "raw_result",
    "result",
    "session_replay",
    "user_account",
    "user_id",
}

METADATA_ALLOWLIST = {
    "applied_filters",
    "answer_phrase",
    "confidence",
    "count_phrase",
    "current_through",
    "date",
    "end_date",
    "end_season",
    "filter",
    "filters",
    "intent",
    "last_n",
    "metric",
    "opponent",
    "opponent_context",
    "opponent_group",
    "opponent_quality",
    "opponent_team_abbrs",
    "opponents",
    "player",
    "player_context",
    "players",
    "players_context",
    "primary_count",
    "query_class",
    "reason",
    "result_shape",
    "route",
    "scope_kind",
    "season",
    "season_type",
    "split_type",
    "start_date",
    "start_season",
    "stat",
    "status",
    "target_metric",
    "target_stat",
    "team",
    "team_context",
    "teams",
    "teams_context",
    "unsupported_filters",
}


class FeedbackValidationError(ValueError):
    """Raised when a feedback payload fails schema validation."""


class FeedbackStorageError(RuntimeError):
    """Raised when a configured feedback store fails to persist a record."""


@dataclass(frozen=True)
class FeedbackStoreConfig:
    """R2-backed query feedback store configuration."""

    store: str
    bucket_name: str
    prefix: str
    r2: R2Config


@dataclass(frozen=True)
class FeedbackStoreResult:
    """Result of attempting to persist a feedback record."""

    stored: bool
    disabled: bool = False
    key: str | None = None
    reason: str | None = None


def build_feedback_record(
    payload: dict[str, Any],
    *,
    now: datetime | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Validate and sanitize a submitted feedback payload."""
    if not isinstance(payload, dict):
        raise FeedbackValidationError("Feedback payload must be a JSON object")

    query = _required_text(payload, "query", QUERY_MAX_LENGTH)
    feedback_source = _required_choice(
        payload,
        "feedback_source",
        ALLOWED_FEEDBACK_SOURCES,
    )
    feedback_type = _required_choice(
        payload,
        "feedback_type",
        ALLOWED_FEEDBACK_TYPES,
    )

    created_at_dt = now.astimezone(UTC) if now else datetime.now(UTC)
    created_at = _isoformat_z(created_at_dt)
    record_id = _feedback_id(created_at_dt)
    status = _optional_text(payload, "status", METADATA_TEXT_MAX_LENGTH)
    reason = _optional_text(payload, "reason", METADATA_TEXT_MAX_LENGTH)
    route = _optional_text(payload, "route", METADATA_TEXT_MAX_LENGTH)
    source_page = normalize_source_page(payload.get("source_page"))

    record: dict[str, Any] = {
        "id": record_id,
        "created_at": created_at,
        "schema_version": SCHEMA_VERSION,
        "feedback_source": feedback_source,
        "feedback_type": feedback_type,
        "query": query,
        "query_normalized_hash": _query_hash(query, route, status, reason),
        "source_page": source_page,
        "environment": _environment_name(env),
        "route": route,
        "status": status,
        "reason": reason,
        "result_shape": sanitize_result_shape(payload),
        "metadata": sanitize_metadata(payload.get("metadata")),
        "notes": _sanitize_text_list(payload.get("notes"), NOTES_MAX_ITEMS),
        "caveats": _sanitize_text_list(payload.get("caveats"), NOTES_MAX_ITEMS),
        "user_note": _optional_text(payload, "user_note", USER_NOTE_MAX_LENGTH),
        "error_message": _optional_text(
            payload,
            "error_message",
            ERROR_MESSAGE_MAX_LENGTH,
        ),
        "answer_text_preview": _optional_text(
            payload,
            "answer_text_preview",
            ANSWER_TEXT_PREVIEW_MAX_LENGTH,
        ),
        "elapsed_ms": _optional_non_negative_number(payload.get("elapsed_ms")),
        "review_status": "new",
        "triage_decision": None,
    }

    deployment = _deployment_context(env)
    if deployment:
        record["deployment"] = deployment

    return record


def sanitize_metadata(value: Any) -> dict[str, Any]:
    """Return only compact, allowlisted diagnostic metadata."""
    if not isinstance(value, dict):
        return {}

    sanitized: dict[str, Any] = {}
    for key, raw_value in value.items():
        if key in DISALLOWED_FIELD_NAMES or key not in METADATA_ALLOWLIST:
            continue
        clean_value = _sanitize_compact_value(raw_value, depth=0)
        if clean_value is not None:
            sanitized[key] = clean_value
    return sanitized


def sanitize_result_shape(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a compact result-shape snapshot without storing result rows."""
    supplied = payload.get("result_shape")
    if isinstance(supplied, dict):
        section_counts = supplied.get("section_row_counts")
        if not isinstance(section_counts, dict):
            section_counts = supplied.get("row_counts")
        shape = {
            "query_class": _clean_text(supplied.get("query_class"), METADATA_TEXT_MAX_LENGTH),
            "section_keys": _sanitize_string_list(supplied.get("section_keys"), LIST_MAX_ITEMS),
            "section_row_counts": _sanitize_section_counts(section_counts),
        }
        return {key: value for key, value in shape.items() if value}

    result = payload.get("result")
    if not isinstance(result, dict):
        return {}

    sections = result.get("sections")
    section_counts = _section_counts_from_sections(sections)
    shape = {
        "query_class": _clean_text(result.get("query_class"), METADATA_TEXT_MAX_LENGTH),
        "section_keys": sorted(section_counts),
        "section_row_counts": section_counts,
    }
    return {key: value for key, value in shape.items() if value}


def store_feedback_record(
    record: dict[str, Any],
    *,
    env: dict[str, str] | None = None,
    client: Any | None = None,
) -> FeedbackStoreResult:
    """Persist a sanitized feedback record to the configured store."""
    config = load_feedback_store_config(env=env)
    if config is None:
        return FeedbackStoreResult(
            stored=False,
            disabled=True,
            reason="QUERY_FEEDBACK_STORE is not configured",
        )

    key = feedback_object_key(record, prefix=config.prefix)
    body = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    r2_client = client or create_r2_client(config.r2)

    try:
        r2_client.put_object(
            Bucket=config.bucket_name,
            Key=key,
            Body=body,
            ContentType="application/json",
        )
    except Exception as exc:  # pragma: no cover - exact boto error shape varies
        raise FeedbackStorageError(f"Could not store query feedback record: {exc}") from exc

    return FeedbackStoreResult(stored=True, disabled=False, key=key)


def load_feedback_store_config(
    *,
    env: dict[str, str] | None = None,
    env_file: Path | None = Path(".env"),
) -> FeedbackStoreConfig | None:
    """Load query-feedback storage config, returning None when disabled."""
    values = _merged_env(env, env_file)
    store = values.get(QUERY_FEEDBACK_STORE_ENV, "").strip().lower()
    if not store:
        return None
    if store != "r2":
        raise FeedbackStorageError("QUERY_FEEDBACK_STORE must be 'r2' when configured")

    bucket_name = values.get(QUERY_FEEDBACK_BUCKET_ENV, "").strip()
    if not bucket_name:
        return None

    r2_values = dict(values)
    r2_values["R2_BUCKET_NAME"] = bucket_name
    missing = [
        key
        for key in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")
        if not r2_values.get(key)
    ]
    if missing:
        return None

    prefix = values.get(QUERY_FEEDBACK_PREFIX_ENV, DEFAULT_QUERY_FEEDBACK_PREFIX).strip("/ ")
    if not prefix:
        prefix = DEFAULT_QUERY_FEEDBACK_PREFIX

    return FeedbackStoreConfig(
        store=store,
        bucket_name=bucket_name,
        prefix=prefix,
        r2=R2Config(
            account_id=r2_values["R2_ACCOUNT_ID"],
            access_key_id=r2_values["R2_ACCESS_KEY_ID"],
            secret_access_key=r2_values["R2_SECRET_ACCESS_KEY"],
            bucket_name=bucket_name,
        ),
    )


def feedback_object_key(record: dict[str, Any], *, prefix: str) -> str:
    """Return the immutable R2 object key for a feedback record."""
    created_at = str(record.get("created_at") or _isoformat_z(datetime.now(UTC)))
    dt = _parse_created_at(created_at)
    created_at_ms = int(dt.timestamp() * 1000)
    short_id = str(record.get("id") or secrets.token_hex(4))[-8:]
    return f"{prefix.strip('/')}/{dt:%Y/%m/%d}/{created_at_ms}_{_safe_key_token(short_id)}.json"


def handle_feedback_submission(
    payload: dict[str, Any],
    *,
    source_page: str | None = None,
    env: dict[str, str] | None = None,
    client: Any | None = None,
) -> tuple[int, dict[str, Any]]:
    """Validate, store, and format an API response for a feedback submission."""
    if source_page and isinstance(payload, dict):
        payload = {**payload, "source_page": payload.get("source_page") or source_page}

    try:
        record = build_feedback_record(payload, env=env)
    except FeedbackValidationError as exc:
        return HTTPStatus.UNPROCESSABLE_ENTITY, {
            "ok": False,
            "error": "validation_error",
            "detail": str(exc),
        }

    try:
        result = store_feedback_record(record, env=env, client=client)
    except FeedbackStorageError as exc:
        return HTTPStatus.INTERNAL_SERVER_ERROR, {
            "ok": False,
            "error": "feedback_storage_error",
            "detail": str(exc),
        }

    return HTTPStatus.OK, {
        "ok": True,
        "feedback_id": record["id"],
        "stored": result.stored,
        "disabled": result.disabled,
    }


def maybe_log_query_diagnostic(
    query_payload: dict[str, Any],
    *,
    elapsed_ms: int | float | None = None,
    source_page: str | None = None,
    env: dict[str, str] | None = None,
) -> bool:
    """Best-effort automatic diagnostic logging for negative query outcomes."""
    if not should_log_query_diagnostic(
        query_payload,
        elapsed_ms=elapsed_ms,
        source_page=source_page,
    ):
        return False

    try:
        record = build_feedback_record(
            automatic_feedback_payload(
                query_payload,
                elapsed_ms=elapsed_ms,
                source_page=source_page,
            ),
            env=env,
        )
        store_feedback_record(record, env=env)
    except Exception:
        return False
    return True


def should_log_query_diagnostic(
    query_payload: dict[str, Any],
    *,
    elapsed_ms: int | float | None = None,
    source_page: str | None = None,
) -> bool:
    """Return whether a query response should create an automatic diagnostic."""
    if normalize_source_page(source_page) in SUPPRESSED_SOURCE_PAGES:
        return False

    status = _clean_text(query_payload.get("result_status"), METADATA_TEXT_MAX_LENGTH)
    reason = _clean_text(query_payload.get("result_reason"), METADATA_TEXT_MAX_LENGTH)
    metadata = _response_metadata(query_payload)
    unsupported_filters = metadata.get("unsupported_filters")
    slow = elapsed_ms is not None and elapsed_ms >= SLOW_QUERY_WARNING_MS

    return (
        status in {"no_result", "error"}
        or reason in AUTOMATIC_DIAGNOSTIC_REASONS
        or bool(unsupported_filters)
        or slow
    )


def automatic_feedback_payload(
    query_payload: dict[str, Any],
    *,
    elapsed_ms: int | float | None = None,
    source_page: str | None = None,
) -> dict[str, Any]:
    """Build a sanitized-input payload for automatic diagnostic records."""
    metadata = _response_metadata(query_payload)
    status = _clean_text(query_payload.get("result_status"), METADATA_TEXT_MAX_LENGTH)
    reason = _clean_text(query_payload.get("result_reason"), METADATA_TEXT_MAX_LENGTH)
    feedback_type = _automatic_feedback_type(status, reason, metadata)
    result = query_payload.get("result") if isinstance(query_payload.get("result"), dict) else {}

    return {
        "query": query_payload.get("query"),
        "feedback_source": "automatic",
        "feedback_type": feedback_type,
        "source_page": normalize_source_page(source_page),
        "route": query_payload.get("route"),
        "status": status,
        "reason": reason,
        "current_through": query_payload.get("current_through"),
        "intent": query_payload.get("intent"),
        "confidence": query_payload.get("confidence"),
        "metadata": {
            **metadata,
            "route": query_payload.get("route"),
            "status": status,
            "reason": reason,
            "intent": query_payload.get("intent"),
            "confidence": query_payload.get("confidence"),
            "current_through": query_payload.get("current_through"),
            "query_class": result.get("query_class"),
        },
        "result_shape": sanitize_result_shape({"result": result}),
        "notes": query_payload.get("notes"),
        "caveats": query_payload.get("caveats"),
        "answer_text_preview": _answer_preview(query_payload, metadata),
        "error_message": _error_preview(query_payload),
        "elapsed_ms": elapsed_ms,
    }


def normalize_source_page(value: Any) -> str:
    """Normalize a frontend source page to a compact path string."""
    if not isinstance(value, str) or not value.strip():
        return "/"
    text = value.strip()
    if not text.startswith("/"):
        text = f"/{text}"
    return _clean_text(text, METADATA_TEXT_MAX_LENGTH) or "/"


def _required_text(payload: dict[str, Any], key: str, max_length: int) -> str:
    value = _clean_text(payload.get(key), max_length)
    if not value:
        raise FeedbackValidationError(f"Field '{key}' must be a non-empty string")
    return value


def _required_choice(payload: dict[str, Any], key: str, allowed: set[str]) -> str:
    value = _clean_text(payload.get(key), METADATA_TEXT_MAX_LENGTH)
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise FeedbackValidationError(f"Field '{key}' must be one of: {choices}")
    return value


def _optional_text(payload: dict[str, Any], key: str, max_length: int) -> str | None:
    value = _clean_text(payload.get(key), max_length)
    return value or None


def _clean_text(value: Any, max_length: int) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    if not text:
        return None
    return text[:max_length]


def _sanitize_text_list(value: Any, max_items: int) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value[:max_items]:
        text = _clean_text(item, METADATA_TEXT_MAX_LENGTH)
        if text:
            result.append(text)
    return result


def _sanitize_string_list(value: Any, max_items: int) -> list[str]:
    return _sanitize_text_list(value, max_items)


def _sanitize_compact_value(value: Any, *, depth: int) -> Any:
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _clean_text(value, METADATA_TEXT_MAX_LENGTH)
    if isinstance(value, list):
        return [
            clean
            for item in value[:LIST_MAX_ITEMS]
            if (clean := _sanitize_compact_value(item, depth=depth + 1)) is not None
        ]
    if isinstance(value, dict) and depth < 2:
        sanitized: dict[str, Any] = {}
        for key, item in list(value.items())[:DICT_MAX_ITEMS]:
            key_text = _clean_text(key, 80)
            if not key_text or key_text in DISALLOWED_FIELD_NAMES:
                continue
            clean = _sanitize_compact_value(item, depth=depth + 1)
            if clean is not None:
                sanitized[key_text] = clean
        return sanitized
    return None


def _optional_non_negative_number(value: Any) -> int | float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float) and value >= 0:
        return round(value, 3) if isinstance(value, float) else value
    return None


def _sanitize_section_counts(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    counts: dict[str, int] = {}
    for key, raw_count in list(value.items())[:DICT_MAX_ITEMS]:
        key_text = _clean_text(key, 80)
        if not key_text or isinstance(raw_count, bool):
            continue
        if isinstance(raw_count, int | float) and raw_count >= 0:
            counts[key_text] = int(raw_count)
    return counts


def _section_counts_from_sections(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    counts: dict[str, int] = {}
    for key, rows in list(value.items())[:DICT_MAX_ITEMS]:
        key_text = _clean_text(key, 80)
        if not key_text:
            continue
        counts[key_text] = len(rows) if isinstance(rows, list) else 0
    return counts


def _query_hash(
    query: str,
    route: str | None,
    status: str | None,
    reason: str | None,
) -> str:
    normalized = " ".join(query.lower().split())
    digest_input = "|".join([normalized, route or "", status or "", reason or ""])
    return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()


def _feedback_id(created_at: datetime) -> str:
    stamp = created_at.strftime("%Y%m%dT%H%M%S%fZ")
    return f"qfb_{stamp}_{secrets.token_hex(4)}"


def _isoformat_z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse_created_at(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return datetime.now(UTC)


def _safe_key_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "", value)[:24] or secrets.token_hex(4)


def _response_metadata(query_payload: dict[str, Any]) -> dict[str, Any]:
    result = query_payload.get("result")
    if not isinstance(result, dict):
        return {}
    metadata = result.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _answer_preview(query_payload: dict[str, Any], metadata: dict[str, Any]) -> str | None:
    for key in ("answer_phrase", "count_phrase"):
        text = _clean_text(metadata.get(key), ANSWER_TEXT_PREVIEW_MAX_LENGTH)
        if text:
            return text

    result = query_payload.get("result")
    if not isinstance(result, dict):
        return None
    notes = result.get("notes")
    if isinstance(notes, list):
        return _clean_text(
            " ".join(str(item) for item in notes[:2]),
            ANSWER_TEXT_PREVIEW_MAX_LENGTH,
        )
    return None


def _error_preview(query_payload: dict[str, Any]) -> str | None:
    if query_payload.get("result_status") != "error":
        return None
    result = query_payload.get("result")
    if isinstance(result, dict):
        metadata = result.get("metadata")
        if isinstance(metadata, dict):
            for key in ("error_message", "message", "detail"):
                text = _clean_text(metadata.get(key), ERROR_MESSAGE_MAX_LENGTH)
                if text:
                    return text
    return _clean_text(query_payload.get("result_reason"), ERROR_MESSAGE_MAX_LENGTH)


def _automatic_feedback_type(
    status: str | None,
    reason: str | None,
    metadata: dict[str, Any],
) -> str:
    if status == "error":
        return "error"
    if reason in {"filter_not_supported", "unsupported", "unrouted"}:
        return "unsupported"
    if metadata.get("unsupported_filters"):
        return "unsupported"
    if status == "no_result" or reason == "no_data":
        return "no_result"
    return "other"


def _environment_name(env: dict[str, str] | None) -> str:
    values = _merged_env(env, Path(".env"))
    return (
        values.get("VERCEL_ENV")
        or values.get("NBATOOLS_ENV")
        or values.get("ENVIRONMENT")
        or "local"
    )


def _deployment_context(env: dict[str, str] | None) -> dict[str, str]:
    values = _merged_env(env, Path(".env"))
    context: dict[str, str] = {}
    for source_key, record_key in (
        ("VERCEL_URL", "vercel_url"),
        ("VERCEL_GIT_COMMIT_SHA", "vercel_git_commit_sha"),
    ):
        text = _clean_text(values.get(source_key), METADATA_TEXT_MAX_LENGTH)
        if text:
            context[record_key] = text
    return context


def _merged_env(
    env: dict[str, str] | None,
    env_file: Path | None,
) -> dict[str, str]:
    values = dict(os.environ if env is None else env)
    if env_file is None:
        return values

    candidates = [env_file]
    repo_env = Path(__file__).resolve().parents[2] / ".env"
    if repo_env != env_file:
        candidates.append(repo_env)

    for candidate in candidates:
        if not candidate.exists():
            continue
        for key, value in _read_simple_env_file(candidate).items():
            values.setdefault(key, value)
    return values


def _read_simple_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def elapsed_ms_since(start_time: float) -> int:
    """Return integer milliseconds elapsed since a monotonic start time."""
    return int((time.monotonic() - start_time) * 1000)
