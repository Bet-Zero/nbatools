"""Sync the local data warehouse to Cloudflare R2.

The command implementation lives here so CLI wrappers can stay thin.  R2 is
S3-compatible, so the runtime client is a boto3 S3 client configured with the
Cloudflare endpoint.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REQUIRED_ENV_VARS = (
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
)
MD5_METADATA_KEY = "nbatools-md5"


class R2SyncError(Exception):
    """Base exception for user-actionable R2 sync failures."""


class R2CredentialError(R2SyncError):
    """Raised when required R2 credentials are missing."""


@dataclass(frozen=True)
class R2SyncConfig:
    """Runtime configuration for R2 sync."""

    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str

    @property
    def endpoint_url(self) -> str:
        return f"https://{self.account_id}.r2.cloudflarestorage.com"


@dataclass(frozen=True)
class SyncProgress:
    """Progress event emitted after a file is inspected or uploaded."""

    processed_files: int
    total_files: int
    key: str
    action: str
    size_bytes: int


@dataclass(frozen=True)
class SyncFailure:
    """Per-file sync failure."""

    key: str
    path: Path
    error: str


@dataclass
class R2SyncResult:
    """Summary of one R2 sync run."""

    bucket_name: str
    data_dir: Path
    dry_run: bool
    total_files: int = 0
    synced_files: int = 0
    skipped_files: int = 0
    bytes_uploaded: int = 0
    failures: list[SyncFailure] = field(default_factory=list)

    @property
    def failed_files(self) -> int:
        return len(self.failures)

    @property
    def success(self) -> bool:
        return not self.failures

    @property
    def summary_lines(self) -> list[str]:
        mode = "dry run" if self.dry_run else "sync"
        synced_label = "Files that would sync" if self.dry_run else "Files synced"
        bytes_label = "Bytes that would upload" if self.dry_run else "Bytes uploaded"
        lines = [
            f"R2 sync mode: {mode}",
            f"Data directory: {self.data_dir}",
            f"Bucket: {self.bucket_name}",
            f"Files scanned: {self.total_files}",
            f"{synced_label}: {self.synced_files}",
            f"Files skipped: {self.skipped_files}",
            f"Files failed: {self.failed_files}",
            f"{bytes_label}: {self.bytes_uploaded}",
        ]
        if self.failures:
            lines.append("Failures:")
            for failure in self.failures:
                lines.append(f"  {failure.key}: {failure.error}")
        return lines


def load_r2_config(
    *,
    env: Mapping[str, str] | None = None,
    env_file: Path | None = Path(".env"),
) -> R2SyncConfig:
    """Load R2 config from environment variables, falling back to local .env."""
    values = dict(os.environ if env is None else env)

    if env_file is not None and env_file.exists():
        for key, value in _read_env_file(env_file).items():
            values.setdefault(key, value)

    missing = [key for key in REQUIRED_ENV_VARS if not values.get(key)]
    if missing:
        raise R2CredentialError("Missing R2 environment variables: " + ", ".join(missing))

    return R2SyncConfig(
        account_id=values["R2_ACCOUNT_ID"],
        access_key_id=values["R2_ACCESS_KEY_ID"],
        secret_access_key=values["R2_SECRET_ACCESS_KEY"],
        bucket_name=values["R2_BUCKET_NAME"],
    )


def run_sync_r2(
    *,
    data_dir: Path = Path("data"),
    dry_run: bool = False,
    prefix: str = "",
    client: Any | None = None,
    env: Mapping[str, str] | None = None,
    env_file: Path | None = Path(".env"),
    progress: Callable[[SyncProgress], None] | None = None,
) -> R2SyncResult:
    """Sync ``data_dir`` to the configured R2 bucket."""
    data_dir = data_dir.expanduser()
    if not data_dir.is_dir():
        raise R2SyncError(f"Data directory not found: {data_dir}")

    config = load_r2_config(env=env, env_file=env_file)
    s3_client = client or create_r2_client(config)
    files = _iter_sync_files(data_dir)
    result = R2SyncResult(
        bucket_name=config.bucket_name,
        data_dir=data_dir,
        dry_run=dry_run,
        total_files=len(files),
    )

    for index, path in enumerate(files, start=1):
        rel_path = path.relative_to(data_dir)
        key = _object_key(rel_path, prefix)
        size_bytes = path.stat().st_size
        local_md5 = _file_md5(path)

        try:
            if _remote_matches(s3_client, config.bucket_name, key, local_md5):
                result.skipped_files += 1
                _emit_progress(
                    progress,
                    index,
                    result.total_files,
                    key,
                    "skip",
                    size_bytes,
                )
                continue
        except R2SyncError as exc:
            result.failures.append(SyncFailure(key=key, path=path, error=str(exc)))
            _emit_progress(progress, index, result.total_files, key, "failed", size_bytes)
            continue

        result.synced_files += 1
        result.bytes_uploaded += size_bytes

        if dry_run:
            _emit_progress(
                progress,
                index,
                result.total_files,
                key,
                "would-upload",
                size_bytes,
            )
            continue

        try:
            _upload_file(s3_client, config.bucket_name, key, path, local_md5, size_bytes)
            _emit_progress(progress, index, result.total_files, key, "upload", size_bytes)
        except R2SyncError as exc:
            result.failures.append(SyncFailure(key=key, path=path, error=str(exc)))
            _emit_progress(progress, index, result.total_files, key, "failed", size_bytes)

    return result


def create_r2_client(config: R2SyncConfig) -> Any:
    """Create a boto3 S3 client configured for Cloudflare R2."""
    try:
        import boto3
    except ImportError as exc:
        message = "boto3 is required for R2 sync. Install project dependencies."
        raise R2SyncError(message) from exc

    return boto3.client(
        "s3",
        endpoint_url=config.endpoint_url,
        aws_access_key_id=config.access_key_id,
        aws_secret_access_key=config.secret_access_key,
        region_name="auto",
    )


def _read_env_file(path: Path) -> dict[str, str]:
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


def _iter_sync_files(data_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in data_dir.rglob("*")
        if path.is_file() and not _has_ignored_part(path.relative_to(data_dir))
    )


def _has_ignored_part(path: Path) -> bool:
    return any(part.startswith(".") or part == "__pycache__" for part in path.parts)


def _object_key(relative_path: Path, prefix: str) -> str:
    key = relative_path.as_posix()
    clean_prefix = prefix.strip("/")
    if clean_prefix:
        return f"{clean_prefix}/{key}"
    return key


def _file_md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _remote_matches(client: Any, bucket_name: str, key: str, local_md5: str) -> bool:
    try:
        response = client.head_object(Bucket=bucket_name, Key=key)
    except Exception as exc:
        if _is_not_found(exc):
            return False
        if _is_auth_error(exc):
            message = "R2 authentication failed. Check credentials and bucket scope."
            raise R2SyncError(message) from exc
        raise R2SyncError(f"Could not inspect remote object: {_format_client_error(exc)}") from exc

    metadata = response.get("Metadata") or {}
    remote_md5 = metadata.get(MD5_METADATA_KEY)
    if remote_md5:
        return remote_md5.lower() == local_md5

    etag = str(response.get("ETag", "")).strip('"').lower()
    return etag == local_md5


def _upload_file(
    client: Any,
    bucket_name: str,
    key: str,
    path: Path,
    local_md5: str,
    size_bytes: int,
) -> None:
    try:
        with path.open("rb") as handle:
            client.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=handle,
                ContentLength=size_bytes,
                Metadata={MD5_METADATA_KEY: local_md5},
            )
    except Exception as exc:
        if _is_auth_error(exc):
            message = "R2 authentication failed. Check credentials and bucket scope."
            raise R2SyncError(message) from exc
        raise R2SyncError(f"Could not upload object: {_format_client_error(exc)}") from exc


def _is_not_found(exc: Exception) -> bool:
    code, status = _client_error_code_and_status(exc)
    return status == 404 or code in {"404", "NoSuchKey", "NotFound", "NoSuchBucket"}


def _is_auth_error(exc: Exception) -> bool:
    code, status = _client_error_code_and_status(exc)
    return status in {401, 403} or code in {"401", "403", "AccessDenied", "InvalidAccessKeyId"}


def _client_error_code_and_status(exc: Exception) -> tuple[str | None, int | None]:
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return None, None

    error = response.get("Error") or {}
    metadata = response.get("ResponseMetadata") or {}
    code = str(error.get("Code")) if error.get("Code") is not None else None
    status = metadata.get("HTTPStatusCode")
    return code, int(status) if status is not None else None


def _format_client_error(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        error = response.get("Error") or {}
        code = error.get("Code")
        message = error.get("Message")
        if code and message:
            return f"{code}: {message}"
        if code:
            return str(code)
    return f"{type(exc).__name__}: {exc}"


def _emit_progress(
    progress: Callable[[SyncProgress], None] | None,
    processed_files: int,
    total_files: int,
    key: str,
    action: str,
    size_bytes: int,
) -> None:
    if progress is None:
        return
    progress(
        SyncProgress(
            processed_files=processed_files,
            total_files=total_files,
            key=key,
            action=action,
            size_bytes=size_bytes,
        )
    )
