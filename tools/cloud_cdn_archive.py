"""Recover one real CDN PBP game from a pinned public archive into new staging.

No direct NBA network bypass, NBA Stats relabeling, production write or credential.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import tarfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

from nbatools.commands.pipeline.generation_publication import (
    GENERATION_MANIFEST_PATH,
    _build_staged_generation,
    validate_staged_generation,
)
from nbatools.commands.pipeline.pull_play_by_play_events import normalize_play_by_play_events
from nbatools.commands.pipeline.validate_raw import validate_play_by_play_events_df
from nbatools.commands.source_invariants import (
    apply_play_by_play_trust_decisions,
    expected_game_terminal_states,
)
from nbatools.commands.validation_control import (
    DATASET_SPECS,
    build_slice_manifest,
    validate_manifest_document,
    write_slice_manifest,
)

REVISION = "e829d4678be1e075f99e5d41a1c5f97089be446b"
ARCHIVE_URL = (
    f"https://raw.githubusercontent.com/shufinskiy/nba_data/{REVISION}/datasets/cdnnba_2025.tar.xz"
)
ARCHIVE_SHA256 = "a5d1bed30778430816b755676649cb2e3690ea62df5d96f4d9d6e9a8b8839339"
CORE_SHA256 = "76aad9d054c5edc6d699e26a72f89073b55908a247ee9c72dee414e2f70c99f1"
SUFFIX = "2025-26_regular_season.csv"


def _download(url: str, limit: int) -> bytes:
    payload = bytearray()
    with requests.get(url, timeout=30, stream=True) as response:
        response.raise_for_status()
        for chunk in response.iter_content(65536):
            payload.extend(chunk)
            if len(payload) > limit:
                raise ValueError("Public source exceeds bounded download limit")
    return bytes(payload)


class _CapturedLines:
    """Retain original CSV text for selected records, including quoted newlines."""

    def __init__(self, stream):
        self.stream = stream
        self.parts = []

    def __iter__(self):
        return self

    def __next__(self):
        line = self.stream.readline()
        if not line:
            raise StopIteration
        self.parts.append(line)
        return line


def selected_source(archive_bytes: bytes) -> bytes:
    if hashlib.sha256(archive_bytes).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Pinned source archive checksum mismatch")
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:xz") as archive:
        member = archive.next()
        if (
            member is None
            or not member.isfile()
            or member.name != "cdnnba_2025.csv"
            or member.size > 250_000_000
        ):
            raise ValueError("Unexpected bounded CSV archive inventory")
        stream = io.TextIOWrapper(archive.extractfile(member), encoding="utf-8", newline="")
        capture = _CapturedLines(stream)
        reader = csv.DictReader(capture)
        if not reader.fieldnames or "gameId" not in reader.fieldnames:
            raise ValueError("Source CSV has no NBA game identity")
        parts = ["".join(capture.parts)]
        capture.parts = []
        rows = 0
        for row in reader:
            if row["gameId"] == "22500003":
                parts.append("".join(capture.parts))
                rows += 1
                if rows > 1000:
                    raise ValueError("Selected source exceeds one-game bound")
            capture.parts = []
        if rows != 605 or archive.next() is not None:
            raise ValueError("Pinned source game/archive inventory changed")
    return "".join(parts).encode("utf-8")


def prepare(destination: Path) -> dict:
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    sources = destination / "data/raw/play_by_play_events_sources"
    sources.mkdir(parents=True)
    original = selected_source(_download(ARCHIVE_URL, 20_000_000))
    (sources / "cdn-game-original.csv").write_bytes(original)
    license_url = f"https://raw.githubusercontent.com/shufinskiy/nba_data/{REVISION}/LICENSE"
    (sources / "LICENSE").write_bytes(_download(license_url, 100_000))
    core_bundle = Path(__file__).resolve().parents[1] / (
        "working/nba-tools-completion-program/cloud-operations/core-archive-staging.zip"
    )
    payload = core_bundle.read_bytes()
    if hashlib.sha256(payload).hexdigest() != CORE_SHA256:
        raise ValueError("Reviewed core identity/final-score context checksum mismatch")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        # Exact reviewed archive hash, fixed files, no general ZIP extraction.
        for dataset in ("games", "team_game_stats", "player_game_stats"):
            name = f"data/raw/{dataset}/{SUFFIX}"
            target = destination / name
            target.parent.mkdir(parents=True)
            target.write_bytes(archive.read(name))
    team = pd.read_csv(destination / "data/raw/team_game_stats" / SUFFIX)
    frame = pd.read_csv(io.BytesIO(original), dtype=str, keep_default_na=False)
    if not frame.gameId.eq("22500003").all():
        raise ValueError("Unexpected NBA game identity")
    frame["actionNumber"] = pd.to_numeric(frame.actionNumber, errors="raise")
    out = normalize_play_by_play_events(
        frame.sort_values("actionNumber"),
        season="2025-26",
        season_type="Regular Season",
        source="cdn.nba.com.liveData.playbyplay",
        source_schema_version="cdn_live_pbp.v1",
    )
    out, decisions = apply_play_by_play_trust_decisions(out, expected_game_terminal_states(team))
    if any(decisions.values()) or not out.pbp_source_trusted.eq(1).all():
        raise ValueError(f"Whole-game completeness failed: {decisions}")
    validate_play_by_play_events_df(out)
    if tuple(out.iloc[-1][["score_home", "score_away"]]) != (119, 111):
        raise ValueError("CDN final score/home-away mismatch")
    path = destination / "data/raw/play_by_play_events" / SUFFIX
    path.parent.mkdir()
    out.to_csv(path, index=False)
    receipt = {
        "schema_version": 1,
        "state": "qualified archival CDN one-game development slice",
        "collected_at": datetime.now(UTC).isoformat(),
        "mirror": "shufinskiy/nba_data",
        "mirror_revision": REVISION,
        "archive_url": ARCHIVE_URL,
        "archive_sha256": ARCHIVE_SHA256,
        "core_context_sha256": CORE_SHA256,
        "attribution": "shufinskiy/nba_data, Apache-2.0; original NBA CDN liveData playbyplay",
        "source_representation": (
            "exact original header and 605 CSV records selected from authenticated pinned archive; "
            "not original HTTP JSON bytes"
        ),
        "game_id": "0022500003",
        "rows": len(out),
        "final_home_points": 119,
        "final_away_points": 111,
        "final_period": int(out.period.max()),
        "canonical_source": "cdn.nba.com.liveData.playbyplay",
        "schema": "cdn_live_pbp.v1",
        "event_identity": "original actionNumber preserved",
        "timeline": "original orderNumber preserved as source_order_number; no renumbering",
        "r2_writes": 0,
        "production_publication": "not requested or performed",
        "limitations": [
            "one archived game, not fresh/live source acceptance",
            "no NBA Stats PBP equivalence claim",
            "no period/on-off data or clutch-feature acceptance",
        ],
    }
    source_receipt = receipt | {
        "original_selected_csv_sha256": hashlib.sha256(original).hexdigest(),
        "canonical_csv_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    (sources / "source-receipt.json").write_text(json.dumps(source_receipt, indent=2) + "\n")
    generation = "cloud-cdn-archival-development-v1"
    # Deliberately scoped development receipt. This does NOT replace the full
    # default DATASET_SPECS receipt required by season refresh/publication.
    names = {"games", "team_game_stats", "player_game_stats", "play_by_play_events"}
    specs = tuple(spec for spec in DATASET_SPECS if spec.name in names)
    document = build_slice_manifest(
        "2025-26",
        "Regular Season",
        data_root=destination / "data",
        specs=specs,
        generation_id=generation,
    )
    errors = validate_manifest_document(document, specs=specs)
    if errors or document["validation_state"] != "passed":
        raise ValueError(f"Scoped development validation failed: {document['validation_errors']}")
    write_slice_manifest(document, data_root=destination / "data")
    candidate = destination / "candidate"
    _build_staged_generation(destination / "data", candidate, generation)
    manifest = validate_staged_generation(candidate, generation)
    receipt["immutable_candidate"] = {
        "generation": generation,
        "files": len(manifest["files"]),
        "kind": "isolated development subset, not a full R2 publication package",
        "validation_scope": sorted(names),
        "manifest_sha256": hashlib.sha256(
            (candidate / GENERATION_MANIFEST_PATH).read_bytes()
        ).hexdigest(),
    }
    receipt["files"] = {
        str(p.relative_to(destination)): {
            "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        }
        for p in sorted(destination.rglob("*"))
        if p.is_file()
    }
    (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output), indent=2))


if __name__ == "__main__":
    main()
