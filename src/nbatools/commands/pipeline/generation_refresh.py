"""Scheduled-refresh helpers around immutable R2 generations.

A refresh runner starts with no data. It downloads the active generation into
a plain local data directory, refreshes the current season there, publishes a
new generation only when a data file actually changed, and prunes superseded
generations so nightly copies stay inside the storage allowance.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nbatools.commands.pipeline.generation_publication import (
    GENERATION_MANIFEST_PATH,
    GenerationConflictError,
    GenerationPublicationError,
    GenerationValidationError,
    _file_sha256,
    _head_r2_object,
    _read_r2_pointer,
    _resolve_r2_target,
    _safe_relative_path,
)
from nbatools.data_source import GENERATIONS_DIR, LEGACY_GENERATION, PLAYER_NAMES_PATH
from nbatools.r2_errors import format_client_error

# Files publication derives itself; downloading them would only be overwritten.
_DERIVED_PATHS = {GENERATION_MANIFEST_PATH.as_posix(), PLAYER_NAMES_PATH.as_posix()}
# Only these layers hold game data. Metadata (manifests, refresh logs, load
# timestamps) changes on every run, so it does not count as new data.
_DATA_LAYERS = ("raw/", "processed/")


@dataclass(frozen=True)
class DownloadedGeneration:
    generation_id: str
    manifest: dict[str, Any]
    file_count: int
    total_bytes: int


@dataclass
class PruneResult:
    kept: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    deleted_objects: int = 0
    dry_run: bool = False


def download_active_generation(
    dest: Path,
    *,
    client: Any | None = None,
    bucket_name: str | None = None,
    env: Mapping[str, str] | None = None,
    env_file: Path | None = Path(".env"),
) -> DownloadedGeneration:
    """Download every file of the active R2 generation into an empty ``dest``.

    Each file is checked against the manifest's size and SHA-256, so a refresh
    never builds on a partial or corrupted copy.
    """
    if dest.exists() and any(dest.iterdir()):
        raise GenerationPublicationError(f"Download target is not empty: {dest}")
    s3_client, bucket = _resolve_r2_target(
        client=client, bucket_name=bucket_name, env=env, env_file=env_file
    )
    generation = _read_r2_pointer(s3_client, bucket).generation_id
    if generation == LEGACY_GENERATION:
        raise GenerationPublicationError("No active immutable generation to download")
    prefix = f"{GENERATIONS_DIR}/{generation}"
    manifest = json.loads(_get_bytes(s3_client, bucket, f"{prefix}/{GENERATION_MANIFEST_PATH}"))
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise GenerationValidationError(f"Generation manifest lists no files: {generation}")

    dest.mkdir(parents=True, exist_ok=True)
    total = 0
    count = 0
    for item in files:
        relative = _safe_relative_path(str(item.get("path", ""))).as_posix()
        if relative in _DERIVED_PATHS:
            continue
        payload = _get_bytes(s3_client, bucket, f"{prefix}/{relative}")
        if len(payload) != item.get("size_bytes") or hashlib.sha256(
            payload
        ).hexdigest() != item.get("sha256"):
            raise GenerationValidationError(
                f"Downloaded file does not match the generation manifest: {relative}"
            )
        _write_atomic(dest / relative, payload)
        total += len(payload)
        count += 1
    return DownloadedGeneration(generation, manifest, count, total)


def changed_data_files(source: Path, manifest: Mapping[str, Any]) -> list[str]:
    """Return raw/processed data files that differ from ``manifest``.

    Covers changed, added and removed files. An empty list means a refresh
    found no new games and there is nothing worth publishing.
    """
    published = {
        str(item["path"]): str(item["sha256"])
        for item in manifest.get("files") or []
        if str(item.get("path", "")).startswith(_DATA_LAYERS)
    }
    local: dict[str, Path] = {}
    for layer in _DATA_LAYERS:
        root = source / layer
        if root.is_dir():
            for path in root.rglob("*"):
                relative = path.relative_to(source)
                if path.is_file() and not any(
                    part.startswith(".") or part == "__pycache__" for part in relative.parts
                ):
                    local[relative.as_posix()] = path
    changed = [
        relative
        for relative, path in local.items()
        if published.get(relative) != _file_sha256(path)
    ]
    changed.extend(relative for relative in published if relative not in local)
    return sorted(changed)


def prune_r2_generations(
    *,
    keep: int,
    dry_run: bool = False,
    client: Any | None = None,
    bucket_name: str | None = None,
    env: Mapping[str, str] | None = None,
    env_file: Path | None = Path(".env"),
) -> PruneResult:
    """Delete superseded generations, keeping the newest ``keep`` of them.

    Age comes from each generation's manifest, which publication uploads among
    its first objects, so an upload in progress is the newest and is kept.
    The active and retained-previous generations are always kept, and the
    pointer is re-read before every deletion: if it moved, pruning stops.
    A prefix with no manifest (left by an interrupted deletion, or not a
    generation) is reported and left alone.
    """
    if keep < 2:
        raise GenerationPublicationError("Keep at least 2 generations (active and previous)")
    s3_client, bucket = _resolve_r2_target(
        client=client, bucket_name=bucket_name, env=env, env_file=env_file
    )
    pointer = _read_r2_pointer(s3_client, bucket)
    if pointer.generation_id == LEGACY_GENERATION:
        raise GenerationPublicationError("No active generation pointer; refusing to prune")
    protected = {pointer.generation_id, pointer.previous_generation_id}

    published: list[tuple[Any, str]] = []
    result = PruneResult(dry_run=dry_run)
    for generation in _list_generation_ids(s3_client, bucket):
        head = _head_r2_object(
            s3_client, bucket, f"{GENERATIONS_DIR}/{generation}/{GENERATION_MANIFEST_PATH}"
        )
        if head is None or head.get("LastModified") is None:
            result.ignored.append(generation)
            continue
        published.append((head["LastModified"], generation))

    published.sort(reverse=True)
    newest = {generation for _, generation in published[:keep]}
    for _, generation in published:
        if generation in protected or generation in newest:
            result.kept.append(generation)
            continue
        result.deleted.append(generation)
        if dry_run:
            continue
        if _read_r2_pointer(s3_client, bucket).etag != pointer.etag:
            raise GenerationConflictError(
                "Active generation pointer changed during pruning; stopped before "
                f"deleting {generation}"
            )
        result.deleted_objects += _delete_generation(s3_client, bucket, generation)
    return result


def _list_generation_ids(client: Any, bucket: str) -> list[str]:
    generations: list[str] = []
    token: str | None = None
    while True:
        kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Prefix": f"{GENERATIONS_DIR}/",
            "Delimiter": "/",
        }
        if token:
            kwargs["ContinuationToken"] = token
        try:
            response = client.list_objects_v2(**kwargs)
        except Exception as exc:
            raise GenerationPublicationError(
                f"Could not list R2 generations: {format_client_error(exc)}"
            ) from exc
        for entry in response.get("CommonPrefixes") or []:
            name = str(entry.get("Prefix", "")).removeprefix(f"{GENERATIONS_DIR}/").strip("/")
            if name:
                generations.append(name)
        if not response.get("IsTruncated"):
            return generations
        token = response.get("NextContinuationToken")


def _delete_generation(client: Any, bucket: str, generation: str) -> int:
    """Delete one generation's objects, its manifest last.

    The manifest is what marks a prefix as a generation, so an interrupted
    deletion leaves a reported, manifest-less prefix rather than a
    half-deleted generation that still looks complete.
    """
    prefix = f"{GENERATIONS_DIR}/{generation}/"
    manifest_key = f"{prefix}{GENERATION_MANIFEST_PATH}"
    deleted = 0
    # Re-list from the start each round: deleting while paging with a
    # continuation token can skip keys.
    while True:
        try:
            response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        except Exception as exc:
            raise GenerationPublicationError(
                f"Could not list R2 generation {prefix}: {format_client_error(exc)}"
            ) from exc
        keys = [
            str(item["Key"])
            for item in response.get("Contents") or []
            if item["Key"] != manifest_key
        ]
        if not keys:
            break
        deleted += _delete_keys(client, bucket, keys)
    if _head_r2_object(client, bucket, manifest_key) is not None:
        deleted += _delete_keys(client, bucket, [manifest_key])
    return deleted


def _delete_keys(client: Any, bucket: str, keys: list[str]) -> int:
    try:
        outcome = client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": key} for key in keys], "Quiet": True},
        )
    except Exception as exc:
        raise GenerationPublicationError(
            f"Could not delete R2 objects: {format_client_error(exc)}"
        ) from exc
    if outcome.get("Errors"):
        raise GenerationPublicationError(
            f"R2 refused to delete {len(outcome['Errors'])} object(s), e.g. {keys[0]}"
        )
    return len(keys)


def _get_bytes(client: Any, bucket: str, key: str) -> bytes:
    try:
        return client.get_object(Bucket=bucket, Key=key)["Body"].read()
    except Exception as exc:
        raise GenerationPublicationError(
            f"Could not download R2 object {key}: {format_client_error(exc)}"
        ) from exc


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise
