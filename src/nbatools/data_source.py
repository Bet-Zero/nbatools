"""Configurable data-source access for local and deployed runtime modes."""

from __future__ import annotations

import csv
import fnmatch
import json
import os
import re
import tempfile
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

DATA_SOURCE_ENV = "DATA_SOURCE"
LOCAL_DATA_ROOT_ENV = "NBATOOLS_DATA_ROOT"
R2_CACHE_DIR_ENV = "NBATOOLS_R2_CACHE_DIR"
DATA_GENERATION_ENV = "NBATOOLS_DATA_GENERATION"
ACTIVE_GENERATION_PATH = Path("metadata/active_generation.json")
GENERATIONS_DIR = "generations"
LEGACY_GENERATION = "legacy"
REQUIRED_R2_ENV_VARS = (
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
)

_GENERATION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_REQUEST_GENERATION: ContextVar[str | None] = ContextVar(
    "nbatools_request_data_generation", default=None
)


class DataSourceError(Exception):
    """Raised when configured data-source access fails."""


class DataSourceConfigError(DataSourceError):
    """Raised when data-source configuration is incomplete or invalid."""


@dataclass(frozen=True)
class R2Config:
    """Cloudflare R2 connection configuration."""

    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str

    @property
    def endpoint_url(self) -> str:
        return f"https://{self.account_id}.r2.cloudflarestorage.com"


def data_source_mode(env: Mapping[str, str] | None = None) -> str:
    """Return configured data-source mode, defaulting to local."""
    values = os.environ if env is None else env
    mode = values.get(DATA_SOURCE_ENV, "local").strip().lower()
    if mode not in {"local", "r2"}:
        raise DataSourceConfigError("DATA_SOURCE must be either 'local' or 'r2'")
    return mode


def data_source_cache_key() -> str:
    """Return a cache key for the source and the request-pinned generation."""
    return f"{_data_source_config_key()}:{current_data_generation()}"


def current_data_generation() -> str:
    """Return the request-pinned generation or resolve the current active one."""
    pinned = _REQUEST_GENERATION.get()
    if pinned is not None:
        return pinned
    return _resolve_active_data_generation()


@contextmanager
def data_generation_context() -> Iterator[str]:
    """Pin one immutable data generation for the duration of a request."""
    pinned = _REQUEST_GENERATION.get()
    if pinned is not None:
        yield pinned
        return

    generation = _resolve_active_data_generation()
    token = _REQUEST_GENERATION.set(generation)
    try:
        yield generation
    finally:
        _REQUEST_GENERATION.reset(token)


def _data_source_config_key() -> str:
    """Return a cache key for source configuration, excluding generation."""
    mode = data_source_mode()
    if mode == "local":
        root = os.environ.get(LOCAL_DATA_ROOT_ENV, os.getcwd())
        return f"local:{Path(root).resolve()}"
    config = load_r2_config()
    cache_dir = _r2_cache_root(config)
    return f"r2:{config.bucket_name}:{cache_dir}"


def reset_data_source_cache() -> None:
    """Clear the process-local data-source object cache."""
    global _DATA_SOURCE, _DATA_SOURCE_KEY
    _DATA_SOURCE = None
    _DATA_SOURCE_KEY = None


def data_exists(path: str | Path) -> bool:
    """Return whether a logical data path exists in the configured source."""
    return _get_data_source().exists(path)


def data_path(path: str | Path) -> Path:
    """Resolve a logical data path to a local filesystem path."""
    return _get_data_source().resolve_path(path)


def data_glob(pattern: str | Path) -> list[Path]:
    """Return logical data paths matching ``pattern``."""
    return _get_data_source().glob(pattern)


def data_read_csv(path: str | Path, *args: Any, **kwargs: Any) -> pd.DataFrame:
    """Read a CSV from the configured data source."""
    return pd.read_csv(data_path(path), *args, **kwargs)


def data_read_text(path: str | Path) -> str:
    """Read UTF-8 text from the configured data source."""
    return data_path(path).read_text()


def data_read_csv_dicts(path: str | Path) -> list[dict[str, str]]:
    """Read a CSV as dict rows, returning an empty list when missing."""
    if not data_exists(path):
        return []
    with data_path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_r2_config(
    *,
    env: Mapping[str, str] | None = None,
    env_file: Path | None = Path(".env"),
) -> R2Config:
    """Load R2 config from environment variables, falling back to local .env."""
    values = dict(os.environ if env is None else env)
    for candidate in _env_file_candidates(env_file):
        if candidate.exists():
            for key, value in _read_env_file(candidate).items():
                values.setdefault(key, value)

    missing = [key for key in REQUIRED_R2_ENV_VARS if not values.get(key)]
    if missing:
        raise DataSourceConfigError("Missing R2 environment variables: " + ", ".join(missing))

    return R2Config(
        account_id=values["R2_ACCOUNT_ID"],
        access_key_id=values["R2_ACCESS_KEY_ID"],
        secret_access_key=values["R2_SECRET_ACCESS_KEY"],
        bucket_name=values["R2_BUCKET_NAME"],
    )


def create_r2_client(config: R2Config) -> Any:
    """Create a boto3 S3 client configured for Cloudflare R2."""
    try:
        import boto3
    except ImportError as exc:
        raise DataSourceConfigError(
            "boto3 is required for DATA_SOURCE=r2. Install project dependencies."
        ) from exc

    return boto3.client(
        "s3",
        endpoint_url=config.endpoint_url,
        aws_access_key_id=config.access_key_id,
        aws_secret_access_key=config.secret_access_key,
        region_name="auto",
    )


class _LocalDataSource:
    def __init__(self) -> None:
        root = os.environ.get(LOCAL_DATA_ROOT_ENV)
        self.root = Path(root) if root else Path()

    def exists(self, path: str | Path) -> bool:
        return self.resolve_path(path).exists()

    def resolve_path(self, path: str | Path) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        rel = _logical_relative_path(candidate)
        generation = current_data_generation()
        base = self._data_root()
        if generation != LEGACY_GENERATION:
            base = base / GENERATIONS_DIR / generation
        return base / rel

    def glob(self, pattern: str | Path) -> list[Path]:
        rel = _logical_relative_path(pattern)
        generation = current_data_generation()
        base = self._data_root()
        if generation != LEGACY_GENERATION:
            base = base / GENERATIONS_DIR / generation
        return [Path("data") / path.relative_to(base) for path in sorted(base.glob(rel.as_posix()))]

    def active_generation(self) -> str:
        pointer_path = self._data_root() / ACTIVE_GENERATION_PATH
        if not pointer_path.exists():
            return LEGACY_GENERATION
        try:
            return _parse_generation_pointer(pointer_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise DataSourceError(f"Could not read active generation pointer: {exc}") from exc

    def _data_root(self) -> Path:
        return Path("data") if self.root == Path() else self.root / "data"


class _R2DataSource:
    def __init__(self, config: R2Config, client: Any | None = None) -> None:
        self.config = config
        self.client = client or create_r2_client(config)
        self.cache_root = _r2_cache_root(config)
        self._downloaded_keys: set[str] = set()

    def exists(self, path: str | Path) -> bool:
        key = self._generation_key(path)
        try:
            self.client.head_object(Bucket=self.config.bucket_name, Key=key)
            return True
        except Exception as exc:
            if _is_not_found(exc):
                return False
            raise DataSourceError(f"Could not inspect R2 object {key}: {_format_client_error(exc)}")

    def resolve_path(self, path: str | Path) -> Path:
        rel_path = _logical_relative_path(path)
        generation = current_data_generation()
        key = self._generation_key(rel_path, generation=generation)
        cache_path = self.cache_root / generation / rel_path
        if key in self._downloaded_keys and cache_path.exists():
            return cache_path

        try:
            response = self.client.get_object(Bucket=self.config.bucket_name, Key=key)
            body = response["Body"].read()
        except Exception as exc:
            if _is_not_found(exc):
                raise FileNotFoundError(f"Missing R2 data object: {key}") from exc
            raise DataSourceError(f"Could not read R2 object {key}: {_format_client_error(exc)}")

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(body)
        self._downloaded_keys.add(key)
        return cache_path

    def glob(self, pattern: str | Path) -> list[Path]:
        rel_pattern = _logical_relative_path(pattern).as_posix()
        generation = current_data_generation()
        generation_prefix = self._generation_prefix(generation)
        object_pattern = f"{generation_prefix}{rel_pattern}"
        prefix = _glob_prefix(object_pattern)
        keys: list[str] = []
        continuation_token: str | None = None

        while True:
            kwargs: dict[str, Any] = {"Bucket": self.config.bucket_name, "Prefix": prefix}
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token
            try:
                response = self.client.list_objects_v2(**kwargs)
            except Exception as exc:
                raise DataSourceError(
                    f"Could not list R2 objects for {rel_pattern}: {_format_client_error(exc)}"
                )

            for item in response.get("Contents", []):
                key = item.get("Key", "")
                if key and fnmatch.fnmatch(key, object_pattern):
                    keys.append(key)

            if not response.get("IsTruncated"):
                break
            continuation_token = response.get("NextContinuationToken")
            if not continuation_token:
                break

        return [Path("data") / key.removeprefix(generation_prefix) for key in sorted(keys)]

    def active_generation(self) -> str:
        key = ACTIVE_GENERATION_PATH.as_posix()
        try:
            response = self.client.get_object(Bucket=self.config.bucket_name, Key=key)
            payload = response["Body"].read().decode("utf-8")
        except Exception as exc:
            if _is_not_found(exc):
                return LEGACY_GENERATION
            raise DataSourceError(
                f"Could not read active generation pointer {key}: {_format_client_error(exc)}"
            ) from exc
        return _parse_generation_pointer(payload)

    @staticmethod
    def _generation_prefix(generation: str) -> str:
        if generation == LEGACY_GENERATION:
            return ""
        return f"{GENERATIONS_DIR}/{generation}/"

    def _generation_key(self, path: str | Path, *, generation: str | None = None) -> str:
        resolved_generation = generation or current_data_generation()
        rel_path = _logical_relative_path(path).as_posix()
        return f"{self._generation_prefix(resolved_generation)}{rel_path}"


_DATA_SOURCE: _LocalDataSource | _R2DataSource | None = None
_DATA_SOURCE_KEY: str | None = None


def _get_data_source() -> _LocalDataSource | _R2DataSource:
    global _DATA_SOURCE, _DATA_SOURCE_KEY

    key = _data_source_config_key()
    if _DATA_SOURCE is not None and _DATA_SOURCE_KEY == key:
        return _DATA_SOURCE

    mode = data_source_mode()
    if mode == "local":
        source: _LocalDataSource | _R2DataSource = _LocalDataSource()
    else:
        source = _R2DataSource(load_r2_config())

    _DATA_SOURCE = source
    _DATA_SOURCE_KEY = key
    return source


def _resolve_active_data_generation() -> str:
    configured = os.environ.get(DATA_GENERATION_ENV, "").strip()
    if configured:
        return _validate_generation(configured)
    return _get_data_source().active_generation()


def _parse_generation_pointer(payload: str) -> str:
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise DataSourceError(f"Active generation pointer is not valid JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise DataSourceError("Active generation pointer must be a JSON object")
    generation = document.get("generation_id")
    if not isinstance(generation, str) or not generation.strip():
        raise DataSourceError("Active generation pointer is missing generation_id")
    return _validate_generation(generation.strip())


def _validate_generation(generation: str) -> str:
    if not _GENERATION_PATTERN.fullmatch(generation):
        raise DataSourceError(f"Invalid data generation identifier: {generation!r}")
    return generation


def _logical_relative_path(path: str | Path) -> Path:
    candidate = Path(path)
    parts = candidate.parts
    if "data" in parts:
        data_index = parts.index("data")
        return Path(*parts[data_index + 1 :])
    return candidate


def _glob_prefix(pattern: str) -> str:
    wildcard_positions = [pos for token in ("*", "?", "[") if (pos := pattern.find(token)) >= 0]
    if not wildcard_positions:
        return pattern
    prefix = pattern[: min(wildcard_positions)]
    return prefix.rsplit("/", 1)[0] + "/" if "/" in prefix else ""


def _r2_cache_root(config: R2Config) -> Path:
    configured = os.environ.get(R2_CACHE_DIR_ENV)
    root = Path(configured) if configured else Path(tempfile.gettempdir()) / "nbatools-r2-cache"
    return root / config.bucket_name


def _env_file_candidates(env_file: Path | None) -> Iterable[Path]:
    if env_file is not None:
        yield env_file
    repo_env = Path(__file__).resolve().parents[2] / ".env"
    if env_file is None or repo_env != env_file:
        yield repo_env


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


def _is_not_found(exc: Exception) -> bool:
    code, status = _client_error_code_and_status(exc)
    return status == 404 or code in {"404", "NoSuchKey", "NotFound", "NoSuchBucket"}


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
