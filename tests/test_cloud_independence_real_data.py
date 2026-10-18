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
import subprocess
import sys
import zipfile
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.pipeline.generation_publication import (
    _build_staged_generation,
    _read_r2_pointer,
    _resolve_r2_target,
    _validate_r2_rollback_target,
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


def test_durable_stage_recovery_in_separate_runner(tmp_path, capfd, monkeypatch):
    """Recover exact committed public staging bytes without acquisition/artifacts."""
    clone = tmp_path / "cloud-clone"
    subprocess.run(
        [
            "git",
            "clone",
            "--single-branch",
            "--branch",
            "data-staging/cloud-acceptance-20261018",
            "https://github.com/Bet-Zero/nbatools.git",
            str(clone),
        ],
        check=True,
    )
    # Bind below to the independently reviewed durable staging commit.
    expected_sha = "e4900f515bc2536859293599efdd7ba7889a7969"
    actual = subprocess.check_output(
        ["git", "-C", str(clone), "rev-parse", "HEAD"], text=True
    ).strip()
    assert actual == expected_sha
    raw = (
        clone / "working/nba-tools-completion-program/cloud-staged/recovery-bundle.zip"
    ).read_bytes()
    assert (
        hashlib.sha256(raw).hexdigest()
        == "1a482b76f7455dc6cefef89620e9e2d935f144b2c2765ce624080bf6e33ac9ea"
    )
    destination = tmp_path / "recovered"
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert sum(item.file_size for item in archive.infolist()) < 5_000_000
        for item in archive.infolist():
            path = Path(item.filename)
            assert not path.is_absolute() and ".." not in path.parts
            assert item.external_attr >> 16 & 0o170000 != 0o120000
        archive.extractall(destination)
    validate_publication(destination / "data")
    from nbatools.data_source import data_read_csv, reset_data_source_cache

    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(destination))
    monkeypatch.delenv("NBATOOLS_DATA_GENERATION", raising=False)
    reset_data_source_cache()
    frame = data_read_csv("data/raw/player_game_availability/2025-26_regular_season.csv")
    assert len(frame) == 33 and set(pd.to_numeric(frame.game_id)) == {22500003}
    reset_data_source_cache()

    # Provider-representative read-only rollback-target verification, not a live
    # rollback or an independent backup proof. Never move the production pointer.
    client, bucket = _resolve_r2_target(client=None, bucket_name=None, env=None, env_file=None)
    before = _read_r2_pointer(client, bucket)
    assert before.previous_generation_id == "queue-d-production-0574735-20260716"
    previous, digest = _validate_r2_rollback_target(client, bucket, before.previous_generation_id)
    assert previous and _read_r2_pointer(client, bucket) == before
    _emit(
        {
            "recovered_staging_commit": actual,
            "recovered_rows": len(frame),
            "source": "durable-github-git-objects-not-actions-artifacts",
            "rollback_target": before.previous_generation_id,
            "rollback_target_manifest_sha256": digest,
            "rollback_target_objects": len(previous["files"]),
            "r2_writes": 0,
            "live_rollback": "not-executed",
            "independent_backup": "not-proven",
        },
        capfd,
    )


def test_new_slice_registered_readonly_preparation(tmp_path, capfd, monkeypatch):
    """Exercise existing registry/source gates and exact-base preparation only."""
    root = Path(__file__).resolve().parents[1]
    package_name = "cloud-acceptance-cle-nyk-v1"
    package = json.loads((root / ".github/data-publication-packages.json").read_text())["packages"][
        package_name
    ]
    publisher = tmp_path / "publisher"
    subprocess.run(
        [
            "git",
            "clone",
            "--single-branch",
            "--branch",
            "setup/cloud-independence-acceptance-20261018",
            "https://github.com/Bet-Zero/nbatools.git",
            str(publisher),
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(publisher), "checkout", "--detach", package["publisher_sha"]], check=True
    )
    work = tmp_path / "prepared"
    # The normal CLI starts a fresh interpreter, preserving the existing
    # publisher checkout/import identity guard even when pytest imported modules.
    subprocess.run(
        [
            sys.executable,
            str(root / "tools/r2_publication.py"),
            "prepare",
            "--package",
            package_name,
            "--publisher",
            str(publisher),
            "--work",
            str(work),
        ],
        check=True,
    )
    receipt = json.loads((work / "prepared.json").read_text())
    assert receipt["publication_state"] == "prepared_no_writes"
    assert receipt["base_generation"] == os.environ["NBATOOLS_DATA_GENERATION"]
    assert receipt["file_count"] == 705
    assert receipt["generation_id"] == "cloud-acceptance-cle-nyk-20261018"
    assert not (work / "publication.json").exists()
    assert receipt["budget"]["conservative_projected_bytes"] <= receipt["budget"]["limit_bytes"]
    destination = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"])
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(work / "prepared.json", destination / "new-slice-prepared.json")
    shutil.copy2(
        work / "staging/local-validation.json", destination / "new-slice-local-validation.json"
    )
    from fastapi.testclient import TestClient

    from nbatools.api import app
    from nbatools.data_source import reset_data_source_cache

    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(work / "staging"))
    monkeypatch.delenv("NBATOOLS_DATA_GENERATION", raising=False)
    reset_data_source_cache()
    answers = []
    for case in package["deployed_checks"]:
        response = TestClient(app).post("/query", json={"query": case["query"]})
        assert response.status_code == 200
        answer = response.json()
        rows = answer.get("result", {}).get("sections", {}).get("summary", [])
        assert answer.get("result_status") == "ok" and len(rows) == 1
        assert all(rows[0].get(k) == v for k, v in case["summary"].items())
        answers.append({"query": case["query"], "summary": rows[0]})
    reset_data_source_cache()
    _emit(
        {
            "new_slice_registered_preparation": receipt,
            "protected_environment_publication": "not-requested",
            "r2_writes": 0,
            "new_generation_uploaded": False,
            "staged_real_data_api_answers": answers,
        },
        capfd,
    )
