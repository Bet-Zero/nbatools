"""Replay retained originals into partial player staging; never publish or fetch."""

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.player_game_finder import _apply_filters
from tools.season_rollover_core_bridge import stage_retained_core
from tools.season_rollover_source_stats import retained_stats_documents

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]


def test_retained_sources_stage_corrected_player_date_minute_answers():
    evidence = ROOT / "working/nba-tools-completion-program/source-evidence/rollover-2026-27"
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "rollover-core-bridge"
    report = stage_retained_core(evidence, output)
    assert report["primary_player_rows"] == report["staged_player_rows"] == 1829
    assert report["corroborated_observations"] == 1253
    assert report["production_writes"] == 0 and report["canonical_core_accepted"] is False
    assert report["canonical_pbp_ingestion_accepted"] is False
    primary = pd.read_csv(output / "primary-player-game-logs.csv", dtype={"GAME_ID": str})
    staged = pd.read_csv(output / "staged-player-game-logs.csv", dtype={"GAME_ID": str})
    assert primary.PTS.sum() == 18461 and staged.PTS.sum() == 18464

    def answer(rows, player, points, minutes, day):
        renamed = rows.rename(
            columns={
                "GAME_ID": "game_id",
                "GAME_DATE": "game_date",
                "PLAYER_ID": "player_id",
                "PLAYER_NAME": "player_name",
                "PTS": "pts",
                "MIN": "minutes",
            }
        )
        return _apply_filters(
            renamed,
            player=player,
            stat="pts",
            min_value=points,
            conditions=[dict(stat="minutes", op=">=", value=minutes)],
            start_date=day,
            end_date=day,
        )

    assert answer(primary, "Caleb Martin", 10, 13, "2026-10-28").empty
    caleb = answer(staged, "Caleb Martin", 10, 13, "2026-10-28")
    assert caleb.game_id.tolist() == ["0022600142"] and caleb.pts.item() == 10
    assert caleb.minutes.item() == pytest.approx(13 + 49 / 60)
    assert answer(primary, "Jalen Johnson", 17, 0, "2026-10-29").empty
    assert answer(staged, "Jalen Johnson", 17, 0, "2026-10-29").game_id.tolist() == ["0022600144"]
    unchanged = (
        primary.GAME_ID.ne("0022600138")
        & primary.GAME_ID.ne("0022600142")
        & primary.GAME_ID.ne("0022600144")
    )
    pd.testing.assert_frame_equal(
        primary.loc[unchanged].reset_index(drop=True), staged.loc[unchanged].reset_index(drop=True)
    )


def test_staged_producer_natural_and_api_preserve_corrected_player_fields(tmp_path, monkeypatch):
    from nbatools.commands._seasons import reset_latest_served_season_cache
    from nbatools.commands.pipeline import pull_games, pull_player_game_stats, pull_team_game_stats
    from nbatools.commands.pipeline.generation_publication import _write_player_names
    from nbatools.commands.pipeline.structured_participation import _table
    from nbatools.data_source import reset_data_source_cache
    from nbatools.query_service import execute_natural_query

    # Derive only identity metadata from the exact staged rows, using the
    # existing producer; no completeness flag, active pointer or served manifest.
    evidence = ROOT / "working/nba-tools-completion-program/source-evidence/rollover-2026-27"
    report = stage_retained_core(evidence, tmp_path / "qualified")
    staged = pd.read_csv(tmp_path / "qualified/staged-player-game-logs.csv", dtype={"GAME_ID": str})
    primary = pd.read_csv(
        tmp_path / "qualified/primary-player-game-logs.csv", dtype={"GAME_ID": str}
    )
    identity = ["GAME_ID", "PLAYER_ID", "PLAYER_NAME"]
    pd.testing.assert_frame_equal(primary[identity], staged[identity])
    documents, _, _ = retained_stats_documents(evidence)
    finder = _table(documents["finder"], "LeagueGameFinderResults")
    root = tmp_path / "stage"
    root.mkdir()
    monkeypatch.chdir(root)
    pull_games.run("2026-27", "Regular Season", raw_frame=finder)
    pull_team_game_stats.run("2026-27", "Regular Season", raw_frame=finder)
    pull_player_game_stats.run("2026-27", "Regular Season", raw_frame=staged)
    names_path = _write_player_names(root / "data")
    assert names_path is not None
    names = names_path.read_bytes()
    indexed = pd.read_csv(names_path)
    assert indexed.player_id.nunique() == 432
    assert set(indexed.season) == {"2026-27"}
    assert set(zip(indexed.player_id, indexed.player_name)) == set(
        zip(staged.PLAYER_ID, staged.PLAYER_NAME)
    )
    metadata = root / "data/metadata"
    assert not (metadata / "backfill_manifest.csv").exists()
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    reset_latest_served_season_cache()
    cases = [
        dict(
            query="Caleb Martin games with at least 10 points and at least 13 minutes in 2026-27 from 2026-10-28 to 2026-10-28",
            game_id=22600142,
            player_id=1628997,
            pts=10,
            minutes=13 + 49 / 60,
        ),
        dict(
            query="Jalen Johnson games with at least 17 points in 2026-27 from 2026-10-29 to 2026-10-29",
            game_id=22600144,
            player_id=1630552,
            pts=17,
            ftm=1,
            fta=1,
        ),
    ]
    try:
        from fastapi.testclient import TestClient

        from nbatools.api import app

        client = TestClient(app)
        answers = []
        for case in cases:
            natural = execute_natural_query(case["query"])
            assert natural.result_status == "ok", natural.metadata
            assert natural.route == "player_game_finder"
            response = client.post("/query", json={"query": case["query"]})
            assert response.status_code == 200
            public = response.json()
            assert public["result_status"] == "ok" and public["route"] == "player_game_finder"
            for result in [natural.result.to_dict(), public["result"]]:
                sections = result["sections"]
                assert len(sections["finder"]) == 1
                row = sections["finder"][0]
                for field in ["game_id", "player_id", "pts", "ftm", "fta", "minutes"]:
                    if field in case:
                        assert row[field] == pytest.approx(case[field], abs=0.001)
            answers.append(dict(query=case["query"], result=public["result"]))
        destination = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "core-stage-consumers"
        destination.mkdir(parents=True, exist_ok=True)
        receipt = dict(
            classification="partial_offline_core_staging_not_full_slice_or_publication",
            staged_identity_sha256=hashlib.sha256(names).hexdigest(),
            staged_identity_rows=len(indexed),
            primary_rows=report["primary_player_rows"],
            staged_rows=report["staged_player_rows"],
            producer="unchanged_pull_player_game_stats_raw_frame",
            natural_and_api_answers=answers,
            production_writes=0,
            full_required_slice_accepted=False,
            starter_roles_accepted=False,
            canonical_pbp_ingestion_accepted=False,
            period_qualification=False,
        )
        (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    finally:
        reset_data_source_cache()
        reset_latest_served_season_cache()
