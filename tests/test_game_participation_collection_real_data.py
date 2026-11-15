"""Recover a finite game population from retained originals, never fetch or publish."""

import csv
import hashlib
import io
import json
import os
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.player_membership import build_result
from nbatools.data_source import data_generation_context, data_path, reset_data_source_cache
from nbatools.dataframe_cache import clear_frame_cache
from nbatools.query_service import execute_natural_query
from tools.stage_participation_collection import build_stage

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
PROGRAM = Path(__file__).resolve().parents[1] / "working/nba-tools-completion-program"
GENERATION = "availability-participation-2025-durant-v1-20261114"
MANIFEST = "cde98408f3390e6191da564197fb77ffbc598a3059963cfc21d9f2d7e1a6b366"
CSV = "raw/player_game_availability/2023-24_regular_season.csv"
# Counts independently read from the native Traditional and InactivePlayers
# tables, not calculated by the stager or participation engine.
COUNTS = {
    "0022300373": (24, 11),
    "0022300432": (21, 14),
    "0022300507": (21, 14),
    "0022300984": (21, 13),
    "0022301011": (23, 12),
    "0022301134": (20, 15),
    "0022301173": (23, 12),
    "0022301186": (20, 14),
}


def test_retained_game_requests_recover_all_listed_players_and_preserve_unknowns(
    tmp_path, monkeypatch
):
    original = json.loads(
        (
            PROGRAM / "collection-requests/bos-tatum-participation-remaining-2023-24.json"
        ).read_bytes()
    )
    request = {
        key: original[key]
        for key in [
            "schema_version",
            "dataset",
            "season",
            "season_type",
            "revision",
            "repository",
            "source_files",
        ]
    }
    request.update(
        requirement_grain="game",
        base_generation=GENERATION,
        base_manifest_sha256=MANIFEST,
        requirements=[
            {key: row[key] for key in ["game_id", "game_date", "proposed_sources"]}
            for row in original["requirements"]
        ],
    )
    assert {row["game_id"] for row in request["requirements"]} == set(COUNTS)
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request))
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", tmp_path / "output"))
    output = output / "retained-game-collection"
    with data_generation_context() as generation:
        assert generation == GENERATION
        manifest = data_path("data/metadata/generation_manifest.json").read_bytes()
        assert hashlib.sha256(manifest).hexdigest() == MANIFEST
        before = data_path("data/" + CSV).read_bytes()
        team_bytes = data_path("data/raw/team_game_stats/2023-24_regular_season.csv").read_bytes()
        validation = build_stage(
            request_path,
            PROGRAM / "source-evidence/k08-tatum-2023",
            tmp_path / "stage",
            output,
            candidate_sha=os.environ["VALIDATION_SHA"],
        )
        assert data_path("data/" + CSV).read_bytes() == before
    assert validation["publication_state"] == "staged_only_no_writes"
    assert validation["qualified_targets"] == [] and validation["requested_target_count"] == 0
    assert {
        row["game_id"]: (row["played"], row["did_not_play"])
        for row in validation["qualified_games"]
    } == COUNTS
    assert all(row["unknown"] == 0 for row in validation["qualified_games"])
    assert validation["append_only"][CSV]["added_records"] == 278
    root = tmp_path / "stage/data"
    after = (root / CSV).read_bytes()
    old_cells = list(csv.DictReader(io.StringIO(before.decode())))
    cells = list(csv.DictReader(io.StringIO(after.decode())))
    old_keys = {(row["game_id"], row["player_id"]) for row in old_cells}
    assert [row for row in cells if (row["game_id"], row["player_id"]) in old_keys] == old_cells
    assert len(old_cells) == 597 and len(cells) == 875
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    clear_frame_cache()
    try:
        # Arbitrary players on the other teams, including two-way and recently
        # signed players, are recovered by the same game request.
        for pid, day, team, game in [
            (1641806, "2023-12-29", 1610612761, 22300432),  # Markquis Nowell
            (201959, "2024-03-22", 1610612765, 22301011),  # Taj Gibson
            (203552, "2024-04-12", 1610612766, 22301173),  # Seth Curry
        ]:
            row = build_result(pid, day, "2023-24", team_id=team, game_id=game).summary.iloc[0]
            assert (row.membership_state, row.participation_state) == ("member", "did_not_play")
        # A source omission remains unknown, even on a fully imported game.
        row = build_result(
            2544, "2024-04-12", "2023-24", team_id=1610612738, game_id=22301173
        ).summary.iloc[0]
        assert (row.membership_state, row.participation_state) == ("unknown", "unknown")
        result = execute_natural_query("Celtics record without Tatum in 2023-24")
        assert result.result_status == "ok", result.metadata
        payload = result.to_dict()["sections"]
        teams = pd.read_csv(io.BytesIO(team_bytes))
        expected = teams.loc[teams.team_id.eq(1610612738) & teams.game_id.isin(map(int, COUNTS))]
        assert len(expected) == 8
        assert {int(row["game_id"]) for row in payload["game_log"]} == set(expected.game_id)
        summary = payload["summary"][0]
        assert (summary["games"], summary["wins"], summary["losses"]) == (
            8,
            int(expected.wl.eq("W").sum()),
            int(expected.wl.eq("L").sum()),
        )
        assert summary["pts_avg"] == pytest.approx(expected.pts.mean(), abs=0.001)
    finally:
        reset_data_source_cache()
        clear_frame_cache()
