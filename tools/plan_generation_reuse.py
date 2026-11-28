"""Prepare an offline object-reuse manifest and measure the exact storage delta."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from nbatools.generation_manifest import plan_object_reuse


def _read_exact(path: Path, expected: str) -> dict:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Input manifest differs from its expected immutable checksum")
    return json.loads(raw)


def plan(base_path: Path, base_hash: str, candidate_path: Path, candidate_hash: str):
    base = _read_exact(base_path, base_hash)
    candidate = _read_exact(candidate_path, candidate_hash)
    raw, footprint = plan_object_reuse(candidate, base)
    receipt = {
        "base_generation": base["generation_id"],
        "base_manifest_sha256": base_hash,
        "standalone_manifest_sha256": candidate_hash,
        **footprint,
        "actual_production_writes": 0,
    }
    return raw, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-manifest", type=Path, required=True)
    parser.add_argument("--base-sha256", required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw, receipt = plan(
        args.base_manifest, args.base_sha256, args.candidate_manifest, args.candidate_sha256
    )
    args.output.mkdir(parents=True)
    (args.output / "generation_manifest.json").write_bytes(raw)
    (args.output / "reuse-plan.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
