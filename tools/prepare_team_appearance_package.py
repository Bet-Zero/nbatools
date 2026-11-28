"""Compose a retained team-season appearance package against its immutable base."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from time import perf_counter


def _file_sha(path: Path) -> str:
    with path.open("rb") as body:
        return hashlib.file_digest(body, "sha256").hexdigest()


def _append_appearance_scope(previous: dict, incoming: dict) -> dict:
    scope_fields = ("schema_version", "season", "season_type", "scope", "dependencies")
    if any(previous[field] != incoming[field] for field in scope_fields):
        raise ValueError("Team-season proof dependencies conflict with the retained proof")
    sides = {(side["game_id"], side["team_id"]): side for side in previous["sides"]}
    prior_count = len(sides)
    if prior_count != len(previous["sides"]):
        raise ValueError("Duplicate side in the retained appearance proof")
    for side in incoming["sides"]:
        key = (side["game_id"], side["team_id"])
        if sides.setdefault(key, side) != side:
            raise ValueError("Team-season package would replace an accepted side")
    if len(sides) == prior_count:
        raise ValueError("Team-season package adds no independently qualified sides")
    return {
        **previous,
        "sides": list(sides.values()),
        "unqualified": previous["unqualified"] + incoming["unqualified"],
        "source_requests": previous["source_requests"] + incoming["source_requests"],
    }


def _final_team_games(data, before, relative, team_id, season, kind):
    source = data / relative
    if _file_sha(source) != before[relative]["sha256"]:
        raise ValueError("Team-season denominator differs from the immutable base")
    population = {}
    with source.open(newline="", encoding="utf-8") as rows:
        for row in csv.DictReader(rows):
            if str(team_id) not in {
                row["team_a_id"],
                row["team_b_id"],
                row["home_team_id"],
                row["away_team_id"],
            }:
                continue
            home, away = int(row["home_team_id"]), int(row["away_team_id"])
            game = int(row["game_id"])
            if (
                team_id not in {home, away}
                or row["status"].casefold() != "final"
                or row["season"] != season
                or row["season_type"] != kind
                or home == away
                or game in population
            ):
                raise ValueError("Team-season denominator contains unfinished or conflicting games")
            population[game] = (row["game_date"], home, away)
    return population


def prepare(artifact_dir: Path, code_root: Path, work: Path, generation: str, base_data=None):
    from nbatools.commands.pipeline.generation_publication import publish_local_generation
    from nbatools.commands.pipeline.generation_refresh import download_active_generation
    from tools.compose_participation_overlays import compose_overlays

    started = perf_counter()
    packet_path = artifact_dir / "package.json"
    packet = json.loads(packet_path.read_bytes())
    season, kind, team_id = packet["season"], packet["season_type"], packet["team_id"]
    game_ids = packet["game_ids"]
    if base_data is not None and (
        base_data.resolve() == work.resolve() or base_data.resolve() in work.resolve().parents
    ):
        raise ValueError("Preparation workspace must be outside the restored base")
    if (
        work.exists()
        or packet.get("schema_version") != 1
        or generation != packet["generation_id"]
        or generation == packet["base_generation"]
        or not re.fullmatch(r"(?:19|20)\d{2}-\d{2}", season)
        or kind not in {"Regular Season", "Playoffs"}
        or type(team_id) is not int
        or team_id <= 0
        or not game_ids
        or any(type(game) is not int or game <= 0 for game in game_ids)
        or len(set(game_ids)) != len(game_ids)
    ):
        raise ValueError("Invalid team-season package or preparation workspace")

    suffix = f"{season}_{kind.lower().replace(' ', '_')}"
    overlay = artifact_dir / "qualified-overlay.zip"
    proof_path = artifact_dir / f"{suffix}.json"
    retained = {packet_path, overlay, proof_path}
    if set(artifact_dir.iterdir()) != retained or any(p.is_symlink() for p in retained):
        raise ValueError("Unexpected team-season package inputs")
    if (_file_sha(overlay), _file_sha(proof_path)) != (
        packet["overlay_sha256"],
        packet["appearance_proof_sha256"],
    ):
        raise ValueError("Retained team-season package checksum mismatch")
    proof = json.loads(proof_path.read_bytes())
    if (
        proof["season"] != season
        or proof["season_type"] != kind
        or proof["scope"] != "complete_team_appearance_lists"
        or any(side["team_id"] != team_id for side in proof["sides"])
        or len(proof["sides"]) != len(game_ids)
        or {side["game_id"] for side in proof["sides"]} != set(game_ids)
    ):
        raise ValueError("Proof does not cover the exact reviewed team-season population")

    work.mkdir(parents=True)
    data = work / "data"
    manifest_path = data / "metadata/generation_manifest.json"
    if base_data is None:
        downloaded = download_active_generation(data, env_file=None)
        manifest_path.write_text(json.dumps(downloaded.manifest, indent=2, sort_keys=True) + "\n")
    else:
        shutil.copytree(base_data, data, symlinks=True)
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    if (
        hashlib.sha256(manifest_raw).hexdigest() != packet["base_manifest_sha256"]
        or manifest["generation_id"] != packet["base_generation"]
    ):
        raise ValueError("Preparation base differs from the retained package")
    before = {
        item["path"]: {key: value for key, value in item.items() if key != "storage_generation"}
        for item in manifest["files"]
    }
    games, schedule = (
        _final_team_games(data, before, f"raw/{family}/{suffix}.csv", team_id, season, kind)
        for family in ("games", "schedule")
    )
    if (
        games != schedule
        or games.keys() != set(game_ids)
        or any(side["game_date"] != games[side["game_id"]][0] for side in proof["sides"])
    ):
        raise ValueError("Package omits or conflicts with a finalized team-season game")
    base_ready = perf_counter()
    staged = compose_overlays(
        [(overlay, packet["overlay_sha256"])],
        data,
        work / "composed",
        base_generation=packet["base_generation"],
        base_manifest_sha256=packet["base_manifest_sha256"],
        candidate_sha=subprocess.check_output(
            ["git", "-C", str(code_root), "rev-parse", "HEAD"], text=True
        ).strip(),
    )
    for entry in staged["overlay_files"]:
        relative = Path(entry["path"])
        target = data / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(work / "composed" / relative, target)
    relative_proof = f"raw/team_game_appearances/{proof_path.name}"
    target = data / relative_proof
    target.parent.mkdir(parents=True, exist_ok=True)
    if relative_proof in before:
        if _file_sha(target) != before[relative_proof]["sha256"]:
            raise ValueError("Retained team-season proof differs from the immutable base")
        previous = json.loads(target.read_bytes())
        combined = _append_appearance_scope(previous, proof)
        target.write_text(json.dumps(combined, indent=2) + "\n")
    elif target.exists():
        raise ValueError("Unmanifested proof would replace accepted season authority")
    else:
        shutil.copyfile(proof_path, target)
    composed_at = perf_counter()

    result = publish_local_generation(generation, source_dir=data, data_root=work / "validation")
    new_manifest = (
        work / "validation/generations" / generation / "metadata/generation_manifest.json"
    )
    after = {item["path"]: item for item in json.loads(new_manifest.read_bytes())["files"]}
    changes = {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
    allowed = {entry["path"] for entry in staged["overlay_files"]} | {relative_proof}
    if changes != allowed or before.keys() - after.keys():
        raise ValueError("Prepared generation differs outside the qualified overlay and proof")
    metrics = {
        "base_seconds": base_ready - started,
        "compose_seconds": composed_at - base_ready,
        "full_validation_seconds": perf_counter() - composed_at,
        "base_files": len(before),
        "base_bytes": sum(item["size_bytes"] for item in before.values()),
        "changed_paths": sorted(changes),
        "changed_object_bytes": sum(after[path]["size_bytes"] for path in changes),
        "new_objects": len(after.keys() - before.keys()),
        "manifest_bytes": new_manifest.stat().st_size,
        "qualified_side_count": len(proof["sides"]),
        "production_writes": 0,
    }
    (work / "local-validation.json").write_text(json.dumps(asdict(result), indent=2) + "\n")
    (work / "preparation-metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--generation-id", required=True)
    parser.add_argument("--prepare", action="store_true", required=True)
    parser.add_argument(
        "--base-data", type=Path, help="Independently restored base for a local run"
    )
    args = parser.parse_args()
    sys.path[:0] = [str(args.code_root / "src"), str(args.code_root)]
    prepare(args.artifact_dir, args.code_root, args.work_dir, args.generation_id, args.base_data)


if __name__ == "__main__":
    main()
