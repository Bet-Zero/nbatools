"""Validated, generation-atomic publication for local data and Cloudflare R2."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nbatools.commands.pipeline.sync_r2 import R2SyncError, create_r2_client, load_r2_config
from nbatools.data_source import (
    ACTIVE_GENERATION_PATH,
    GENERATIONS_DIR,
    LEGACY_GENERATION,
    DataSourceError,
    validate_data_generation_id,
)
from nbatools.r2_errors import (
    format_client_error,
    is_not_found,
    is_precondition_failed,
)

GENERATION_MANIFEST_PATH = Path("metadata/generation_manifest.json")
GENERATION_MANIFEST_SCHEMA_VERSION = 1
POINTER_SCHEMA_VERSION = 1
SHA256_METADATA_KEY = "nbatools-sha256"


class GenerationPublicationError(Exception):
    """Base exception for safe generation publication failures."""


class GenerationValidationError(GenerationPublicationError):
    """Raised when a staged generation fails validation."""


class GenerationObjectValidationError(GenerationValidationError):
    """Identify the exact immutable object that failed rollback validation."""

    def __init__(self, generation_id: str, object_key: str, reason: str):
        self.generation_id = generation_id
        self.object_key = object_key
        self.reason = reason
        super().__init__(
            f"R2 rollback generation object failed verification: {object_key} ({reason})"
        )


class GenerationConflictError(GenerationPublicationError):
    """Raised when immutable data or active-pointer ownership changed."""


@dataclass(frozen=True)
class GenerationPublicationResult:
    """Receipt for one completed generation publication or rollback."""

    target: str
    generation_id: str
    previous_generation_id: str
    file_count: int
    total_bytes: int
    manifest_sha256: str | None
    pointer: str
    action: str = "publish"


@dataclass(frozen=True)
class _PointerState:
    generation_id: str
    previous_generation_id: str | None
    fingerprint: str | None
    etag: str | None = None


def publish_local_generation(
    generation_id: str,
    *,
    source_dir: Path = Path("data"),
    data_root: Path | None = None,
) -> GenerationPublicationResult:
    """Validate and atomically activate one immutable local data generation."""
    generation = _validated_generation_id(generation_id)
    source = source_dir.expanduser().resolve()
    root = (data_root or source_dir).expanduser().resolve()
    if not source.is_dir():
        raise GenerationPublicationError(f"Data source directory not found: {source}")

    pointer_path = root / ACTIVE_GENERATION_PATH
    starting_pointer = _read_local_pointer(pointer_path)
    generations_dir = root / GENERATIONS_DIR
    generations_dir.mkdir(parents=True, exist_ok=True)
    staged = generations_dir / f".staging-{generation}-{uuid.uuid4().hex}"
    final = generations_dir / generation

    try:
        _build_staged_generation(source, staged, generation)
        manifest = validate_staged_generation(staged, generation)
        if final.exists():
            _require_same_generation(final, staged, generation)
            shutil.rmtree(staged)
        else:
            try:
                staged.rename(final)
            except OSError as exc:
                if not final.exists():
                    raise GenerationPublicationError(
                        f"Could not publish local generation directory: {exc}"
                    ) from exc
                _require_same_generation(final, staged, generation)
                shutil.rmtree(staged)
            _fsync_directory(generations_dir)

        manifest_path = final / GENERATION_MANIFEST_PATH
        manifest_sha256 = _file_sha256(manifest_path)
        if starting_pointer.generation_id != generation:
            payload = _pointer_payload(
                generation,
                starting_pointer.generation_id,
                manifest_sha256,
            )
            _write_local_pointer_atomic(
                pointer_path,
                payload,
                expected_fingerprint=starting_pointer.fingerprint,
            )

        return GenerationPublicationResult(
            target="local",
            generation_id=generation,
            previous_generation_id=(
                starting_pointer.previous_generation_id
                if starting_pointer.generation_id == generation
                and starting_pointer.previous_generation_id is not None
                else starting_pointer.generation_id
            ),
            file_count=len(manifest["files"]),
            total_bytes=sum(item["size_bytes"] for item in manifest["files"]),
            manifest_sha256=manifest_sha256,
            pointer=str(pointer_path),
        )
    except Exception:
        if staged.exists():
            shutil.rmtree(staged)
        raise


def rollback_local_generation(
    *,
    data_root: Path = Path("data"),
) -> GenerationPublicationResult:
    """Atomically switch the local pointer to its retained previous generation."""
    root = data_root.expanduser().resolve()
    pointer_path = root / ACTIVE_GENERATION_PATH
    current = _read_local_pointer(pointer_path)
    target = current.previous_generation_id
    if target is None:
        raise GenerationPublicationError(
            "Active generation pointer has no retained previous generation"
        )
    if target == current.generation_id:
        raise GenerationPublicationError("Active and previous generation identifiers are identical")

    manifest, manifest_sha256 = _validate_local_rollback_target(root, target)
    payload = _pointer_payload(target, current.generation_id, manifest_sha256)
    _write_local_pointer_atomic(
        pointer_path,
        payload,
        expected_fingerprint=current.fingerprint,
    )
    return GenerationPublicationResult(
        target="local",
        generation_id=target,
        previous_generation_id=current.generation_id,
        file_count=len(manifest["files"]) if manifest else 0,
        total_bytes=sum(item["size_bytes"] for item in manifest["files"]) if manifest else 0,
        manifest_sha256=manifest_sha256,
        pointer=str(pointer_path),
        action="rollback",
    )


def publish_r2_generation(
    generation_id: str,
    *,
    source_dir: Path = Path("data"),
    client: Any | None = None,
    bucket_name: str | None = None,
    env: Mapping[str, str] | None = None,
    env_file: Path | None = Path(".env"),
) -> GenerationPublicationResult:
    """Validate, upload, verify, and atomically activate an immutable R2 generation."""
    generation = _validated_generation_id(generation_id)
    source = source_dir.expanduser().resolve()
    if not source.is_dir():
        raise GenerationPublicationError(f"Data source directory not found: {source}")
    s3_client, bucket = _resolve_r2_target(
        client=client,
        bucket_name=bucket_name,
        env=env,
        env_file=env_file,
    )
    starting_pointer = _read_r2_pointer(s3_client, bucket)

    with tempfile.TemporaryDirectory(prefix=f"nbatools-generation-{generation}-") as temp_dir:
        staged = Path(temp_dir) / generation
        _build_staged_generation(source, staged, generation)
        manifest = validate_staged_generation(staged, generation)
        _publish_r2_files(s3_client, bucket, staged, generation)
        manifest_sha256 = _file_sha256(staged / GENERATION_MANIFEST_PATH)

    if starting_pointer.generation_id != generation:
        payload = _pointer_payload(
            generation,
            starting_pointer.generation_id,
            manifest_sha256,
        )
        _write_r2_pointer_atomic(
            s3_client,
            bucket,
            payload,
            expected_etag=starting_pointer.etag,
        )

    return GenerationPublicationResult(
        target="r2",
        generation_id=generation,
        previous_generation_id=(
            starting_pointer.previous_generation_id
            if starting_pointer.generation_id == generation
            and starting_pointer.previous_generation_id is not None
            else starting_pointer.generation_id
        ),
        file_count=len(manifest["files"]),
        total_bytes=sum(item["size_bytes"] for item in manifest["files"]),
        manifest_sha256=manifest_sha256,
        pointer=ACTIVE_GENERATION_PATH.as_posix(),
    )


def rollback_r2_generation(
    *,
    client: Any | None = None,
    bucket_name: str | None = None,
    env: Mapping[str, str] | None = None,
    env_file: Path | None = Path(".env"),
) -> GenerationPublicationResult:
    """Conditionally switch the R2 pointer to its retained previous generation."""
    s3_client, bucket = _resolve_r2_target(
        client=client,
        bucket_name=bucket_name,
        env=env,
        env_file=env_file,
    )
    current = _read_r2_pointer(s3_client, bucket)
    target = current.previous_generation_id
    if target is None:
        raise GenerationPublicationError(
            "Active generation pointer has no retained previous generation"
        )
    if target == current.generation_id:
        raise GenerationPublicationError("Active and previous generation identifiers are identical")

    manifest, manifest_sha256 = _validate_r2_rollback_target(s3_client, bucket, target)
    payload = _pointer_payload(target, current.generation_id, manifest_sha256)
    _write_r2_pointer_atomic(
        s3_client,
        bucket,
        payload,
        expected_etag=current.etag,
    )
    return GenerationPublicationResult(
        target="r2",
        generation_id=target,
        previous_generation_id=current.generation_id,
        file_count=len(manifest["files"]) if manifest else 0,
        total_bytes=sum(item["size_bytes"] for item in manifest["files"]) if manifest else 0,
        manifest_sha256=manifest_sha256,
        pointer=ACTIVE_GENERATION_PATH.as_posix(),
        action="rollback",
    )


def validate_staged_generation(stage: Path, generation_id: str) -> dict[str, Any]:
    """Validate snapshot integrity plus every versioned dataset receipt."""
    generation = _validated_generation_id(generation_id)
    manifest_path = stage / GENERATION_MANIFEST_PATH
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise GenerationValidationError(f"Generation manifest is unreadable: {exc}") from exc
    if not isinstance(document, dict):
        raise GenerationValidationError("Generation manifest must be a JSON object")
    if document.get("schema_version") != GENERATION_MANIFEST_SCHEMA_VERSION:
        raise GenerationValidationError("Generation manifest schema_version is invalid")
    if document.get("generation_id") != generation:
        raise GenerationValidationError("Generation manifest identifier does not match staging")
    expected = document.get("files")
    if not isinstance(expected, list) or not expected:
        raise GenerationValidationError("Generation manifest must list at least one data file")

    expected_by_path: dict[str, dict[str, Any]] = {}
    for item in expected:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise GenerationValidationError("Generation manifest contains an invalid file record")
        path = _safe_relative_path(item["path"])
        key = path.as_posix()
        if key in expected_by_path:
            raise GenerationValidationError(f"Generation manifest contains duplicate path: {key}")
        expected_by_path[key] = item

    actual_files = {
        path.relative_to(stage).as_posix(): path
        for path in _iter_snapshot_files(stage, exclude_manifest=True)
    }
    if set(actual_files) != set(expected_by_path):
        missing = sorted(set(expected_by_path) - set(actual_files))
        unexpected = sorted(set(actual_files) - set(expected_by_path))
        raise GenerationValidationError(
            f"Generation file inventory mismatch; missing={missing}, unexpected={unexpected}"
        )
    for key, path in actual_files.items():
        item = expected_by_path[key]
        if item.get("size_bytes") != path.stat().st_size:
            raise GenerationValidationError(f"Generation file size mismatch: {key}")
        if item.get("sha256") != _file_sha256(path):
            raise GenerationValidationError(f"Generation file checksum mismatch: {key}")

    _validate_dataset_receipts(stage)
    return document


def _build_staged_generation(source: Path, staged: Path, generation: str) -> None:
    if staged.exists():
        raise GenerationConflictError(f"Staging path already exists: {staged}")
    staged.mkdir(parents=True)
    files = _iter_source_files(source)
    if not files:
        raise GenerationValidationError("Data source contains no publishable files")
    for source_path in files:
        relative = source_path.relative_to(source)
        destination = staged / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
    _write_generation_manifest(staged, generation)


def _iter_source_files(source: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if relative.parts and relative.parts[0] == GENERATIONS_DIR:
            continue
        if relative in {ACTIVE_GENERATION_PATH, GENERATION_MANIFEST_PATH}:
            continue
        if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
            continue
        if path.is_symlink():
            raise GenerationValidationError(f"Data source may not contain symlinks: {relative}")
        if path.is_file():
            files.append(path)
    return files


def _iter_snapshot_files(stage: Path, *, exclude_manifest: bool = False) -> list[Path]:
    files: list[Path] = []
    for path in sorted(stage.rglob("*")):
        if path.is_symlink():
            raise GenerationValidationError(
                f"Staged generation may not contain symlinks: {path.relative_to(stage)}"
            )
        if not path.is_file():
            continue
        if exclude_manifest and path.relative_to(stage) == GENERATION_MANIFEST_PATH:
            continue
        files.append(path)
    return files


def _write_generation_manifest(stage: Path, generation: str) -> Path:
    records = [
        {
            "path": path.relative_to(stage).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": _file_sha256(path),
        }
        for path in _iter_snapshot_files(stage)
    ]
    document = {
        "schema_version": GENERATION_MANIFEST_SCHEMA_VERSION,
        "generation_id": generation,
        "files": records,
    }
    path = stage / GENERATION_MANIFEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _validate_dataset_receipts(stage: Path) -> None:
    receipt_dir = stage / "metadata" / "dataset_manifests"
    receipt_paths = sorted(receipt_dir.glob("*.json")) if receipt_dir.is_dir() else []
    if not receipt_paths:
        raise GenerationValidationError("No versioned dataset validation receipts were staged")

    for receipt_path in receipt_paths:
        relative_receipt = receipt_path.relative_to(stage)
        try:
            document = json.loads(receipt_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise GenerationValidationError(
                f"Dataset validation receipt is unreadable ({relative_receipt}): {exc}"
            ) from exc
        if not isinstance(document, dict):
            raise GenerationValidationError(
                f"Dataset validation receipt must be an object: {relative_receipt}"
            )
        receipt_generation = document.get("generation_id")
        if not isinstance(receipt_generation, str) or not receipt_generation:
            raise GenerationValidationError(
                f"Dataset validation receipt lacks generation_id: {relative_receipt}"
            )
        if document.get("validation_state") != "passed" or document.get("validation_errors"):
            raise GenerationValidationError(
                f"Dataset validation receipt is not passed: {relative_receipt}"
            )
        datasets = document.get("datasets")
        if not isinstance(datasets, list) or not datasets:
            raise GenerationValidationError(
                f"Dataset validation receipt has no dataset records: {relative_receipt}"
            )
        for record in datasets:
            _validate_dataset_record(stage, relative_receipt, receipt_generation, record)


def _validate_dataset_record(
    stage: Path,
    receipt_path: Path,
    receipt_generation: str,
    record: Any,
) -> None:
    if not isinstance(record, dict):
        raise GenerationValidationError(f"Invalid dataset record in {receipt_path}")
    name = str(record.get("name") or "<unnamed>")
    if record.get("generation_id") != receipt_generation:
        raise GenerationValidationError(f"{receipt_path}: {name} generation mismatch")
    validation = record.get("validation")
    if not isinstance(validation, dict):
        raise GenerationValidationError(f"{receipt_path}: {name} validation is missing")
    state = validation.get("state")
    if state == "unavailable" and not record.get("required"):
        return
    if state != "passed" or validation.get("errors"):
        raise GenerationValidationError(f"{receipt_path}: {name} validation is not passed")
    record_path = record.get("path")
    expected_hash = record.get("file_sha256")
    if not isinstance(record_path, str) or not isinstance(expected_hash, str):
        raise GenerationValidationError(f"{receipt_path}: {name} lacks path/checksum")
    relative = _logical_data_path(record_path)
    data_path = stage / relative
    if not data_path.is_file():
        raise GenerationValidationError(f"{receipt_path}: {name} manifested file is missing")
    if _file_sha256(data_path) != expected_hash:
        raise GenerationValidationError(f"{receipt_path}: {name} checksum mismatch")


def _require_same_generation(existing: Path, staged: Path, generation: str) -> None:
    existing_manifest = validate_staged_generation(existing, generation)
    staged_manifest = validate_staged_generation(staged, generation)
    if existing_manifest.get("files") != staged_manifest.get("files"):
        raise GenerationConflictError(
            f"Immutable local generation already exists with different content: {generation}"
        )


def _validate_local_rollback_target(
    root: Path, target: str
) -> tuple[dict[str, Any] | None, str | None]:
    if target == LEGACY_GENERATION:
        _validate_dataset_receipts(root)
        return None, None
    generation = _validated_generation_id(target)
    generation_dir = root / GENERATIONS_DIR / generation
    if not generation_dir.is_dir():
        raise GenerationValidationError(f"Rollback generation is missing: {generation}")
    manifest = validate_staged_generation(generation_dir, generation)
    return manifest, _file_sha256(generation_dir / GENERATION_MANIFEST_PATH)


def _read_local_pointer(path: Path) -> _PointerState:
    if not path.exists():
        return _PointerState(LEGACY_GENERATION, None, None)
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise GenerationPublicationError(
            f"Could not read active generation pointer: {exc}"
        ) from exc
    return _parse_pointer(payload, fingerprint=hashlib.sha256(payload).hexdigest())


def _write_local_pointer_atomic(
    path: Path,
    payload: bytes,
    *,
    expected_fingerprint: str | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _local_pointer_lock(path):
        current = _read_local_pointer(path)
        if current.fingerprint != expected_fingerprint:
            raise GenerationConflictError(
                "Local active generation pointer changed during publication"
            )
        temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
            _fsync_directory(path.parent)
        finally:
            if temp.exists():
                temp.unlink()


@contextmanager
def _local_pointer_lock(path: Path) -> Iterator[None]:
    lock_path = path.with_name(f".{path.name}.lock")
    with lock_path.open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _publish_r2_files(client: Any, bucket: str, staged: Path, generation: str) -> None:
    for path in _iter_snapshot_files(staged):
        relative = path.relative_to(staged).as_posix()
        key = f"{GENERATIONS_DIR}/{generation}/{relative}"
        sha256 = _file_sha256(path)
        size = path.stat().st_size
        existing = _head_r2_object(client, bucket, key)
        if existing is not None:
            metadata = existing.get("Metadata") or {}
            if (
                metadata.get(SHA256_METADATA_KEY) == sha256
                and existing.get("ContentLength") == size
            ):
                continue
            raise GenerationConflictError(
                f"Immutable R2 generation object already exists with different content: {key}"
            )
        try:
            with path.open("rb") as handle:
                client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=handle,
                    ContentLength=size,
                    Metadata={SHA256_METADATA_KEY: sha256},
                    IfNoneMatch="*",
                )
        except Exception as exc:
            if is_precondition_failed(exc):
                raced = _head_r2_object(client, bucket, key)
                metadata = (raced or {}).get("Metadata") or {}
                if (
                    raced is not None
                    and raced.get("ContentLength") == size
                    and metadata.get(SHA256_METADATA_KEY) == sha256
                ):
                    continue
                raise GenerationConflictError(
                    f"Immutable R2 generation object won a conflicting write: {key}"
                ) from exc
            raise GenerationPublicationError(
                f"Could not upload immutable generation object {key}: {format_client_error(exc)}"
            ) from exc
        verified = _head_r2_object(client, bucket, key)
        metadata = (verified or {}).get("Metadata") or {}
        if (
            verified is None
            or verified.get("ContentLength") != size
            or metadata.get(SHA256_METADATA_KEY) != sha256
        ):
            raise GenerationValidationError(
                f"Uploaded R2 generation object failed verification: {key}"
            )


def _read_r2_pointer(client: Any, bucket: str) -> _PointerState:
    key = ACTIVE_GENERATION_PATH.as_posix()
    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except Exception as exc:
        if is_not_found(exc):
            return _PointerState(LEGACY_GENERATION, None, None, None)
        raise GenerationPublicationError(
            f"Could not read active R2 generation pointer: {format_client_error(exc)}"
        ) from exc
    etag = str(response.get("ETag") or "").strip()
    if not etag:
        raise GenerationValidationError("Active R2 generation pointer has no ETag")
    try:
        payload = response["Body"].read()
    except Exception as exc:
        raise GenerationPublicationError(f"Could not read active R2 pointer body: {exc}") from exc
    state = _parse_pointer(payload, fingerprint=hashlib.sha256(payload).hexdigest())
    return _PointerState(
        state.generation_id,
        state.previous_generation_id,
        state.fingerprint,
        etag,
    )


def _write_r2_pointer_atomic(
    client: Any,
    bucket: str,
    payload: bytes,
    *,
    expected_etag: str | None,
) -> None:
    kwargs: dict[str, Any] = {
        "Bucket": bucket,
        "Key": ACTIVE_GENERATION_PATH.as_posix(),
        "Body": payload,
        "ContentLength": len(payload),
        "ContentType": "application/json",
    }
    if expected_etag is None:
        kwargs["IfNoneMatch"] = "*"
    else:
        kwargs["IfMatch"] = expected_etag
    try:
        client.put_object(**kwargs)
    except Exception as exc:
        if is_precondition_failed(exc):
            raise GenerationConflictError(
                "R2 active generation pointer changed during publication"
            ) from exc
        raise GenerationPublicationError(
            f"Could not switch active R2 generation pointer: {format_client_error(exc)}"
        ) from exc


def _validate_r2_rollback_target(
    client: Any, bucket: str, target: str
) -> tuple[dict[str, Any] | None, str | None]:
    if target == LEGACY_GENERATION:
        raise GenerationValidationError(
            "Legacy R2 data has no immutable generation manifest; bootstrap the current "
            "last-good snapshot before publishing a new candidate"
        )
    generation = _validated_generation_id(target)
    key = f"{GENERATIONS_DIR}/{generation}/{GENERATION_MANIFEST_PATH.as_posix()}"
    try:
        response = client.get_object(Bucket=bucket, Key=key)
        payload = response["Body"].read()
        document = json.loads(payload)
    except Exception as exc:
        raise GenerationValidationError(
            f"Could not validate R2 rollback generation {generation}: {format_client_error(exc)}"
        ) from exc
    if not isinstance(document, dict) or document.get("generation_id") != generation:
        raise GenerationValidationError(f"R2 rollback generation manifest is invalid: {generation}")
    metadata = response.get("Metadata") or {}
    manifest_sha256 = metadata.get(SHA256_METADATA_KEY)
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if manifest_sha256 != actual_sha256:
        raise GenerationValidationError(
            f"R2 rollback generation manifest checksum failed: {generation}"
        )
    _validate_r2_manifest_inventory(client, bucket, generation, document)
    return document, actual_sha256


def _validate_r2_manifest_inventory(
    client: Any,
    bucket: str,
    generation: str,
    document: dict[str, Any],
) -> None:
    if document.get("schema_version") != GENERATION_MANIFEST_SCHEMA_VERSION:
        raise GenerationValidationError(f"R2 rollback generation schema is invalid: {generation}")
    files = document.get("files")
    if not isinstance(files, list) or not files:
        raise GenerationValidationError(f"R2 rollback generation inventory is empty: {generation}")
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise GenerationValidationError(
                f"R2 rollback generation has an invalid file record: {generation}"
            )
        relative = _safe_relative_path(item["path"]).as_posix()
        if relative in seen:
            raise GenerationValidationError(
                f"R2 rollback generation has a duplicate file: {relative}"
            )
        seen.add(relative)
        key = f"{GENERATIONS_DIR}/{generation}/{relative}"
        response = _head_r2_object(client, bucket, key)
        metadata = (response or {}).get("Metadata") or {}
        if response is None:
            raise GenerationObjectValidationError(generation, key, "missing")
        if response.get("ContentLength") != item.get("size_bytes") or metadata.get(
            SHA256_METADATA_KEY
        ) != item.get("sha256"):
            raise GenerationObjectValidationError(generation, key, "metadata_mismatch")


def _head_r2_object(client: Any, bucket: str, key: str) -> dict[str, Any] | None:
    try:
        return client.head_object(Bucket=bucket, Key=key)
    except Exception as exc:
        if is_not_found(exc):
            return None
        raise GenerationPublicationError(
            f"Could not inspect R2 generation object {key}: {format_client_error(exc)}"
        ) from exc


def _resolve_r2_target(
    *,
    client: Any | None,
    bucket_name: str | None,
    env: Mapping[str, str] | None,
    env_file: Path | None,
) -> tuple[Any, str]:
    if client is not None and bucket_name:
        return client, bucket_name
    if client is not None or bucket_name:
        raise GenerationPublicationError("client and bucket_name must be provided together")
    try:
        config = load_r2_config(env=env, env_file=env_file)
        return create_r2_client(config), config.bucket_name
    except R2SyncError as exc:
        raise GenerationPublicationError(str(exc)) from exc


def _pointer_payload(
    generation: str,
    previous_generation: str,
    manifest_sha256: str | None,
) -> bytes:
    document = {
        "schema_version": POINTER_SCHEMA_VERSION,
        "generation_id": generation,
        "previous_generation_id": previous_generation,
        "manifest_sha256": manifest_sha256,
        "published_at": _utc_now(),
    }
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def _parse_pointer(payload: bytes, *, fingerprint: str) -> _PointerState:
    try:
        document = json.loads(payload)
    except Exception as exc:
        raise GenerationValidationError(
            f"Active generation pointer is invalid JSON: {exc}"
        ) from exc
    if not isinstance(document, dict):
        raise GenerationValidationError("Active generation pointer must be an object")
    generation_raw = document.get("generation_id")
    if not isinstance(generation_raw, str) or not generation_raw:
        raise GenerationValidationError("Active generation pointer is missing generation_id")
    generation = _validated_generation_id(generation_raw)
    previous_raw = document.get("previous_generation_id")
    previous = None
    if previous_raw is not None:
        if not isinstance(previous_raw, str) or not previous_raw:
            raise GenerationValidationError(
                "Active generation pointer previous_generation_id is invalid"
            )
        previous = _validated_generation_id(previous_raw)
    return _PointerState(generation, previous, fingerprint)


def _logical_data_path(value: str) -> Path:
    path = Path(value)
    parts = path.parts
    if "data" in parts:
        path = Path(*parts[parts.index("data") + 1 :])
    return _safe_relative_path(path.as_posix())


def _safe_relative_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise GenerationValidationError(f"Unsafe generation-relative path: {value!r}")
    return path


def _validated_generation_id(value: str) -> str:
    try:
        return validate_data_generation_id(value)
    except DataSourceError as exc:
        raise GenerationValidationError(str(exc)) from exc


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        try:
            os.fsync(descriptor)
        except OSError:
            pass
    finally:
        os.close(descriptor)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
