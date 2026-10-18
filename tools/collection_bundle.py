"""Acquisition-only laptop handoff; Python standard library, no NBA Tools install.

Packages data, original source responses and provenance. Never runs code from an
archive, touches R2, validates NBA statistics or approves publication.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath

MAX_ARCHIVE = 20_000_000
MAX_EXPANDED = 100_000_000
MAX_FILES = 2000
MANIFEST = "collection-manifest.json"


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def _safe(name):
    path = PurePosixPath(name)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or any(p.startswith(".") for p in path.parts)
        or path.as_posix() != name
        or path.suffix not in {".json", ".csv", ".pdf"}
        or not (name.startswith(("sources/", "data/raw/")) or name == "acquisition.json")
    ):
        raise ValueError(
            "Only explicit raw data, source responses and acquisition metadata allowed"
        )
    return path


def _request(request):
    if request.get("status") != "collection_requirement_not_publication_approval":
        raise ValueError("Expected cloud-generated collection requirement")
    if not request.get("base_generation") or not request.get("base_manifest_sha256"):
        raise ValueError("Collection request must identify its cloud base generation")
    return digest(json.dumps(request, sort_keys=True, separators=(",", ":")).encode())


def create(root, request, output):
    root, output = Path(root), Path(output)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Expected a data-only collection directory")
    request_sha = _request(request)
    files = {}
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlink not allowed")
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        _safe(name)
        size = path.stat().st_size
        total += size
        if size > MAX_EXPANDED or total > MAX_EXPANDED or len(files) >= MAX_FILES:
            raise ValueError("Collection must be split into smaller bounded requests")
        data = path.read_bytes()
        files[name] = {"bytes": size, "sha256": digest(data)}
    if "acquisition.json" not in files or not any(p.startswith("sources/") for p in files):
        raise ValueError("Original source payloads and acquisition.json are required")
    metadata = json.loads((root / "acquisition.json").read_text())
    if (
        not metadata.get("source")
        or not metadata.get("captured_at")
        or "parameters" not in metadata
    ):
        raise ValueError("Record source, capture time and exact request parameters")
    manifest = {
        "schema_version": 1,
        "classification": "unvalidated_development_collection",
        "request_sha256": request_sha,
        "request": request,
        "files": files,
        "production_writes": 0,
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(root / name, name)
        archive.writestr(MANIFEST, json.dumps(manifest, indent=2) + "\n")
    payload = buffer.getvalue()
    if len(payload) > MAX_ARCHIVE:
        raise ValueError("Split collections to keep GitHub web uploads below20MB")
    with output.open("xb") as handle:
        handle.write(payload)
    return {
        "bytes": len(payload),
        "sha256": digest(payload),
        "files": len(files),
        "state": "unvalidated_staging_only",
        "production_writes": 0,
    }


def unpack(archive_path, request, destination):
    archive_path, destination = Path(archive_path), Path(destination)
    if destination.exists():
        raise ValueError("Cloud staging destination must not exist")
    if archive_path.stat().st_size > MAX_ARCHIVE:
        raise ValueError("Archive exceeds collection bound")
    payload = archive_path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        entries = archive.infolist()
        names = [item.filename for item in entries]
        if len(names) != len(set(names)) or len(names) > MAX_FILES + 1:
            raise ValueError("Duplicate/excessive archive entries")
        if sum(item.file_size for item in entries) > MAX_EXPANDED + 100_000:
            raise ValueError("Expanded archive exceeds bound")
        manifest = json.loads(archive.read(MANIFEST))
        if (
            manifest.get("schema_version") != 1
            or manifest.get("request_sha256") != _request(request)
            or manifest.get("request") != request
        ):
            raise ValueError("Archive does not match original cloud request")
        if set(names) != set(manifest["files"]) | {MANIFEST}:
            raise ValueError("Archive member inventory mismatch")
        verified = {}
        for item in entries:
            if stat.S_ISLNK(item.external_attr >> 16) or item.is_dir():
                raise ValueError("Symlink/directory entry not allowed")
            if item.filename == MANIFEST:
                continue
            _safe(item.filename)
            expected = manifest["files"][item.filename]
            if item.file_size != expected["bytes"]:
                raise ValueError("Collection size mismatch")
            data = archive.read(item)
            if digest(data) != expected["sha256"]:
                raise ValueError("Collection checksum mismatch")
            verified[item.filename] = data
    # All paths, hashes and the original request are checked before any write.
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in verified.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (destination / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
    return {
        "state": "unvalidated_staging_only",
        "files": len(verified),
        "sha256": digest(payload),
        "production_writes": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["create", "unpack"])
    parser.add_argument("source", type=Path)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text())
    result = (
        create(args.source, request, args.output)
        if args.command == "create"
        else unpack(args.source, request, args.output)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
