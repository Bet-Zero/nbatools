"""Write legacy completeness metadata and the authoritative validation receipt."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from nbatools.commands.validation_control import (
    DATASET_SPECS,
    build_slice_manifest,
    dataset_path,
    write_slice_manifest,
)


def raw_paths(season: str, season_type: str) -> list[Path]:
    return [
        dataset_path(Path("data"), spec, season, season_type)
        for spec in DATASET_SPECS
        if spec.required and spec.layer == "raw" and spec.applies(season_type)
    ]


def processed_paths(season: str, season_type: str) -> list[Path]:
    return [
        dataset_path(Path("data"), spec, season, season_type)
        for spec in DATASET_SPECS
        if spec.required and spec.layer == "processed" and spec.applies(season_type)
    ]


def _write_legacy_manifest(
    season: str,
    season_type: str,
    *,
    raw_complete: bool,
    processed_complete: bool,
    loaded_at: str,
) -> Path:
    metadata_dir = Path("data/metadata")
    metadata_dir.mkdir(parents=True, exist_ok=True)
    path = metadata_dir / "backfill_manifest.csv"
    new_row = pd.DataFrame(
        [
            {
                "season": season,
                "season_type": season_type,
                "raw_complete": int(raw_complete),
                "processed_complete": int(processed_complete),
                "loaded_at": loaded_at,
            }
        ]
    )
    if path.exists():
        existing = pd.read_csv(path)
        existing = existing[
            ~((existing["season"] == season) & (existing["season_type"] == season_type))
        ].copy()
        new_row = pd.concat([existing, new_row], ignore_index=True)
    new_row.sort_values(["season", "season_type"]).reset_index(drop=True).to_csv(path, index=False)
    return path


def run(season: str, season_type: str) -> None:
    generated_at = datetime.now().isoformat(timespec="seconds")
    document = build_slice_manifest(
        season,
        season_type,
        generated_at=generated_at,
    )
    receipt_path = write_slice_manifest(document)
    records = document["datasets"]
    raw_ok = all(
        record["validation"]["state"] in {"passed", "unavailable"}
        for record in records
        if record["layer"] == "raw"
    )
    processed_ok = all(
        record["validation"]["state"] in {"passed", "unavailable"}
        for record in records
        if record["layer"] == "processed"
    )
    legacy_path = _write_legacy_manifest(
        season,
        season_type,
        raw_complete=raw_ok,
        processed_complete=processed_ok,
        loaded_at=generated_at,
    )
    print(f"Updated {legacy_path}")
    print(f"Wrote validation receipt {receipt_path}")
    if document["validation_state"] != "passed":
        raise ValueError("Dataset validation failed: " + "; ".join(document["validation_errors"]))
