"""Setup acceptance only: cloud acquisition and no-write generation preparation.

The small public NBA bundle is emitted to the job log for the authorized agent
to commit to a durable staging branch, without granting a runner write access.
No fixture, credential, or full production snapshot is included in that bundle.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import shutil
import zipfile
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.pipeline.generation_publication import (
    _build_staged_generation,
    _read_r2_pointer,
    _resolve_r2_target,
    validate_staged_generation,
)
from nbatools.commands.pipeline.generation_refresh import download_active_generation
from nbatools.commands.pipeline.pull_player_game_availability import (
    backfill,
    validate_publication,
)

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def _emit(document, capfd):
    with capfd.disabled():
        print("CLOUD_ACCEPTANCE_JSON " + json.dumps(document, sort_keys=True), flush=True)


def test_new_game_cloud_acquisition_and_candidate(tmp_path, capfd):
    client, bucket = _resolve_r2_target(client=None, bucket_name=None, env=None, env_file=None)
    before = _read_r2_pointer(client, bucket)
    assert before.generation_id == os.environ["NBATOOLS_DATA_GENERATION"]
    root = tmp_path / "data"
    downloaded = download_active_generation(root, client=client, bucket_name=bucket)
    assert downloaded.generation_id == before.generation_id
    season, kind, suffix = "2025-26", "Regular Season", "2025-26_regular_season.csv"
    games = pd.read_csv(root / "raw/games" / suffix)
    availability = root / "raw/player_game_availability" / suffix
    previous = pd.read_csv(availability)
    candidates = games[
        games.game_date.astype(str).eq("2025-10-22")
        & ~pd.to_numeric(games.game_id).isin(pd.to_numeric(previous.game_id))
        & games.is_final.astype(str).str.lower().isin(["true", "1"])
    ].sort_values("game_id")
    assert not candidates.empty, "No new qualified game available in fixed bounded date"
    game = candidates.iloc[0]
    game_id = int(game.game_id)
    original_sources = {p.name for p in (root / "raw/player_game_availability_sources").iterdir()}
    rows = backfill(season, kind, root=root, game_ids=[game_id], limit=1, source="report")
    new = rows[pd.to_numeric(rows.game_id).eq(game_id)]
    assert not new.empty
    validate_publication(root)

    # Availability's contract is raw observations; it has no processed owner.
    # The existing publisher derives the player-name index, authenticates every
    # retained raw/processed file and receipt, and validates the new observation.
    generation = "cloud-acceptance-" + os.environ["VALIDATION_SHA"][:12]
    stage = tmp_path / "candidate"
    _build_staged_generation(root, stage, generation)
    manifest = validate_staged_generation(stage, generation)
    assert len(manifest["files"]) >= downloaded.file_count
    assert _read_r2_pointer(client, bucket) == before

    bundle = tmp_path / "recovery-bundle"
    for label in ("games", "team_game_stats", "player_game_stats"):
        df = pd.read_csv(root / "raw" / label / suffix)
        scoped = df[pd.to_numeric(df.game_id).eq(game_id)]
        path = bundle / "data/raw" / label / suffix
        path.parent.mkdir(parents=True, exist_ok=True)
        scoped.to_csv(path, index=False)
    target = bundle / "data/raw/player_game_availability" / suffix
    target.parent.mkdir(parents=True)
    new.to_csv(target, index=False)
    imports = json.loads(availability.with_suffix(".imports.json").read_text())
    selected_imports = {k: v for k, v in imports.items() if int(k) == game_id}
    assert len(selected_imports) == 1
    target.with_suffix(".imports.json").write_text(json.dumps(selected_imports) + "\n")
    prior = pd.read_csv(root / "raw/player_game_stats/2024-25_regular_season.csv")
    prior[prior.player_id.isin(new.player_id)].to_csv(
        bundle / "data/raw/player_game_stats/2024-25_regular_season.csv", index=False
    )
    sources = bundle / "data/raw/player_game_availability_sources"
    sources.mkdir(parents=True)
    for path in (root / "raw/player_game_availability_sources").iterdir():
        if path.name not in original_sources:
            shutil.copy2(path, sources / path.name)
    validate_publication(bundle / "data")
    evidence = {
        "schema_version": 1,
        "source_revision": os.environ["VALIDATION_SHA"],
        "base_generation": before.generation_id,
        "download": asdict(downloaded) | {"manifest": "verified-by-existing-downloader"},
        "new_game_id": game_id,
        "game_date": str(game.game_date),
        "rows": len(new),
        "states": new.participation_state.value_counts().to_dict(),
        "candidate_generation": generation,
        "candidate_manifest_sha256": hashlib.sha256(
            (stage / "metadata/generation_manifest.json").read_bytes()
        ).hexdigest(),
        "candidate_files": len(manifest["files"]),
        "r2_writes": 0,
        "production_pointer_unchanged": True,
        "protected_registry_preparation": "not-run-for-this-unregistered-package",
        "processed_applicability": "availability is raw-only; base processed files retained",
    }
    (bundle / "receipt.json").write_text(json.dumps(evidence, indent=2) + "\n")
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(bundle))
    raw = payload.getvalue()
    assert len(raw) <= 512_000, "Public evidence transport exceeds bounded staging size"
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "cloud-recovery-bundle.zip").write_bytes(raw)
    _emit(evidence | {"bundle_sha256": hashlib.sha256(raw).hexdigest()}, capfd)
    with capfd.disabled():
        print("CLOUD_PUBLIC_BUNDLE_BASE64 " + base64.b64encode(raw).decode(), flush=True)


def test_cloud_source_access_inventory(capfd):
    from nba_api.stats.endpoints import (
        BoxScoreTraditionalV3,
        LeagueGameFinder,
        LeagueLineupViz,
        PlayByPlayV3,
        TeamPlayerOnOffSummary,
    )

    from nbatools.commands.pipeline.player_game_availability_espn import _scoreboard

    calls = {
        "core_game_logs": lambda: LeagueGameFinder(
            team_id_nullable=1610612738, season_nullable="2025-26", timeout=8
        ).get_data_frames(),
        "boxscore_and_period_source": lambda: BoxScoreTraditionalV3(
            game_id="0022500002", timeout=8
        ).get_data_frames(),
        "play_by_play_source": lambda: PlayByPlayV3(
            game_id="0022500002", timeout=8
        ).get_data_frames(),
        "on_off_source": lambda: TeamPlayerOnOffSummary(
            team_id=1610612738, season="2025-26", timeout=8
        ).get_data_frames(),
        "lineup_source": lambda: LeagueLineupViz(
            minutes_min=10, team_id_nullable=1610612738, season="2025-26", timeout=8
        ).get_data_frames(),
        "espn_scoreboard": lambda: _scoreboard("20251022"),
    }
    report = {}
    for name, call in calls.items():
        try:
            result = call()
            sizes = (
                [len(frame) for frame in result]
                if isinstance(result, list)
                else [len(result.get("events", []))]
            )
            report[name] = {"status": "returned-data" if any(sizes) else "empty", "rows": sizes}
        except Exception as exc:
            # No request URLs, headers, response bodies or credential values.
            report[name] = {"status": "blocked-or-error", "error_type": type(exc).__name__}
    _emit({"source_inventory": report, "classification": "diagnostic-not-source-acceptance"}, capfd)
