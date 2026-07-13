from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.freshness import FreshnessStatus, build_freshness_info
from nbatools.commands.ops import inventory, update_manifest
from nbatools.commands.pipeline import backfill_season
from nbatools.commands.validation_control import (
    DatasetSpec,
    build_slice_manifest,
    inspect_slice_manifest,
    manifest_path,
    validate_manifest_document,
    validate_raw_coverage,
    write_slice_manifest,
)

pytestmark = pytest.mark.engine

CONTROL_SPECS = (
    DatasetSpec("games", "raw", "game", ("game_id",), "games"),
    DatasetSpec("schedule", "raw", "game", ("game_id",), "schedule"),
    DatasetSpec(
        "team_game_stats",
        "raw",
        "team-game",
        ("game_id", "team_id"),
        "team-games",
    ),
    DatasetSpec(
        "player_game_stats",
        "raw",
        "player-game",
        ("game_id", "team_id", "player_id"),
        "player-games",
    ),
    DatasetSpec(
        "player_game_starter_roles",
        "raw",
        "player-game role",
        ("game_id", "team_id", "player_id"),
        "roles",
        trust_column="role_source_trusted",
        trust_reason_column="role_validation_reason",
    ),
    DatasetSpec(
        "player_game_period_stats",
        "raw",
        "player-game window",
        ("game_id", "team_id", "player_id", "period_family", "period_value"),
        "periods",
    ),
    DatasetSpec(
        "team_game_period_stats",
        "raw",
        "team-game window",
        ("game_id", "team_id", "period_family", "period_value"),
        "periods",
    ),
    DatasetSpec(
        "play_by_play_events",
        "raw",
        "event",
        ("season", "season_type", "game_id", "action_number"),
        "pbp",
        required=False,
        trust_column="pbp_source_trusted",
        trust_reason_column="pbp_validation_reason",
    ),
)

WINDOWS = (
    ("quarter", "1"),
    ("quarter", "2"),
    ("quarter", "3"),
    ("quarter", "4"),
    ("half", "first"),
    ("half", "second"),
)


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def _fixture(data_root: Path, *, include_pbp: bool = False, pbp_trusted: bool = True) -> None:
    suffix = "2099-00_regular_season.csv"
    games = [
        {"game_id": game_id, "game_date": f"2099-01-0{game_id}", "is_final": 1}
        for game_id in (1, 2)
    ]
    team = [{"game_id": game_id, "team_id": 10} for game_id in (1, 2)]
    player = [{"game_id": game_id, "team_id": 10, "player_id": 100} for game_id in (1, 2)]
    roles = [
        {
            **row,
            "role_source_trusted": 1,
            "role_validation_reason": "",
        }
        for row in player
    ]
    team_period = [
        {**row, "period_family": family, "period_value": value}
        for row in team
        for family, value in WINDOWS
    ]
    player_period = [
        {**row, "period_family": family, "period_value": value}
        for row in player
        for family, value in WINDOWS
    ]
    for name, rows in (
        ("games", games),
        ("schedule", games),
        ("team_game_stats", team),
        ("player_game_stats", player),
        ("player_game_starter_roles", roles),
        ("team_game_period_stats", team_period),
        ("player_game_period_stats", player_period),
    ):
        _write(data_root / "raw" / name / suffix, rows)
    if include_pbp:
        _write(
            data_root / "raw" / "play_by_play_events" / suffix,
            [
                {
                    "season": "2099-00",
                    "season_type": "Regular Season",
                    "game_id": game_id,
                    "action_number": 1,
                    "pbp_source_trusted": int(pbp_trusted),
                    "pbp_validation_reason": "" if pbp_trusted else "incomplete_game",
                }
                for game_id in (1, 2)
            ],
        )


def _build(data_root: Path) -> dict:
    return build_slice_manifest(
        "2099-00",
        "Regular Season",
        data_root=data_root,
        specs=CONTROL_SPECS,
        generation_id="generation-test",
        generated_at="2099-01-03T00:00:00",
    )


def _record(document: dict, name: str) -> dict:
    return next(record for record in document["datasets"] if record["name"] == name)


def test_manifest_records_versioned_per_dataset_validation_contract(tmp_path):
    _fixture(tmp_path)
    document = _build(tmp_path)

    assert document["schema_version"] == 1
    assert document["generation_id"] == "generation-test"
    assert document["validation_state"] == "passed"
    games = _record(document, "games")
    assert games["source"] == "games"
    assert games["grain"] == "game"
    assert games["row_count"] == 2
    assert len(games["file_sha256"]) == 64
    assert len(games["key_set_sha256"]) == 64
    assert games["coverage"]["state"] == "complete"
    assert games["validation"]["state"] == "passed"


def test_present_but_incomplete_game_set_fails_manifest(tmp_path):
    _fixture(tmp_path)
    path = tmp_path / "raw/team_game_period_stats/2099-00_regular_season.csv"
    frame = pd.read_csv(path)
    frame = frame[~((frame["game_id"] == 2) & (frame["period_family"] == "quarter"))]
    frame.to_csv(path, index=False)

    document = _build(tmp_path)
    record = _record(document, "team_game_period_stats")

    assert document["validation_state"] == "failed"
    assert record["coverage"]["state"] == "failed"
    assert record["coverage"]["missing_keys"]
    assert "quarter:1" in record["coverage"]["missing_windows"]


def test_cross_dataset_extra_game_key_fails_manifest(tmp_path):
    _fixture(tmp_path)
    path = tmp_path / "raw/games/2099-00_regular_season.csv"
    frame = pd.read_csv(path)
    frame.loc[len(frame)] = {"game_id": 3, "game_date": "2099-01-03", "is_final": 1}
    frame.to_csv(path, index=False)

    document = _build(tmp_path)
    record = _record(document, "games")

    assert document["validation_state"] == "failed"
    assert record["coverage"]["unexpected_keys"] == ["game_id=3"]


def test_roster_snapshot_is_not_claimed_as_player_game_coverage(tmp_path):
    specs = (
        DatasetSpec(
            "team_game_stats",
            "raw",
            "team-game",
            ("game_id", "team_id"),
            "team-games",
        ),
        DatasetSpec(
            "player_game_stats",
            "raw",
            "player-game",
            ("game_id", "team_id", "player_id"),
            "player-games",
        ),
        DatasetSpec(
            "rosters",
            "raw",
            "player-team-season stint",
            ("player_id", "team_id", "season", "stint"),
            "common-team-roster",
            season_only=True,
        ),
    )
    _write(
        tmp_path / "raw/team_game_stats/2099-00_regular_season.csv",
        [{"game_id": 1, "team_id": 10}],
    )
    _write(
        tmp_path / "raw/player_game_stats/2099-00_regular_season.csv",
        [{"game_id": 1, "team_id": 10, "player_id": 100}],
    )
    _write(
        tmp_path / "raw/rosters/2099-00.csv",
        [{"player_id": 200, "team_id": 10, "season": "2099-00", "stint": 1}],
    )

    document = build_slice_manifest(
        "2099-00",
        "Regular Season",
        data_root=tmp_path,
        specs=specs,
        generation_id="generation-test",
    )

    assert document["validation_state"] == "passed"
    assert _record(document, "rosters")["coverage"]["state"] == "present"
    assert _record(document, "rosters")["coverage"]["expected_keys"] is None


def test_one_missing_requested_window_fails_raw_validation(tmp_path):
    _fixture(tmp_path)
    frames = {
        name: pd.read_csv(tmp_path / "raw" / name / "2099-00_regular_season.csv")
        for name in (
            "games",
            "schedule",
            "team_game_stats",
            "player_game_stats",
            "player_game_starter_roles",
            "player_game_period_stats",
            "team_game_period_stats",
        )
    }
    frames["team_game_period_stats"] = frames["team_game_period_stats"].iloc[:-1].copy()

    with pytest.raises(ValueError, match="Cross-dataset coverage validation failed"):
        validate_raw_coverage(frames)


def test_one_untrusted_required_role_row_fails_raw_validation(tmp_path):
    _fixture(tmp_path)
    frames = {
        name: pd.read_csv(tmp_path / "raw" / name / "2099-00_regular_season.csv")
        for name in (
            "games",
            "schedule",
            "team_game_stats",
            "player_game_stats",
            "player_game_starter_roles",
            "player_game_period_stats",
            "team_game_period_stats",
        )
    }
    frames["player_game_starter_roles"].loc[0, "role_source_trusted"] = 0
    frames["player_game_starter_roles"]["role_validation_reason"] = frames[
        "player_game_starter_roles"
    ]["role_validation_reason"].astype("string")
    frames["player_game_starter_roles"].loc[0, "role_validation_reason"] = "missing_role"

    with pytest.raises(ValueError, match="1 untrusted rows"):
        validate_raw_coverage(frames)


def test_generation_mismatch_fails_manifest_document(tmp_path):
    _fixture(tmp_path)
    document = _build(tmp_path)
    document["datasets"][0]["generation_id"] = "different-generation"

    errors = validate_manifest_document(document, specs=CONTROL_SPECS)

    assert any("generation mismatch" in error for error in errors)


def test_missing_declared_schema_column_fails_manifest(tmp_path):
    spec = DatasetSpec(
        "sample",
        "raw",
        "sample row",
        ("row_id",),
        "synthetic",
        ("required_value",),
    )
    _write(tmp_path / "raw/sample/2099-00_regular_season.csv", [{"row_id": 1}])

    document = build_slice_manifest(
        "2099-00",
        "Regular Season",
        data_root=tmp_path,
        specs=(spec,),
        generation_id="generation-test",
    )

    assert document["validation_state"] == "failed"
    assert "missing required columns" in _record(document, "sample")["validation"]["errors"][0]


def test_corrupt_manifest_fails_inspection(tmp_path):
    path = manifest_path(tmp_path, "2099-00", "Regular Season")
    path.parent.mkdir(parents=True)
    path.write_text("not-json", encoding="utf-8")

    inspection = inspect_slice_manifest(
        "2099-00", "Regular Season", data_root=tmp_path, specs=CONTROL_SPECS
    )

    assert inspection["validation_state"] == "failed"
    assert "manifest is corrupt" in inspection["errors"][0]


def test_checksum_mismatch_after_manifest_write_fails_inspection(tmp_path):
    _fixture(tmp_path)
    write_slice_manifest(_build(tmp_path), data_root=tmp_path)
    games_path = tmp_path / "raw/games/2099-00_regular_season.csv"
    games_path.write_text(games_path.read_text() + "\n", encoding="utf-8")

    inspection = inspect_slice_manifest(
        "2099-00", "Regular Season", data_root=tmp_path, specs=CONTROL_SPECS
    )

    assert inspection["validation_state"] == "failed"
    assert any("games: checksum mismatch" in error for error in inspection["errors"])


def test_present_untrusted_optional_capability_fails_slice(tmp_path):
    _fixture(tmp_path, include_pbp=True, pbp_trusted=False)

    document = _build(tmp_path)
    pbp = _record(document, "play_by_play_events")

    assert document["validation_state"] == "failed"
    assert pbp["required"] is False
    assert pbp["trust"]["state"] == "failed"
    assert pbp["trust"]["reasons"] == ["incomplete_game"]


def test_freshness_fails_when_versioned_manifest_validation_fails(tmp_path):
    _fixture(tmp_path, include_pbp=True, pbp_trusted=False)
    write_slice_manifest(_build(tmp_path), data_root=tmp_path)

    info = build_freshness_info(
        seasons=["2099-00"],
        season_type="Regular Season",
        data_root=tmp_path,
    )

    assert info.status == FreshnessStatus.FAILED
    assert info.seasons[0].validation_state == "failed"
    assert info.seasons[0].generation_id == "generation-test"
    assert info.seasons[0].validation_errors


def test_manifest_json_round_trip_is_machine_readable(tmp_path):
    _fixture(tmp_path)
    path = write_slice_manifest(_build(tmp_path), data_root=tmp_path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["validation_state"] == "passed"


def test_skip_existing_requires_a_passing_validation_receipt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    suffix = "2099-00_regular_season.csv"
    for name in (
        "team_game_features",
        "game_features",
        "schedule_context_features",
        "player_game_features",
        "league_season_stats",
    ):
        _write(tmp_path / "data" / "processed" / name / suffix, [{"value": 1}])

    monkeypatch.setattr(
        backfill_season,
        "inspect_slice_manifest",
        lambda *args: {"validation_state": "failed"},
    )
    assert not backfill_season.outputs_exist("2099-00", "Regular Season")

    monkeypatch.setattr(
        backfill_season,
        "inspect_slice_manifest",
        lambda *args: {"validation_state": "passed"},
    )
    assert backfill_season.outputs_exist("2099-00", "Regular Season")


def test_update_manifest_persists_failed_receipt_and_refuses_success(monkeypatch):
    document = {
        "validation_state": "failed",
        "validation_errors": ["team_game_period_stats: coverage missing 1 requested keys"],
        "datasets": [
            {"required": True, "layer": "raw", "validation": {"state": "failed"}},
            {"required": True, "layer": "processed", "validation": {"state": "passed"}},
        ],
    }
    legacy: dict = {}
    monkeypatch.setattr(update_manifest, "build_slice_manifest", lambda *args, **kwargs: document)
    monkeypatch.setattr(
        update_manifest,
        "write_slice_manifest",
        lambda payload: Path("data/metadata/dataset_manifests/failed.json"),
    )
    monkeypatch.setattr(
        update_manifest,
        "_write_legacy_manifest",
        lambda *args, **kwargs: (
            legacy.update(kwargs) or Path("data/metadata/backfill_manifest.csv")
        ),
    )

    with pytest.raises(ValueError, match="coverage missing 1 requested keys"):
        update_manifest.run("2099-00", "Regular Season")

    assert legacy["raw_complete"] is False
    assert legacy["processed_complete"] is True


def test_inventory_reports_corrupt_validation_receipt_as_failed(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "data/metadata/dataset_manifests/corrupt.json"
    path.parent.mkdir(parents=True)
    path.write_text("not-json", encoding="utf-8")

    inventory.run()

    output = capsys.readouterr().out
    assert "receipt count: 1" in output
    assert "all validation receipts passed: False" in output
    assert "corrupt.json: failed" in output
