"""Prepare one exact reviewed new-game availability append; never write to R2."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import sys
import zipfile
from dataclasses import asdict
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--generation-id", required=True)
    parser.add_argument("--prepare", action="store_true", required=True)
    args = parser.parse_args()
    inventory = json.loads(Path(__file__).with_name("cloud-acceptance-inventory.json").read_text())
    if args.generation_id != inventory["generation_id"] or args.work_dir.exists():
        raise ValueError("Exact new-generation identifier and empty workspace required")
    code_root = args.code_root.resolve()
    for item in inventory["code_files"]:
        path = code_root / item["path"]
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Preparation code differs from exact reviewed inventory")
    expected = inventory["files"]
    if len(expected) != 1 or expected[0]["path"] != "cloud-recovery-bundle.zip":
        raise ValueError("Only the reviewed bounded public bundle is accepted")
    paths = [
        p.relative_to(args.artifact_dir).as_posix()
        for p in args.artifact_dir.rglob("*")
        if p.is_file()
    ]
    if paths != ["cloud-recovery-bundle.zip"]:
        raise ValueError("Unexpected preparation input")
    raw = (args.artifact_dir / paths[0]).read_bytes()
    if (
        len(raw) != expected[0]["size_bytes"]
        or hashlib.sha256(raw).hexdigest() != expected[0]["sha256"]
    ):
        raise ValueError("Public source bundle hash/size mismatch")
    args.work_dir.mkdir(parents=True)
    overlay = args.work_dir / "qualified-overlay"
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if sum(p.file_size for p in archive.infolist()) > 5_000_000:
            raise ValueError("Oversized source bundle")
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate source bundle entry")
        for item in archive.infolist():
            path = Path(item.filename)
            if (
                path.is_absolute()
                or ".." in path.parts
                or item.external_attr >> 16 & 0o170000 == 0o120000
            ):
                raise ValueError("Unsafe source bundle entry")
        archive.extractall(overlay)
    receipt = json.loads((overlay / "receipt.json").read_text())
    if (
        receipt["source_revision"] != inventory["request_sha"]
        or receipt["base_generation"] != inventory["base_generation"]
        or receipt["new_game_id"] != inventory["new_game_id"]
    ):
        raise ValueError("Qualified overlay provenance differs")
    sys.path.insert(0, str(code_root / "src"))
    import pandas as pd

    from nbatools.commands.pipeline.generation_publication import publish_local_generation
    from nbatools.commands.pipeline.generation_refresh import (
        changed_data_files,
        download_active_generation,
    )
    from nbatools.commands.pipeline.pull_player_game_availability import validate_publication

    validate_publication(overlay / "data")
    data = args.work_dir / "data"
    base = download_active_generation(data, env_file=None)
    if base.generation_id != inventory["base_generation"]:
        raise ValueError("Active base changed; a new reviewed package is required")
    (args.work_dir / "base-manifest.json").write_text(json.dumps(base.manifest, indent=2) + "\n")
    name = "2025-26_regular_season.csv"
    relative = Path("raw/player_game_availability") / name
    current_path, addition_path = data / relative, overlay / "data" / relative
    current = pd.read_csv(current_path, dtype={"game_id": str})
    addition = pd.read_csv(addition_path, dtype={"game_id": str})
    new_id = inventory["new_game_id"]
    if (
        set(pd.to_numeric(addition.game_id)) != {new_id}
        or pd.to_numeric(current.game_id).eq(new_id).any()
        or len(addition) != inventory["new_rows"]
    ):
        raise ValueError("Append must contain only the exact previously absent qualified game")
    # Preserve all existing rows and their per-game digests; do not overwrite a
    # different observation for an existing game or change the core game logs.
    combined = pd.concat([current, addition], ignore_index=True)
    combined.to_csv(current_path, index=False)
    imports_path = current_path.with_suffix(".imports.json")
    imports = json.loads(imports_path.read_text())
    added_imports = json.loads(addition_path.with_suffix(".imports.json").read_text())
    if set(added_imports) != {str(new_id)} or set(imports) & set(added_imports):
        raise ValueError("Existing per-game source receipts may not be replaced")
    imports_path.write_text(json.dumps(imports | added_imports, sort_keys=True) + "\n")
    allowed = {relative.as_posix(), relative.with_suffix(".imports.json").as_posix()}
    source_dir = Path("raw/player_game_availability_sources")
    for source in (overlay / "data" / source_dir).iterdir():
        destination = data / source_dir / source.name
        if destination.exists() and destination.read_bytes() != source.read_bytes():
            raise ValueError("Immutable retained source collision")
        shutil.copy2(source, destination)
        allowed.add((source_dir / source.name).as_posix())
    validate_publication(data)
    changes = changed_data_files(data, base.manifest)
    if not changes or not set(changes).issubset(allowed):
        raise ValueError("Unexpected core/processed data change")
    local = publish_local_generation(
        args.generation_id, source_dir=data, data_root=args.work_dir / "validation"
    )
    (args.work_dir / "local-validation.json").write_text(json.dumps(asdict(local), indent=2) + "\n")
    print(
        json.dumps(
            {
                "validated_new_game": new_id,
                "new_rows": len(addition),
                "preserved_availability_rows": len(current),
                "changed_files": changes,
                "publication": "not_requested",
                "r2_writes": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
