"""Production-isolated recovery drills for immutable runtime generations."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nbatools.commands.pipeline.generation_publication import (
    GENERATION_MANIFEST_PATH,
    GenerationValidationError,
    publish_local_generation,
    publish_r2_generation,
    rollback_local_generation,
    rollback_r2_generation,
    validate_staged_generation,
)
from nbatools.data_source import ACTIVE_GENERATION_PATH, GENERATIONS_DIR

RECOVERY_DRILL_SCHEMA_VERSION = 1
RECOVERY_DRILL_NAME = "immutable_generation_recovery"
RECOVERY_DRILL_MODE = "temporary_local_and_in_memory_r2"
_DRILL_BUCKET = "recovery-drill"


class RecoveryDrillError(RuntimeError):
    """Raised when a safe recovery drill cannot prove every invariant."""


@dataclass(frozen=True)
class RecoveryDrillReceipt:
    """Machine-readable receipt for one isolated recovery drill."""

    schema_version: int
    drill: str
    mode: str
    status: str
    started_at: str
    completed_at: str
    duration_ms: float
    network_access: bool
    real_credentials_loaded: bool
    production_mutation: bool
    checks: tuple[str, ...]
    measurements_ms: dict[str, float]
    recovered_generations: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible receipt."""
        return asdict(self)


def run_safe_recovery_drill() -> RecoveryDrillReceipt:
    """Run local and in-memory R2 recovery exercises in a temporary directory."""
    started_at = _utc_now()
    drill_started = time.perf_counter()
    checks: list[str] = []
    measurements: dict[str, float] = {}

    try:
        with tempfile.TemporaryDirectory(prefix="nbatools-recovery-drill-") as temp_dir:
            root = Path(temp_dir)
            local_generation = _run_local_drill(root, checks, measurements)
            r2_generation = _run_in_memory_r2_drill(root, checks, measurements)
    except Exception as exc:
        if isinstance(exc, RecoveryDrillError):
            raise
        raise RecoveryDrillError(f"Safe recovery drill failed: {type(exc).__name__}") from exc

    duration_ms = _elapsed_ms(drill_started)
    return RecoveryDrillReceipt(
        schema_version=RECOVERY_DRILL_SCHEMA_VERSION,
        drill=RECOVERY_DRILL_NAME,
        mode=RECOVERY_DRILL_MODE,
        status="passed",
        started_at=started_at,
        completed_at=_utc_now(),
        duration_ms=duration_ms,
        network_access=False,
        real_credentials_loaded=False,
        production_mutation=False,
        checks=tuple(checks),
        measurements_ms=measurements,
        recovered_generations={"local": local_generation, "in_memory_r2": r2_generation},
    )


def _run_local_drill(
    root: Path,
    checks: list[str],
    measurements: dict[str, float],
) -> str:
    data_root = root / "local-data"
    backup_root = root / "local-backup"
    _write_valid_source(data_root, "one")
    publish_local_generation("drill-local-one", source_dir=data_root, data_root=data_root)
    _write_valid_source(data_root, "two")
    publish_local_generation("drill-local-two", source_dir=data_root, data_root=data_root)

    target = data_root / GENERATIONS_DIR / "drill-local-one"
    backup = backup_root / "drill-local-one"
    shutil.copytree(target, backup)
    validate_staged_generation(backup, "drill-local-one")
    checks.append("local_backup_manifest_and_checksums_valid")

    pointer_path = data_root / ACTIVE_GENERATION_PATH
    pointer_before = pointer_path.read_bytes()
    (target / "raw" / "sample.csv").unlink()
    _require_refused_rollback(
        lambda: rollback_local_generation(data_root=data_root),
        pointer_path.read_bytes,
        pointer_before,
    )
    checks.append("local_incomplete_target_refused_without_pointer_change")

    restore_started = time.perf_counter()
    shutil.rmtree(target)
    shutil.copytree(backup, target)
    validate_staged_generation(target, "drill-local-one")
    measurements["local_restore"] = _elapsed_ms(restore_started)
    checks.append("local_backup_restored_with_manifest_and_checksum_verification")

    rollback_started = time.perf_counter()
    result = rollback_local_generation(data_root=data_root)
    measurements["local_rollback"] = _elapsed_ms(rollback_started)
    pointer = _read_json(pointer_path.read_bytes())
    _require(result.generation_id == "drill-local-one", "local rollback chose wrong target")
    _require(pointer.get("generation_id") == "drill-local-one", "local pointer was not restored")
    _require(
        pointer.get("previous_generation_id") == "drill-local-two",
        "local last-good generation was not retained",
    )
    _require(
        (data_root / GENERATIONS_DIR / "drill-local-two" / GENERATION_MANIFEST_PATH).is_file(),
        "local candidate generation disappeared during rollback",
    )
    checks.extend(
        (
            "local_pointer_switched_atomically_to_verified_generation",
            "local_pre_rollback_generation_retained",
        )
    )
    return result.generation_id


def _run_in_memory_r2_drill(
    root: Path,
    checks: list[str],
    measurements: dict[str, float],
) -> str:
    source = root / "r2-source"
    client = _InMemoryR2Client()
    _write_valid_source(source, "one")
    publish_r2_generation(
        "drill-r2-one",
        source_dir=source,
        client=client,
        bucket_name=_DRILL_BUCKET,
    )
    _write_valid_source(source, "two")
    publish_r2_generation(
        "drill-r2-two",
        source_dir=source,
        client=client,
        bucket_name=_DRILL_BUCKET,
    )

    target_prefix = f"{GENERATIONS_DIR}/drill-r2-one/"
    backup = client.snapshot_prefix(target_prefix)
    _require(bool(backup), "in-memory R2 backup was empty")
    checks.append("in_memory_r2_backup_contains_immutable_generation")

    pointer_key = ACTIVE_GENERATION_PATH.as_posix()
    pointer_before = client.objects[pointer_key]
    missing_key = f"{target_prefix}raw/sample.csv"
    client.delete_object_for_drill(missing_key)
    _require_refused_rollback(
        lambda: rollback_r2_generation(client=client, bucket_name=_DRILL_BUCKET),
        lambda: client.objects[pointer_key],
        pointer_before,
    )
    checks.append("in_memory_r2_incomplete_target_refused_without_pointer_change")

    restore_started = time.perf_counter()
    client.restore_snapshot(backup)
    measurements["in_memory_r2_restore"] = _elapsed_ms(restore_started)
    checks.append("in_memory_r2_backup_restored_with_exact_bytes_and_metadata")

    rollback_started = time.perf_counter()
    result = rollback_r2_generation(client=client, bucket_name=_DRILL_BUCKET)
    measurements["in_memory_r2_rollback"] = _elapsed_ms(rollback_started)
    pointer = _read_json(client.objects[pointer_key])
    _require(result.generation_id == "drill-r2-one", "in-memory R2 chose wrong target")
    _require(pointer.get("generation_id") == "drill-r2-one", "R2 pointer was not restored")
    _require(
        pointer.get("previous_generation_id") == "drill-r2-two",
        "R2 last-good generation was not retained",
    )
    _require(
        any(key.startswith(f"{GENERATIONS_DIR}/drill-r2-two/") for key in client.objects),
        "R2 candidate generation disappeared during rollback",
    )
    checks.extend(
        (
            "in_memory_r2_pointer_switched_conditionally_to_verified_generation",
            "in_memory_r2_pre_rollback_generation_retained",
        )
    )
    return result.generation_id


def _require_refused_rollback(
    operation: Any,
    read_pointer: Any,
    pointer_before: bytes,
) -> None:
    try:
        operation()
    except GenerationValidationError:
        pass
    else:
        raise RecoveryDrillError("rollback accepted an incomplete recovery target")
    _require(read_pointer() == pointer_before, "failed rollback changed the active pointer")


def _write_valid_source(data_root: Path, value: str) -> None:
    data_path = data_root / "raw" / "sample.csv"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(f"value\n{value}\n")
    generation_id = f"drill-receipt-{value}"
    receipt = {
        "schema_version": 1,
        "season": "drill",
        "season_type": "Regular Season",
        "generation_id": generation_id,
        "generated_at": "2026-07-21T00:00:00+00:00",
        "validation_state": "passed",
        "validation_errors": [],
        "datasets": [
            {
                "name": "sample",
                "path": "data/raw/sample.csv",
                "required": True,
                "generation_id": generation_id,
                "file_sha256": _sha256(data_path.read_bytes()),
                "validation": {"state": "passed", "errors": []},
            }
        ],
    }
    receipt_path = data_root / "metadata" / "dataset_manifests" / "drill_regular_season.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


def _read_json(payload: bytes) -> dict[str, Any]:
    document = json.loads(payload)
    if not isinstance(document, dict):
        raise RecoveryDrillError("recovery pointer is not a JSON object")
    return document


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _etag(payload: bytes) -> str:
    return hashlib.md5(payload, usedforsecurity=False).hexdigest()


def _elapsed_ms(started: float) -> float:
    return round(max(0.0, (time.perf_counter() - started) * 1000), 3)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RecoveryDrillError(message)


class _Body:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


class _InMemoryClientError(Exception):
    def __init__(self, code: str, status: int):
        self.response = {
            "Error": {"Code": code, "Message": "in-memory recovery drill"},
            "ResponseMetadata": {"HTTPStatusCode": status},
        }
        super().__init__(code)


class _InMemoryR2Client:
    """Minimum conditional object API used by the network-free drill."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.metadata: dict[str, dict[str, str]] = {}

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        del Bucket
        if Key not in self.objects:
            raise _InMemoryClientError("404", 404)
        payload = self.objects[Key]
        return {
            "ContentLength": len(payload),
            "Metadata": dict(self.metadata.get(Key, {})),
            "ETag": f'"{_etag(payload)}"',
        }

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        response = self.head_object(Bucket=Bucket, Key=Key)
        return {**response, "Body": _Body(self.objects[Key])}

    def put_object(self, **kwargs: Any) -> dict[str, str]:
        key = kwargs["Key"]
        existing = self.objects.get(key)
        if kwargs.get("IfNoneMatch") == "*" and existing is not None:
            raise _InMemoryClientError("PreconditionFailed", 412)
        if "IfMatch" in kwargs:
            if existing is None or kwargs["IfMatch"] != f'"{_etag(existing)}"':
                raise _InMemoryClientError("PreconditionFailed", 412)
        body = kwargs["Body"]
        payload = body.read() if hasattr(body, "read") else bytes(body)
        _require(kwargs["ContentLength"] == len(payload), "in-memory object size mismatch")
        self.objects[key] = payload
        self.metadata[key] = dict(kwargs.get("Metadata") or {})
        return {"ETag": f'"{_etag(payload)}"'}

    def snapshot_prefix(self, prefix: str) -> dict[str, tuple[bytes, dict[str, str]]]:
        return {
            key: (payload, dict(self.metadata.get(key, {})))
            for key, payload in self.objects.items()
            if key.startswith(prefix)
        }

    def delete_object_for_drill(self, key: str) -> None:
        self.objects.pop(key, None)
        self.metadata.pop(key, None)

    def restore_snapshot(self, snapshot: dict[str, tuple[bytes, dict[str, str]]]) -> None:
        for key, (payload, metadata) in snapshot.items():
            self.objects[key] = payload
            self.metadata[key] = dict(metadata)
