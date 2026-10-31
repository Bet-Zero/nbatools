"""Verify the reviewed overlay; optionally stage/publish with existing operator authority.

Default is offline verification only. --prepare downloads and validates a full
base snapshot locally. --publish additionally invokes the existing conditional
R2 publisher. Never supply runtime or read-only validation credentials for writes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path


def verify_overlay(root: Path, inventory: dict) -> list[dict]:
    expected = {item["path"]: item for item in inventory["files"]}
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != set(expected):
        raise ValueError("Overlay file inventory differs from reviewed artifact")
    for relative, item in expected.items():
        path = root / relative
        if path.is_symlink() or ".." in Path(relative).parts:
            raise ValueError("Unsafe overlay path")
        raw = path.read_bytes()
        if len(raw) != item["size_bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise ValueError(f"Overlay checksum differs: {relative}")
    evidence = json.loads((root / "validation.json").read_text())
    if (
        evidence["candidate_sha"] != inventory["request_sha"]
        or evidence["base_generation"] != inventory["base_generation"]
    ):
        raise ValueError("Overlay validation provenance differs")
    return [item for item in inventory["files"] if item["path"].startswith("raw/")]


def main(
    *,
    inventory_path: Path | None = None,
    default_generation: str = "availability-opening-631b259a-20261017",
    append_only_paths: tuple[str, ...] = (),
) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-dir", required=True, type=Path, help="Extracted acquired_data directory"
    )
    parser.add_argument(
        "--code-root",
        type=Path,
        help="Reviewed repository checkout; defaults to this script's repository",
    )
    parser.add_argument(
        "--work-dir", type=Path, help="New empty operator workspace for full snapshot"
    )
    parser.add_argument("--generation-id", default=default_generation)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--prepare", action="store_true", help="Download and validate locally; no remote writes"
    )
    mode.add_argument(
        "--publish",
        action="store_true",
        help="Validate and invoke existing authorized R2 publisher",
    )
    args = parser.parse_args()
    inventory = json.loads(
        (
            inventory_path or Path(__file__).with_name("opening-availability-inventory.json")
        ).read_text()
    )
    items = verify_overlay(args.artifact_dir, inventory)
    print(
        json.dumps(
            dict(
                verified_overlay_files=len(items),
                overlay_bytes=sum(x["size_bytes"] for x in items),
                reviewed_sha=inventory["reviewed_sha"],
                base_generation=inventory["base_generation"],
            )
        )
    )
    if not (args.prepare or args.publish):
        return
    if args.work_dir is None or args.work_dir.exists():
        raise ValueError("Staging requires a new --work-dir")
    code_root = (args.code_root or Path(__file__).resolve().parents[2]).resolve()
    for item in inventory["code_files"]:
        path = code_root / item["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Executing code differs from reviewed validator: {path}")
    sys.path.insert(0, str(code_root / "src"))
    import nbatools.commands.pipeline.generation_publication as publication_module
    from nbatools.commands.pipeline.generation_publication import (
        publish_local_generation,
        publish_r2_generation,
    )
    from nbatools.commands.pipeline.generation_refresh import (
        changed_data_files,
        download_active_generation,
    )

    if not Path(publication_module.__file__).resolve().is_relative_to(code_root / "src"):
        raise ValueError("Publication imported from the wrong checkout")

    args.work_dir.mkdir(parents=True)
    data = args.work_dir / "data"
    base = download_active_generation(data, env_file=None)
    if base.generation_id != inventory["base_generation"]:
        raise ValueError(
            "Active generation changed: revalidate overlay against the new base before publication"
        )
    append_bindings = inventory.get("append_only", {})
    if set(append_bindings) != set(append_only_paths):
        raise ValueError("Append policy differs from the fixed publisher entry point")
    if append_only_paths:
        sys.path.insert(0, str(code_root))
        from tools.availability_overlay import verify_append

        overlay_paths = {item["path"] for item in items}
        if not set(append_only_paths) <= overlay_paths:
            raise ValueError("Append policy has no matching overlay file")
        for relative in append_only_paths:
            verify_append(
                relative,
                (data / relative).read_bytes(),
                (args.artifact_dir / relative).read_bytes(),
                append_bindings[relative],
            )
    (args.work_dir / "base-manifest.json").write_text(json.dumps(base.manifest, indent=2) + "\n")
    for item in items:
        source, destination = args.artifact_dir / item["path"], data / item["path"]
        if (
            destination.exists()
            and destination.read_bytes() != source.read_bytes()
            and item["path"] not in append_only_paths
        ):
            raise ValueError(
                "Overlay would overwrite existing data; review a combined dataset first"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    changed = changed_data_files(data, base.manifest)
    if not changed or not set(changed).issubset({item["path"] for item in items}):
        raise ValueError("Unexpected core data change or already-published overlay")
    local = publish_local_generation(
        args.generation_id, source_dir=data, data_root=args.work_dir / "validation"
    )
    (args.work_dir / "local-validation.json").write_text(json.dumps(asdict(local), indent=2) + "\n")
    print(
        json.dumps(
            dict(
                changed_files=changed,
                validated_snapshot_bytes=local.total_bytes,
                publication="not_requested" if not args.publish else "requested",
            )
        )
    )
    if args.publish:
        result = publish_r2_generation(
            args.generation_id, source_dir=data, expected_base=base.generation_id, env_file=None
        )
        (args.work_dir / "publication.json").write_text(json.dumps(asdict(result), indent=2) + "\n")
        print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
