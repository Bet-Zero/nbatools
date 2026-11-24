"""Prepare only the exact retained Cleveland v2 + team appearance proof; no writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

BASE = "availability-season-inactive-2024-v1-20261116"
BASE_SHA = "0abce6f8261957df6cffc19ce24a4ed408a548e1292a33456ce55c0481903ecc"
GENERATION = "availability-cleveland-2024-v3-20261124"
BUNDLE_SHA = "a8a9ecfdd447a513498d5ae9a0333357711618e6abeacd2a7fb16b1d0807c298"
PROOF_SHA = "fd637c6d36c4fd9ce30b9e3f769c9ba806f535b9a943dc4be3fc6314529df86a"
PROOF_PATH = "raw/team_game_appearances/2024-25_regular_season.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--generation-id", required=True)
    parser.add_argument("--prepare", action="store_true", required=True)
    args = parser.parse_args()
    if args.generation_id != GENERATION or args.work_dir.exists():
        raise ValueError("Exact generation and empty preparation workspace required")
    bundle = args.artifact_dir / "qualified-overlay-v2.zip"
    proof = args.artifact_dir / "2024-25_regular_season.json"
    if (sha(bundle), sha(proof)) != (BUNDLE_SHA, PROOF_SHA):
        raise ValueError("Accepted Cleveland inputs differ")
    if set(p.name for p in args.artifact_dir.iterdir()) != {bundle.name, proof.name}:
        raise ValueError("Unexpected retained input")
    sys.path[:0] = [str(args.code_root / "src"), str(args.code_root)]
    from nbatools.commands.pipeline import generation_publication as publication
    from nbatools.commands.pipeline.generation_refresh import download_active_generation
    from tools.compose_participation_overlays import compose_overlays

    work = args.work_dir
    work.mkdir(parents=True)
    data = work / "data"
    downloaded = download_active_generation(data, env_file=None)
    base_raw = (json.dumps(downloaded.manifest, indent=2, sort_keys=True) + "\n").encode()
    if downloaded.generation_id != BASE or hashlib.sha256(base_raw).hexdigest() != BASE_SHA:
        raise ValueError("Active base differs from the reviewed Cleveland base")
    (work / "base-manifest.json").write_bytes(base_raw)
    (data / "metadata/generation_manifest.json").write_bytes(base_raw)
    before = {i["path"]: i for i in json.loads(base_raw)["files"]}
    # The established composer preserves every old serialized cell and import
    # authority, refuses conflicting sources, and checks pinned archive bytes.
    composed = compose_overlays(
        [(bundle, BUNDLE_SHA)],
        data,
        work / "composed",
        base_generation=BASE,
        base_manifest_sha256=BASE_SHA,
        candidate_sha=subprocess.check_output(
            ["git", "-C", str(args.code_root), "rev-parse", "HEAD"], text=True
        ).strip(),
    )
    for item in composed["overlay_files"]:
        target = data / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(work / "composed" / item["path"], target)
    target = data / PROOF_PATH
    if target.exists() or PROOF_PATH in before:
        raise ValueError("New proof must not replace an existing authority")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(proof, target)
    result = publication.publish_local_generation(
        GENERATION, source_dir=data, data_root=work / "validation"
    )
    snapshot = work / "validation/generations" / GENERATION
    after = {
        i["path"]: i
        for i in json.loads((snapshot / "metadata/generation_manifest.json").read_bytes())["files"]
    }
    allowed = {i["path"] for i in composed["overlay_files"]} | {PROOF_PATH}
    changed = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
    if changed != allowed or before.keys() - after.keys():
        raise ValueError("Complete snapshot differs outside qualified overlay")
    (work / "local-validation.json").write_text(json.dumps(asdict(result), indent=2) + "\n")
    (work / "preservation.json").write_text(
        json.dumps(
            dict(
                base_generation=BASE,
                base_manifest_sha256=BASE_SHA,
                unchanged_files=len(before) - len(before.keys() & changed),
                changed_paths=sorted(changed),
                append_only=composed["append_only"],
                team_complete_cases=21,
                rostered_complete_cases=14,
                production_writes=0,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
