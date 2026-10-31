"""Offline six-game overlay from retained sources and one pinned served snapshot.

This producer has no acquisition, R2 writer or publication operation. Its compact
output is only an input to the existing reviewed/protected publication process.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from nbatools.commands.pipeline.pull_player_game_availability import backfill, validate_publication
from nbatools.commands.pipeline.structured_participation import stage_structured_game
from nbatools.data_source import data_exists, data_glob, data_path
from tools.availability_overlay import binding, preserve_cells, verify_append

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "working/nba-tools-completion-program/source-evidence"
BASE = "availability-opening-s4-v1-20261017"
BASE_MANIFEST = "5497832bca4567734386e26367798c60fd6e3685a0c93cd561227a5e5d833f52"
GENERATION = "availability-k08-retained-v1-20261031"
HISTORICAL = [("1997-98", 29700002), ("2004-05", 20400001), ("2014-15", 21400001)]
PDF_GAMES = ["0022500019", "0022500113", "0022500122"]
CSV = "raw/player_game_availability/2025-26_regular_season.csv"
LEDGER = CSV.removesuffix(".csv") + ".imports.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build_overlay(work: Path, output: Path, *, candidate_sha: str) -> dict:
    if os.environ.get("NBATOOLS_DATA_GENERATION") != BASE:
        raise ValueError("Retained-source preparation requires the pinned base generation")
    if work.exists() or output.exists():
        raise ValueError("Preparation requires new work and output directories")
    root = work / "data"
    root.mkdir(parents=True)
    baseline = {}

    def copy(relative):
        raw = data_path("data/" + relative).read_bytes()
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        baseline[relative] = raw

    for season in [s for s, _ in HISTORICAL] + ["2025-26"]:
        for kind in ("games", "team_game_stats", "player_game_stats"):
            copy(f"raw/{kind}/{season}_regular_season.csv")
    for relative in [
        CSV,
        LEDGER,
        "raw/player_game_stats/2024-25_regular_season.csv",
        "raw/rosters/2024-25.csv",
        "raw/rosters/2025-26.csv",
    ]:
        copy(relative)
    # Existing source authority is needed for validation, never replaced.
    for path in data_glob("data/raw/player_game_availability_sources/*"):
        copy("raw/player_game_availability_sources/" + path.name)
    for season, _ in HISTORICAL:
        if data_exists(f"data/raw/player_game_availability/{season}_regular_season.csv"):
            raise ValueError("Historical availability already exists; review the changed base")

    provenance = json.loads((EVIDENCE / "k08-structured/sources.json").read_text())
    for season, game in HISTORICAL:
        paths = []
        for endpoint in ("boxscoretraditionalv3", "boxscoresummaryv2"):
            name = f"{endpoint}_{game:010d}.json"
            path = EVIDENCE / "k08-structured/sources" / name
            expected = provenance["files"][name]
            raw = path.read_bytes()
            if len(raw) != expected["size_bytes"] or sha(raw) != expected["sha256"]:
                raise ValueError("Retained original structured bytes differ")
            paths.append(path)
        captured = max(provenance["files"][p.name]["retrieved_at"] for p in paths)
        stage_structured_game(
            root,
            season=season,
            season_type="Regular Season",
            game_id=game,
            traditional=paths[0],
            summary=paths[1],
            summary_version=2,
            revision=provenance["revision"],
            retrieved_at=captured,
        )
    backfill(
        "2025-26",
        root=root,
        source="report",
        game_ids=[int(g) for g in PDF_GAMES],
        cached_reports=EVIDENCE
        / "k08-three-reports/acquired_data/raw/player_game_availability_sources",
    )
    append = {
        CSV: binding(baseline[CSV], PDF_GAMES, added_records=104),
        LEDGER: binding(baseline[LEDGER], PDF_GAMES, added_records=3),
    }
    (root / CSV).write_bytes(
        preserve_cells(CSV, baseline[CSV], (root / CSV).read_bytes(), append[CSV])
    )
    verify_append(LEDGER, baseline[LEDGER], (root / LEDGER).read_bytes(), append[LEDGER])
    validate_publication(root)
    output.mkdir(parents=True)
    files = []
    for directory in ("raw/player_game_availability", "raw/player_game_availability_sources"):
        for path in sorted((root / directory).iterdir()):
            relative = path.relative_to(root).as_posix()
            raw = path.read_bytes()
            if relative in baseline and raw == baseline[relative]:
                continue
            if relative in baseline and relative not in append:
                raise ValueError("Preparation would change an existing source file")
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            files.append(dict(path=relative, size_bytes=len(raw), sha256=sha(raw)))
    evidence = dict(
        candidate_sha=candidate_sha,
        base_generation=BASE,
        base_manifest_sha256=BASE_MANIFEST,
        publication_state="staged_only_no_writes",
        append_only=append,
        source_kind="retained_originals_only_no_acquisition",
        archive_revision=provenance["revision"],
        historical_games=[dict(season=s, game_id=f"{g:010d}") for s, g in HISTORICAL],
        pdf_game_ids=PDF_GAMES,
        overlay_files=files,
        source_note=(
            "Original retrieval timestamps and attributed archive revision retained; "
            "no freshness claim."
        ),
    )
    (output / "validation.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    return evidence
