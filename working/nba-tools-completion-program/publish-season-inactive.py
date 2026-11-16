"""Prepare the exact PR623 nested overlay; only the protected workflow can publish."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

BASE = "availability-participation-2025-durant-v1-20261114"
BASE_MANIFEST = "cde98408f3390e6191da564197fb77ffbc598a3059963cfc21d9f2d7e1a6b366"
GENERATION = "availability-season-inactive-2023-v1-20261115"
BUNDLE = "qualified-overlay-v1.zip"
BUNDLE_SHA = "cb5caebada456829616fe9f75e54ce8d4a5fd0ab1363945024c75ebf3205b9e8"
QUALIFICATION = "source-evidence/season-inactive-pilot-20261115/qualification.json"
APPENDS = (
    "raw/player_game_availability/2023-24_regular_season.csv",
    "raw/player_game_availability/2023-24_regular_season.imports.json",
)


def unpack(root, destination, inventory):
    """Transport qualification is separate from the original numerical evidence."""
    source = root / BUNDLE
    if (
        {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} != {BUNDLE}
        or source.is_symlink()
        or source.stat().st_size != 324815
        or hashlib.sha256(source.read_bytes()).hexdigest() != BUNDLE_SHA
    ):
        raise ValueError("Only the unchanged PR623 bundle is accepted")
    with ZipFile(io.BytesIO(source.read_bytes())) as archive:
        expected = {item["path"]: item for item in inventory["overlay_files"]}
        if (
            len(expected) != 30
            or len(archive.namelist()) != 30
            or set(archive.namelist()) != expected.keys()
            or sum(item.file_size for item in archive.infolist()) > 6_000_000
        ):
            raise ValueError("Qualified member inventory differs")
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if (
                path.is_absolute()
                or ".." in path.parts
                or str(path) != item.filename
                or "\\" in item.filename
                or item.external_attr >> 16 & 0o170000 == 0o120000
            ):
                raise ValueError("Unsafe qualified member")
            raw = archive.read(item)
            binding = expected[item.filename]
            if (
                len(raw) != binding["size_bytes"]
                or hashlib.sha256(raw).hexdigest() != binding["sha256"]
            ):
                raise ValueError("Qualified member bytes differ")
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--generation-id", required=True)
    parser.add_argument("--prepare", action="store_true", required=True)
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent
    inventory = json.loads((directory / "season-inactive-inventory.json").read_text())
    if (
        args.generation_id != GENERATION
        or inventory["generation_id"] != GENERATION
        or inventory["base_generation"] != BASE
        or inventory["base_manifest_sha256"] != BASE_MANIFEST
        or args.work_dir.exists()
        or set(inventory["append_only"]) != set(APPENDS)
    ):
        raise ValueError("Fixed generation/base/append scope and empty workspace required")
    code = args.code_root.resolve()
    for item in inventory["code_files"]:
        path = code / item["path"]
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Preparation code differs from reviewed inventory")
    qualification = json.loads((directory / QUALIFICATION).read_bytes())
    if (
        qualification["run_id"] != 43690403060
        or qualification["request_sha"] != "7c5c653b9271a668b5ed66b33c693d42c2afaa77"
        or qualification["validated_season_queries"] != 186
        or qualification["overlay_file_sha256"]
        != {item["path"]: item["sha256"] for item in inventory["overlay_files"]}
    ):
        raise ValueError("Original numerical qualification differs")
    args.work_dir.mkdir(parents=True)
    overlay = args.work_dir / "qualified-overlay"
    unpack(args.artifact_dir, overlay, inventory)
    spec = importlib.util.spec_from_file_location(
        "original_overlay", directory / "publish-opening-availability.py"
    )
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    items = original.verify_overlay(
        overlay,
        dict(
            files=inventory["overlay_files"],
            request_sha=qualification["request_sha"],
            reviewed_sha=qualification["reviewed_code"],
            base_generation=BASE,
        ),
    )
    sys.path[:0] = [str(code), str(code / "src")]
    from nbatools.commands.pipeline.generation_publication import publish_local_generation
    from nbatools.commands.pipeline.generation_refresh import (
        changed_data_files,
        download_active_generation,
    )
    from tools.availability_overlay import verify_append

    data = args.work_dir / "data"
    base = download_active_generation(data, env_file=None)
    if base.generation_id != BASE:
        raise ValueError("Active generation changed; requalification is required")
    manifest_raw = (json.dumps(base.manifest, indent=2, sort_keys=True) + "\n").encode()
    if hashlib.sha256(manifest_raw).hexdigest() != BASE_MANIFEST:
        raise ValueError("Base manifest changed")
    (args.work_dir / "base-manifest.json").write_bytes(manifest_raw)
    for relative in APPENDS:
        verify_append(
            relative,
            (data / relative).read_bytes(),
            (overlay / relative).read_bytes(),
            inventory["append_only"][relative],
        )
    for item in items:
        source, target = overlay / item["path"], data / item["path"]
        if (
            target.exists()
            and target.read_bytes() != source.read_bytes()
            and item["path"] not in APPENDS
        ):
            raise ValueError("Existing source/data would be overwritten")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    changes = changed_data_files(data, base.manifest)
    if not changes or not set(changes) <= {item["path"] for item in items}:
        raise ValueError("Unexpected snapshot changes")
    local = publish_local_generation(
        GENERATION, source_dir=data, data_root=args.work_dir / "validation"
    )
    (args.work_dir / "local-validation.json").write_text(json.dumps(asdict(local), indent=2) + "\n")
    print(
        json.dumps(
            dict(
                changed_files=changes,
                validated_snapshot_bytes=local.total_bytes,
                publication="not_requested",
                r2_writes=0,
            )
        )
    )


if __name__ == "__main__":
    main()
