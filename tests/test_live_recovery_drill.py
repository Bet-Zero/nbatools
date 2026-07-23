from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from botocore.exceptions import ReadTimeoutError
from typer.testing import CliRunner

import nbatools.commands.pipeline.live_recovery_drill as live_drill
from nbatools.commands.pipeline.generation_publication import (
    GENERATION_MANIFEST_PATH,
    SHA256_METADATA_KEY,
    publish_local_generation,
)
from nbatools.commands.pipeline.live_recovery_drill import (
    LIVE_DRILL_SCHEMA_VERSION,
    LiveDrillOperationLimits,
    LiveDrillR2ClientHandle,
    LiveRecoveryDrillAuthorization,
    LiveRecoveryDrillError,
    LiveRecoveryDrillExecutionError,
    LiveRecoveryDrillPlan,
    PrefixEnforcingR2Client,
    ProductionGuardResult,
    execute_live_recovery_drill,
    prepare_live_recovery_drill_plan,
)
from nbatools.commands.pipeline.sync_r2 import R2SyncConfig
from nbatools.data_source import ACTIVE_GENERATION_PATH, GENERATIONS_DIR

pytestmark = pytest.mark.engine


TEST_ACCOUNT_ID = "test-account"
TEST_ACCOUNT_SHA256 = hashlib.sha256(TEST_ACCOUNT_ID.encode()).hexdigest()
TEST_BUCKET = "nbatools-data"
TEST_COMMIT = "e0677d66fe1469ba1fcbebf3e06ba7df50dffadd"
TEST_ENDPOINT = f"https://{TEST_ACCOUNT_ID}.r2.cloudflarestorage.com"
TEST_NOW = datetime(2026, 7, 22, 16, 0, tzinfo=UTC)


class FakeBody:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.offset = 0

    def read(self, amount: int = -1) -> bytes:
        if amount < 0:
            amount = len(self.payload) - self.offset
        start = self.offset
        self.offset = min(len(self.payload), self.offset + amount)
        return self.payload[start : self.offset]


class ErrorBody:
    def read(self, amount: int = -1) -> bytes:
        del amount
        raise ReadTimeoutError(endpoint_url=TEST_ENDPOINT)


class FakeClientError(Exception):
    def __init__(self, code: str, status: int):
        self.response = {
            "Error": {"Code": code, "Message": "fake provider detail"},
            "ResponseMetadata": {"HTTPStatusCode": status},
        }
        super().__init__("fake provider detail")


@dataclass
class FakeR2Store:
    objects: dict[str, bytes]
    metadata: dict[str, dict[str, str]]

    @classmethod
    def empty(cls) -> FakeR2Store:
        return cls(objects={}, metadata={})


class FakeR2Client:
    def __init__(
        self,
        store: FakeR2Store,
        *,
        deny_root_head: bool = False,
        account_id: str = TEST_ACCOUNT_ID,
        retry_attempts: int = 1,
    ) -> None:
        self.store = store
        self.deny_root_head = deny_root_head
        self.meta = SimpleNamespace(
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            config=SimpleNamespace(
                retries={"total_max_attempts": retry_attempts, "mode": "standard"}
            ),
        )
        self.calls: list[tuple[str, str]] = []
        self.put_calls: list[str] = []
        self.delete_calls: list[str] = []
        self.mutation_error: Exception | None = None
        self.mutation_error_count = 0
        self.conflict_on_second_prefixed_pointer_put = False
        self.prefixed_pointer_puts = 0
        self.corrupt_get_keys: set[str] = set()
        self.error_body_keys: set[str] = set()
        self.corruption_count = 0
        self.swap_cleanup_inventory = False
        self.prefix_list_count = 0
        self.unexpected_cleanup_key: str | None = None

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        del Bucket
        self.calls.append(("head", Key))
        if self.deny_root_head and Key == ACTIVE_GENERATION_PATH.as_posix():
            raise FakeClientError("AccessDenied", 403)
        return self._head_response(Key)

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        del Bucket
        self.calls.append(("get", Key))
        response = self._head_response(Key)
        payload = self.store.objects[Key]
        if Key in self.corrupt_get_keys:
            corrupted = bytearray(payload)
            corrupted[0] ^= 1
            payload = bytes(corrupted)
            self.corruption_count += 1
        body = ErrorBody() if Key in self.error_body_keys else FakeBody(payload)
        return {**response, "Body": body}

    def put_object(self, **kwargs: Any) -> dict[str, str]:
        key = str(kwargs["Key"])
        self.calls.append(("put", key))
        if self.mutation_error is not None and key.startswith("recovery-drills/"):
            error = self.mutation_error
            self.mutation_error = None
            self.mutation_error_count += 1
            raise error

        if key.startswith("recovery-drills/") and key.endswith(ACTIVE_GENERATION_PATH.as_posix()):
            self.prefixed_pointer_puts += 1
            if (
                self.conflict_on_second_prefixed_pointer_put
                and self.prefixed_pointer_puts == 2
                and key in self.store.objects
            ):
                self.store.objects[key] = b'{"generation_id":"external"}'
                self.store.metadata[key] = {}

        existing = self.store.objects.get(key)
        if kwargs.get("IfNoneMatch") == "*" and existing is not None:
            raise FakeClientError("PreconditionFailed", 412)
        if "IfMatch" in kwargs:
            if existing is None or kwargs["IfMatch"] != f'"{_etag(existing)}"':
                raise FakeClientError("PreconditionFailed", 412)

        body = kwargs["Body"]
        payload = body.read() if hasattr(body, "read") else bytes(body)
        assert len(payload) == kwargs["ContentLength"]
        self.store.objects[key] = payload
        self.store.metadata[key] = dict(kwargs.get("Metadata") or {})
        self.put_calls.append(key)
        return {"ETag": f'"{_etag(payload)}"'}

    def delete_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        del Bucket
        self.calls.append(("delete", Key))
        self.delete_calls.append(Key)
        self.store.objects.pop(Key, None)
        self.store.metadata.pop(Key, None)
        return {}

    def list_objects_v2(self, *, Bucket: str, Prefix: str) -> dict[str, Any]:
        del Bucket
        self.calls.append(("list", Prefix))
        if Prefix.startswith("recovery-drills/"):
            self.prefix_list_count += 1
        if self.swap_cleanup_inventory and self.prefix_list_count == 2:
            existing = sorted(key for key in self.store.objects if key.startswith(Prefix))
            victim = next(
                key for key in existing if not key.endswith(ACTIVE_GENERATION_PATH.as_posix())
            )
            payload = self.store.objects.pop(victim)
            self.store.metadata.pop(victim, None)
            unexpected = f"{Prefix}unexpected-cleanup-object.bin"
            self.store.objects[unexpected] = payload
            self.store.metadata[unexpected] = {SHA256_METADATA_KEY: _sha256(payload)}
            self.unexpected_cleanup_key = unexpected
        contents = [
            {"Key": key, "Size": len(payload)}
            for key, payload in sorted(self.store.objects.items())
            if key.startswith(Prefix)
        ]
        return {"Contents": contents, "IsTruncated": False}

    def _head_response(self, key: str) -> dict[str, Any]:
        if key not in self.store.objects:
            raise FakeClientError("404", 404)
        payload = self.store.objects[key]
        return {
            "ContentLength": len(payload),
            "Metadata": dict(self.store.metadata.get(key, {})),
            "ETag": f'"{_etag(payload)}"',
            "StorageClass": "STANDARD",
        }


@dataclass
class DrillContext:
    source_dir: Path
    plan: LiveRecoveryDrillPlan
    mutation_store: FakeR2Store
    production_store: FakeR2Store
    mutation_client: FakeR2Client
    production_client: FakeR2Client
    mutation_handle: LiveDrillR2ClientHandle
    production_handle: LiveDrillR2ClientHandle
    authorization: LiveRecoveryDrillAuthorization
    production_pointer: bytes


def test_network_free_plan_is_hash_bound_canonical_and_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_dir = _local_generation(tmp_path, "local-one")
    plan = _plan(source_dir, monkeypatch)
    document = plan.to_dict()

    assert plan.schema_version == LIVE_DRILL_SCHEMA_VERSION
    assert plan.state == "prepared_not_authorized"
    assert plan.repository_commit == TEST_COMMIT
    assert plan.r2_account_id_sha256 == TEST_ACCOUNT_SHA256
    assert plan.source_file_count == 2
    assert plan.restored_object_count == 3
    assert plan.candidate_object_count == 3
    assert plan.max_live_objects == 7
    assert plan.operation_limits.class_a == 13
    assert plan.operation_limits.class_b == 38
    assert plan.operation_limits.deletes == 8
    assert plan.operation_limits.put_bytes > plan.max_live_bytes
    assert plan.operation_limits.verified_read_bytes > plan.restored_bytes
    assert document["plan_sha256"] == plan.plan_sha256
    assert LiveRecoveryDrillPlan.from_dict(document) == plan

    tampered = dict(document)
    tampered["bucket_name"] = "different-bucket"
    with pytest.raises(LiveRecoveryDrillError, match="plan_hash_mismatch"):
        LiveRecoveryDrillPlan.from_dict(tampered)


def test_plan_refuses_unapproved_source_by_default(tmp_path: Path) -> None:
    source_dir = _local_generation(tmp_path, "local-one")

    with pytest.raises(LiveRecoveryDrillError, match="approved_source_boundary_changed"):
        prepare_live_recovery_drill_plan(
            source_generation_dir=source_dir,
            source_generation="local-one",
            repository_commit=TEST_COMMIT,
            drill_id="e03b-test-20260722-01",
            r2_account_id_sha256=TEST_ACCOUNT_SHA256,
            bucket_name=TEST_BUCKET,
            production_url="https://deploy.example",
            expected_production_generation="prod-one",
        )


def test_prefix_client_cannot_mutate_root_escape_prefix_or_exceed_budget() -> None:
    store = FakeR2Store.empty()
    inner = FakeR2Client(store)
    wrapped = PrefixEnforcingR2Client(
        inner,
        bucket_name=TEST_BUCKET,
        drill_prefix="recovery-drills/e03b-test-20260722-01/",
        limits=LiveDrillOperationLimits(10, 10, 10, 1_000, 1_000),
    )

    wrapped.put_object(
        Bucket=TEST_BUCKET,
        Key=ACTIVE_GENERATION_PATH.as_posix(),
        Body=b"isolated",
        ContentLength=8,
    )

    assert ACTIVE_GENERATION_PATH.as_posix() not in store.objects
    assert (
        store.objects["recovery-drills/e03b-test-20260722-01/metadata/active_generation.json"]
        == b"isolated"
    )
    with pytest.raises(LiveRecoveryDrillError, match="object_key_invalid"):
        wrapped.delete_object(Bucket=TEST_BUCKET, Key="../metadata/root.json")
    with pytest.raises(LiveRecoveryDrillError, match="bucket_mismatch"):
        wrapped.head_object(Bucket="other-bucket", Key="metadata/file.json")

    no_reads = PrefixEnforcingR2Client(
        inner,
        bucket_name=TEST_BUCKET,
        drill_prefix="recovery-drills/e03b-budget-20260722-01/",
        limits=LiveDrillOperationLimits(0, 0, 0, 0, 0),
    )
    calls_before = len(inner.calls)
    with pytest.raises(LiveRecoveryDrillError, match="operation_budget_exceeded"):
        no_reads.list_objects_v2(Bucket=TEST_BUCKET)
    assert len(inner.calls) == calls_before


def test_authorized_fake_provider_drill_proves_isolation_bytes_and_exact_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path, monkeypatch)

    receipt = _execute(context)

    document = receipt.to_dict()
    limits = context.plan.operation_limits
    assert document["status"] == "passed"
    assert document["repository_commit"] == TEST_COMMIT
    assert document["r2_account_id_sha256"] == TEST_ACCOUNT_SHA256
    assert document["production_generation_unchanged"] is True
    assert document["candidate_retained_until_cleanup"] is True
    assert document["isolated_prefix_empty_after_cleanup"] is True
    assert document["operation_usage"] == {
        "class_a": limits.class_a,
        "class_b": limits.class_b - 1,
        "deletes": limits.deletes,
        "put_bytes": limits.put_bytes,
        "verified_read_bytes": limits.verified_read_bytes,
    }
    assert "full_source_restored_and_byte_verified_in_isolated_generation" in document["checks"]
    assert "incomplete_target_refused_without_pointer_change" in document["checks"]
    assert (
        context.production_store.objects[ACTIVE_GENERATION_PATH.as_posix()]
        == context.production_pointer
    )
    assert not any(
        key.startswith(context.plan.drill_prefix) for key in context.mutation_store.objects
    )
    assert len(context.mutation_client.delete_calls) == limits.deletes


def test_recomputed_noncanonical_plan_is_rejected_before_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path, monkeypatch)
    tampered = replace(context.plan, max_live_bytes=context.plan.max_live_bytes + 1)
    guard_calls: list[None] = []

    with pytest.raises(LiveRecoveryDrillError, match="plan_not_canonical"):
        execute_live_recovery_drill(
            tampered,
            _authorization(tampered),
            source_generation_dir=context.source_dir,
            mutation_client=context.mutation_handle,
            production_read_client=context.production_handle,
            current_repository_commit=TEST_COMMIT,
            production_guard=lambda: guard_calls.append(None),  # type: ignore[arg-type,return-value]
            clock=lambda: TEST_NOW,
        )

    assert context.mutation_client.calls == []
    assert context.production_client.calls == []
    assert guard_calls == []


def test_same_size_payload_corruption_is_caught_by_streaming_byte_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path, monkeypatch)
    source_manifest = json.loads((context.source_dir / GENERATION_MANIFEST_PATH).read_text())
    relative = source_manifest["files"][0]["path"]
    corrupt_key = (
        f"{context.plan.drill_prefix}{GENERATIONS_DIR}/"
        f"{context.plan.restored_generation}/{relative}"
    )
    context.mutation_client.corrupt_get_keys.add(corrupt_key)

    with pytest.raises(LiveRecoveryDrillExecutionError) as excinfo:
        _execute(context)

    assert excinfo.value.code == "restored_object_byte_verification_failed"
    assert excinfo.value.receipt.cleanup_state == "not_completed_prefix_requires_inspection"
    assert excinfo.value.receipt.operation_usage["verified_read_bytes"] > 0
    assert context.mutation_client.corruption_count == 1
    assert context.mutation_client.delete_calls == []
    assert any(key.startswith(context.plan.drill_prefix) for key in context.mutation_store.objects)


def test_streaming_read_timeout_after_mutation_is_read_failure_with_guard_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path, monkeypatch)
    source_manifest = json.loads((context.source_dir / GENERATION_MANIFEST_PATH).read_text())
    relative = source_manifest["files"][0]["path"]
    error_key = (
        f"{context.plan.drill_prefix}{GENERATIONS_DIR}/"
        f"{context.plan.restored_generation}/{relative}"
    )
    context.mutation_client.error_body_keys.add(error_key)

    with pytest.raises(LiveRecoveryDrillExecutionError) as excinfo:
        _execute(context)

    assert excinfo.value.code == "provider_read_failed"
    assert excinfo.value.receipt.mutation_started is True
    assert excinfo.value.receipt.production_guard_before is not None
    assert excinfo.value.receipt.production_guard_after is None
    assert excinfo.value.receipt.cleanup_state == "not_completed_prefix_requires_inspection"


def test_conditional_pointer_conflict_aborts_and_preserves_production(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path, monkeypatch)
    context.mutation_client.conflict_on_second_prefixed_pointer_put = True

    with pytest.raises(LiveRecoveryDrillExecutionError) as excinfo:
        _execute(context)

    assert excinfo.value.code == "conditional_conflict"
    assert (
        context.production_store.objects[ACTIVE_GENERATION_PATH.as_posix()]
        == context.production_pointer
    )
    assert any(key.startswith(context.plan.drill_prefix) for key in context.mutation_store.objects)


def test_botocore_mutation_timeout_is_ambiguous_with_receipt_and_no_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path, monkeypatch)
    context.mutation_client.mutation_error = ReadTimeoutError(endpoint_url=TEST_ENDPOINT)

    with pytest.raises(LiveRecoveryDrillExecutionError) as excinfo:
        _execute(context)

    error = excinfo.value
    assert error.code == "ambiguous_mutation_result"
    assert error.receipt.error_code == "ambiguous_mutation_result"
    assert error.receipt.mutation_started is True
    assert error.receipt.cleanup_state == "not_completed_prefix_requires_inspection"
    assert error.receipt.mutation_outcomes == ()
    assert context.mutation_client.mutation_error_count == 1
    assert context.mutation_client.delete_calls == []
    assert context.mutation_client.prefix_list_count == 1


def test_expired_authorization_is_rejected_before_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path, monkeypatch)
    expired = replace(
        context.authorization,
        expires_at=TEST_NOW.isoformat(),
    )

    with pytest.raises(LiveRecoveryDrillError, match="authorization_not_current"):
        _execute(context, authorization=expired)

    assert context.mutation_client.calls == []
    assert context.production_client.calls == []


def test_execution_crossing_authorization_deadline_refuses_first_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path, monkeypatch)
    expires_at = TEST_NOW + timedelta(seconds=30)
    authorization = replace(context.authorization, expires_at=expires_at.isoformat())
    authorization = replace(authorization, projected_execution_seconds=1.0)
    clock = SequenceClock(TEST_NOW, TEST_NOW, TEST_NOW, expires_at)

    with pytest.raises(LiveRecoveryDrillExecutionError) as excinfo:
        _execute(context, authorization=authorization, clock=clock)

    assert excinfo.value.code == "authorization_expired_during_execution"
    assert excinfo.value.receipt.mutation_started is False
    assert context.mutation_client.put_calls == []
    assert context.mutation_client.delete_calls == []


def test_wrong_production_guard_url_fails_before_data_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path, monkeypatch)
    wrong_guard = replace(
        _guard(context.plan, context.authorization),
        production_url="https://wrong.example",
    )

    with pytest.raises(LiveRecoveryDrillExecutionError) as excinfo:
        _execute(context, production_guard=lambda: wrong_guard)

    assert excinfo.value.code == "production_guard_failed"
    assert excinfo.value.receipt.mutation_started is False
    assert context.mutation_client.put_calls == []
    assert context.mutation_client.delete_calls == []
    assert context.production_client.calls == []


def test_post_cleanup_guard_must_be_newer_than_cleanup_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path, monkeypatch)
    cached_guards = _guard_sequence(context.plan, context.authorization)

    with pytest.raises(LiveRecoveryDrillExecutionError) as excinfo:
        _execute(
            context,
            production_guard=cached_guards,
            clock=lambda: TEST_NOW + timedelta(minutes=1),
        )

    assert excinfo.value.code == "production_guard_failed"
    assert excinfo.value.receipt.cleanup_state == "completed_prefix_verified_empty"
    assert not any(
        key.startswith(context.plan.drill_prefix) for key in context.mutation_store.objects
    )


def test_same_count_unexpected_cleanup_inventory_is_preserved_for_investigation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path, monkeypatch)
    context.mutation_client.swap_cleanup_inventory = True

    with pytest.raises(LiveRecoveryDrillExecutionError) as excinfo:
        _execute(context)

    assert excinfo.value.code == "cleanup_inventory_mismatch"
    assert excinfo.value.receipt.cleanup_state == "not_completed_prefix_requires_inspection"
    assert context.mutation_client.unexpected_cleanup_key in context.mutation_store.objects
    assert len(context.mutation_client.delete_calls) == 1
    assert any(key.startswith(context.plan.drill_prefix) for key in context.mutation_store.objects)


def test_external_cost_plan_and_backup_authorization_are_hard_pre_network_gates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path, monkeypatch)

    for authorization, code in (
        (replace(context.authorization, projected_cost_usd=0.01), "zero_cost_gate_failed"),
        (
            replace(context.authorization, approved_plan_sha256="0" * 64),
            "authorization_plan_mismatch",
        ),
        (
            replace(context.authorization, backup_bytes=context.plan.source_bytes + 1),
            "backup_source_mismatch",
        ),
    ):
        with pytest.raises(LiveRecoveryDrillError, match=code):
            _execute(context, authorization=authorization)

    assert context.mutation_client.calls == []
    assert context.production_client.calls == []


def test_execution_requires_distinct_retry_disabled_role_bound_clients_and_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path, monkeypatch)

    same_client = replace(
        context.production_handle,
        client=context.mutation_client,
    )
    with pytest.raises(LiveRecoveryDrillError, match="separate_credentials_required"):
        _execute(context, production_handle=same_client)

    same_credential = replace(
        context.production_handle,
        credential_id_sha256=context.mutation_handle.credential_id_sha256,
    )
    with pytest.raises(LiveRecoveryDrillError, match="separate_credentials_required"):
        _execute(context, production_handle=same_credential)

    context.mutation_client.meta.config.retries["total_max_attempts"] = 2
    with pytest.raises(LiveRecoveryDrillError, match="sdk_retries_not_disabled"):
        _execute(context)
    context.mutation_client.meta.config.retries["total_max_attempts"] = 1

    context.mutation_client.meta.endpoint_url = "https://different-account.r2.cloudflarestorage.com"
    with pytest.raises(LiveRecoveryDrillError, match="provider_target_mismatch"):
        _execute(context)

    assert context.mutation_client.calls == []
    assert context.production_client.calls == []


def test_temporary_credential_identity_distinguishes_locally_signed_sessions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clients: list[SimpleNamespace] = []

    def fake_create_r2_client(
        config: R2SyncConfig,
        *,
        disable_retries: bool,
    ) -> SimpleNamespace:
        assert disable_retries is True
        client = SimpleNamespace(
            meta=SimpleNamespace(
                config=SimpleNamespace(retries={"total_max_attempts": 1}),
                endpoint_url=(f"https://{config.account_id}.r2.cloudflarestorage.com"),
            )
        )
        clients.append(client)
        return client

    monkeypatch.setattr(live_drill, "create_r2_client", fake_create_r2_client)
    shared = {
        "account_id": TEST_ACCOUNT_ID,
        "access_key_id": "shared-parent-access-key",
        "bucket_name": TEST_BUCKET,
    }
    mutation = live_drill.create_live_drill_mutation_client(
        R2SyncConfig(
            **shared,
            secret_access_key="mutation-secret",
            session_token="mutation-session",
        )
    )
    production = live_drill.create_live_drill_production_reader(
        R2SyncConfig(
            **shared,
            secret_access_key="production-secret",
            session_token="production-session",
        )
    )
    repeated_mutation = live_drill.create_live_drill_mutation_client(
        R2SyncConfig(
            **shared,
            secret_access_key="mutation-secret",
            session_token="mutation-session",
        )
    )

    assert mutation.client is not production.client
    assert mutation.credential_id_sha256 != production.credential_id_sha256
    assert mutation.credential_id_sha256 == repeated_mutation.credential_id_sha256
    assert all(
        len(handle.credential_id_sha256) == 64
        for handle in (mutation, production, repeated_mutation)
    )
    assert len(clients) == 3


def test_live_plan_cli_fails_closed_without_traceback_or_provider_access(
    tmp_path: Path,
) -> None:
    from nbatools.cli_apps.pipeline import app

    source_dir = _local_generation(tmp_path, "local-one")
    result = CliRunner().invoke(
        app,
        [
            "live-recovery-drill-plan",
            "--source-generation-dir",
            str(source_dir),
            "--source-generation",
            "local-one",
            "--repository-commit",
            TEST_COMMIT,
            "--drill-id",
            "e03b-test-20260722-01",
            "--r2-account-id-sha256",
            TEST_ACCOUNT_SHA256,
            "--production-url",
            "https://deploy.example",
            "--expected-production-generation",
            "prod-one",
        ],
    )

    assert result.exit_code == 1
    assert "approved_source_boundary_changed" in result.output
    assert "Traceback" not in result.output


class SequenceClock:
    def __init__(self, *values: datetime):
        self.values = list(values)

    def __call__(self) -> datetime:
        if len(self.values) > 1:
            return self.values.pop(0)
        return self.values[0]


def _context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DrillContext:
    source_dir = _local_generation(tmp_path, "local-one")
    plan = _plan(source_dir, monkeypatch)
    mutation_store = FakeR2Store.empty()
    production_store = FakeR2Store.empty()
    mutation_client = FakeR2Client(mutation_store, deny_root_head=True)
    production_client = FakeR2Client(production_store)
    mutation_handle = _handle(
        mutation_client,
        role="isolated-prefix-read-write",
        credential_id="mutation-temporary-key",
    )
    production_handle = _handle(
        production_client,
        role="production-read-only",
        credential_id="production-read-temporary-key",
    )
    authorization = _authorization(plan)
    pointer = _install_production_snapshot(production_store, plan, source_dir)
    return DrillContext(
        source_dir=source_dir,
        plan=plan,
        mutation_store=mutation_store,
        production_store=production_store,
        mutation_client=mutation_client,
        production_client=production_client,
        mutation_handle=mutation_handle,
        production_handle=production_handle,
        authorization=authorization,
        production_pointer=pointer,
    )


def _execute(
    context: DrillContext,
    *,
    authorization: LiveRecoveryDrillAuthorization | None = None,
    production_guard: Any | None = None,
    production_handle: LiveDrillR2ClientHandle | None = None,
    clock: Any | None = None,
):
    selected_authorization = authorization or context.authorization
    selected_guard = production_guard or _guard_sequence(
        context.plan,
        selected_authorization,
    )
    return execute_live_recovery_drill(
        context.plan,
        selected_authorization,
        source_generation_dir=context.source_dir,
        mutation_client=context.mutation_handle,
        production_read_client=production_handle or context.production_handle,
        current_repository_commit=TEST_COMMIT,
        production_guard=selected_guard,
        clock=clock or (lambda: TEST_NOW),
    )


def _plan(
    source_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> LiveRecoveryDrillPlan:
    _approve_source(source_dir, monkeypatch)
    return prepare_live_recovery_drill_plan(
        source_generation_dir=source_dir,
        source_generation=source_dir.name,
        repository_commit=TEST_COMMIT,
        drill_id="e03b-test-20260722-01",
        r2_account_id_sha256=TEST_ACCOUNT_SHA256,
        bucket_name=TEST_BUCKET,
        production_url="https://deploy.example",
        expected_production_generation="prod-one",
        _generated_at="2026-07-22T15:00:00Z",
    )


def _approve_source(source_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest_payload = (source_dir / GENERATION_MANIFEST_PATH).read_bytes()
    manifest = json.loads(manifest_payload)
    monkeypatch.setattr(live_drill, "APPROVED_SOURCE_GENERATION", source_dir.name)
    monkeypatch.setattr(
        live_drill,
        "APPROVED_SOURCE_MANIFEST_SHA256",
        _sha256(manifest_payload),
    )
    monkeypatch.setattr(live_drill, "APPROVED_SOURCE_FILE_COUNT", len(manifest["files"]))
    monkeypatch.setattr(
        live_drill,
        "APPROVED_SOURCE_BYTES",
        sum(int(item["size_bytes"]) for item in manifest["files"]),
    )


def _authorization(plan: LiveRecoveryDrillPlan) -> LiveRecoveryDrillAuthorization:
    return LiveRecoveryDrillAuthorization(
        approved_plan_sha256=plan.plan_sha256,
        approval_reference="owner-approved-exact-plan",
        operator="test-operator",
        incident_owner="John Matthew",
        production_deployment_id="deployment-20260722",
        approved_at=(TEST_NOW - timedelta(minutes=1)).isoformat(),
        expires_at=(TEST_NOW + timedelta(hours=1)).isoformat(),
        projected_cost_usd=0.0,
        storage_class="Standard",
        credential_scope="separate-temporary-prefix-write-and-production-read-only",
        billing_usage_receipt="billing-receipt-id",
        mutation_credential_scope_receipt="mutation-scope-receipt-id",
        production_read_credential_scope_receipt="production-read-scope-receipt-id",
        production_preflight_receipt="preflight-receipt-id",
        independent_backup_receipt="backup-receipt-id",
        backup_created_at=(TEST_NOW - timedelta(hours=1)).isoformat(),
        backup_generation=plan.local_source_generation,
        backup_manifest_sha256=plan.local_source_manifest_sha256,
        backup_file_count=plan.source_file_count,
        backup_bytes=plan.source_bytes,
        projected_execution_seconds=60.0,
        duration_estimate_receipt="duration-estimate-receipt-id",
    )


def _guard(
    plan: LiveRecoveryDrillPlan,
    authorization: LiveRecoveryDrillAuthorization,
    *,
    request_id: str = "request-20260722-1",
) -> ProductionGuardResult:
    return ProductionGuardResult(
        production_url=plan.production_url,
        active_generation=plan.expected_production_generation,
        deployment_id=authorization.production_deployment_id,
        checked_at=TEST_NOW.isoformat(),
        request_id=request_id,
        readiness_state="ready",
        latency_ms=125.0,
    )


def _guard_sequence(
    plan: LiveRecoveryDrillPlan,
    authorization: LiveRecoveryDrillAuthorization,
):
    call_count = 0

    def run() -> ProductionGuardResult:
        nonlocal call_count
        call_count += 1
        return _guard(
            plan,
            authorization,
            request_id=f"request-20260722-{call_count}",
        )

    return run


def _handle(
    client: FakeR2Client,
    *,
    role: str,
    credential_id: str,
) -> LiveDrillR2ClientHandle:
    return LiveDrillR2ClientHandle(
        client=client,
        role=role,
        account_id_sha256=TEST_ACCOUNT_SHA256,
        bucket_name=TEST_BUCKET,
        credential_id_sha256=hashlib.sha256(credential_id.encode()).hexdigest(),
    )


def _local_generation(tmp_path: Path, generation: str) -> Path:
    data_root = tmp_path / "data"
    data_path = data_root / "raw" / "sample.csv"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text("value\none\n")
    receipt = {
        "schema_version": 1,
        "season": "test",
        "season_type": "Regular Season",
        "generation_id": "test-source",
        "generated_at": "2026-07-22T00:00:00+00:00",
        "validation_state": "passed",
        "validation_errors": [],
        "datasets": [
            {
                "name": "sample",
                "path": "data/raw/sample.csv",
                "required": True,
                "generation_id": "test-source",
                "file_sha256": _sha256(data_path.read_bytes()),
                "validation": {"state": "passed", "errors": []},
            }
        ],
    }
    receipt_path = data_root / "metadata" / "dataset_manifests" / "test.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    publish_local_generation(generation, source_dir=data_root, data_root=data_root)
    return data_root / GENERATIONS_DIR / generation


def _install_production_snapshot(
    store: FakeR2Store,
    plan: LiveRecoveryDrillPlan,
    source_dir: Path,
) -> bytes:
    source_manifest = json.loads((source_dir / GENERATION_MANIFEST_PATH).read_text())
    production_manifest = {
        "schema_version": 1,
        "generation_id": plan.expected_production_generation,
        "files": source_manifest["files"],
    }
    manifest_payload = (json.dumps(production_manifest, indent=2, sort_keys=True) + "\n").encode()
    assert _sha256(manifest_payload) == plan.expected_production_manifest_sha256
    manifest_key = (
        f"{GENERATIONS_DIR}/{plan.expected_production_generation}/"
        f"{GENERATION_MANIFEST_PATH.as_posix()}"
    )
    store.objects[manifest_key] = manifest_payload
    store.metadata[manifest_key] = {SHA256_METADATA_KEY: _sha256(manifest_payload)}
    for item in source_manifest["files"]:
        payload = (source_dir / item["path"]).read_bytes()
        key = f"{GENERATIONS_DIR}/{plan.expected_production_generation}/{item['path']}"
        store.objects[key] = payload
        store.metadata[key] = {SHA256_METADATA_KEY: item["sha256"]}
    pointer = (
        json.dumps(
            {
                "schema_version": 1,
                "generation_id": plan.expected_production_generation,
                "previous_generation_id": "legacy",
                "manifest_sha256": plan.expected_production_manifest_sha256,
                "published_at": "2026-07-22T00:00:00+00:00",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode()
    store.objects[ACTIVE_GENERATION_PATH.as_posix()] = pointer
    store.metadata[ACTIVE_GENERATION_PATH.as_posix()] = {}
    return pointer


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _etag(payload: bytes) -> str:
    return hashlib.md5(payload, usedforsecurity=False).hexdigest()
