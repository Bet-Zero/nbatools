"""Configurable data-source access for local and deployed runtime modes."""

from __future__ import annotations

import csv
import fnmatch
import hashlib
import json
import os
import re
import shutil
import tempfile
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from types import MappingProxyType
from typing import Any

import pandas as pd

from nbatools.development_data import MANIFEST, selected_snapshot
from nbatools.r2_errors import format_client_error, is_not_found

DATA_SOURCE_ENV = "DATA_SOURCE"
LOCAL_DATA_ROOT_ENV = "NBATOOLS_DATA_ROOT"
R2_CACHE_DIR_ENV = "NBATOOLS_R2_CACHE_DIR"
DATA_GENERATION_ENV = "NBATOOLS_DATA_GENERATION"
ACTIVE_GENERATION_PATH = Path("metadata/active_generation.json")
GENERATION_MANIFEST_PATH = Path("metadata/generation_manifest.json")
# Every distinct (player_id, player_name, season) in raw/player_game_stats, with
# ``first_seen`` numbering them in game order (seasons ascending, regular season
# before playoffs, rows in file order), derived at publication so a cold process
# can build its player name and id indexes from one small file.
PLAYER_NAMES_PATH = Path("metadata/player_names.csv")
GENERATIONS_DIR = "generations"
LEGACY_GENERATION = "legacy"
REQUIRED_R2_ENV_VARS = (
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
)

# Concurrent R2 downloads in data_prefetch; boto3's default pool holds 10.
_PREFETCH_WORKERS = 8
_GENERATION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SHA256_PATTERN = re.compile(r"[a-f0-9]{64}")


@dataclass(frozen=True)
class _Generation:
    id: str
    manifest_sha256: str | None = None


@dataclass(frozen=True)
class GenerationFile:
    size_bytes: int
    sha256: str


_REQUEST_GENERATION: ContextVar[_Generation | None] = ContextVar(
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
    generation = _current_generation()
    key = f"{_data_source_config_key()}:{generation.id}"
    return f"{key}:{generation.manifest_sha256}" if generation.manifest_sha256 else key


def verified_generation_files() -> Mapping[str, GenerationFile] | None:
    """Return the authenticated R2 inventory, when selected by a trusted digest."""
    generation = _current_generation()
    if generation.manifest_sha256 is None:
        return None
    return _get_data_source().verified_manifest(generation)


def season_file_order(path: object) -> tuple[str, int, str]:
    """Sort key putting ``YYYY-YY_<type>.csv`` files in game order.

    Seasons ascend and, within one, the regular season comes before the
    play-in and playoffs, so the last row read is the most recent.
    """
    name = Path(str(path)).name
    return (name[:7], 0 if "regular_season" in name else 1, name)


def current_data_generation() -> str:
    """Return the request-pinned generation or resolve the current active one."""
    return _current_generation().id


def _current_generation() -> _Generation:
    return _REQUEST_GENERATION.get() or _resolve_active_data_generation()


@contextmanager
def data_generation_context() -> Iterator[str]:
    """Pin one immutable data generation for the duration of a request."""
    pinned = _REQUEST_GENERATION.get()
    if pinned is not None:
        yield pinned.id
        return

    generation = _resolve_active_data_generation()
    token = _REQUEST_GENERATION.set(generation)
    try:
        source = _get_data_source()
        if (
            isinstance(source, _R2DataSource)
            and source.worker_cache is not None
            and generation.manifest_sha256 is not None
        ):
            with source.pin_cache(generation):
                yield generation.id
        else:
            yield generation.id
    finally:
        _REQUEST_GENERATION.reset(token)


def _data_source_config_key() -> str:
    """Return a cache key for source configuration, excluding generation."""
    snapshot = selected_snapshot()
    if snapshot is not None:
        return f"development:{snapshot.root}:{snapshot.manifest_sha256}"
    mode = data_source_mode()
    if mode == "local":
        root = os.environ.get(LOCAL_DATA_ROOT_ENV, os.getcwd())
        return f"local:{Path(root).resolve()}"
    config = load_r2_config()
    cache_dir = _r2_cache_root(config)
    return f"r2:{config.account_id}:{config.bucket_name}:{cache_dir}"


def reset_data_source_cache() -> None:
    """Clear the process-local data-source object cache."""
    global _DATA_SOURCE, _DATA_SOURCE_KEY
    with _DATA_SOURCE_LOCK:
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


def data_prefetch(paths: Iterable[str | Path]) -> None:
    """Fetch several files concurrently so the reads that follow are local.

    Only R2 fetches over the network; a local source has nothing to do. A file
    that can't be fetched here is skipped, and the later read reports it.
    """
    source = _get_data_source()
    if isinstance(source, _R2DataSource):
        source.prefetch(paths)


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


def _reject_provisional_path(path: Path) -> None:
    for ancestor in (path.resolve(), *path.resolve().parents):
        if (ancestor / MANIFEST.relative_to("data")).exists():
            raise DataSourceConfigError(
                "Provisional snapshot requires explicit local development selection"
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
            _reject_provisional_path(candidate)
            return candidate
        rel = _logical_relative_path(candidate)
        generation = current_data_generation()
        base = self._data_root()
        if generation != LEGACY_GENERATION:
            base = base / GENERATIONS_DIR / generation
        _reject_provisional_path(base)
        return base / rel

    def glob(self, pattern: str | Path) -> list[Path]:
        rel = _logical_relative_path(pattern)
        generation = current_data_generation()
        base = self._data_root()
        if generation != LEGACY_GENERATION:
            base = base / GENERATIONS_DIR / generation
        _reject_provisional_path(base)
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
        base = Path("data") if self.root == Path() else self.root / "data"
        if (base / MANIFEST.relative_to("data")).exists():
            raise DataSourceConfigError(
                "Provisional snapshot requires explicit local development selection"
            )
        return base


class _R2DataSource:
    def __init__(self, config: R2Config, client: Any | None = None) -> None:
        self.config = config
        self.client = client or create_r2_client(config)
        self.cache_root = _r2_cache_root(config)
        self.worker_cache = None
        on_vercel = os.environ.get("VERCEL") == "1" or os.environ.get("VERCEL_ENV") in {
            "preview",
            "production",
        }
        if on_vercel and not os.environ.get(R2_CACHE_DIR_ENV):
            self.cache_root.mkdir(parents=True, exist_ok=True)
            self.worker_cache = tempfile.TemporaryDirectory(prefix="worker-", dir=self.cache_root)
            self.cache_root = Path(self.worker_cache.name)
        self._cache_lock = RLock()
        self._cache_readers: Counter[_Generation] = Counter()
        self._latest_cache_generation: _Generation | None = None
        self._retired_cache_generations: set[_Generation] = set()
        self._downloaded_keys: set[str] = set()
        # Published generations are immutable, so what exists in one never
        # changes. Answer from its file manifest (one GET) and remember HEAD
        # results, instead of a network round trip on every check.
        self._generation_files: dict[str, frozenset[str] | None] = {}
        self._verified_manifests: dict[_Generation, Mapping[str, GenerationFile]] = {}
        self._known_keys: dict[str, bool] = {}

    @contextmanager
    def pin_cache(self, generation: _Generation) -> Iterator[None]:
        """Keep in-flight paths readable while retiring the prior worker cache."""
        with self._cache_lock:
            if self._latest_cache_generation is None:
                # An explicitly pinned preview has no active-pointer lookup.
                self._latest_cache_generation = generation
            if generation != self._latest_cache_generation:
                self._retired_cache_generations.add(generation)
            self._cache_readers[generation] += 1
            self._retire_idle_caches()
        try:
            yield
        finally:
            with self._cache_lock:
                self._cache_readers[generation] -= 1
                if not self._cache_readers[generation]:
                    del self._cache_readers[generation]
                self._retire_idle_caches()

    def _retire_idle_caches(self) -> None:
        for generation in self._retired_cache_generations - self._cache_readers.keys():
            root = self._generation_cache_root(generation)
            try:
                shutil.rmtree(root)
            except FileNotFoundError:
                pass
            except OSError:
                # Leave it eligible for another cleanup when the cache is idle.
                continue
            try:
                root.parent.rmdir()
            except OSError:
                pass
            self._retired_cache_generations.remove(generation)
            self._verified_manifests.pop(generation, None)
            prefix = str(root) + os.sep
            self._downloaded_keys.difference_update(
                {path for path in self._downloaded_keys if path.startswith(prefix)}
            )

    def exists(self, path: str | Path) -> bool:
        selection = _current_generation()
        rel_path = _logical_relative_path(path).as_posix()
        if selection.manifest_sha256 is not None:
            files = self.verified_manifest(selection)
            return rel_path == GENERATION_MANIFEST_PATH.as_posix() or rel_path in files
        generation = selection.id
        key = self._generation_key(rel_path, generation=generation)
        immutable = generation != LEGACY_GENERATION
        if immutable:
            files = self._manifest_files(generation)
            if files is not None and rel_path in files:
                return True
            if key in self._known_keys:
                return self._known_keys[key]
        try:
            self.client.head_object(Bucket=self.config.bucket_name, Key=key)
            found = True
        except Exception as exc:
            if not is_not_found(exc):
                raise DataSourceError(
                    f"Could not inspect R2 object {key}: {format_client_error(exc)}"
                )
            found = False
        if immutable:
            self._known_keys[key] = found
        return found

    def _manifest_files(self, generation: str) -> frozenset[str] | None:
        """Paths listed in a generation's manifest, or None when it has none."""
        if generation in self._generation_files:
            return self._generation_files[generation]
        key = self._generation_key(GENERATION_MANIFEST_PATH, generation=generation)
        try:
            response = self.client.get_object(Bucket=self.config.bucket_name, Key=key)
            document = json.loads(response["Body"].read().decode("utf-8"))
            files = frozenset(
                str(record["path"]) for record in document["files"] if record.get("path")
            )
        except Exception as exc:
            if not is_not_found(exc) and not isinstance(
                exc, (ValueError, KeyError, TypeError, AttributeError)
            ):
                # Transient failure: fall back to HEAD now, try the manifest again later.
                return None
            files = None
        self._generation_files[generation] = files
        return files

    def resolve_path(self, path: str | Path) -> Path:
        return self._fetch(_logical_relative_path(path), _current_generation())

    def verified_manifest(self, generation: _Generation) -> Mapping[str, GenerationFile]:
        """Load one inventory whose bytes match the pointer or preview digest."""
        manifest = self._verified_manifests.get(generation)
        if manifest is not None:
            return manifest
        raw = self._fetch(GENERATION_MANIFEST_PATH, generation).read_bytes()
        try:
            document = json.loads(raw)
            if document["schema_version"] != 1 or document["generation_id"] != generation.id:
                raise ValueError("Wrong schema or generation")
            files = document["files"]
            if not isinstance(files, list) or not files:
                raise ValueError("Missing file inventory")
            entries = {}
            for item in files:
                name, size, digest = item["path"], item["size_bytes"], item["sha256"]
                path = Path(name)
                if (
                    path.is_absolute()
                    or not path.parts
                    or ".." in path.parts
                    or path.as_posix() != name
                    or name in entries
                    or type(size) is not int
                    or size < 0
                    or not _SHA256_PATTERN.fullmatch(digest)
                ):
                    raise ValueError("Invalid file inventory record")
                entries[name] = GenerationFile(size, digest)
        except (ValueError, KeyError, TypeError) as exc:
            raise DataSourceError("Invalid authenticated generation manifest") from exc
        manifest = MappingProxyType(entries)
        self._verified_manifests[generation] = manifest
        return manifest

    def prefetch(self, paths: Iterable[str | Path]) -> None:
        # Worker threads don't inherit the request's pinned generation, so
        # resolve it here and hand it to each fetch.
        generation = _current_generation()
        pending = []
        for path in paths:
            rel_path = _logical_relative_path(path)
            cached = self._cache_path(rel_path, generation)
            if str(cached) not in self._downloaded_keys or not cached.exists():
                pending.append(rel_path)
        if len(pending) < 2:
            return

        def fetch(rel_path: Path) -> None:
            try:
                self._fetch(rel_path, generation)
            except (DataSourceError, FileNotFoundError, OSError):
                pass

        with ThreadPoolExecutor(max_workers=min(_PREFETCH_WORKERS, len(pending))) as pool:
            list(pool.map(fetch, pending))

    def _generation_cache_root(self, generation: _Generation) -> Path:
        root = self.cache_root / generation.id
        if generation.manifest_sha256 is not None:
            root = root / f".verified-{generation.manifest_sha256}"
        return root

    def _cache_path(self, path: Path, generation: _Generation) -> Path:
        return self._generation_cache_root(generation) / path

    def _fetch(self, rel_path: Path, generation: _Generation) -> Path:
        expected_hash = generation.manifest_sha256
        expected_size = None
        if expected_hash is not None and rel_path != GENERATION_MANIFEST_PATH:
            entry = self.verified_manifest(generation).get(rel_path.as_posix())
            if entry is None:
                raise FileNotFoundError(f"File is absent from the generation manifest: {rel_path}")
            expected_hash, expected_size = entry.sha256, entry.size_bytes
        key = self._generation_key(rel_path, generation=generation.id)
        cache_path = self._cache_path(rel_path, generation)
        if str(cache_path) in self._downloaded_keys and cache_path.exists():
            return cache_path

        try:
            response = self.client.get_object(Bucket=self.config.bucket_name, Key=key)
            body = response["Body"].read()
        except Exception as exc:
            if is_not_found(exc):
                if expected_hash is not None:
                    raise DataSourceError(f"Missing published R2 data object: {key}") from exc
                raise FileNotFoundError(f"Missing R2 data object: {key}") from exc
            raise DataSourceError(f"Could not read R2 object {key}: {format_client_error(exc)}")

        if expected_hash is not None and (
            (expected_size is not None and len(body) != expected_size)
            or hashlib.sha256(body).hexdigest() != expected_hash
        ):
            raise DataSourceError(f"R2 object checksum differs from its published digest: {key}")

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        # Write then rename: another process or thread sharing the cache may be
        # reading this path, and must never see a truncated file.
        fd, temp_name = tempfile.mkstemp(dir=cache_path.parent, prefix=f".{cache_path.name}.")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(body)
            os.replace(temp_name, cache_path)
        except BaseException:
            Path(temp_name).unlink(missing_ok=True)
            raise
        with self._cache_lock:
            self._downloaded_keys.add(str(cache_path))
        return cache_path

    def glob(self, pattern: str | Path) -> list[Path]:
        rel_pattern = _logical_relative_path(pattern).as_posix()
        selection = _current_generation()
        if selection.manifest_sha256 is not None:
            paths = self.verified_manifest(selection).keys() | {GENERATION_MANIFEST_PATH.as_posix()}
            return [
                Path("data") / path for path in sorted(paths) if fnmatch.fnmatch(path, rel_pattern)
            ]
        generation = selection.id
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
                    f"Could not list R2 objects for {rel_pattern}: {format_client_error(exc)}"
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
        return self.active_generation_selection().id

    def active_generation_selection(self) -> _Generation:
        key = ACTIVE_GENERATION_PATH.as_posix()
        try:
            response = self.client.get_object(Bucket=self.config.bucket_name, Key=key)
            payload = response["Body"].read().decode("utf-8")
        except Exception as exc:
            if is_not_found(exc):
                return _Generation(LEGACY_GENERATION)
            raise DataSourceError(
                f"Could not read active generation pointer {key}: {format_client_error(exc)}"
            ) from exc
        generation = _parse_generation_pointer(payload)
        digest = json.loads(payload).get("manifest_sha256")
        if digest is not None and (
            generation == LEGACY_GENERATION
            or not isinstance(digest, str)
            or not _SHA256_PATTERN.fullmatch(digest)
        ):
            raise DataSourceError("Invalid manifest checksum in active generation pointer")
        selection = _Generation(generation, digest)
        if self.worker_cache is not None and digest is not None:
            # Record the pointer observation before its request can wait to pin.
            # A delayed reader may use older bytes, but cannot displace this copy.
            with self._cache_lock:
                previous = self._latest_cache_generation
                if previous is not None and previous != selection:
                    self._retired_cache_generations.add(previous)
                self._latest_cache_generation = selection
                self._retired_cache_generations.discard(selection)
        return selection

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
_DATA_SOURCE_LOCK = RLock()


def _get_data_source() -> _LocalDataSource | _R2DataSource:
    global _DATA_SOURCE, _DATA_SOURCE_KEY

    snapshot = selected_snapshot()
    if snapshot is not None:
        return snapshot
    key = _data_source_config_key()
    if _DATA_SOURCE is not None and _DATA_SOURCE_KEY == key:
        return _DATA_SOURCE

    with _DATA_SOURCE_LOCK:
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


def _resolve_active_data_generation() -> _Generation:
    snapshot = selected_snapshot()
    if snapshot is not None:
        return _Generation("development-" + snapshot.manifest_sha256)
    configured = os.environ.get(DATA_GENERATION_ENV, "").strip()
    from nbatools.candidate_preview import MANIFEST_ENV, verify_pin

    if MANIFEST_ENV in os.environ:
        digest = verify_pin(_get_data_source(), configured)
        return _Generation(configured, digest)
    if configured:
        return _Generation(validate_data_generation_id(configured))
    source = _get_data_source()
    if isinstance(source, _R2DataSource):
        return source.active_generation_selection()
    return _Generation(source.active_generation())


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
    return validate_data_generation_id(generation.strip())


def validate_data_generation_id(generation: str) -> str:
    """Validate one runtime generation identifier and return it unchanged."""
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
