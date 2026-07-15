"""Retention verification and receipt-addressable feedback deletion helpers."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from nbatools.query_feedback import FEEDBACK_RETENTION_DAYS
from nbatools.r2_errors import is_not_found


class FeedbackPrivacyError(RuntimeError):
    """Raised when retention or deletion proof cannot be completed safely."""


@dataclass(frozen=True)
class RetentionVerification:
    """Read-only proof that an enabled lifecycle rule covers feedback objects."""

    bucket_name: str
    prefix: str
    rule_id: str
    expiration_days: int


@dataclass(frozen=True)
class DeletionReceipt:
    """Minimal operator receipt for one verified feedback deletion request."""

    deletion_receipt_id: str
    feedback_id: str
    object_key: str
    completed_at: str
    result: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def feedback_key_from_receipt(feedback_id: str, *, prefix: str) -> str:
    """Resolve a schema-v2 feedback receipt to its one immutable key."""
    if not feedback_id.startswith("qfb_") or not feedback_id.replace("_", "").isalnum():
        raise FeedbackPrivacyError("Feedback receipt has an invalid format")
    token = feedback_id.removeprefix("qfb_")
    clean_prefix = prefix.strip("/")
    if not clean_prefix:
        raise FeedbackPrivacyError("Feedback prefix must not be empty")
    if len(token) == 32:
        try:
            submission_id = str(uuid.UUID(hex=token))
        except ValueError as exc:
            raise FeedbackPrivacyError("Feedback receipt is not a valid UUID-backed ID") from exc
        return f"{clean_prefix}/submissions/{submission_id}.json"
    return f"{clean_prefix}/receipts/{feedback_id}.json"


def verify_feedback_lifecycle(
    client: Any,
    *,
    bucket_name: str,
    prefix: str,
) -> RetentionVerification:
    """Read and validate an enabled relative-expiry rule of at most 90 days."""
    try:
        response = client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
    except Exception as exc:  # pragma: no cover - provider error shape varies
        raise FeedbackPrivacyError(
            f"Could not read feedback lifecycle configuration: {exc}"
        ) from exc

    normalized_prefix = prefix.strip("/")
    for rule in response.get("Rules", []):
        if rule.get("Status") != "Enabled":
            continue
        expiration = rule.get("Expiration")
        if not isinstance(expiration, dict):
            continue
        days = expiration.get("Days")
        if not isinstance(days, int) or isinstance(days, bool):
            continue
        rule_prefix = _rule_prefix(rule).strip("/")
        if rule_prefix and not (
            normalized_prefix == rule_prefix or normalized_prefix.startswith(f"{rule_prefix}/")
        ):
            continue
        if days > FEEDBACK_RETENTION_DAYS:
            continue
        return RetentionVerification(
            bucket_name=bucket_name,
            prefix=normalized_prefix,
            rule_id=str(rule.get("ID") or "unnamed"),
            expiration_days=days,
        )

    raise FeedbackPrivacyError(
        "No enabled lifecycle rule covers the feedback prefix with expiration at or below 90 days"
    )


def delete_feedback_by_receipt(
    client: Any,
    *,
    bucket_name: str,
    prefix: str,
    feedback_id: str,
    now: datetime | None = None,
) -> DeletionReceipt:
    """Delete one receipt-addressed record and verify it is absent afterward."""
    object_key = feedback_key_from_receipt(feedback_id, prefix=prefix)
    completed = (now or datetime.now(UTC)).astimezone(UTC)
    existed = _object_exists(client, bucket_name=bucket_name, object_key=object_key)
    if existed:
        try:
            client.delete_object(Bucket=bucket_name, Key=object_key)
        except Exception as exc:  # pragma: no cover - provider error shape varies
            raise FeedbackPrivacyError(f"Could not delete feedback receipt: {exc}") from exc
        if _object_exists(client, bucket_name=bucket_name, object_key=object_key):
            raise FeedbackPrivacyError("Feedback object still exists after deletion")

    completed_at = completed.isoformat(timespec="seconds").replace("+00:00", "Z")
    digest = hashlib.sha256(f"{feedback_id}|{object_key}|{completed_at}".encode()).hexdigest()
    return DeletionReceipt(
        deletion_receipt_id=f"qfd_{digest[:24]}",
        feedback_id=feedback_id,
        object_key=object_key,
        completed_at=completed_at,
        result="deleted" if existed else "already_absent",
    )


def _object_exists(client: Any, *, bucket_name: str, object_key: str) -> bool:
    try:
        client.head_object(Bucket=bucket_name, Key=object_key)
    except Exception as exc:  # pragma: no cover - provider error shape varies
        if is_not_found(exc):
            return False
        raise FeedbackPrivacyError(f"Could not verify feedback object state: {exc}") from exc
    return True


def _rule_prefix(rule: dict[str, Any]) -> str:
    direct = rule.get("Prefix")
    if isinstance(direct, str):
        return direct
    rule_filter = rule.get("Filter")
    if not isinstance(rule_filter, dict):
        return ""
    prefix = rule_filter.get("Prefix")
    if isinstance(prefix, str):
        return prefix
    conjunction = rule_filter.get("And")
    if isinstance(conjunction, dict) and isinstance(conjunction.get("Prefix"), str):
        return conjunction["Prefix"]
    return ""
