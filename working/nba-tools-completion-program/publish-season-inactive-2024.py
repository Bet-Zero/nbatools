"""Prepare the unchanged PR626 overlay; only the protected gate can publish."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

BASE = "availability-season-inactive-2023-v1-20261115"
BASE_MANIFEST = "8ec80812ae9dda9222d9d157c253d7a919af214ae40c49a27c20f87b52d156c8"
GENERATION = "availability-season-inactive-2024-v1-20261116"
BUNDLE = "qualified-overlay-v1.zip"
BUNDLE_SHA = "a910703174d54873965f36f5f855e214fdb186a209565332922749f63de73e50"
QUALIFIED = "source-evidence/season-inactive-2024/product-results.json"
PATHS = {
    "raw/player_game_inactive/2024-25_regular_season.csv",
    "raw/player_game_inactive/2024-25_regular_season.source.json",
    "raw/player_game_inactive_sources/"
    "906e36b7f4f5010ff33b35bf12b22d0083b9a0099f49383b01d2fea8ae82e769.csv",
}


def unpack(root, destination, inventory):
    source = root / BUNDLE
    if (
        {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} != {BUNDLE}
        or source.is_symlink()
        or source.stat().st_size != 237876
        or hashlib.sha256(source.read_bytes()).hexdigest() != BUNDLE_SHA
    ):
        raise ValueError("Only the unchanged PR626 bundle is accepted")
    expected = {item["path"]: item for item in inventory["overlay_files"]}
    with ZipFile(io.BytesIO(source.read_bytes())) as archive:
        if (
            len(inventory["overlay_files"]) != 3
            or len(expected) != 3
            or set(expected) != PATHS
            or len(archive.namelist()) != 3
            or set(archive.namelist()) != PATHS
            or sum(item.file_size for item in archive.infolist()) != 4481346
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
            raw, binding = archive.read(item), expected[item.filename]
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
    inventory = json.loads((directory / "season-inactive-2024-inventory.json").read_bytes())
    if (
        args.generation_id != GENERATION
        or inventory["generation_id"] != GENERATION
        or inventory["base_generation"] != BASE
        or inventory["base_manifest_sha256"] != BASE_MANIFEST
        or inventory["append_only"] != {}
        or args.work_dir.exists()
        or inventory["source_qualification"]
        != dict(
            reviewed_sha="84b3fb26bf5bd7a6f37722345fa39dfdeb781f9f",
            request_sha="69a9234f69b34f4367b470b9ad378a34ab667c82",
            run_id=43816748972,
            job_id=133130723752,
        )
    ):
        raise ValueError("Fixed generation/base/additions and empty workspace required")
    code = args.code_root.resolve()
    for item in inventory["code_files"]:
        path = code / item["path"]
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Preparation code differs from reviewed inventory")
    proof = json.loads((directory / QUALIFIED).read_bytes())
    if (
        proof["base_generation"] != BASE
        or proof["base_manifest_sha256"] != BASE_MANIFEST
        or proof["after"]["candidate_cases"] != 707
        or proof["after"]["complete_cases"] != 69
        or proof["after"]["states"]["unknown"] != 20649
        or len(proof["identity_name_rejections"]) != 7
        or proof["accepted_rows"] != 10847
        or len(proof["complete_season_queries"]) != 138
    ):
        raise ValueError("Original numerical qualification differs")
    args.work_dir.mkdir(parents=True)
    overlay = args.work_dir / "qualified-overlay"
    unpack(args.artifact_dir, overlay, inventory)
    sys.path[:0] = [str(code), str(code / "src")]
    from nbatools.commands.pipeline.generation_publication import publish_local_generation
    from nbatools.commands.pipeline.generation_refresh import (
        changed_data_files,
        download_active_generation,
    )

    data = args.work_dir / "data"
    base = download_active_generation(data, env_file=None)
    manifest_raw = (json.dumps(base.manifest, indent=2, sort_keys=True) + "\n").encode()
    if base.generation_id != BASE or hashlib.sha256(manifest_raw).hexdigest() != BASE_MANIFEST:
        raise ValueError("Active base changed; requalification is required")
    (args.work_dir / "base-manifest.json").write_bytes(manifest_raw)
    for relative in sorted(PATHS):
        source, target = overlay / relative, data / relative
        if target.exists():
            raise ValueError("Only new paths are permitted; existing data must be preserved")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    changes = changed_data_files(data, base.manifest)
    if set(changes) != PATHS:
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
