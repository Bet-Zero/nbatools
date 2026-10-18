"""Explicit, bounded setup operations. Only the existing read-only R2 runner.

Source failures are recorded as diagnostics, never relabeled source acceptance.
The full backup test is independently gated before durable release preservation.
This file deliberately requires an explicit selector; ordinary full test discovery
must not launch setup acquisitions or full exports.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools.cloud_backup import export_backup

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def test_full_generation_backup(capfd):
    root = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "cloud-backup"
    receipt = export_backup(root, os.environ["NBATOOLS_DATA_GENERATION"])
    assert receipt["files"] > 600 and receipt["data_bytes"] > 300_000_000
    assert receipt["r2_writes"] == 0 and receipt["production_pointer_unchanged"] is True
    with capfd.disabled():
        print("CLOUD_BACKUP_JSON " + json.dumps(receipt, sort_keys=True), flush=True)


def test_core_cloud_routes(tmp_path, capfd):
    from nba_api.live.nba.endpoints import boxscore

    # Actual existing core pipeline, with its normal 3 x 30-second request/retry
    # policy. Never weaken it to an eight-second diagnostic or mock NBA values.
    started = __import__("time").monotonic()
    result = None
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from nbatools.commands.pipeline.pull_games import run; run('2025-26', 'Regular Season')",
            ],
            cwd=tmp_path,
            capture_output=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        pass  # Retain an explicit timeout diagnosis and continue bounded alternatives.
    report = {
        "core_games": {
            "returned_canonical_csv": result is not None and result.returncode == 0,
            "elapsed_seconds": round(__import__("time").monotonic() - started, 2),
            "normal_timeout_seconds": 30,
            "normal_attempts": 3,
        }
    }
    if result is None:
        report["core_games"]["error_category"] = "bounded-process-timeout"
        report["core_games"]["failure"] = "normal core pipeline exceeded 120-second test ceiling"
    elif result.returncode:
        report["core_games"]["error_category"] = (
            "read-timeout" if b"Read timed out" in result.stderr else "pipeline-acquisition-error"
        )
        report["core_games"]["failure"] = (
            "existing pipeline exhausted normal acquisition retries; no canonical data produced"
        )
    else:
        import pandas as pd

        games = pd.read_csv(tmp_path / "data/raw/games/2025-26_regular_season.csv")
        assert not games.empty and not games.game_id.duplicated().any()
        report["core_games"]["rows"] = len(games)
    try:
        game = boxscore.BoxScore("0022500003", timeout=20).get_dict()["game"]
        assert game["gameId"] == "0022500003" and game["gameStatus"] == 3
        report["official_live_boxscore"] = {
            "status": "returned-final-game",
            "home_points": game["homeTeam"]["score"],
            "away_points": game["awayTeam"]["score"],
        }
    except Exception as exc:
        report["official_live_boxscore"] = {
            "status": "unavailable",
            "error_type": type(exc).__name__,
        }

    # Recover the already qualified identity support from permanent Git, then
    # exercise the existing ESPN adapter rather than merely pinging scoreboard.
    bundle = tmp_path / "bundle.zip"
    import requests

    url = "https://raw.githubusercontent.com/Bet-Zero/nbatools/e4900f515bc2536859293599efdd7ba7889a7969/working/nba-tools-completion-program/cloud-staged/recovery-bundle.zip"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    bundle.write_bytes(response.content)
    assert (
        hashlib.sha256(response.content).hexdigest()
        == "1a482b76f7455dc6cefef89620e9e2d935f144b2c2765ce624080bf6e33ac9ea"
    )
    import zipfile

    with zipfile.ZipFile(bundle) as archive:
        # Exact reviewed hash above authenticates this fixed small inventory.
        assert sum(i.file_size for i in archive.infolist()) < 500_000
        archive.extractall(tmp_path / "identity")
    from nbatools.commands.pipeline.player_game_availability_espn import espn_boxscore_as_v3

    try:
        rows, event = espn_boxscore_as_v3(
            game_id=22500003,
            game_date="2025-10-22",
            season="2025-26",
            season_type="Regular Season",
            home_team_id=1610612752,
            away_team_id=1610612739,
            data_root=tmp_path / "identity/data",
        )
        assert len(rows) >= 21 and rows.personId.nunique() == len(rows)
        report["espn_participation"] = {
            "status": "qualified-adapter-returned",
            "rows": len(rows),
            "event_id": event,
            "scope": "participation only; canonical NBA identity support required",
        }
    except Exception as exc:
        report["espn_participation"] = {
            "status": "unavailable-or-unqualified",
            "error_type": type(exc).__name__,
        }
    report["classification"] = "source diagnostics, not universal core acquisition acceptance"
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "source-routes.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    with capfd.disabled():
        print("CLOUD_ROUTES_JSON " + json.dumps(report, sort_keys=True), flush=True)


def test_alternative_cloud_details(tmp_path, capfd):
    """One follow-up to distinguish access restrictions from adapter defects."""
    import zipfile

    import requests

    from nbatools.commands.pipeline.player_game_availability_espn import (
        _get_json,
        _scoreboard,
        espn_boxscore_as_v3,
    )

    report = {}
    response = requests.get(
        "https://cdn.nba.com/static/json/liveData/boxscore/boxscore_0022500003.json", timeout=20
    )
    report["official_cdn"] = {
        "http_status": response.status_code,
        "bytes": len(response.content),
        "body_sha256": hashlib.sha256(response.content).hexdigest(),
    }
    events = _scoreboard("2025-10-22")["events"]
    matching = [
        event
        for event in events
        if {c["team"]["abbreviation"] for c in event["competitions"][0]["competitors"]}
        == {"CLE", "NY"}
    ]
    assert len(matching) == 1
    summary = _get_json("summary?event=" + matching[0]["id"])
    report["espn_event_id"] = matching[0]["id"]
    report["espn_columns"] = [
        {"names": table.get("names"), "labels": table.get("labels")}
        for team in summary["boxscore"]["players"]
        for table in team["statistics"]
    ]
    response = requests.get(
        "https://raw.githubusercontent.com/Bet-Zero/nbatools/e4900f515bc2536859293599efdd7ba7889a7969/working/nba-tools-completion-program/cloud-staged/recovery-bundle.zip",
        timeout=30,
    )
    response.raise_for_status()
    assert (
        hashlib.sha256(response.content).hexdigest()
        == "1a482b76f7455dc6cefef89620e9e2d935f144b2c2765ce624080bf6e33ac9ea"
    )
    bundle = tmp_path / "identity.zip"
    bundle.write_bytes(response.content)
    with zipfile.ZipFile(bundle) as archive:
        archive.extractall(tmp_path / "identity")  # exact reviewed fixed hash above
    try:
        rows, event = espn_boxscore_as_v3(
            game_id=22500003,
            game_date="2025-10-22",
            season="2025-26",
            season_type="Regular Season",
            home_team_id=1610612752,
            away_team_id=1610612739,
            data_root=tmp_path / "identity/data",
        )
        report["espn_adapter"] = {"status": "qualified", "rows": len(rows), "event_id": event}
    except ValueError as exc:
        # Fixed public source, no credentials; adapter errors contain validation
        # reasons and NBA identities, not request headers or secret values.
        report["espn_adapter"] = {"status": "rejected", "reason": str(exc)[:500]}
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "alternative-details.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    with capfd.disabled():
        print("CLOUD_ALTERNATIVES_JSON " + json.dumps(report, sort_keys=True), flush=True)


def test_espn_with_cloud_identity_catalog(tmp_path, capfd, monkeypatch):
    """Qualify the existing alternative using full, authenticated cloud identity support."""
    import base64
    import io
    import zipfile
    from datetime import UTC, datetime

    import pandas as pd
    import requests

    from nbatools.commands.pipeline import player_game_availability_espn as adapter
    from nbatools.commands.pipeline.generation_publication import _resolve_r2_target
    from nbatools.commands.pipeline.pull_player_game_availability import (
        backfill,
        validate_availability,
        validate_publication,
    )
    from tools.r2_publication import verify_pointer_manifest

    response = requests.get(
        "https://raw.githubusercontent.com/Bet-Zero/nbatools/e4900f515bc2536859293599efdd7ba7889a7969/working/nba-tools-completion-program/cloud-staged/recovery-bundle.zip",
        timeout=30,
    )
    response.raise_for_status()
    assert (
        hashlib.sha256(response.content).hexdigest()
        == "1a482b76f7455dc6cefef89620e9e2d935f144b2c2765ce624080bf6e33ac9ea"
    )
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(tmp_path / "identity")  # authenticated fixed inventory
    root = tmp_path / "identity/data"
    suffix = "2025-26_regular_season.csv"
    oracle = pd.read_csv(root / "raw/player_game_availability" / suffix)
    client, bucket = _resolve_r2_target(client=None, bucket_name=None, env=None, env_file=None)
    generation = os.environ["NBATOOLS_DATA_GENERATION"]
    before, manifest, manifest_hash = verify_pointer_manifest(client, bucket, generation)
    key = "raw/player_game_stats/" + suffix
    item = next(item for item in manifest["files"] if item["path"] == key)
    assert item["size_bytes"] < 20_000_000
    body = client.get_object(Bucket=bucket, Key=f"generations/{generation}/{key}")["Body"]
    try:
        raw = body.read(item["size_bytes"] + 1)
    finally:
        body.close()
    assert len(raw) == item["size_bytes"] and hashlib.sha256(raw).hexdigest() == item["sha256"]
    (root / key).write_bytes(raw)

    # Observe actual existing-source responses without changing any returned fact.
    responses = {}
    original = adapter._get_json

    def record(endpoint):
        payload = original(endpoint)
        responses[endpoint] = payload
        return payload

    monkeypatch.setattr(adapter, "_get_json", record)
    adapter._scoreboard.cache_clear()
    rows = backfill(
        "2025-26", "Regular Season", root=root, game_ids=[22500003], limit=1, source="espn"
    )
    validate_availability(rows)
    played = rows[rows.participation_state.eq("played")]
    expected = oracle[oracle.participation_state.eq("played")]
    assert len(played) == 21 and set(played.player_id) == set(expected.player_id)
    compare = played.merge(
        expected, on=["player_id", "team_id"], suffixes=("_espn", "_pdf"), validate="one_to_one"
    )
    delta = (compare.source_minutes_espn - compare.source_minutes_pdf).abs()
    assert len(compare) == 21 and delta.le(1).all()  # ESPN reports rounded whole minutes.
    dnp = rows[rows.participation_state.eq("did_not_play")]
    assert set(dnp.player_id) <= set(
        oracle[oracle.participation_state.eq("did_not_play")].player_id
    )
    assert rows.coverage_scope.eq("listed_player_rows_only").all()
    assert rows.source.eq("espn_game_summary:401809234").all()
    with pytest.raises(
        ValueError, match="Availability import is incomplete or lacks source provenance"
    ):
        validate_publication(root)  # Existing protected source gate stays intact.
    after, _, after_hash = verify_pointer_manifest(client, bucket, generation)
    assert before == after and manifest_hash == after_hash

    evidence = {
        "base_generation": generation,
        "base_manifest_sha256": manifest_hash,
        "identity_catalog": key,
        "identity_catalog_sha256": item["sha256"],
        "identity_catalog_bytes": len(raw),
        "game_id": 22500003,
        "source": "espn_game_summary:401809234",
        "rows": len(rows),
        "played": len(played),
        "explicit_dnp": len(dnp),
        "played_ids_match_official_pdf": True,
        "maximum_minute_difference_from_pdf": float(delta.max()),
        "coverage": "listed_player_rows_only",
        "r2_writes": 0,
        "publication": "rejected-by-existing-official-source-gate",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "source_payload_encoding": "serialized parsed JSON returned by existing adapter; no historical injury interpretation",
    }
    bundle = tmp_path / "espn-staging"
    (bundle / "sources").mkdir(parents=True)
    source_receipts = []
    for endpoint, payload in responses.items():
        name = "scoreboard.json" if endpoint.startswith("scoreboard?") else "summary.json"
        path = bundle / "sources" / name
        path.write_text(json.dumps(payload, sort_keys=True) + "\n")
        source_receipts.append(
            {
                "path": "sources/" + name,
                "url": adapter.BASE_URL + endpoint,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    evidence["source_payloads"] = source_receipts
    rows.to_csv(bundle / "canonical-availability.csv", index=False)
    oracle.to_csv(bundle / "official-pdf-comparison.csv", index=False)
    identities = adapter._nba_players(root, "2025-26", "regular_season")
    identities[identities.player_id.isin(rows.player_id)][
        ["team_id", "player_id", "player_name"]
    ].drop_duplicates().to_csv(bundle / "derived-identity-support.csv", index=False)
    (bundle / "receipt.json").write_text(json.dumps(evidence, indent=2) + "\n")
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(bundle).as_posix())
    raw = payload.getvalue()
    assert len(raw) < 512_000
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "espn-development-staging.zip").write_bytes(raw)
    evidence["bundle_sha256"] = hashlib.sha256(raw).hexdigest()
    with capfd.disabled():
        print("CLOUD_ESPN_JSON " + json.dumps(evidence, sort_keys=True), flush=True)
        print("CLOUD_ESPN_BUNDLE_BASE64 " + base64.b64encode(raw).decode(), flush=True)
