"""Report which seasons and datasets the configured data generation serves.

Read-only. Answers "what data does the app actually have?" from the
generation itself rather than from documentation: the immutable generation
manifest (every published file), each season slice's validation manifest
(per-dataset state and row counts as the pipeline recorded them), and an
independent count of final games read straight from the ``games`` CSVs.

Run it against the served R2 generation through the R2 validation workflow
(``tests/test_served_data_coverage_real_data.py`` prints this report), or
locally with ``python -m nbatools.commands.ops.served_coverage``.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from nbatools.commands.freshness import manifest_entry
from nbatools.commands.validation_control import inspect_slice_manifest
from nbatools.data_source import (
    current_data_generation,
    data_exists,
    data_glob,
    data_read_csv,
    data_read_text,
)

GENERATION_MANIFEST_PATH = Path("data/metadata/generation_manifest.json")
SEASON_TYPES = ("Regular Season", "Playoffs")
_SLICE_FILE = re.compile(r"^(?P<season>\d{4}-\d{2})_(?P<type>regular_season|playoffs)\.csv$")
_SEASON_FILE = re.compile(r"^(?P<season>\d{4}-\d{2})\.csv$")
_TYPE_LABELS = {"regular_season": "Regular Season", "playoffs": "Playoffs"}


@dataclass
class SliceCoverage:
    """Evidence for one season / season-type slice."""

    season: str
    season_type: str
    validation_state: str = "unknown"
    # Legacy slices predate versioned receipts; their backfill-manifest flags.
    legacy_complete: bool | None = None
    final_games: int | None = None
    first_game_date: str | None = None
    last_game_date: str | None = None
    datasets: dict[str, dict[str, Any]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "season": self.season,
            "season_type": self.season_type,
            "validation_state": self.validation_state,
            "legacy_complete": self.legacy_complete,
            "final_games": self.final_games,
            "first_game_date": self.first_game_date,
            "last_game_date": self.last_game_date,
            "datasets": self.datasets,
            "errors": self.errors,
        }


@dataclass
class ServedCoverage:
    """What one data generation serves, by dataset and by season slice."""

    generation: str
    manifest_file_count: int | None
    manifest_total_mb: float | None
    dataset_seasons: dict[str, list[str]]
    reference_files: list[str]
    slices: list[SliceCoverage]

    def slice(self, season: str, season_type: str) -> SliceCoverage | None:
        for item in self.slices:
            if item.season == season and item.season_type == season_type:
                return item
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "manifest_file_count": self.manifest_file_count,
            "manifest_total_mb": self.manifest_total_mb,
            "dataset_seasons": self.dataset_seasons,
            "reference_files": self.reference_files,
            "slices": [item.to_dict() for item in self.slices],
        }


def _published_paths() -> tuple[list[str], int | None, float | None]:
    """Return every published data path, with the manifest's file count and size."""
    if data_exists(GENERATION_MANIFEST_PATH):
        document = json.loads(data_read_text(GENERATION_MANIFEST_PATH))
        entries = document.get("files") or []
        files = [str(item.get("path", "")) for item in entries]
        total_bytes = sum(int(item.get("size_bytes") or 0) for item in entries)
        return files, len(files), round(total_bytes / 1_000_000, 1)
    # Legacy or local layouts without a generation manifest: list the tree.
    paths = [p.relative_to("data").as_posix() for p in data_glob("**/*.csv")]
    return paths, None, None


def _dataset_seasons(paths: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    """Group ``<layer>/<dataset>/<season>_<type>.csv`` files into season labels."""
    seasons: dict[str, set[str]] = defaultdict(set)
    reference: list[str] = []
    for path in paths:
        parts = Path(path).parts
        if len(parts) != 3 or parts[0] not in {"raw", "processed"}:
            continue
        dataset = f"{parts[0]}/{parts[1]}"
        name = parts[2]
        if match := _SLICE_FILE.match(name):
            seasons[dataset].add(f"{match['season']} {_TYPE_LABELS[match['type']]}")
        elif match := _SEASON_FILE.match(name):
            seasons[dataset].add(match["season"])
        elif name.endswith(".csv"):
            reference.append(path)
    return {key: sorted(value) for key, value in sorted(seasons.items())}, sorted(reference)


def _slice_keys(dataset_seasons: dict[str, list[str]]) -> list[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for labels in dataset_seasons.values():
        for label in labels:
            season, _, season_type = label.partition(" ")
            if season_type in SEASON_TYPES:
                keys.add((season, season_type))
    return sorted(keys, key=lambda key: (key[0], SEASON_TYPES.index(key[1])))


def _collect_slice(season: str, season_type: str) -> SliceCoverage:
    item = SliceCoverage(season=season, season_type=season_type)
    inspection = inspect_slice_manifest(season, season_type, verify_files=False)
    item.validation_state = str(inspection.get("validation_state", "unknown"))
    item.errors = [str(error) for error in inspection.get("errors") or []]
    if inspection.get("manifest") is None and item.validation_state == "unknown":
        legacy = manifest_entry(season, season_type)
        if legacy is not None:
            item.validation_state = str(legacy.get("validation_state"))
            item.legacy_complete = bool(legacy.get("raw_complete")) and bool(
                legacy.get("processed_complete")
            )
            item.errors = []
    for record in (inspection.get("manifest") or {}).get("datasets") or []:
        if not isinstance(record, dict) or not record.get("name"):
            continue
        validation = record.get("validation") or {}
        coverage = record.get("coverage") or {}
        item.datasets[str(record["name"])] = {
            "required": bool(record.get("required")),
            "state": validation.get("state") if isinstance(validation, dict) else None,
            "coverage": coverage.get("state") if isinstance(coverage, dict) else None,
            "row_count": record.get("row_count"),
        }

    safe = season_type.lower().replace(" ", "_")
    games_path = Path(f"data/raw/games/{season}_{safe}.csv")
    if data_exists(games_path):
        games = data_read_csv(games_path, dtype={"game_id": str})
        final = games
        if "is_final" in games.columns:
            flags = games["is_final"].astype(str).str.strip().str.lower()
            final = games.loc[flags.isin({"1", "true", "1.0"})]
        item.final_games = int(final["game_id"].nunique())
        dates = pd.to_datetime(final.get("game_date"), errors="coerce").dropna()
        if not dates.empty:
            item.first_game_date = str(dates.min().date())
            item.last_game_date = str(dates.max().date())
    return item


def collect_served_coverage() -> ServedCoverage:
    """Collect the coverage evidence for the configured generation."""
    paths, manifest_count, manifest_mb = _published_paths()
    dataset_seasons, reference = _dataset_seasons(paths)
    slices = [_collect_slice(season, kind) for season, kind in _slice_keys(dataset_seasons)]
    return ServedCoverage(
        generation=current_data_generation(),
        manifest_file_count=manifest_count,
        manifest_total_mb=manifest_mb,
        dataset_seasons=dataset_seasons,
        reference_files=reference,
        slices=slices,
    )


def _season_runs(labels: list[str]) -> str:
    """Compress season labels into contiguous ranges, e.g. 1996-97..2025-26."""
    by_type: dict[str, list[int]] = defaultdict(list)
    for label in labels:
        season, _, season_type = label.partition(" ")
        by_type[season_type or "season"].append(int(season[:4]))
    parts = []
    for season_type, years in sorted(by_type.items()):
        years = sorted(set(years))
        runs: list[tuple[int, int]] = []
        for year in years:
            if runs and year == runs[-1][1] + 1:
                runs[-1] = (runs[-1][0], year)
            else:
                runs.append((year, year))
        text = ", ".join(_label(a) if a == b else f"{_label(a)}..{_label(b)}" for a, b in runs)
        parts.append(f"{season_type}: {text}")
    return "; ".join(parts)


def _label(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"


def format_report(coverage: ServedCoverage) -> str:
    lines = [
        f"Generation: {coverage.generation}",
        f"Files in generation manifest: {coverage.manifest_file_count}"
        + (f" ({coverage.manifest_total_mb} MB)" if coverage.manifest_total_mb is not None else ""),
        "",
        "Datasets by season (from the published file inventory):",
    ]
    for dataset, labels in coverage.dataset_seasons.items():
        lines.append(f"  {dataset}: {len(labels)} slice(s); {_season_runs(labels)}")
    if coverage.reference_files:
        lines.append("Reference files: " + ", ".join(coverage.reference_files))
    states: dict[str, int] = defaultdict(int)
    for item in coverage.slices:
        states[item.validation_state] += 1
    lines += [
        "",
        "Slice validation states: "
        + ", ".join(f"{state} {count}" for state, count in sorted(states.items())),
    ]
    lines += [
        "",
        "Slices (validation from slice manifest; games counted from raw/games):",
        "  season   type            validation        final_games  first_date  last_date"
        "   optional datasets present",
    ]
    for item in coverage.slices:
        optional = sorted(
            name
            for name, record in item.datasets.items()
            if not record["required"] and (record.get("row_count") or 0) > 0
        )
        lines.append(
            f"  {item.season}  {item.season_type:<15} {item.validation_state:<17} "
            f"{item.final_games if item.final_games is not None else '-':>11}  "
            f"{item.first_game_date or '-':<10}  {item.last_game_date or '-':<10}  "
            + (", ".join(optional) or "-")
        )
        for error in item.errors[:3]:
            lines.append(f"      error: {error}")
    return "\n".join(lines)


def main() -> None:
    print(format_report(collect_served_coverage()))


if __name__ == "__main__":
    main()
