"""Bounded, byte-exact cloud backup and offline restore. No R2 write methods.

Durability is provided by the dedicated GitHub release job, never by Actions
artifact retention. This module neither publishes nor prunes generations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from nbatools.commands.pipeline.generation_publication import (
    GENERATION_MANIFEST_PATH,
    _resolve_r2_target,
    _safe_relative_path,
    validate_staged_generation,
)
from tools.r2_publication import verify_pointer_manifest

MAX_FILES = 3000
MAX_BYTES = 1_000_000_000
MAX_ARCHIVE = 200_000_000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory(manifest):
    files = manifest["files"]
    if not 0 < len(files) <= MAX_FILES:
        raise ValueError("Backup file count exceeds bound")
    result = {}
    total = 0
    for item in files:
        key = _safe_relative_path(item["path"]).as_posix()
        if not key.startswith(("raw/", "processed/", "metadata/")) or key in result:
            raise ValueError("Unexpected or duplicate backup path")
        size = item["size_bytes"]
        if not isinstance(size, int) or size < 0 or size > MAX_BYTES:
            raise ValueError("Invalid backup file size")
        total += size
        result[key] = item
    if total > MAX_BYTES:
        raise ValueError("Backup total exceeds bound")
    return result


def export_backup(output, generation, *, client=None, bucket=None):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Backup output must be empty")
    output.mkdir(parents=True, exist_ok=True)
    if client is None:
        client, bucket = _resolve_r2_target(client=None, bucket_name=None, env=None, env_file=None)
    before, manifest, manifest_sha = verify_pointer_manifest(client, bucket, generation)
    files = inventory(manifest)
    stage = output / "validation"
    stage.mkdir()
    prefix = f"generations/{generation}/"
    # Preserve original derived files and receipt bytes, including the manifest.
    for key in [*files, GENERATION_MANIFEST_PATH.as_posix()]:
        body = client.get_object(Bucket=bucket, Key=prefix + key)["Body"]
        try:
            limit = files[key]["size_bytes"] if key in files else 5_000_000
            raw = body.read(limit + 1)
        finally:
            body.close()
        if key in files:
            expected = files[key]
            if (
                len(raw) != expected["size_bytes"]
                or hashlib.sha256(raw).hexdigest() != expected["sha256"]
            ):
                raise ValueError("Downloaded backup object differs from manifest")
        elif hashlib.sha256(raw).hexdigest() != manifest_sha:
            raise ValueError("Downloaded manifest differs from active pointer")
        path = stage / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    validate_staged_generation(stage, generation)
    after, _, after_sha = verify_pointer_manifest(client, bucket, generation)
    if before != after or manifest_sha != after_sha:
        raise ValueError("Active pointer changed during backup")
    archive = output / "generation.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                zipped.write(path, path.relative_to(stage).as_posix())
    if archive.stat().st_size > MAX_ARCHIVE:
        raise ValueError("Compressed backup exceeds bound; do not upload")
    receipt = {
        "schema_version": 1,
        "generation_id": generation,
        "manifest_sha256": manifest_sha,
        "archive_sha256": sha(archive),
        "archive_bytes": archive.stat().st_size,
        "files": len(files),
        "data_bytes": sum(item["size_bytes"] for item in files.values()),
        "captured_at": datetime.now(UTC).isoformat(),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "workflow_sha": os.environ.get("GITHUB_SHA"),
        "r2_writes": 0,
        "production_pointer_unchanged": True,
    }
    shutil.rmtree(stage)  # Only this invocation's newly created validation copy.
    (output / "backup-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def restore_backup(archive, receipt, destination):
    """Recover to a new directory; authenticate every byte with original manifest."""
    archive, destination = Path(archive), Path(destination)
    if destination.exists():
        raise ValueError("Restore target must not exist")
    if (
        archive.stat().st_size > MAX_ARCHIVE
        or archive.stat().st_size != receipt["archive_bytes"]
        or sha(archive) != receipt["archive_sha256"]
    ):
        raise ValueError("Backup archive checksum/size mismatch")
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        names = [item.filename for item in entries]
        if len(names) != len(set(names)) or len(names) > MAX_FILES + 1:
            raise ValueError("Duplicate or excessive archive entries")
        if sum(item.file_size for item in entries) > MAX_BYTES + 5_000_000:
            raise ValueError("Expanded backup exceeds bound")
        for item in entries:
            path = _safe_relative_path(item.filename)
            if (
                not path.as_posix().startswith(("raw/", "processed/", "metadata/"))
                or stat.S_ISLNK(item.external_attr >> 16)
                or item.is_dir()
            ):
                raise ValueError("Unsafe backup archive member")
        manifest_raw = zipped.read(GENERATION_MANIFEST_PATH.as_posix())
        if hashlib.sha256(manifest_raw).hexdigest() != receipt["manifest_sha256"]:
            raise ValueError("Backup manifest checksum mismatch")
        manifest = json.loads(manifest_raw)
        files = inventory(manifest)
        if (
            set(names) != {*files, GENERATION_MANIFEST_PATH.as_posix()}
            or len(files) != receipt["files"]
        ):
            raise ValueError("Backup inventory mismatch")
        if sum(item["size_bytes"] for item in files.values()) != receipt["data_bytes"]:
            raise ValueError("Backup byte inventory mismatch")
        for item in entries:
            expected = files.get(item.filename)
            if expected and item.file_size != expected["size_bytes"]:
                raise ValueError("Backup member size mismatch")
        destination.mkdir(parents=True)
        for item in entries:
            path = destination / item.filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(zipped.read(item))
    validate_staged_generation(destination, receipt["generation_id"])
    return {
        "generation_id": receipt["generation_id"],
        "files": len(files),
        "data_bytes": receipt["data_bytes"],
        "manifest_sha256": receipt["manifest_sha256"],
        "archive_sha256": receipt["archive_sha256"],
        "restored_at": datetime.now(UTC).isoformat(),
        "r2_credentials_used": False,
        "production_writes": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    result = restore_backup(args.archive, json.loads(args.receipt.read_text()), args.destination)
    Path("restore-receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
