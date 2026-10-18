"""Combine exact reviewed availability artifacts locally; never publish or replace a base.

Source artifact acquisition uses r2_publication's existing producer/run/archive
checks. The output is a new producer artifact, not a directly publishable package:
its successful runner receipt and complete file inventory must be reviewed and
pinned separately before registration in the protected publication workflow.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path, PurePosixPath


def verify_source(root: Path, inventory: dict) -> None:
    """Authenticate all input files, including canonical evidence not published."""
    expected = {}
    for item in inventory["files"]:
        relative = PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts or item["path"] in expected:
            raise ValueError("Unsafe or duplicate reviewed source path")
        expected[item["path"]] = item
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if root.is_symlink() or actual != set(expected) or any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("Source file inventory differs")
    for name, item in expected.items():
        raw = (root / name).read_bytes()
        if len(raw) != item["size_bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise ValueError(f"Source checksum differs: {name}")


def combine(sources: list[tuple[Path, dict]], destination: Path, *, candidate_sha: str) -> dict:
    """Preserve every source cell/receipt; reject overlapping games and file conflicts."""
    if destination.exists():
        raise ValueError("Combined output requires a new directory")
    bases = {inventory["base_generation"] for _, inventory in sources}
    if not sources or len(bases) != 1:
        raise ValueError("Sources must share one reviewed base")
    for root, inventory in sources:
        verify_source(root, inventory)
    files: dict[str, bytes] = {}
    tables: dict[str, tuple[list[str], list[dict]]] = {}
    imports: dict[str, dict] = {}
    for root, inventory in sources:
        for item in inventory["files"]:
            name = item["path"]
            if not name.startswith("raw/"):
                continue
            path = root / name
            if name.startswith("raw/player_game_availability/") and name.endswith(".csv"):
                with path.open(newline="", encoding="utf-8") as stream:
                    reader = csv.DictReader(stream)
                    header, rows = reader.fieldnames, list(reader)
                if not header or not rows or any(None in row for row in rows):
                    raise ValueError("Invalid source CSV")
                previous_header, previous_rows = tables.setdefault(name, (header, []))
                if header != previous_header:
                    raise ValueError("Availability schemas differ")
                old_games = {int(row["game_id"]) for row in previous_rows}
                if old_games & {int(row["game_id"]) for row in rows}:
                    raise ValueError("Overlapping source games require separate review")
                previous_rows.extend(rows)
            elif name.startswith("raw/player_game_availability/") and name.endswith(
                ".imports.json"
            ):
                incoming = json.loads(path.read_text())
                existing = imports.setdefault(name, {})
                if existing.keys() & incoming.keys():
                    raise ValueError("Overlapping import lineage")
                existing.update(incoming)
            elif name.startswith("raw/player_game_availability_sources/"):
                raw = path.read_bytes()
                if name in files and files[name] != raw:
                    raise ValueError("Conflicting retained source bytes")
                files[name] = raw
            else:
                raise ValueError("Unexpected raw dataset in source artifact")
    expected_imports = {name.removesuffix(".csv") + ".imports.json" for name in tables}
    if set(imports) != expected_imports:
        raise ValueError("Missing or extraneous import lineage file")
    for name, (_, rows) in tables.items():
        keys = [(int(row["game_id"]), int(row["player_id"])) for row in rows]
        receipts = imports[name.removesuffix(".csv") + ".imports.json"]
        if len(keys) != len(set(keys)) or {str(k[0]) for k in keys} != set(receipts):
            raise ValueError("Availability row keys do not match import lineage")
    destination.mkdir(parents=True)
    for name, raw in sorted(files.items()):
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    for name, (header, rows) in sorted(tables.items()):
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=header, lineterminator="\n")
            writer.writeheader()
            writer.writerows(
                sorted(
                    rows, key=lambda r: (int(r["game_id"]), int(r["team_id"]), int(r["player_id"]))
                )
            )
    for name, receipts in sorted(imports.items()):
        (destination / name).write_text(json.dumps(receipts, sort_keys=True) + "\n")
    evidence = {
        "candidate_sha": candidate_sha,
        "base_generation": next(iter(bases)),
        "publication_state": "staged_only",
        "row_counts": {name: len(rows) for name, (_, rows) in sorted(tables.items())},
        "sources": [
            {
                key: inventory[key]
                for key in (
                    "reviewed_sha",
                    "request_sha",
                    "run_id",
                    "artifact_id",
                    "artifact_zip_sha256",
                )
            }
            for _, inventory in sources
        ],
    }
    (destination / "validation.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    )
    return evidence
