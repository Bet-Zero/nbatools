"""One retained report qualifies Boston only; it cannot invent Milwaukee or tenure."""

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from nbatools.commands.pipeline import player_game_availability_report as report
from nbatools.commands.pipeline.pull_player_game_availability import backfill, validate_publication
from nbatools.data_source import data_path, reset_data_source_cache
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
CACHE = (
    ROOT
    / "working/nba-tools-completion-program/source-evidence/tatum-20260201/acquired_data/raw/player_game_availability_sources"
)
ORACLE = json.loads((ROOT / "tests/fixtures/participation/boston-20260201.json").read_text())
BOS = 1610612738
GAME = 22500702


def _offline(*args, **kwargs):
    raise AssertionError("Retained source replay must never fetch an NBA endpoint")


def _stage(tmp_path):
    root = tmp_path / "data"
    files = {**ORACLE["canonical_files_sha256"], **ORACLE["identity_files_sha256"]}
    for name, digest in files.items():
        original = data_path(name)
        assert hashlib.sha256(original.read_bytes()).hexdigest() == digest
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
    return root


def test_retained_boston_team_scope_preserves_exact_source_and_consumer_limits(
    tmp_path, monkeypatch
):
    root = _stage(tmp_path)
    monkeypatch.setattr(report.urllib.request, "urlopen", _offline)
    args = dict(root=root, source="report", cached_reports=CACHE, game_ids=[GAME])
    rows = backfill("2025-26", **args, imported_team_ids=[BOS])
    assert set(rows.team_id) == {BOS} and len(rows) == 17
    assert rows.coverage_scope.eq("listed_player_rows_only").all()
    assert rows.source_sha256.eq(ORACLE["source"]["sha256"]).all()
    expected = {r["player_id"]: r for r in ORACLE["rows"]}
    assert set(rows.player_id) == set(expected)
    for row in rows.itertuples():
        truth = expected[row.player_id]
        assert row.player_name == truth["player_name"]
        assert row.participation_state == (
            "played" if truth["state"] == "played" else "did_not_play"
        )
        assert row.source_comment == truth["comment"]
        if truth["state"] == "played":
            assert row.source_minutes == pytest.approx(truth["source_seconds"] / 60)
    assert rows.loc[rows.participation_state.eq("played"), "source_minutes"].sum() == pytest.approx(
        240
    )
    directory = root / "raw/player_game_availability"
    target = directory / "2025-26_regular_season.csv"
    receipts = target.with_suffix(".imports.json")
    receipt = json.loads(receipts.read_text())[str(GAME)]
    assert receipt["imported_team_ids"] == [BOS]
    source = root / "raw/player_game_availability_sources"
    assert (source / "20260201_MILBOS.json").read_bytes() == (
        CACHE / "20260201_MILBOS.json"
    ).read_bytes()
    validate_publication(root)

    # A scoped success is never completion of a full-game import; failure
    # preserves the earlier Boston evidence and receipt byte for byte.
    before = target.read_bytes(), receipts.read_bytes()
    with pytest.raises(ValueError, match="candidate IDs=2"):
        backfill("2025-26", **args)
    assert (target.read_bytes(), receipts.read_bytes()) == before

    # The isolated stage supports only this exact Boston game. Neither an
    # uncovered game nor another team's game gains a synthetic observation.
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    try:
        r = execute_natural_query("Celtics record without Jayson Tatum on 2026-02-01")
        assert r.result_status == "ok", r.metadata
        summary = r.result.to_dict()["sections"]["summary"][0]
        assert (summary["games"], summary["wins"], summary["losses"]) == (1, 1, 0)
        assert (summary["pts_avg"], summary["reb_avg"], summary["ast_avg"]) == (107, 52, 24)
        with_him = execute_natural_query("Celtics record with Jayson Tatum on 2026-02-01")
        assert with_him.result_status == "no_result" and with_him.result_reason == "no_match"
        broad = execute_natural_query("Celtics record without Jayson Tatum in 2025-26")
        assert broad.result_status == "no_result" and broad.result_reason != "no_match"
        other = execute_natural_query("Lakers record without Jayson Tatum on 2026-02-01")
        assert other.result_status == "no_result" and other.result_reason != "no_match"
    finally:
        reset_data_source_cache()

    original = json.loads(receipts.read_text())
    for scope in (None, [], [1610612749], [BOS, 1610612749], [999], [BOS, BOS], ["1610612738"]):
        damaged = json.loads(json.dumps(original))
        if scope is None:
            damaged[str(GAME)].pop("imported_team_ids")
        else:
            damaged[str(GAME)]["imported_team_ids"] = scope
        receipts.write_text(json.dumps(damaged))
        with pytest.raises(ValueError):
            validate_publication(root)
    receipts.write_text(json.dumps(original))
    validate_publication(root)
    if output := os.environ.get("NBATOOLS_ACQUISITION_OUTPUT"):
        evidence = Path(output) / "boston-team-scope"
        evidence.mkdir(parents=True, exist_ok=True)
        for path in (target, receipts, source / "20260201_MILBOS.json"):
            shutil.copyfile(path, evidence / path.name)
        (evidence / "scope.json").write_text(
            json.dumps(
                {
                    "game_id": GAME,
                    "imported_team_ids": [BOS],
                    "listed_rows": 17,
                    "source_sha256": ORACLE["source"]["sha256"],
                    "publication_state": "staged_only",
                    "production_writes": 0,
                    "qualification": "One Boston game only; no MIL, tenure or other-game inference",
                },
                indent=2,
            )
            + "\n"
        )
