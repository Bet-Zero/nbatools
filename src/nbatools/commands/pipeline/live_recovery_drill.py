"""Prefix-isolated preparation and execution primitives for the E-03B live drill.

The public preparation path is network-free. Live execution requires an injected
R2 client plus a plan-bound authorization record; this module never discovers or
loads credentials on its own.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import tempfile
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    HTTPClientError,
    ReadTimeoutError,
    SSLError,
)

from nbatools.commands.pipeline.generation_publication import (
    GENERATION_MANIFEST_PATH,
    GENERATION_MANIFEST_SCHEMA_VERSION,
    SHA256_METADATA_KEY,
    GenerationConflictError,
    GenerationObjectValidationError,
    GenerationPublicationError,
    publish_r2_generation,
    rollback_r2_generation,
    validate_staged_generation,
)
from nbatools.commands.pipeline.sync_r2 import R2SyncConfig, create_r2_client
from nbatools.data_source import (
    ACTIVE_GENERATION_PATH,
    GENERATIONS_DIR,
    LEGACY_GENERATION,
    validate_data_generation_id,
)
from nbatools.r2_errors import client_error_code_and_status

LIVE_DRILL_SCHEMA_VERSION = 1
LIVE_DRILL_MODE = "isolated_real_r2_prefix"
LIVE_DRILL_PREFIX_ROOT = "recovery-drills"
LIVE_DRILL_RTO_HOURS = 8
LIVE_DRILL_RPO_HOURS = 24
MAX_CONTROL_BODY_BYTES = 2 * 1024 * 1024

APPROVED_SOURCE_GENERATION = "queue-d-local-7e55c810-20260715"
APPROVED_SOURCE_MANIFEST_SHA256 = "912eb92d8a6924d5acd37b133131fe72d6a9309be4268d21669b350f4a4bf4d5"
APPROVED_SOURCE_FILE_COUNT = 684
APPROVED_SOURCE_BYTES = 401_730_141
ABSOLUTE_MAX_LIVE_OBJECTS = 689
ABSOLUTE_MAX_PUT_BYTES = 401_900_000
ABSOLUTE_MAX_CLASS_A_OPERATIONS = 695
ABSOLUTE_MAX_CLASS_B_OPERATIONS = 3_448
ABSOLUTE_MAX_DELETE_OPERATIONS = 690
ABSOLUTE_MAX_VERIFIED_READ_BYTES = 401_900_000

_DRILL_ID_PATTERN = re.compile(r"^e03b-[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_SAFE_RECEIPT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/#-]{0,255}$")
_AMBIGUOUS_TRANSPORT_ERRORS = (
    TimeoutError,
    ConnectionError,
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    HTTPClientError,
    ReadTimeoutError,
    SSLError,
)


class LiveRecoveryDrillError(RuntimeError):
    """Stable, redacted live-drill failure."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class LiveDrillOperationLimits:
    """Hard ceilings enforced before every provider operation."""

    class_a: int
    class_b: int
    deletes: int
    put_bytes: int
    verified_read_bytes: int


@dataclass(frozen=True)
class LiveRecoveryDrillPlan:
    """Immutable, network-free plan bound to one source and isolated prefix."""

    schema_version: int
    state: str
    mode: str
    generated_at: str
    repository_commit: str
    drill_id: str
    drill_prefix: str
    r2_account_id_sha256: str
    bucket_name: str
    production_url: str
    expected_production_generation: str
    expected_production_manifest_sha256: str
    local_source_generation: str
    local_source_manifest_sha256: str
    source_file_count: int
    source_bytes: int
    restored_generation: str
    restored_manifest_sha256: str
    restored_object_count: int
    restored_bytes: int
    candidate_generation: str
    candidate_manifest_sha256: str
    candidate_object_count: int
    candidate_bytes: int
    max_live_objects: int
    max_live_bytes: int
    operation_limits: LiveDrillOperationLimits
    approved_rto_hours: int
    approved_rpo_hours: int
    required_external_gates: tuple[str, ...]

    def payload_dict(self) -> dict[str, Any]:
        """Return canonical plan content without its derived hash."""
        return asdict(self)

    @property
    def plan_sha256(self) -> str:
        """Bind authorization to every plan field."""
        payload = json.dumps(
            self.payload_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(payload).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        document = self.payload_dict()
        document["plan_sha256"] = self.plan_sha256
        return document

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> LiveRecoveryDrillPlan:
        """Load and hash-verify a serialized plan."""
        try:
            values = dict(document)
            expected_hash = values.pop("plan_sha256", None)
            limits = values.get("operation_limits")
            if not isinstance(limits, Mapping):
                raise TypeError
            values["operation_limits"] = LiveDrillOperationLimits(**dict(limits))
            gates = values.get("required_external_gates")
            if not isinstance(gates, list | tuple):
                raise TypeError
            values["required_external_gates"] = tuple(gates)
            plan = cls(**values)
        except (TypeError, ValueError) as exc:
            raise LiveRecoveryDrillError("plan_invalid") from exc
        if expected_hash != plan.plan_sha256:
            raise LiveRecoveryDrillError("plan_hash_mismatch")
        return plan


@dataclass(frozen=True)
class LiveRecoveryDrillAuthorization:
    """External approval and cost/credential attestations for one exact plan."""

    approved_plan_sha256: str
    approval_reference: str
    operator: str
    incident_owner: str
    production_deployment_id: str
    approved_at: str
    expires_at: str
    projected_cost_usd: float
    storage_class: str
    credential_scope: str
    billing_usage_receipt: str
    mutation_credential_scope_receipt: str
    production_read_credential_scope_receipt: str
    production_preflight_receipt: str
    independent_backup_receipt: str
    backup_created_at: str
    backup_generation: str
    backup_manifest_sha256: str
    backup_file_count: int
    backup_bytes: int
    projected_execution_seconds: float
    duration_estimate_receipt: str


@dataclass(frozen=True)
class ProductionGuardResult:
    """Allowlisted proof from one bound readiness/deployment smoke check."""

    production_url: str
    active_generation: str
    deployment_id: str
    checked_at: str
    request_id: str
    readiness_state: str
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LiveDrillR2ClientHandle:
    """Non-secret binding between one provider client, target, and exact role."""

    client: Any = field(repr=False, compare=False)
    role: str
    account_id_sha256: str
    bucket_name: str
    credential_id_sha256: str


@dataclass(frozen=True)
class LiveRecoveryDrillReceipt:
    """Privacy-safe successful execution receipt."""

    schema_version: int
    drill_id: str
    plan_sha256: str
    status: str
    started_at: str
    completed_at: str
    duration_ms: float
    authorization_reference: str
    operator: str
    incident_owner: str
    repository_commit: str
    production_url: str
    production_deployment_id: str
    r2_account_id_sha256: str
    bucket_name: str
    local_source_generation: str
    independent_backup_receipt: str
    authorization_expires_at: str
    production_generation_unchanged: bool
    restored_generation: str
    candidate_retained_until_cleanup: bool
    isolated_prefix_empty_after_cleanup: bool
    source_file_count: int
    source_bytes: int
    operation_usage: dict[str, int]
    measurements_ms: dict[str, float]
    production_guard_before: dict[str, Any]
    production_guard_after: dict[str, Any]
    rto_evidence_state: str
    detection_evidence_state: str
    data_loss_evidence_state: str
    remaining_exceptions: tuple[str, ...]
    mutation_outcomes: tuple[str, ...]
    checks: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LiveRecoveryDrillFailureReceipt:
    """Redacted evidence retained when a live execution fails closed."""

    schema_version: int
    drill_id: str
    plan_sha256: str
    status: str
    error_code: str
    started_at: str
    failed_at: str
    duration_ms: float
    authorization_reference: str
    operator: str
    production_url: str
    production_generation: str
    mutation_started: bool
    cleanup_state: str
    operation_usage: dict[str, int]
    measurements_ms: dict[str, float]
    production_guard_before: dict[str, Any] | None
    production_guard_after: dict[str, Any] | None
    mutation_outcomes: tuple[str, ...]
    checks: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LiveRecoveryDrillExecutionError(LiveRecoveryDrillError):
    """Stable execution failure carrying a safe immutable receipt payload."""

    def __init__(self, code: str, receipt: LiveRecoveryDrillFailureReceipt):
        self.receipt = receipt
        super().__init__(code)


@dataclass
class _OperationUsage:
    class_a: int = 0
    class_b: int = 0
    deletes: int = 0
    put_bytes: int = 0
    put_operations: int = 0
    verified_read_bytes: int = 0


class _BoundedControlBody:
    """Bound untrusted pointer/manifest reads used by publication helpers."""

    def __init__(self, body: Any, limit: int = MAX_CONTROL_BODY_BYTES) -> None:
        self._body = body
        self._remaining = limit

    def read(self, amount: int = -1) -> bytes:
        requested = self._remaining + 1 if amount < 0 else min(amount, self._remaining + 1)
        try:
            payload = self._body.read(requested)
        except Exception as exc:
            _raise_read_transport_error(exc)
            raise LiveRecoveryDrillError("provider_read_failed") from exc
        if not isinstance(payload, bytes) or len(payload) > self._remaining:
            raise LiveRecoveryDrillError("provider_body_too_large")
        self._remaining -= len(payload)
        return payload


def _bounded_control_response(response: Mapping[str, Any]) -> dict[str, Any]:
    body = response.get("Body")
    if body is None or not hasattr(body, "read"):
        raise LiveRecoveryDrillError("provider_body_missing")
    safe = dict(response)
    safe["Body"] = _BoundedControlBody(body)
    return safe


class PrefixEnforcingR2Client:
    """S3-shaped client that can mutate only one exact drill prefix."""

    def __init__(
        self,
        client: Any,
        *,
        bucket_name: str,
        drill_prefix: str,
        limits: LiveDrillOperationLimits,
        usage: _OperationUsage | None = None,
        mutation_deadline: datetime | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self.bucket_name = _validated_name(bucket_name, "bucket")
        self.drill_prefix = _validated_prefix(drill_prefix)
        self.limits = limits
        self.usage = usage or _OperationUsage()
        self._mutation_deadline = mutation_deadline
        self._clock = clock or (lambda: datetime.now(UTC))

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self._require_bucket(Bucket)
        self._charge("class_b")
        try:
            return self._client.head_object(Bucket=Bucket, Key=self._physical_key(Key))
        except Exception as exc:
            _raise_read_transport_error(exc)
            raise

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self._require_bucket(Bucket)
        self._charge("class_b")
        try:
            response = self._client.get_object(Bucket=Bucket, Key=self._physical_key(Key))
            return _bounded_control_response(response)
        except Exception as exc:
            _raise_read_transport_error(exc)
            raise

    def get_verified_object(
        self,
        *,
        Bucket: str,
        Key: str,
        expected_bytes: int,
    ) -> dict[str, Any]:
        """GET one drill object and reserve its exact verification byte budget."""
        self._require_bucket(Bucket)
        if expected_bytes < 0:
            raise LiveRecoveryDrillError("verified_read_size_invalid")
        self._charge("class_b", verified_read_bytes=expected_bytes)
        try:
            return self._client.get_object(Bucket=Bucket, Key=self._physical_key(Key))
        except Exception as exc:
            _raise_read_transport_error(exc)
            raise

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        self._require_bucket(str(kwargs.get("Bucket") or ""))
        key = self._physical_key(str(kwargs.get("Key") or ""))
        try:
            size = int(kwargs["ContentLength"])
        except (KeyError, TypeError, ValueError) as exc:
            raise LiveRecoveryDrillError("put_content_length_invalid") from exc
        if size < 0:
            raise LiveRecoveryDrillError("put_content_length_invalid")
        self._require_mutation_window()
        self._charge("class_a", put_bytes=size, put_operation=True)
        forwarded = dict(kwargs)
        forwarded["Key"] = key
        try:
            return self._client.put_object(**forwarded)
        except Exception as exc:
            _raise_mutation_transport_error(exc)
            raise

    def delete_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self._require_bucket(Bucket)
        self._require_mutation_window()
        self._charge("delete")
        try:
            return self._client.delete_object(Bucket=Bucket, Key=self._physical_key(Key))
        except Exception as exc:
            _raise_mutation_transport_error(exc)
            raise

    def list_objects_v2(self, *, Bucket: str, Prefix: str = "") -> dict[str, Any]:
        self._require_bucket(Bucket)
        self._charge("class_a")
        physical_prefix = self.drill_prefix
        if Prefix:
            physical_prefix = self._physical_key(Prefix)
        try:
            response = self._client.list_objects_v2(Bucket=Bucket, Prefix=physical_prefix)
        except Exception as exc:
            _raise_read_transport_error(exc)
            raise
        safe_response = dict(response)
        safe_contents: list[dict[str, Any]] = []
        for item in response.get("Contents") or []:
            physical_key = str(item.get("Key") or "")
            if not physical_key.startswith(self.drill_prefix):
                raise LiveRecoveryDrillError("provider_returned_out_of_prefix_key")
            safe_item = dict(item)
            safe_item["Key"] = physical_key[len(self.drill_prefix) :]
            safe_contents.append(safe_item)
        safe_response["Contents"] = safe_contents
        return safe_response

    def _physical_key(self, logical_key: str) -> str:
        logical = _validated_logical_key(logical_key)
        physical = f"{self.drill_prefix}{logical}"
        if not physical.startswith(self.drill_prefix):
            raise LiveRecoveryDrillError("drill_prefix_escape")
        return physical

    def _require_bucket(self, bucket: str) -> None:
        if bucket != self.bucket_name:
            raise LiveRecoveryDrillError("bucket_mismatch")

    def _require_mutation_window(self) -> None:
        if self._mutation_deadline is None:
            return
        now = self._clock()
        if now.tzinfo is None or now >= self._mutation_deadline:
            raise LiveRecoveryDrillError("authorization_expired_during_execution")

    def _charge(
        self,
        operation: str,
        *,
        put_bytes: int = 0,
        put_operation: bool = False,
        verified_read_bytes: int = 0,
    ) -> None:
        next_a = self.usage.class_a + (1 if operation == "class_a" else 0)
        next_b = self.usage.class_b + (1 if operation == "class_b" else 0)
        next_deletes = self.usage.deletes + (1 if operation == "delete" else 0)
        next_bytes = self.usage.put_bytes + put_bytes
        next_verified_read_bytes = self.usage.verified_read_bytes + verified_read_bytes
        if (
            next_a > self.limits.class_a
            or next_b > self.limits.class_b
            or next_deletes > self.limits.deletes
            or next_bytes > self.limits.put_bytes
            or next_verified_read_bytes > self.limits.verified_read_bytes
        ):
            raise LiveRecoveryDrillError("operation_budget_exceeded")
        self.usage.class_a = next_a
        self.usage.class_b = next_b
        self.usage.deletes = next_deletes
        self.usage.put_bytes = next_bytes
        self.usage.verified_read_bytes = next_verified_read_bytes
        if put_operation:
            self.usage.put_operations += 1


class ProductionReadOnlyR2Client:
    """Exact-allowlist production reader with no mutation methods."""

    def __init__(
        self,
        client: Any,
        *,
        bucket_name: str,
        allowed_keys: frozenset[str],
        limits: LiveDrillOperationLimits,
        usage: _OperationUsage,
    ) -> None:
        self._client = client
        self.bucket_name = _validated_name(bucket_name, "bucket")
        self._allowed_keys = frozenset(_validated_logical_key(key) for key in allowed_keys)
        self.limits = limits
        self.usage = usage

    def get_object(self, key: str) -> dict[str, Any]:
        logical = self._require_allowed(key)
        self._charge_read()
        try:
            response = self._client.get_object(Bucket=self.bucket_name, Key=logical)
            return _bounded_control_response(response)
        except Exception as exc:
            _raise_read_transport_error(exc)
            raise

    def head_object(self, key: str) -> dict[str, Any]:
        logical = self._require_allowed(key)
        self._charge_read()
        try:
            return self._client.head_object(Bucket=self.bucket_name, Key=logical)
        except Exception as exc:
            _raise_read_transport_error(exc)
            raise

    def _require_allowed(self, key: str) -> str:
        logical = _validated_logical_key(key)
        if logical not in self._allowed_keys:
            raise LiveRecoveryDrillError("production_read_not_allowlisted")
        return logical

    def _charge_read(self) -> None:
        next_b = self.usage.class_b + 1
        if next_b > self.limits.class_b:
            raise LiveRecoveryDrillError("operation_budget_exceeded")
        self.usage.class_b = next_b


def create_live_drill_mutation_client(config: R2SyncConfig) -> LiveDrillR2ClientHandle:
    """Create the retry-disabled client for the temporary prefix-scoped credential."""
    if not config.session_token:
        raise LiveRecoveryDrillError("temporary_session_token_required")
    client = create_r2_client(config, disable_retries=True)
    _require_retries_disabled(client)
    return LiveDrillR2ClientHandle(
        client=client,
        role="isolated-prefix-read-write",
        account_id_sha256=hashlib.sha256(config.account_id.encode()).hexdigest(),
        bucket_name=config.bucket_name,
        credential_id_sha256=_temporary_credential_identity_sha256(config),
    )


def create_live_drill_production_reader(config: R2SyncConfig) -> LiveDrillR2ClientHandle:
    """Create a retry-disabled client for the separate production read-only credential."""
    if not config.session_token:
        raise LiveRecoveryDrillError("temporary_session_token_required")
    client = create_r2_client(config, disable_retries=True)
    _require_retries_disabled(client)
    return LiveDrillR2ClientHandle(
        client=client,
        role="production-read-only",
        account_id_sha256=hashlib.sha256(config.account_id.encode()).hexdigest(),
        bucket_name=config.bucket_name,
        credential_id_sha256=_temporary_credential_identity_sha256(config),
    )


def _temporary_credential_identity_sha256(config: R2SyncConfig) -> str:
    """Fingerprint one temporary session without retaining credential material."""
    if not config.session_token:
        raise LiveRecoveryDrillError("temporary_session_token_required")
    identity = (
        b"r2-temporary-session-v1\0"
        + config.access_key_id.encode()
        + b"\0"
        + config.session_token.encode()
    )
    return hashlib.sha256(identity).hexdigest()


def prepare_live_recovery_drill_plan(
    *,
    source_generation_dir: Path,
    source_generation: str,
    repository_commit: str,
    drill_id: str,
    r2_account_id_sha256: str,
    bucket_name: str,
    production_url: str,
    expected_production_generation: str,
    enforce_approved_source: bool = True,
    _generated_at: str | None = None,
) -> LiveRecoveryDrillPlan:
    """Build an exact local-only plan; never load credentials or open a network connection."""
    if not _COMMIT_PATTERN.fullmatch(repository_commit):
        raise LiveRecoveryDrillError("repository_commit_invalid")
    if not _DRILL_ID_PATTERN.fullmatch(drill_id):
        raise LiveRecoveryDrillError("drill_id_invalid")
    if not _SHA256_PATTERN.fullmatch(r2_account_id_sha256):
        raise LiveRecoveryDrillError("r2_account_fingerprint_invalid")
    bucket = _validated_name(bucket_name, "bucket")
    production = _validated_production_url(production_url)
    try:
        source_generation = validate_data_generation_id(source_generation)
        production_generation = validate_data_generation_id(expected_production_generation)
        restored_generation = validate_data_generation_id(f"{drill_id}-restored")
        candidate_generation = validate_data_generation_id(f"{drill_id}-candidate")
    except Exception as exc:
        raise LiveRecoveryDrillError("generation_id_invalid") from exc

    source_dir = source_generation_dir.expanduser().resolve()
    try:
        source_manifest = validate_staged_generation(source_dir, source_generation)
        source_manifest_bytes = (source_dir / GENERATION_MANIFEST_PATH).read_bytes()
    except Exception as exc:
        raise LiveRecoveryDrillError("local_source_validation_failed") from exc
    source_manifest_sha256 = hashlib.sha256(source_manifest_bytes).hexdigest()
    source_records = source_manifest["files"]
    source_file_count = len(source_records)
    source_bytes = sum(int(item["size_bytes"]) for item in source_records)
    if enforce_approved_source and (
        source_generation != APPROVED_SOURCE_GENERATION
        or source_manifest_sha256 != APPROVED_SOURCE_MANIFEST_SHA256
        or source_file_count != APPROVED_SOURCE_FILE_COUNT
        or source_bytes != APPROVED_SOURCE_BYTES
    ):
        raise LiveRecoveryDrillError("approved_source_boundary_changed")

    production_manifest_bytes = _generation_manifest_bytes(
        production_generation,
        source_records,
    )
    restored_manifest_bytes = _generation_manifest_bytes(restored_generation, source_records)
    candidate_files = _candidate_source_files()
    candidate_records = _records_for_bytes(candidate_files)
    candidate_manifest_bytes = _generation_manifest_bytes(
        candidate_generation,
        candidate_records,
    )

    restored_manifest_sha256 = hashlib.sha256(restored_manifest_bytes).hexdigest()
    candidate_manifest_sha256 = hashlib.sha256(candidate_manifest_bytes).hexdigest()
    restored_object_count = source_file_count + 1
    candidate_object_count = len(candidate_records) + 1
    restored_bytes = source_bytes + len(restored_manifest_bytes)
    candidate_bytes = sum(len(value) for value in candidate_files.values()) + len(
        candidate_manifest_bytes
    )
    max_live_objects = restored_object_count + candidate_object_count + 1
    pointer_sizes = (
        len(
            _pointer_bytes_for_budget(
                restored_generation,
                LEGACY_GENERATION,
                restored_manifest_sha256,
            )
        ),
        len(
            _pointer_bytes_for_budget(
                candidate_generation,
                restored_generation,
                candidate_manifest_sha256,
            )
        ),
        len(
            _pointer_bytes_for_budget(
                restored_generation,
                candidate_generation,
                restored_manifest_sha256,
            )
        ),
    )
    damaged_size = int(source_records[0]["size_bytes"])
    put_bytes = (
        restored_bytes
        + pointer_sizes[0]
        + candidate_bytes
        + pointer_sizes[1]
        + damaged_size
        + pointer_sizes[2]
    )
    max_live_bytes = restored_bytes + candidate_bytes + max(pointer_sizes)
    limits = LiveDrillOperationLimits(
        class_a=max_live_objects + 6,
        class_b=5 * source_file_count + 3 * candidate_object_count + 19,
        deletes=max_live_objects + 1,
        put_bytes=put_bytes,
        verified_read_bytes=restored_bytes + candidate_bytes + damaged_size,
    )
    if (
        max_live_objects > ABSOLUTE_MAX_LIVE_OBJECTS
        or max_live_bytes > ABSOLUTE_MAX_PUT_BYTES
        or limits.put_bytes > ABSOLUTE_MAX_PUT_BYTES
        or limits.class_a > ABSOLUTE_MAX_CLASS_A_OPERATIONS
        or limits.class_b > ABSOLUTE_MAX_CLASS_B_OPERATIONS
        or limits.deletes > ABSOLUTE_MAX_DELETE_OPERATIONS
        or limits.verified_read_bytes > ABSOLUTE_MAX_VERIFIED_READ_BYTES
    ):
        raise LiveRecoveryDrillError("approved_operation_scope_exceeded")

    return LiveRecoveryDrillPlan(
        schema_version=LIVE_DRILL_SCHEMA_VERSION,
        state="prepared_not_authorized",
        mode=LIVE_DRILL_MODE,
        generated_at=_generated_at or _utc_now(),
        repository_commit=repository_commit,
        drill_id=drill_id,
        drill_prefix=f"{LIVE_DRILL_PREFIX_ROOT}/{drill_id}/",
        r2_account_id_sha256=r2_account_id_sha256,
        bucket_name=bucket,
        production_url=production,
        expected_production_generation=production_generation,
        expected_production_manifest_sha256=hashlib.sha256(production_manifest_bytes).hexdigest(),
        local_source_generation=source_generation,
        local_source_manifest_sha256=source_manifest_sha256,
        source_file_count=source_file_count,
        source_bytes=source_bytes,
        restored_generation=restored_generation,
        restored_manifest_sha256=restored_manifest_sha256,
        restored_object_count=restored_object_count,
        restored_bytes=restored_bytes,
        candidate_generation=candidate_generation,
        candidate_manifest_sha256=candidate_manifest_sha256,
        candidate_object_count=candidate_object_count,
        candidate_bytes=candidate_bytes,
        max_live_objects=max_live_objects,
        max_live_bytes=max_live_bytes,
        operation_limits=limits,
        approved_rto_hours=LIVE_DRILL_RTO_HOURS,
        approved_rpo_hours=LIVE_DRILL_RPO_HOURS,
        required_external_gates=(
            "exact_owner_execution_approval",
            "current_production_deployment_and_readiness_verified",
            "r2_standard_storage_and_zero_projected_cost_verified",
            "r2_account_target_fingerprint_verified",
            "prefix_scoped_temporary_read_write_credential_verified",
            "separate_temporary_production_read_only_credential_verified",
            "independent_backup_source_within_24_hour_rpo_verified",
        ),
    )


def execute_live_recovery_drill(
    plan: LiveRecoveryDrillPlan,
    authorization: LiveRecoveryDrillAuthorization,
    *,
    source_generation_dir: Path,
    mutation_client: LiveDrillR2ClientHandle,
    production_read_client: LiveDrillR2ClientHandle,
    current_repository_commit: str,
    production_guard: Callable[[], ProductionGuardResult],
    clock: Callable[[], datetime] | None = None,
) -> LiveRecoveryDrillReceipt:
    """Execute one exact authorized plan through the prefix-enforcing wrapper."""
    now = clock or (lambda: datetime.now(UTC))
    started_at = _utc_now()
    started = time.perf_counter()
    source_dir = source_generation_dir.expanduser().resolve()
    _validate_canonical_plan(plan, source_dir, current_repository_commit)
    expires_at = _validate_authorization(plan, authorization, now=now())
    _validate_client_handles(plan, mutation_client, production_read_client)
    source_manifest = _revalidate_source(plan, source_dir)
    damage_record = source_manifest["files"][0]
    damage_relative = str(damage_record["path"])
    damage_payload = (source_dir / damage_relative).read_bytes()
    if (
        len(damage_payload) != damage_record["size_bytes"]
        or hashlib.sha256(damage_payload).hexdigest() != damage_record["sha256"]
    ):
        raise LiveRecoveryDrillError("local_source_changed_after_plan")
    production_read_keys = _production_read_allowlist(plan, source_manifest)
    usage = _OperationUsage()
    wrapped = PrefixEnforcingR2Client(
        mutation_client.client,
        bucket_name=plan.bucket_name,
        drill_prefix=plan.drill_prefix,
        limits=plan.operation_limits,
        usage=usage,
        mutation_deadline=expires_at,
        clock=now,
    )
    production_reader = ProductionReadOnlyR2Client(
        production_read_client.client,
        bucket_name=plan.bucket_name,
        allowed_keys=production_read_keys,
        limits=plan.operation_limits,
        usage=usage,
    )
    checks: list[str] = []
    mutations: list[str] = []
    measurements: dict[str, float] = {}
    guard_before: ProductionGuardResult | None = None
    guard_after: ProductionGuardResult | None = None
    cleanup_completed = False

    try:
        _require_execution_window(authorization, expires_at, now())
        _prove_mutation_credential_is_prefix_scoped(
            mutation_client.client,
            plan,
            usage,
        )
        checks.append("mutation_credential_root_read_denied")
        guard_before = _require_production_guard(
            production_guard,
            plan,
            authorization,
            clock=now,
        )
        production_pointer_before = _verify_production_snapshot(
            production_reader,
            plan,
            source_manifest,
        )
        checks.append("bound_production_readiness_and_inventory_verified_before")

        _require_empty_prefix(wrapped)
        checks.append("isolated_prefix_empty_before")

        restore_started = time.perf_counter()
        restored = publish_r2_generation(
            plan.restored_generation,
            source_dir=source_dir,
            client=wrapped,
            bucket_name=plan.bucket_name,
        )
        mutations.append("full_isolated_generation_published")
        measurements["full_restore"] = _elapsed_ms(restore_started)
        if (
            restored.file_count != plan.source_file_count
            or restored.total_bytes != plan.source_bytes
            or restored.manifest_sha256 != plan.restored_manifest_sha256
        ):
            raise LiveRecoveryDrillError("restored_generation_receipt_mismatch")
        _verify_isolated_generation_bytes(
            wrapped,
            plan.restored_generation,
            source_manifest,
            plan.restored_manifest_sha256,
        )
        checks.append("full_source_restored_and_byte_verified_in_isolated_generation")

        with tempfile.TemporaryDirectory(prefix="nbatools-e03b-candidate-") as temp_dir:
            candidate_source = Path(temp_dir)
            _write_candidate_source(candidate_source)
            candidate = publish_r2_generation(
                plan.candidate_generation,
                source_dir=candidate_source,
                client=wrapped,
                bucket_name=plan.bucket_name,
            )
        mutations.append("isolated_candidate_published")
        if candidate.manifest_sha256 != plan.candidate_manifest_sha256:
            raise LiveRecoveryDrillError("candidate_generation_receipt_mismatch")
        checks.append("tiny_candidate_activated_inside_isolated_prefix")

        damage_key = f"{GENERATIONS_DIR}/{plan.restored_generation}/{damage_relative}"
        isolated_pointer_before = _read_isolated_pointer_bytes(wrapped, plan.bucket_name)
        wrapped.delete_object(Bucket=plan.bucket_name, Key=damage_key)
        mutations.append("one_restored_object_deleted")
        try:
            rollback_r2_generation(client=wrapped, bucket_name=plan.bucket_name)
        except GenerationObjectValidationError as exc:
            if (
                exc.generation_id != plan.restored_generation
                or exc.object_key != damage_key
                or exc.reason != "missing"
            ):
                raise LiveRecoveryDrillError("unexpected_rollback_refusal") from exc
        else:
            raise LiveRecoveryDrillError("incomplete_target_was_accepted")
        mutations.append("incomplete_rollback_refused")
        isolated_pointer_after = _read_isolated_pointer_bytes(wrapped, plan.bucket_name)
        if isolated_pointer_before != isolated_pointer_after:
            raise LiveRecoveryDrillError("pointer_changed_after_refused_rollback")
        checks.append("incomplete_target_refused_without_pointer_change")

        repair_started = time.perf_counter()
        wrapped.put_object(
            Bucket=plan.bucket_name,
            Key=damage_key,
            Body=damage_payload,
            ContentLength=len(damage_payload),
            Metadata={SHA256_METADATA_KEY: str(damage_record["sha256"])},
            IfNoneMatch="*",
        )
        mutations.append("deleted_object_repaired_pending_verification")
        _verify_isolated_object_bytes(wrapped, damage_key, damage_record)
        mutations[-1] = "deleted_object_exactly_repaired"
        measurements["single_object_repair"] = _elapsed_ms(repair_started)
        checks.append("exact_damaged_object_restored_and_verified")

        rollback_started = time.perf_counter()
        rolled_back = rollback_r2_generation(client=wrapped, bucket_name=plan.bucket_name)
        mutations.append("isolated_pointer_conditionally_rolled_back")
        measurements["conditional_rollback"] = _elapsed_ms(rollback_started)
        if rolled_back.generation_id != plan.restored_generation:
            raise LiveRecoveryDrillError("rollback_selected_wrong_generation")
        _verify_candidate_retained(wrapped, plan)
        checks.extend(
            (
                "isolated_pointer_conditionally_rolled_back",
                "candidate_retained_until_cleanup",
            )
        )

        production_pointer_before_cleanup = _read_production_pointer(production_reader, plan)
        if production_pointer_before_cleanup != production_pointer_before:
            raise LiveRecoveryDrillError("production_pointer_changed_during_drill")
        checks.append("production_pointer_unchanged_before_cleanup")

        cleanup_started = time.perf_counter()
        _cleanup_isolated_prefix(wrapped, plan, source_manifest)
        cleanup_completed = True
        mutations.append("exact_isolated_inventory_deleted")
        measurements["isolated_cleanup"] = _elapsed_ms(cleanup_started)
        checks.append("isolated_prefix_empty_after_cleanup")

        post_guard_not_before = now().replace(microsecond=0)
        guard_after = _require_production_guard(
            production_guard,
            plan,
            authorization,
            clock=now,
            not_before=post_guard_not_before,
        )
        if guard_before is None or guard_after.request_id == guard_before.request_id:
            raise LiveRecoveryDrillError("production_post_guard_not_fresh")
        production_pointer_after = _read_production_pointer(production_reader, plan)
        if production_pointer_after != production_pointer_before:
            raise LiveRecoveryDrillError("production_pointer_changed_during_drill")
        if now() >= expires_at:
            raise LiveRecoveryDrillError("authorization_expired_during_execution")
        checks.append("bound_production_readiness_and_pointer_verified_after_cleanup")
    except Exception as exc:
        stable = _stable_execution_error(exc, wrapped.usage)
        failure = LiveRecoveryDrillFailureReceipt(
            schema_version=LIVE_DRILL_SCHEMA_VERSION,
            drill_id=plan.drill_id,
            plan_sha256=plan.plan_sha256,
            status="failed",
            error_code=stable.code,
            started_at=started_at,
            failed_at=_utc_now(),
            duration_ms=_elapsed_ms(started),
            authorization_reference=authorization.approval_reference,
            operator=authorization.operator,
            production_url=plan.production_url,
            production_generation=plan.expected_production_generation,
            mutation_started=bool(wrapped.usage.put_operations or wrapped.usage.deletes),
            cleanup_state=(
                "completed_prefix_verified_empty"
                if cleanup_completed
                else (
                    "not_completed_prefix_requires_inspection"
                    if wrapped.usage.put_operations or wrapped.usage.deletes
                    else "not_started_no_drill_mutation"
                )
            ),
            operation_usage=_operation_usage_dict(wrapped.usage),
            measurements_ms=dict(measurements),
            production_guard_before=(guard_before.to_dict() if guard_before else None),
            production_guard_after=(guard_after.to_dict() if guard_after else None),
            mutation_outcomes=tuple(mutations),
            checks=tuple(checks),
        )
        raise LiveRecoveryDrillExecutionError(stable.code, failure) from None

    return LiveRecoveryDrillReceipt(
        schema_version=LIVE_DRILL_SCHEMA_VERSION,
        drill_id=plan.drill_id,
        plan_sha256=plan.plan_sha256,
        status="passed",
        started_at=started_at,
        completed_at=_utc_now(),
        duration_ms=_elapsed_ms(started),
        authorization_reference=authorization.approval_reference,
        operator=authorization.operator,
        incident_owner=authorization.incident_owner,
        repository_commit=plan.repository_commit,
        production_url=plan.production_url,
        production_deployment_id=authorization.production_deployment_id,
        r2_account_id_sha256=plan.r2_account_id_sha256,
        bucket_name=plan.bucket_name,
        local_source_generation=plan.local_source_generation,
        independent_backup_receipt=authorization.independent_backup_receipt,
        authorization_expires_at=authorization.expires_at,
        production_generation_unchanged=True,
        restored_generation=plan.restored_generation,
        candidate_retained_until_cleanup=True,
        isolated_prefix_empty_after_cleanup=True,
        source_file_count=plan.source_file_count,
        source_bytes=plan.source_bytes,
        operation_usage=_operation_usage_dict(wrapped.usage),
        measurements_ms=measurements,
        production_guard_before=guard_before.to_dict(),
        production_guard_after=guard_after.to_dict(),
        rto_evidence_state="component_measured_not_incident_rto_proof",
        detection_evidence_state="not_applicable_isolated_no_outage_drill",
        data_loss_evidence_state="not_applicable_no_production_data_mutation",
        remaining_exceptions=("incident_level_8_hour_rto_not_proven",),
        mutation_outcomes=tuple(mutations),
        checks=tuple(checks),
    )


def _validate_authorization(
    plan: LiveRecoveryDrillPlan,
    authorization: LiveRecoveryDrillAuthorization,
    *,
    now: datetime,
) -> datetime:
    if authorization.approved_plan_sha256 != plan.plan_sha256:
        raise LiveRecoveryDrillError("authorization_plan_mismatch")
    required_text = (
        authorization.approval_reference,
        authorization.operator,
        authorization.production_deployment_id,
        authorization.billing_usage_receipt,
        authorization.mutation_credential_scope_receipt,
        authorization.production_read_credential_scope_receipt,
        authorization.production_preflight_receipt,
        authorization.independent_backup_receipt,
        authorization.duration_estimate_receipt,
    )
    if any(
        not isinstance(value, str) or not _SAFE_RECEIPT_PATTERN.fullmatch(value)
        for value in required_text
    ):
        raise LiveRecoveryDrillError("authorization_incomplete")
    if authorization.incident_owner != "John Matthew":
        raise LiveRecoveryDrillError("incident_owner_mismatch")
    try:
        approved_at = _parse_aware_time(authorization.approved_at)
        expires_at = _parse_aware_time(authorization.expires_at)
        backup_created_at = _parse_aware_time(authorization.backup_created_at)
    except ValueError as exc:
        raise LiveRecoveryDrillError("authorization_time_invalid") from exc
    if now.tzinfo is None:
        raise LiveRecoveryDrillError("authorization_time_invalid")
    if now < approved_at or now >= expires_at:
        raise LiveRecoveryDrillError("authorization_not_current")
    if expires_at - approved_at > timedelta(hours=LIVE_DRILL_RTO_HOURS):
        raise LiveRecoveryDrillError("authorization_window_too_long")
    if backup_created_at > now or now - backup_created_at > timedelta(hours=LIVE_DRILL_RPO_HOURS):
        raise LiveRecoveryDrillError("backup_rpo_gate_failed")
    if (
        authorization.backup_generation != plan.local_source_generation
        or authorization.backup_manifest_sha256 != plan.local_source_manifest_sha256
        or authorization.backup_file_count != plan.source_file_count
        or authorization.backup_bytes != plan.source_bytes
    ):
        raise LiveRecoveryDrillError("backup_source_mismatch")
    if (
        isinstance(authorization.projected_execution_seconds, bool)
        or not isinstance(authorization.projected_execution_seconds, int | float)
        or not math.isfinite(authorization.projected_execution_seconds)
        or authorization.projected_execution_seconds <= 0
        or authorization.projected_execution_seconds > LIVE_DRILL_RTO_HOURS * 60 * 60
        or (expires_at - now).total_seconds() < authorization.projected_execution_seconds
    ):
        raise LiveRecoveryDrillError("execution_window_gate_failed")
    if (
        isinstance(authorization.projected_cost_usd, bool)
        or not isinstance(authorization.projected_cost_usd, int | float)
        or authorization.projected_cost_usd != 0
    ):
        raise LiveRecoveryDrillError("zero_cost_gate_failed")
    if authorization.storage_class != "Standard":
        raise LiveRecoveryDrillError("storage_class_gate_failed")
    if authorization.credential_scope != "separate-temporary-prefix-write-and-production-read-only":
        raise LiveRecoveryDrillError("credential_scope_gate_failed")
    return expires_at


def _validate_canonical_plan(
    plan: LiveRecoveryDrillPlan,
    source_dir: Path,
    current_repository_commit: str,
) -> None:
    if current_repository_commit != plan.repository_commit:
        raise LiveRecoveryDrillError("repository_commit_mismatch")
    try:
        _parse_aware_time(plan.generated_at)
        expected = prepare_live_recovery_drill_plan(
            source_generation_dir=source_dir,
            source_generation=plan.local_source_generation,
            repository_commit=plan.repository_commit,
            drill_id=plan.drill_id,
            r2_account_id_sha256=plan.r2_account_id_sha256,
            bucket_name=plan.bucket_name,
            production_url=plan.production_url,
            expected_production_generation=plan.expected_production_generation,
            enforce_approved_source=True,
            _generated_at=plan.generated_at,
        )
    except LiveRecoveryDrillError:
        raise
    except Exception as exc:
        raise LiveRecoveryDrillError("plan_invalid") from exc
    if plan != expected:
        raise LiveRecoveryDrillError("plan_not_canonical")


def _require_execution_window(
    authorization: LiveRecoveryDrillAuthorization,
    expires_at: datetime,
    now: datetime,
) -> None:
    if (
        now.tzinfo is None
        or now >= expires_at
        or (expires_at - now).total_seconds() < authorization.projected_execution_seconds
    ):
        raise LiveRecoveryDrillError("execution_window_gate_failed")


def _validate_client_handles(
    plan: LiveRecoveryDrillPlan,
    mutation: LiveDrillR2ClientHandle,
    production_reader: LiveDrillR2ClientHandle,
) -> None:
    if not isinstance(mutation, LiveDrillR2ClientHandle) or not isinstance(
        production_reader, LiveDrillR2ClientHandle
    ):
        raise LiveRecoveryDrillError("live_client_handle_required")
    if mutation.client is production_reader.client:
        raise LiveRecoveryDrillError("separate_credentials_required")
    if mutation.credential_id_sha256 == production_reader.credential_id_sha256:
        raise LiveRecoveryDrillError("separate_credentials_required")
    if mutation.role != "isolated-prefix-read-write":
        raise LiveRecoveryDrillError("mutation_client_role_invalid")
    if production_reader.role != "production-read-only":
        raise LiveRecoveryDrillError("production_reader_role_invalid")
    for handle in (mutation, production_reader):
        if (
            handle.bucket_name != plan.bucket_name
            or handle.account_id_sha256 != plan.r2_account_id_sha256
            or not _SHA256_PATTERN.fullmatch(handle.credential_id_sha256)
            or _client_account_id_sha256(handle.client) != plan.r2_account_id_sha256
        ):
            raise LiveRecoveryDrillError("provider_target_mismatch")
        _require_retries_disabled(handle.client)


def _revalidate_source(plan: LiveRecoveryDrillPlan, source_dir: Path) -> dict[str, Any]:
    try:
        manifest = validate_staged_generation(source_dir, plan.local_source_generation)
        manifest_sha256 = hashlib.sha256(
            (source_dir / GENERATION_MANIFEST_PATH).read_bytes()
        ).hexdigest()
    except Exception as exc:
        raise LiveRecoveryDrillError("local_source_validation_failed") from exc
    if (
        manifest_sha256 != plan.local_source_manifest_sha256
        or len(manifest["files"]) != plan.source_file_count
        or sum(int(item["size_bytes"]) for item in manifest["files"]) != plan.source_bytes
    ):
        raise LiveRecoveryDrillError("local_source_changed_after_plan")
    return manifest


def _production_read_allowlist(
    plan: LiveRecoveryDrillPlan,
    source_manifest: Mapping[str, Any],
) -> frozenset[str]:
    generation_prefix = f"{GENERATIONS_DIR}/{plan.expected_production_generation}/"
    keys = {
        ACTIVE_GENERATION_PATH.as_posix(),
        f"{generation_prefix}{GENERATION_MANIFEST_PATH.as_posix()}",
    }
    keys.update(f"{generation_prefix}{item['path']}" for item in source_manifest["files"])
    return frozenset(keys)


def _verify_production_snapshot(
    client: ProductionReadOnlyR2Client,
    plan: LiveRecoveryDrillPlan,
    source_manifest: Mapping[str, Any],
) -> tuple[bytes, str]:
    pointer_payload, pointer_etag = _read_production_pointer(client, plan)
    pointer = _json_object(pointer_payload, "production_pointer_invalid")
    if (
        pointer.get("generation_id") != plan.expected_production_generation
        or pointer.get("manifest_sha256") != plan.expected_production_manifest_sha256
    ):
        raise LiveRecoveryDrillError("production_generation_changed")

    manifest_key = (
        f"{GENERATIONS_DIR}/{plan.expected_production_generation}/"
        f"{GENERATION_MANIFEST_PATH.as_posix()}"
    )
    response = client.get_object(manifest_key)
    manifest_payload = _read_control_body(response)
    manifest_sha256 = hashlib.sha256(manifest_payload).hexdigest()
    if (
        manifest_sha256 != plan.expected_production_manifest_sha256
        or (response.get("Metadata") or {}).get(SHA256_METADATA_KEY) != manifest_sha256
    ):
        raise LiveRecoveryDrillError("production_manifest_checksum_mismatch")
    remote_manifest = _json_object(manifest_payload, "production_manifest_invalid")
    if remote_manifest.get("files") != source_manifest.get("files"):
        raise LiveRecoveryDrillError("production_inventory_differs_from_backup")

    generation_prefix = f"{GENERATIONS_DIR}/{plan.expected_production_generation}/"
    for item in source_manifest["files"]:
        response = client.head_object(f"{generation_prefix}{item['path']}")
        if (
            response.get("ContentLength") != item["size_bytes"]
            or (response.get("Metadata") or {}).get(SHA256_METADATA_KEY) != item["sha256"]
        ):
            raise LiveRecoveryDrillError("production_inventory_differs_from_backup")
    return pointer_payload, pointer_etag


def _read_production_pointer(
    client: ProductionReadOnlyR2Client,
    plan: LiveRecoveryDrillPlan,
) -> tuple[bytes, str]:
    response = client.get_object(ACTIVE_GENERATION_PATH.as_posix())
    etag = str(response.get("ETag") or "")
    if not etag:
        raise LiveRecoveryDrillError("production_pointer_etag_missing")
    return _read_control_body(response), etag


def _read_isolated_pointer_bytes(
    client: PrefixEnforcingR2Client,
    bucket_name: str,
) -> bytes:
    response = client.get_object(Bucket=bucket_name, Key=ACTIVE_GENERATION_PATH.as_posix())
    return _read_control_body(response)


def _require_empty_prefix(client: PrefixEnforcingR2Client) -> None:
    response = client.list_objects_v2(Bucket=client.bucket_name)
    if response.get("IsTruncated") or response.get("Contents"):
        raise LiveRecoveryDrillError("isolated_prefix_not_empty")


def _verify_candidate_retained(
    client: PrefixEnforcingR2Client,
    plan: LiveRecoveryDrillPlan,
) -> None:
    candidate_files = _candidate_source_files()
    records = _records_for_bytes(candidate_files)
    records.append(
        {
            "path": GENERATION_MANIFEST_PATH.as_posix(),
            "size_bytes": len(_generation_manifest_bytes(plan.candidate_generation, records)),
            "sha256": plan.candidate_manifest_sha256,
        }
    )
    for item in records:
        key = f"{GENERATIONS_DIR}/{plan.candidate_generation}/{item['path']}"
        _verify_isolated_object_bytes(
            client,
            key,
            item,
            error_code="candidate_retention_verification_failed",
        )


def _verify_isolated_generation_bytes(
    client: PrefixEnforcingR2Client,
    generation: str,
    manifest: Mapping[str, Any],
    manifest_sha256: str,
) -> None:
    records = [dict(item) for item in manifest["files"]]
    manifest_payload = _generation_manifest_bytes(generation, records)
    records.append(
        {
            "path": GENERATION_MANIFEST_PATH.as_posix(),
            "size_bytes": len(manifest_payload),
            "sha256": manifest_sha256,
        }
    )
    for item in records:
        key = f"{GENERATIONS_DIR}/{generation}/{item['path']}"
        _verify_isolated_object_bytes(client, key, item)


def _verify_isolated_object_bytes(
    client: PrefixEnforcingR2Client,
    key: str,
    record: Mapping[str, Any],
    *,
    error_code: str = "restored_object_byte_verification_failed",
) -> None:
    expected_size = int(record["size_bytes"])
    expected_sha256 = str(record["sha256"])
    response = client.get_verified_object(
        Bucket=client.bucket_name,
        Key=key,
        expected_bytes=expected_size,
    )
    actual_sha256 = _hash_exact_body(response, expected_size)
    metadata = response.get("Metadata") or {}
    storage_class = response.get("StorageClass") or "STANDARD"
    if (
        actual_sha256 != expected_sha256
        or response.get("ContentLength") != expected_size
        or metadata.get(SHA256_METADATA_KEY) != expected_sha256
        or storage_class != "STANDARD"
    ):
        raise LiveRecoveryDrillError(error_code)


def _cleanup_isolated_prefix(
    client: PrefixEnforcingR2Client,
    plan: LiveRecoveryDrillPlan,
    source_manifest: Mapping[str, Any],
) -> None:
    response = client.list_objects_v2(Bucket=plan.bucket_name)
    if response.get("IsTruncated"):
        raise LiveRecoveryDrillError("unexpected_prefix_pagination")
    contents = response.get("Contents") or []
    actual_keys = [str(item.get("Key") or "") for item in contents]
    expected_keys = _expected_isolated_keys(plan, source_manifest)
    if len(actual_keys) != len(set(actual_keys)) or set(actual_keys) != expected_keys:
        raise LiveRecoveryDrillError("cleanup_inventory_mismatch")
    for key in sorted(expected_keys):
        client.delete_object(Bucket=plan.bucket_name, Key=key)
    final = client.list_objects_v2(Bucket=plan.bucket_name)
    if final.get("IsTruncated") or final.get("Contents"):
        raise LiveRecoveryDrillError("isolated_cleanup_incomplete")


def _expected_isolated_keys(
    plan: LiveRecoveryDrillPlan,
    source_manifest: Mapping[str, Any],
) -> set[str]:
    keys = {
        f"{GENERATIONS_DIR}/{plan.restored_generation}/{item['path']}"
        for item in source_manifest["files"]
    }
    keys.add(f"{GENERATIONS_DIR}/{plan.restored_generation}/{GENERATION_MANIFEST_PATH.as_posix()}")
    keys.update(
        f"{GENERATIONS_DIR}/{plan.candidate_generation}/{path}"
        for path in _candidate_source_files()
    )
    keys.add(f"{GENERATIONS_DIR}/{plan.candidate_generation}/{GENERATION_MANIFEST_PATH.as_posix()}")
    keys.add(ACTIVE_GENERATION_PATH.as_posix())
    if len(keys) != plan.max_live_objects:
        raise LiveRecoveryDrillError("cleanup_inventory_mismatch")
    return keys


def _require_production_guard(
    production_guard: Callable[[], ProductionGuardResult],
    plan: LiveRecoveryDrillPlan,
    authorization: LiveRecoveryDrillAuthorization,
    *,
    clock: Callable[[], datetime],
    not_before: datetime | None = None,
) -> ProductionGuardResult:
    try:
        result = production_guard()
    except Exception as exc:
        raise LiveRecoveryDrillError("production_guard_failed") from exc
    if not isinstance(result, ProductionGuardResult):
        raise LiveRecoveryDrillError("production_guard_failed")
    now = clock()
    try:
        checked_at = _parse_aware_time(result.checked_at)
        approved_at = _parse_aware_time(authorization.approved_at)
        expires_at = _parse_aware_time(authorization.expires_at)
    except ValueError as exc:
        raise LiveRecoveryDrillError("production_guard_failed") from exc
    if (
        result.production_url != plan.production_url
        or result.active_generation != plan.expected_production_generation
        or result.deployment_id != authorization.production_deployment_id
        or result.readiness_state != "ready"
        or not _SAFE_NAME_PATTERN.fullmatch(result.request_id)
        or isinstance(result.latency_ms, bool)
        or not isinstance(result.latency_ms, int | float)
        or not math.isfinite(result.latency_ms)
        or result.latency_ms < 0
        or result.latency_ms > 10_000
        or checked_at < approved_at
        or checked_at >= expires_at
        or (not_before is not None and checked_at < not_before)
        or now >= expires_at
        or checked_at > now
        or now - checked_at > timedelta(minutes=5)
    ):
        raise LiveRecoveryDrillError("production_guard_failed")
    return result


def _stable_execution_error(
    exc: Exception,
    usage: _OperationUsage,
) -> LiveRecoveryDrillError:
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, LiveRecoveryDrillError):
            return current
        if _is_ambiguous_transport_error(current):
            code = (
                "ambiguous_mutation_result"
                if usage.put_operations or usage.deletes
                else "provider_read_failed"
            )
            return LiveRecoveryDrillError(code)
        current = current.__cause__ or current.__context__
    if isinstance(exc, GenerationConflictError):
        return LiveRecoveryDrillError("conditional_conflict")
    if isinstance(exc, GenerationPublicationError):
        return LiveRecoveryDrillError("provider_operation_failed")
    return LiveRecoveryDrillError("live_drill_failed")


def _prove_mutation_credential_is_prefix_scoped(
    client: Any,
    plan: LiveRecoveryDrillPlan,
    usage: _OperationUsage,
) -> None:
    if usage.class_b + 1 > plan.operation_limits.class_b:
        raise LiveRecoveryDrillError("operation_budget_exceeded")
    usage.class_b += 1
    try:
        client.head_object(
            Bucket=plan.bucket_name,
            Key=ACTIVE_GENERATION_PATH.as_posix(),
        )
    except Exception as exc:
        code, status = client_error_code_and_status(exc)
        if status == 403 and code in {"403", "AccessDenied"}:
            return
        _raise_read_transport_error(exc)
        raise LiveRecoveryDrillError("mutation_credential_scope_unverified") from exc
    raise LiveRecoveryDrillError("mutation_credential_scope_too_broad")


def _require_retries_disabled(client: Any) -> None:
    try:
        retries = client.meta.config.retries
        attempts = retries.get("total_max_attempts")
    except (AttributeError, TypeError) as exc:
        raise LiveRecoveryDrillError("retry_configuration_unverified") from exc
    if attempts != 1:
        raise LiveRecoveryDrillError("sdk_retries_not_disabled")


def _client_account_id_sha256(client: Any) -> str:
    try:
        endpoint = str(client.meta.endpoint_url)
    except AttributeError as exc:
        raise LiveRecoveryDrillError("provider_target_unverified") from exc
    parsed = urlsplit(endpoint)
    suffix = ".r2.cloudflarestorage.com"
    hostname = parsed.hostname or ""
    if parsed.scheme != "https" or not hostname.endswith(suffix):
        raise LiveRecoveryDrillError("provider_target_unverified")
    account_id = hostname[: -len(suffix)]
    if not account_id or "." in account_id:
        raise LiveRecoveryDrillError("provider_target_unverified")
    return hashlib.sha256(account_id.encode()).hexdigest()


def _raise_mutation_transport_error(exc: Exception) -> None:
    if _is_ambiguous_transport_error(exc) or _is_ambiguous_provider_response(exc):
        raise LiveRecoveryDrillError("ambiguous_mutation_result") from exc


def _raise_read_transport_error(exc: Exception) -> None:
    if _is_ambiguous_transport_error(exc) or _is_ambiguous_provider_response(exc):
        raise LiveRecoveryDrillError("provider_read_failed") from exc


def _is_ambiguous_transport_error(exc: BaseException) -> bool:
    return isinstance(exc, _AMBIGUOUS_TRANSPORT_ERRORS) or (
        isinstance(exc, BotoCoreError) and not isinstance(exc, ClientError)
    )


def _is_ambiguous_provider_response(exc: Exception) -> bool:
    _, status = client_error_code_and_status(exc)
    return status in {408, 429} or (status is not None and status >= 500)


def _operation_usage_dict(usage: _OperationUsage) -> dict[str, int]:
    return {
        "class_a": usage.class_a,
        "class_b": usage.class_b,
        "deletes": usage.deletes,
        "put_bytes": usage.put_bytes,
        "verified_read_bytes": usage.verified_read_bytes,
    }


def _generation_manifest_bytes(generation: str, records: list[dict[str, Any]]) -> bytes:
    document = {
        "schema_version": GENERATION_MANIFEST_SCHEMA_VERSION,
        "generation_id": generation,
        "files": records,
    }
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def _candidate_source_files() -> dict[str, bytes]:
    data = b"probe,value\nrecovery,1\n"
    data_sha256 = hashlib.sha256(data).hexdigest()
    receipt = {
        "schema_version": 1,
        "season": "recovery-drill",
        "season_type": "Recovery Drill",
        "generation_id": "e03b-candidate-source",
        "generated_at": "2026-07-22T00:00:00+00:00",
        "validation_state": "passed",
        "validation_errors": [],
        "datasets": [
            {
                "name": "recovery_probe",
                "path": "data/raw/recovery_probe.csv",
                "required": True,
                "generation_id": "e03b-candidate-source",
                "file_sha256": data_sha256,
                "validation": {"state": "passed", "errors": []},
            }
        ],
    }
    return {
        "metadata/dataset_manifests/recovery_drill.json": (
            json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        ).encode(),
        "raw/recovery_probe.csv": data,
    }


def _write_candidate_source(root: Path) -> None:
    for relative, payload in _candidate_source_files().items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def _records_for_bytes(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    return [
        {
            "path": path,
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        for path, payload in sorted(files.items())
    ]


def _pointer_bytes_for_budget(
    generation: str,
    previous_generation: str,
    manifest_sha256: str,
) -> bytes:
    document = {
        "schema_version": 1,
        "generation_id": generation,
        "previous_generation_id": previous_generation,
        "manifest_sha256": manifest_sha256,
        "published_at": "2000-01-01T00:00:00+00:00",
    }
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def _read_control_body(response: Mapping[str, Any]) -> bytes:
    body = response.get("Body")
    if body is None or not hasattr(body, "read"):
        raise LiveRecoveryDrillError("provider_body_missing")
    payload = body.read(MAX_CONTROL_BODY_BYTES + 1)
    if not isinstance(payload, bytes) or len(payload) > MAX_CONTROL_BODY_BYTES:
        raise LiveRecoveryDrillError("provider_body_too_large")
    return payload


def _hash_exact_body(response: Mapping[str, Any], expected_bytes: int) -> str:
    body = response.get("Body")
    if body is None or not hasattr(body, "read"):
        raise LiveRecoveryDrillError("provider_body_missing")
    digest = hashlib.sha256()
    remaining = expected_bytes
    while remaining:
        try:
            chunk = body.read(min(1024 * 1024, remaining))
        except Exception as exc:
            _raise_read_transport_error(exc)
            raise LiveRecoveryDrillError("provider_read_failed") from exc
        if not isinstance(chunk, bytes) or not chunk:
            raise LiveRecoveryDrillError("provider_body_size_mismatch")
        if len(chunk) > remaining:
            raise LiveRecoveryDrillError("provider_body_size_mismatch")
        digest.update(chunk)
        remaining -= len(chunk)
    try:
        extra = body.read(1)
    except Exception as exc:
        _raise_read_transport_error(exc)
        raise LiveRecoveryDrillError("provider_read_failed") from exc
    if not isinstance(extra, bytes) or extra:
        raise LiveRecoveryDrillError("provider_body_size_mismatch")
    return digest.hexdigest()


def _json_object(payload: bytes, error_code: str) -> dict[str, Any]:
    try:
        document = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LiveRecoveryDrillError(error_code) from exc
    if not isinstance(document, dict):
        raise LiveRecoveryDrillError(error_code)
    return document


def _validated_logical_key(value: str) -> str:
    if not value or value.startswith("/") or "\\" in value:
        raise LiveRecoveryDrillError("object_key_invalid")
    parts = value.split("/")
    if any(not part or part in {".", ".."} for part in parts):
        raise LiveRecoveryDrillError("object_key_invalid")
    return value


def _validated_prefix(value: str) -> str:
    if not value.startswith(f"{LIVE_DRILL_PREFIX_ROOT}/") or not value.endswith("/"):
        raise LiveRecoveryDrillError("drill_prefix_invalid")
    logical = value[:-1]
    _validated_logical_key(logical)
    if len(logical.split("/")) != 2 or not _DRILL_ID_PATTERN.fullmatch(logical.split("/")[1]):
        raise LiveRecoveryDrillError("drill_prefix_invalid")
    return value


def _validated_name(value: str, kind: str) -> str:
    if not _SAFE_NAME_PATTERN.fullmatch(value):
        raise LiveRecoveryDrillError(f"{kind}_invalid")
    return value


def _validated_production_url(value: str) -> str:
    cleaned = value.strip().rstrip("/")
    parsed = urlsplit(cleaned)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise LiveRecoveryDrillError("production_url_invalid")
    return cleaned


def _parse_aware_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(UTC)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1_000, 3)
