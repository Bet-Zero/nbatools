"""Prepare an offline, append-only participation overlay from retained originals.

No acquisition, snapshot manifest, R2 writer or production activation is provided.
The output still requires independent checking and protected publication approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from nbatools.commands.pipeline.pull_player_game_availability import validate_publication
from nbatools.commands.pipeline.structured_participation import ARCHIVE, stage_structured_game
from nbatools.data_source import data_generation_context, data_glob, data_path
from tools.availability_overlay import binding, preserve_cells, verify_append

SOURCES = "raw/player_game_availability_sources/"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("Duplicate JSON object key")
    return dict(pairs)


def _document(path):
    if path.is_symlink():
        raise ValueError("Retained input must not be a symlink")
    return json.loads(path.read_bytes(), object_pairs_hook=_unique)


def build_stage(
    request_path: Path, source_directory: Path, work: Path, output: Path, *, candidate_sha: str
) -> dict:
    """Qualify one requested season in work/data; export only its changed overlay."""
    request, provenance = _document(request_path), _document(source_directory / "sources.json")
    season, kind = request["season"], request["season_type"]
    if (
        request.get("schema_version") != 1
        or request.get("dataset") != "raw/player_game_availability"
        or not re.fullmatch(r"(?:19|20)\d{2}-\d{2}", season)
        or season[-2:] != str(int(season[:4]) + 1)[-2:]
        or kind not in {"Regular Season", "Playoffs"}
        or not re.fullmatch(r"[a-f0-9]{40}", candidate_sha)
    ):
        raise ValueError("Invalid collection request scope/candidate")
    requirements = request["requirements"]
    if not requirements or len({row["game_id"] for row in requirements}) != len(requirements):
        raise ValueError("Missing or duplicate requested games")
    revision = provenance["revision"]
    if provenance.get("repository") != "sportsdataverse/hoopR-nba-stats-raw" or not re.fullmatch(
        r"[a-f0-9]{40}", revision
    ):
        raise ValueError("Unrecognized retained archive identity")
    inputs = {
        "request": _sha(request_path.read_bytes()),
        "sources.json": _sha((source_directory / "sources.json").read_bytes()),
    }
    qualified = []
    expected_names = set()
    for requirement in requirements:
        gid = requirement["game_id"]
        if (
            not isinstance(gid, str)
            or not re.fullmatch(r"[0-9]{10}", gid)
            or int(gid) <= 0
            or any(
                type(requirement[field]) is not int or requirement[field] <= 0
                for field in ["team_id", "player_id"]
            )
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", requirement["game_date"])
        ):
            raise ValueError("Invalid requested game/player/team/date key")
        proposed = requirement["proposed_sources"]
        endpoints = {row["endpoint"] for row in proposed}
        summary = endpoints - {"boxscoretraditionalv3"}
        if (
            len(proposed) != 2
            or "boxscoretraditionalv3" not in endpoints
            or len(summary) != 1
            or not summary <= {"boxscoresummaryv2", "boxscoresummaryv3"}
        ):
            raise ValueError("Each game requires one traditional and one summary source")
        paths, captures = {}, []
        for item in proposed:
            endpoint = item["endpoint"]
            filename = f"{endpoint}_{gid}.json"
            expected_names.add(filename)
            expected_url = (
                f"{ARCHIVE}/{revision}/nba_stats/json/{endpoint}/{int(season[:4]) + 1}/{gid}.json"
            )
            record = provenance["files"][filename]
            path = source_directory / "sources" / filename
            if path.is_symlink() or path.stat().st_size > 2_000_000:
                raise ValueError("Invalid retained original file")
            raw = path.read_bytes()
            blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
            if (
                item["revision"] != revision
                or item["url"] != expected_url
                or record["url"] != expected_url
                or _sha(raw) != record["sha256"]
                or len(raw) != record["size_bytes"]
                or blob != record["git_blob_sha"]
            ):
                raise ValueError("Retained original bytes/provenance differ from request")
            inputs[filename], paths[endpoint] = _sha(raw), path
            captured = datetime.fromisoformat(record["retrieved_at"])
            if captured.tzinfo is None:
                raise ValueError("Retained capture time requires timezone")
            captures.append(captured)
        qualified.append(
            (requirement, paths, int(next(iter(summary))[-1]), max(captures).isoformat())
        )
    if (
        set(provenance["files"]) != expected_names
        or {path.name for path in (source_directory / "sources").iterdir()} != expected_names
    ):
        raise ValueError("Retained source set differs from exact requested collection")
    if (
        work.exists()
        or output.exists()
        or work.resolve() in output.resolve().parents
        or output.resolve() in work.resolve().parents
        or work.resolve() == output.resolve()
    ):
        raise ValueError("Preparation requires separate new work/output directories")
    with data_generation_context() as generation:
        if generation != request["base_generation"]:
            raise ValueError("Configured generation differs from requested base")
        manifest_raw = data_path("data/metadata/generation_manifest.json").read_bytes()
        if _sha(manifest_raw) != request["base_manifest_sha256"]:
            raise ValueError("Base manifest differs from request")
        manifest = json.loads(manifest_raw, object_pairs_hook=_unique)
        if manifest["generation_id"] != generation:
            raise ValueError("Manifest generation differs from requested base")
        entries = {item["path"]: item for item in manifest["files"]}
        if len(entries) != len(manifest["files"]):
            raise ValueError("Duplicate manifest paths")
        root, baseline = work / "data", {}

        def copy(relative, *, optional=False):
            if optional and relative not in entries:
                return
            item = entries[relative]
            raw = data_path("data/" + relative).read_bytes()
            if len(raw) != item["size_bytes"] or _sha(raw) != item["sha256"]:
                raise ValueError(f"Base snapshot bytes differ from manifest: {relative}")
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            baseline[relative] = raw

        safe = kind.lower().replace(" ", "_")
        suffix = f"{season}_{safe}.csv"
        csv = "raw/player_game_availability/" + suffix
        ledger = csv.removesuffix(".csv") + ".imports.json"
        for relative in [
            *(
                f"raw/{dataset}/{suffix}"
                for dataset in ["games", "team_game_stats", "player_game_stats"]
            ),
            "metadata/player_names.csv",
            csv,
            ledger,
        ]:
            copy(relative)
        previous = f"{int(season[:4]) - 1}-{season[2:4]}"
        for relative in [
            f"raw/player_game_stats/{previous}_{safe}.csv",
            f"raw/rosters/{previous}.csv",
            f"raw/rosters/{season}.csv",
        ]:
            copy(relative, optional=True)
        listed = {name for name in entries if name.startswith(SOURCES)}
        observed = {SOURCES + path.name for path in data_glob("data/" + SOURCES + "*")}
        if listed != observed or any(
            Path(name).name != name.removeprefix(SOURCES) for name in listed
        ):
            raise ValueError("Served retained source set differs from manifest")
        for relative in sorted(listed):
            copy(relative)
        existing = pd.read_csv(root / csv)
        game_ids = [row["game_id"] for row in requirements]
        if set(map(int, game_ids)) & set(pd.to_numeric(existing.game_id)):
            raise ValueError("Collection would replace existing qualified game evidence")
        added, targets = 0, []
        for requirement, paths, version, captured in qualified:
            rows = stage_structured_game(
                root,
                season=season,
                season_type=kind,
                game_id=int(requirement["game_id"]),
                traditional=paths["boxscoretraditionalv3"],
                summary=paths[f"boxscoresummaryv{version}"],
                summary_version=version,
                revision=revision,
                retrieved_at=captured,
            )
            target = rows.loc[
                rows.team_id.eq(requirement["team_id"])
                & rows.player_id.eq(requirement["player_id"])
            ]
            if (
                len(target) != 1
                or target.game_date.item() != requirement["game_date"]
                or target.participation_state.item() not in {"played", "did_not_play"}
            ):
                raise ValueError("Requested target lacks qualified exact-game participation")
            targets.append(
                {
                    **{
                        key: requirement[key]
                        for key in ["game_id", "game_date", "team_id", "player_id"]
                    },
                    "state": target.participation_state.item(),
                }
            )
            added += len(rows)
        append = {
            csv: binding(baseline[csv], game_ids, added_records=added),
            ledger: binding(baseline[ledger], game_ids, added_records=len(game_ids)),
        }
        (root / csv).write_bytes(
            preserve_cells(csv, baseline[csv], (root / csv).read_bytes(), append[csv])
        )
        verify_append(ledger, baseline[ledger], (root / ledger).read_bytes(), append[ledger])
        validate_publication(root)
        output.mkdir(parents=True)
        files = []
        for directory in ["raw/player_game_availability", SOURCES]:
            for path in sorted((root / directory).iterdir()):
                relative, raw = path.relative_to(root).as_posix(), path.read_bytes()
                if relative in baseline and raw == baseline[relative]:
                    continue
                if relative in baseline and relative not in append:
                    raise ValueError("Preparation changed existing source authority")
                destination = output / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
                files.append(dict(path=relative, size_bytes=len(raw), sha256=_sha(raw)))
        result = dict(
            candidate_sha=candidate_sha,
            base_generation=generation,
            base_manifest_sha256=_sha(manifest_raw),
            publication_state="staged_only_no_writes",
            source_kind="retained_originals_only_no_acquisition",
            archive_revision=revision,
            input_hashes=inputs,
            base_file_hashes={path: _sha(raw) for path, raw in baseline.items()},
            append_only=append,
            qualified_targets=targets,
            overlay_files=files,
        )
        (output / "validation.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["request-path", "source-directory", "work", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--candidate-sha", required=True)
    build_stage(**vars(parser.parse_args()))


if __name__ == "__main__":
    main()
