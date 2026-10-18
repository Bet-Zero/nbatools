"""Explicit reviewed setup selectors; never ordinary network test discovery."""

import hashlib
import io
import json
import os
import zipfile
from pathlib import Path

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def test_cdn_archive_collection(tmp_path, capfd):
    from tools.cloud_cdn_archive import prepare

    receipt = prepare(tmp_path / "collected")
    assert receipt["rows"] == 605 and receipt["final_home_points"] == 119
    assert receipt["final_away_points"] == 111 and receipt["final_period"] == 4
    assert receipt["canonical_source"] == "cdn.nba.com.liveData.playbyplay"
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "cdn-archive-collection.json").write_text(json.dumps(receipt, indent=2) + "\n")
    with capfd.disabled():
        print("CDN_COLLECTION_JSON " + json.dumps(receipt), flush=True)


def test_durable_cdn_recovery(tmp_path, monkeypatch, capfd):
    from nbatools.commands.data_utils import load_play_by_play_events_for_seasons
    from nbatools.commands.pipeline.build_clutch_stats import add_event_points
    from nbatools.commands.pipeline.generation_publication import validate_staged_generation

    root = (
        Path(__file__).resolve().parents[1]
        / "working/nba-tools-completion-program/cloud-operations"
    )
    reference = json.loads((root / "cdn-archive-receipt.json").read_text())
    payload = (root / "cdn-archive-staging.zip").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == reference["durable_bundle"]["sha256"]
    restored = tmp_path / "restored"
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        receipt = json.loads(archive.read("receipt.json"))
        assert set(archive.namelist()) == set(receipt["files"]) | {"receipt.json"}
        assert sum(item.file_size for item in archive.infolist()) < 2_000_000
        for name, record in receipt["files"].items():
            relative = Path(name)
            assert not relative.is_absolute() and ".." not in relative.parts
            data = archive.read(name)
            assert len(data) == record["bytes"]
            assert hashlib.sha256(data).hexdigest() == record["sha256"]
            path = restored / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(restored))
    # The parent runner pins production read-only R2. Offline recovery must not
    # accidentally resolve that generation under the new local staging root.
    for name in list(os.environ):
        if name.startswith("R2_") or name in {
            "NBATOOLS_DATA_GENERATION",
            "GH_TOKEN",
            "GITHUB_TOKEN",
        }:
            monkeypatch.delenv(name, raising=False)
    from nbatools.data_source import reset_data_source_cache

    reset_data_source_cache()
    frame = load_play_by_play_events_for_seasons(["2025-26"], "Regular Season")
    assert len(frame) == 605 and frame.action_number.nunique() == 605
    assert frame.pbp_source_trusted.eq(1).all()
    assert frame.pbp_source.eq("cdn.nba.com.liveData.playbyplay").all()
    assert frame[frame.action_number.isin([545, 547, 548])].action_number.tolist() == [
        547,
        545,
        548,
    ]
    # Exercise the existing score-state consumer: no fabricated second increase.
    assert add_event_points(frame).pts.sum() == 230
    candidate = receipt["immutable_candidate"]
    manifest = validate_staged_generation(restored / "candidate", candidate["generation"])
    assert len(manifest["files"]) == candidate["files"]
    with capfd.disabled():
        print(
            "CDN_RECOVERY_JSON "
            + json.dumps(
                {
                    "state": "verified",
                    "rows": 605,
                    "points": 230,
                    "bundle_sha256": reference["durable_bundle"]["sha256"],
                    "candidate_files": len(manifest["files"]),
                    "r2_writes": 0,
                }
            ),
            flush=True,
        )
