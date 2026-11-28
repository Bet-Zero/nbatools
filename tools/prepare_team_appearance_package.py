"""Prepare retained team-season appearance proofs against one immutable base.

Schema 1 keeps the single-team package and its filenames. Schema 2 declares
``team_scopes`` with the same season, type, team ID, game IDs and proof SHA256
per scope; each proof is named ``<season>_<type>-<team_id>.json`` (use
``regular_season`` or ``playoffs``). ``overlays`` maps ZIP filenames to SHA256s.
The existing publication workflow still owns protected approval.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
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


def _final_team_games(data, before, relative, team_ids, season, kind):
    source = data / relative
    if _file_sha(source) != before[relative]["sha256"]:
        raise ValueError("Team-season denominator differs from the immutable base")
    teams = {str(team_id): {} for team_id in team_ids}
    with source.open(newline="", encoding="utf-8") as rows:
        for row in csv.DictReader(rows):
            selected = teams.keys() & {
                row["team_a_id"],
                row["team_b_id"],
                row["home_team_id"],
                row["away_team_id"],
            }
            if not selected:
                continue
            home, away = int(row["home_team_id"]), int(row["away_team_id"])
            game = int(row["game_id"])
            if (
                not selected <= {str(home), str(away)}
                or row["status"].casefold() != "final"
                or row["season"] != season
                or row["season_type"] != kind
                or home == away
                or any(game in teams[team_id] for team_id in selected)
            ):
                raise ValueError("Team-season denominator contains unfinished or conflicting games")
            for team_id in selected:
                teams[team_id][game] = (row["game_date"], home, away)
    return {int(team_id): games for team_id, games in teams.items()}


def _package_inputs(artifact_dir, generation):
    from tools.availability_overlay import _unique_object

    packet_path = artifact_dir / "package.json"
    if packet_path.is_symlink():
        raise ValueError("Unexpected team-season package inputs")
    packet = json.loads(packet_path.read_bytes(), object_pairs_hook=_unique_object)
    version = packet.get("schema_version")
    if (
        generation != packet["generation_id"]
        or generation == packet["base_generation"]
        or type(version) is not int
        or version not in (1, 2)
    ):
        raise ValueError("Invalid team-season package scope")
    if version == 1:
        scopes = [packet]
        zip_names = {"qualified-overlay.zip": packet["overlay_sha256"]}
    else:
        scopes, zip_names = packet["team_scopes"], packet["overlays"]
        if not isinstance(scopes, list) or len(scopes) < 2 or not isinstance(zip_names, dict):
            raise ValueError("A grouped package requires multiple exact team-season scopes")
    if not zip_names or any(
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*\.zip", name) for name in zip_names
    ):
        raise ValueError("A team-season package requires pinned local overlay ZIP names")

    overlays = [(artifact_dir / name, digest) for name, digest in sorted(zip_names.items())]
    proofs = defaultdict(dict)
    retained = {packet_path, *(path for path, _ in overlays)}
    for spec in scopes:
        season, kind, team_id = spec["season"], spec["season_type"], spec["team_id"]
        game_ids = spec["game_ids"]
        if (
            not re.fullmatch(r"(?:19|20)\d{2}-\d{2}", season)
            or kind not in {"Regular Season", "Playoffs"}
            or type(team_id) is not int
            or team_id <= 0
            or not isinstance(game_ids, list)
            or not game_ids
            or any(type(game) is not int or game <= 0 for game in game_ids)
            or len(set(game_ids)) != len(game_ids)
            or team_id in proofs[season, kind]
        ):
            raise ValueError("Invalid or duplicate team-season package scope")
        suffix = f"{season}_{kind.lower().replace(' ', '_')}"
        proof_name = f"{suffix}.json" if version == 1 else f"{suffix}-{team_id}.json"
        path = artifact_dir / proof_name
        retained.add(path)
        proofs[season, kind][team_id] = (path, spec)
    if set(artifact_dir.iterdir()) != retained or any(p.is_symlink() for p in retained):
        raise ValueError("Unexpected team-season package inputs")
    if any(_file_sha(archive) != digest for archive, digest in overlays):
        raise ValueError("Retained team-season package checksum mismatch")

    qualified = {}
    for (season, kind), team_scopes in sorted(proofs.items()):
        qualified[season, kind] = {}
        for team_id, (path, spec) in sorted(team_scopes.items()):
            body = path.read_bytes()
            if hashlib.sha256(body).hexdigest() != spec["appearance_proof_sha256"]:
                raise ValueError("Retained team-season package checksum mismatch")
            proof = json.loads(body, object_pairs_hook=_unique_object)
            games = set(spec["game_ids"])
            if (
                proof["season"] != season
                or proof["season_type"] != kind
                or proof["scope"] != "complete_team_appearance_lists"
                or any(side["team_id"] != team_id for side in proof["sides"])
                or len(proof["sides"]) != len(games)
                or {side["game_id"] for side in proof["sides"]} != games
                or version == 2
                and proof.get("schema_version") != 1
            ):
                raise ValueError("Proof does not cover the exact reviewed team-season population")
            qualified[season, kind][team_id] = (games, body, proof)
    return packet, overlays, qualified


def _verify_denominators(data, before, scopes):
    for (season, kind), team_scopes in scopes.items():
        suffix = f"{season}_{kind.lower().replace(' ', '_')}"
        games, schedule = (
            _final_team_games(data, before, f"raw/{family}/{suffix}.csv", team_scopes, season, kind)
            for family in ("games", "schedule")
        )
        if games != schedule or any(
            games[team_id].keys() != game_ids
            or any(
                side["game_date"] != games[team_id][side["game_id"]][0] for side in proof["sides"]
            )
            for team_id, (game_ids, _, proof) in team_scopes.items()
        ):
            raise ValueError("Package omits or conflicts with a finalized team-season game")


def _verify_grouped_overlay(staged, scopes):
    allowed = {}
    for (season, kind), team_scopes in scopes.items():
        suffix = f"{season}_{kind.lower().replace(' ', '_')}"
        games = set().union(*(game_ids for game_ids, _, _ in team_scopes.values()))
        prefix = f"raw/player_game_availability/{suffix}"
        allowed[prefix + ".csv"] = games
        allowed[prefix + ".imports.json"] = games
    changed_tables = staged["append_only"] | staged["manifest_absent_creations"]
    for path, change in changed_tables.items():
        if path not in allowed or any(
            int(game) not in allowed[path] for game in change["added_game_ids"]
        ):
            raise ValueError("Grouped overlay adds observations outside the declared games")
    if any(
        not item["path"].startswith("raw/player_game_availability_sources/")
        for item in staged["overlay_files"]
        if item["path"] not in changed_tables
    ):
        raise ValueError("Grouped overlay includes an unrelated source family")


def _install_proofs(data, before, scopes):
    paths = set()
    for (season, kind), team_scopes in scopes.items():
        suffix = f"{season}_{kind.lower().replace(' ', '_')}"
        relative = f"raw/team_game_appearances/{suffix}.json"
        target = data / relative
        if any(path.is_symlink() for path in (target, target.parent, target.parent.parent)):
            raise ValueError("Symlink in team-season proof destination")
        target.parent.mkdir(parents=True, exist_ok=True)
        combined = original_bytes = None
        if relative in before:
            if _file_sha(target) != before[relative]["sha256"]:
                raise ValueError("Retained team-season proof differs from the immutable base")
            combined = json.loads(target.read_bytes())
        elif target.exists():
            raise ValueError("Unmanifested proof would replace accepted season authority")
        for _, body, proof in team_scopes.values():
            if combined is None:
                combined, original_bytes = proof, body
            else:
                combined, original_bytes = _append_appearance_scope(combined, proof), None
        if original_bytes is None:
            target.write_text(json.dumps(combined, indent=2) + "\n")
        else:
            target.write_bytes(original_bytes)
        paths.add(relative)
    return paths


def prepare(artifact_dir: Path, code_root: Path, work: Path, generation: str, base_data=None):
    from nbatools.commands.pipeline.generation_publication import publish_local_generation
    from nbatools.commands.pipeline.generation_refresh import download_active_generation
    from tools.compose_participation_overlays import compose_overlays

    started = perf_counter()
    if base_data is not None and (
        base_data.resolve() == work.resolve() or base_data.resolve() in work.resolve().parents
    ):
        raise ValueError("Preparation workspace must be outside the restored base")
    if work.exists():
        raise ValueError("Invalid team-season preparation workspace")
    packet, overlays, scopes = _package_inputs(artifact_dir, generation)

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
    _verify_denominators(data, before, scopes)
    base_ready = perf_counter()
    staged = compose_overlays(
        overlays,
        data,
        work / "composed",
        base_generation=packet["base_generation"],
        base_manifest_sha256=packet["base_manifest_sha256"],
        candidate_sha=subprocess.check_output(
            ["git", "-C", str(code_root), "rev-parse", "HEAD"], text=True
        ).strip(),
    )
    if packet["schema_version"] == 2:
        _verify_grouped_overlay(staged, scopes)
    for entry in staged["overlay_files"]:
        relative = Path(entry["path"])
        target = data / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(work / "composed" / relative, target)
    proof_paths = _install_proofs(data, before, scopes)
    composed_at = perf_counter()

    result = publish_local_generation(generation, source_dir=data, data_root=work / "validation")
    new_manifest = (
        work / "validation/generations" / generation / "metadata/generation_manifest.json"
    )
    after = {item["path"]: item for item in json.loads(new_manifest.read_bytes())["files"]}
    changes = {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
    allowed = {entry["path"] for entry in staged["overlay_files"]} | proof_paths
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
        "qualified_side_count": sum(
            len(game_ids)
            for team_scopes in scopes.values()
            for game_ids, _, _ in team_scopes.values()
        ),
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
