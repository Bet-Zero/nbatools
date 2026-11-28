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
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from nbatools.commands.pipeline.generation_publication import (
    GENERATION_MANIFEST_PATH,
    _resolve_r2_target,
    _safe_relative_path,
    validate_staged_generation,
)
from nbatools.generation_manifest import GENERATIONS_DIR, parse_generation_files
from tools.r2_publication import (
    BACKUP_MAX_ARCHIVE as MAX_ARCHIVE,
)
from tools.r2_publication import (
    BACKUP_MAX_BYTES as MAX_BYTES,
)
from tools.r2_publication import (
    BACKUP_MAX_FILES as MAX_FILES,
)
from tools.r2_publication import (
    BACKUP_MAX_MANIFEST_BYTES,
    REGISTRY,
    same_pointer,
    verify_pointer_manifest,
    write_json,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def qualified_activation_manifest(generation, manifest_sha256):
    """Match only an exact independently qualified generation in the reviewed registry."""
    packages = json.loads(REGISTRY.read_bytes())["packages"]
    return any(
        package["generation_id"] == generation
        and "activate_candidate" in package.get("operations", [])
        and package["activation"]["manifest_sha256"] == manifest_sha256
        for package in packages.values()
    )


def inventory(manifest):
    files = parse_generation_files(manifest, manifest["generation_id"])
    if len(files) > MAX_FILES:
        raise ValueError("Backup file count exceeds bound")
    total = 0
    for key, item in files.items():
        if not key.startswith(("raw/", "processed/", "metadata/")):
            raise ValueError("Unexpected or duplicate backup path")
        size = item.size_bytes
        if size > MAX_BYTES:
            raise ValueError("Invalid backup file size")
        total += size
    if total > MAX_BYTES:
        raise ValueError("Backup total exceeds bound")
    return files


def _verified_object(client, bucket, key, *, size, digest):
    body = client.get_object(Bucket=bucket, Key=key)["Body"]
    try:
        raw = body.read(size + 1)
    finally:
        body.close()
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Downloaded backup object differs from manifest")
    return raw


def candidate_backup_preflight(client, bucket, generation, manifest_sha256, manifest_raw):
    """Measure ZIP size from the exact uploaded bytes, without exporting or repointing."""
    if (
        len(manifest_raw) > BACKUP_MAX_MANIFEST_BYTES
        or hashlib.sha256(manifest_raw).hexdigest() != manifest_sha256
    ):
        raise ValueError("Candidate backup manifest differs from the approved checksum")
    manifest = json.loads(manifest_raw)
    if manifest.get("generation_id") != generation:
        raise ValueError("Candidate backup manifest has the wrong schema or generation")
    files = inventory(manifest)
    with tempfile.TemporaryFile() as handle:
        with zipfile.ZipFile(handle, "w", zipfile.ZIP_DEFLATED) as zipped:
            zipped.writestr(GENERATION_MANIFEST_PATH.as_posix(), manifest_raw)
            for key, item in sorted(files.items()):
                raw = _verified_object(
                    client,
                    bucket,
                    item.object_key(generation, key),
                    size=item.size_bytes,
                    digest=item.sha256,
                )
                zipped.writestr(key, raw)
                if handle.tell() > MAX_ARCHIVE:
                    raise ValueError("Compressed candidate backup exceeds bound")
        archive_bytes = handle.tell()
    if archive_bytes > MAX_ARCHIVE:
        raise ValueError("Compressed candidate backup exceeds bound")
    return {
        "generation_id": generation,
        "manifest_sha256": manifest_sha256,
        "files": len(files),
        "data_bytes": sum(item.size_bytes for item in files.values()),
        "archive_bytes": archive_bytes,
        "r2_writes": 0,
    }


def export_backup(output, generation, *, client=None, bucket=None, expected_pointer=None):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Backup output must be empty")
    output.mkdir(parents=True, exist_ok=True)
    if client is None:
        client, bucket = _resolve_r2_target(client=None, bucket_name=None, env=None, env_file=None)
    before, manifest, manifest_sha = verify_pointer_manifest(client, bucket, generation)
    if expected_pointer is not None and not same_pointer(before, expected_pointer):
        raise ValueError("Active pointer differs from the independently verified activation")
    files = inventory(manifest)
    stage = output / "validation"
    stage.mkdir()
    # Preserve original derived files and receipt bytes, including the manifest.
    for key, expected in files.items():
        raw = _verified_object(
            client,
            bucket,
            expected.object_key(generation, key),
            size=expected.size_bytes,
            digest=expected.sha256,
        )
        path = stage / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    key = GENERATION_MANIFEST_PATH
    body = client.get_object(Bucket=bucket, Key=f"{GENERATIONS_DIR}/{generation}/{key}")["Body"]
    try:
        raw_manifest = body.read(BACKUP_MAX_MANIFEST_BYTES + 1)
    finally:
        body.close()
    if (
        len(raw_manifest) > BACKUP_MAX_MANIFEST_BYTES
        or hashlib.sha256(raw_manifest).hexdigest() != manifest_sha
    ):
        raise ValueError("Downloaded manifest differs from active pointer")
    (stage / key).parent.mkdir(parents=True, exist_ok=True)
    (stage / key).write_bytes(raw_manifest)
    # Every body and the complete inventory above are authenticated by the
    # exact independently qualified manifest. Other backups still replay.
    from nbatools.participation_source_packs import PACK_DIR

    qualified = not any(name.startswith(PACK_DIR + "/") for name in files) and (
        qualified_activation_manifest(generation, manifest_sha)
    )
    if not qualified:
        validate_staged_generation(stage, generation)
    after, _, after_sha = verify_pointer_manifest(client, bucket, generation)
    if not same_pointer(before, after) or manifest_sha != after_sha:
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
        "data_bytes": sum(item.size_bytes for item in files.values()),
        "captured_at": datetime.now(UTC).isoformat(),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "workflow_sha": os.environ.get("GITHUB_SHA"),
        "r2_writes": 0,
        "production_pointer_unchanged": True,
        "source_qualification_reused": qualified,
    }
    if expected_pointer is not None:
        receipt["verified_pointer"] = before
    shutil.rmtree(stage)  # Only this invocation's newly created validation copy.
    (output / "backup-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def export_reconciled_candidate_backup(
    output, reconciliation_receipt, *, expected_receipt_sha256, client=None, bucket=None
):
    """Back up only the unchanged pointer from a reviewed reconciliation receipt."""
    raw = Path(reconciliation_receipt).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_receipt_sha256:
        raise ValueError("Activation reconciliation receipt differs from the reviewed bytes")
    result = json.loads(raw)
    observation = result["reconciliation"]
    pointer = result.get("verified_pointer")
    generation = result["generation_id"]
    if (
        result.get("publication_state") != "candidate_activated_historical_verified"
        or observation.get("status") != "exact_candidate_active"
        or observation.get("production_writes") != 0
        or not isinstance(pointer, dict)
        or not same_pointer(pointer, observation["observed_pointer"])
        or pointer.get("generation_id") != generation
        or pointer.get("previous_generation_id") != result["base_generation"]
        or pointer.get("manifest_sha256") != result["prepared_manifest_sha256"]
    ):
        raise ValueError("Backup requires independently verified candidate activation evidence")
    receipt = export_backup(
        output, generation, client=client, bucket=bucket, expected_pointer=pointer
    )
    if receipt["files"] != result["file_count"] or receipt["data_bytes"] != result["total_bytes"]:
        raise ValueError("Backup inventory differs from the verified candidate inventory")
    receipt["reconciliation_receipt_sha256"] = expected_receipt_sha256
    write_json(Path(output) / "backup-receipt.json", receipt)
    return receipt


def restore_backup(archive, receipt, destination):
    """Recover to a new directory; authenticate every byte with original manifest."""
    archive, destination = Path(archive), Path(destination)
    if destination.exists():
        raise ValueError("Restore target must not exist")
    reconciliation = {}
    if "reconciliation_receipt_sha256" in receipt:
        pointer = receipt["verified_pointer"]
        if (
            pointer.get("generation_id") != receipt["generation_id"]
            or pointer.get("manifest_sha256") != receipt["manifest_sha256"]
        ):
            raise ValueError("Reconciliation pointer differs from the backup identity")
        reconciliation = {
            "verified_pointer": pointer,
            "reconciliation_receipt_sha256": receipt["reconciliation_receipt_sha256"],
        }
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
        if sum(item.file_size for item in entries) > MAX_BYTES + BACKUP_MAX_MANIFEST_BYTES:
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
            or manifest["generation_id"] != receipt["generation_id"]
        ):
            raise ValueError("Backup inventory mismatch")
        if sum(item.size_bytes for item in files.values()) != receipt["data_bytes"]:
            raise ValueError("Backup byte inventory mismatch")
        for item in entries:
            expected = files.get(item.filename)
            if expected and item.file_size != expected.size_bytes:
                raise ValueError("Backup member size mismatch")
        destination.mkdir(parents=True)
        from nbatools.participation_source_packs import PACK_DIR

        qualified = not any(name.startswith(PACK_DIR + "/") for name in files) and (
            qualified_activation_manifest(receipt["generation_id"], receipt["manifest_sha256"])
        )
        for item in entries:
            path = destination / item.filename
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = zipped.read(item)
            expected = files.get(item.filename)
            if qualified and expected and hashlib.sha256(raw).hexdigest() != expected.sha256:
                raise ValueError("Restored backup object differs from the qualified manifest")
            path.write_bytes(raw)
    if not qualified:
        validate_staged_generation(destination, receipt["generation_id"])
    return {
        **reconciliation,
        "generation_id": receipt["generation_id"],
        "files": len(files),
        "data_bytes": receipt["data_bytes"],
        "manifest_sha256": receipt["manifest_sha256"],
        "archive_sha256": receipt["archive_sha256"],
        "restored_at": datetime.now(UTC).isoformat(),
        "r2_credentials_used": False,
        "production_writes": 0,
        "source_qualification_reused": qualified,
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
