"""Logical file inventory and physical object locations for immutable releases."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

GENERATIONS_DIR = "generations"
LEGACY_GENERATION = "legacy"
MANIFEST_PATH = "metadata/generation_manifest.json"
STANDALONE_SCHEMA = 1
REUSE_SCHEMA = 2
_GENERATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_SHA256 = re.compile(r"[a-f0-9]{64}")


@dataclass(frozen=True)
class GenerationFile:
    size_bytes: int
    sha256: str
    storage_generation: str | None = None

    def object_key(self, generation: str, relative: str) -> str:
        """Resolve directly to an immutable generation's own copy of this path."""
        return f"{GENERATIONS_DIR}/{self.storage_generation or generation}/{relative}"


def parse_generation_files(
    document: Mapping[str, Any], generation: str
) -> dict[str, GenerationFile]:
    """Reject invalid inventories and arbitrary cross-prefix references."""
    if not isinstance(document, Mapping):
        raise ValueError("Expected a generation manifest object")
    schema = document.get("schema_version")
    if (
        type(schema) is not int
        or schema not in {STANDALONE_SCHEMA, REUSE_SCHEMA}
        or document.get("generation_id") != generation
    ):
        raise ValueError("Wrong manifest schema or generation")
    files = document.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("Missing file inventory")

    entries = {}
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("Invalid file inventory record")
        name, size, digest = item["path"], item["size_bytes"], item["sha256"]
        path = PurePosixPath(name)
        if (
            path.is_absolute()
            or not path.parts
            or ".." in path.parts
            or path.as_posix() != name
            or name == MANIFEST_PATH
            or name in entries
            or type(size) is not int
            or size < 0
            or not isinstance(digest, str)
            or not _SHA256.fullmatch(digest)
        ):
            raise ValueError("Invalid file inventory record")
        origin = item.get("storage_generation")
        if "storage_generation" in item and (
            schema != REUSE_SCHEMA
            or not isinstance(origin, str)
            or origin in {generation, LEGACY_GENERATION}
            or not _GENERATION_ID.fullmatch(origin)
        ):
            raise ValueError("Invalid immutable file storage generation")
        entries[name] = GenerationFile(size, digest, origin)
    return entries


def manifest_bytes(document: Mapping[str, Any]) -> bytes:
    """Serialize the immutable manifest with the publication format."""
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def with_reused_files(document: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any]:
    """Borrow unchanged same-path bytes from the exact authenticated base.

    A reused record points straight to its physical copy, even when the base
    also reused it. Serving and recovery never follow manifest chains.
    """
    generation, base_generation = document["generation_id"], base["generation_id"]
    if generation == base_generation or document.get("schema_version") != STANDALONE_SCHEMA:
        raise ValueError("Reuse requires a distinct, complete new generation")
    before = parse_generation_files(base, base_generation)
    after = parse_generation_files(document, generation)
    files = []
    for item in document["files"]:
        name = item["path"]
        older = before.get(name)
        newer = after[name]
        if older and (older.sha256, older.size_bytes) == (newer.sha256, newer.size_bytes):
            item = dict(item, storage_generation=older.storage_generation or base_generation)
        files.append(item)
    manifest = dict(document, schema_version=REUSE_SCHEMA, files=files)
    parse_generation_files(manifest, generation)
    return manifest


def plan_object_reuse(
    document: Mapping[str, Any], base: Mapping[str, Any]
) -> tuple[bytes, dict[str, Any]]:
    """Return the planned manifest and the physical cost of staging it."""
    manifest = with_reused_files(document, base)
    raw = manifest_bytes(manifest)
    entries = parse_generation_files(manifest, manifest["generation_id"])
    borrowed = [entry for entry in entries.values() if entry.storage_generation is not None]
    logical_bytes = sum(entry.size_bytes for entry in entries.values())
    borrowed_bytes = sum(entry.size_bytes for entry in borrowed)
    return raw, {
        "candidate_generation": manifest["generation_id"],
        "reuse_manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "logical_files": len(entries),
        "logical_data_bytes": logical_bytes,
        "reused_files": len(borrowed),
        "reused_data_bytes": borrowed_bytes,
        "required_origin_generations": sorted({entry.storage_generation for entry in borrowed}),
        "planned_candidate_puts": len(entries) - len(borrowed) + 1,
        "planned_candidate_write_bytes": logical_bytes - borrowed_bytes + len(raw),
        "manifest_bytes": len(raw),
    }
