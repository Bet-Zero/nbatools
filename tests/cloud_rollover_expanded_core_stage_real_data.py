"""Retained season-wide field reconciliation, entirely offline and unpublished."""

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import pytest

from tools.season_rollover_core_bridge import FIELDS, Source, stage_retained_core

# The hosted required runner selects needs_data and pins the existing generation.
# New season inputs are versioned originals; any missing body fails direct reads.
pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
QUARANTINE_SHA = "2e1f438de7e62dcf0fb967a066ca3db951da231623b4581bc2011bd7cee61941"


def test_retained_expansion_preserves_grains_and_producer_query_values(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from nbatools.api import app
    from nbatools.commands._seasons import reset_latest_served_season_cache
    from nbatools.commands.pipeline import pull_games, pull_player_game_stats, pull_team_game_stats
    from nbatools.commands.pipeline.generation_publication import _write_player_names
    from nbatools.data_source import reset_data_source_cache
    from nbatools.query_service import execute_natural_query

    evidence = ROOT / "working/nba-tools-completion-program/source-evidence/rollover-2026-27"
    retained = evidence / "readiness-reassessment"
    manifest_raw = (retained / "sources.json").read_bytes()
    assert (
        hashlib.sha256(manifest_raw).hexdigest()
        == "e5ece22f60bf71b0976c1447cf854a99c2e842b802f812b69cf1e964d1a2fc51"
    )
    manifest = json.loads(manifest_raw)
    assert manifest["repository"] == "sportsdataverse/hoopR-nba-stats-raw"
    assert manifest["revision"] == "7a1ab93e02f7a4d23443d3c6abb14bafe9c94f11"
    assert (
        manifest["collection_request_sha256"]
        == "d06bb4f3db8a1347f756fe5286493e9fbe44115a1ef3f1211f5ae7c4b30a55b8"
    )
    request = (
        ROOT
        / "working/nba-tools-completion-program/collection-requests/season-rollover-roles-roster-2026-27.json"
    )
    assert hashlib.sha256(request.read_bytes()).hexdigest() == manifest["collection_request_sha256"]
    assert manifest["reader_calls"] == 78 and not manifest["failures"]
    additional, excluded = [], []
    for name, item in manifest["files"].items():
        if item["kind"] != "whole_traditional":
            continue
        path = retained / "sources" / name
        assert not path.is_symlink() and path.stat().st_size < 2_000_000
        raw = path.read_bytes()
        assert len(raw) == item["size_bytes"]
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        assert hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() == item["git_blob_sha"]
        if item["sha256"] == QUARANTINE_SHA:
            assert name == "boxscoretraditionalv3_0022600096.json"
            excluded.append(name)
        else:
            additional.append(Source(name, raw))
    assert len(additional) == 76 and excluded == ["boxscoretraditionalv3_0022600096.json"]
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "expanded-core"
    report = stage_retained_core(
        evidence, output, additional_traditional=additional, reconcile_team_counts=True
    )
    assert report["primary_player_rows"] == report["staged_player_rows"] == 1829
    assert len(report["changed_cells"]) == 115
    assert report["production_writes"] == 0 and report["canonical_core_accepted"] is False
    assert report["canonical_pbp_ingestion_accepted"] is False
    team_report = report["team_reconciliation"]
    assert team_report["primary_team_rows"] == team_report["staged_team_rows"] == 162
    assert sum(x["field"] in FIELDS.values() for x in team_report["changed_cells"]) == 15
    staged = pd.read_csv(output / "staged-player-game-logs.csv", dtype={"GAME_ID": str})
    primary = pd.read_csv(output / "primary-player-game-logs.csv", dtype={"GAME_ID": str})
    teams = pd.read_csv(output / "staged-team-game-logs.csv", dtype={"GAME_ID": str})
    primary_teams = pd.read_csv(output / "primary-team-game-logs.csv", dtype={"GAME_ID": str})
    pd.testing.assert_frame_equal(
        primary[["GAME_ID", "PLAYER_ID", "PLAYER_NAME"]],
        staged[["GAME_ID", "PLAYER_ID", "PLAYER_NAME"]],
    )
    assert primary.PTS.sum() == 18461 and staged.PTS.sum() == teams.PTS.sum() == 18464
    for original, candidate, identity, changes in [
        (primary, staged, "PLAYER_ID", report["changed_cells"]),
        (primary_teams, teams, "TEAM_ID", team_report["changed_cells"]),
    ]:
        original = original.set_index(["GAME_ID", identity])
        candidate = candidate.set_index(["GAME_ID", identity])
        changed_keys = {(x["game_id"], x[identity.lower()], x["field"]) for x in changes}
        for column in original:
            allowed = [(g, p) for g, p, field in changed_keys if field == column]
            pd.testing.assert_series_equal(
                original[column].drop(index=allowed), candidate[column].drop(index=allowed)
            )
        # The malformed supplementary game contributes no numeric observation.
        pd.testing.assert_frame_equal(original.loc[["0022600096"]], candidate.loc[["0022600096"]])
    root = tmp_path / "producer"
    root.mkdir()
    monkeypatch.chdir(root)
    pull_games.run("2026-27", "Regular Season", raw_frame=teams)
    pull_team_game_stats.run("2026-27", "Regular Season", raw_frame=teams)
    pull_player_game_stats.run("2026-27", "Regular Season", raw_frame=staged)
    assert _write_player_names(root / "data") is not None
    for frame, grain in [(staged, "player"), (teams, "team")]:
        produced = pd.read_csv(root / f"data/raw/{grain}_game_stats/2026-27_regular_season.csv")
        keys = ["GAME_ID", f"{grain.upper()}_ID"]
        expected = frame.assign(GAME_ID=pd.to_numeric(frame.GAME_ID)).set_index(keys).sort_index()
        actual = produced.set_index([x.lower() for x in keys]).sort_index()
        for field in FIELDS.values():
            assert actual[field.lower()].tolist() == expected[field].tolist()
    assert not (root / "data/metadata/backfill_manifest.csv").exists()
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    reset_latest_served_season_cache()
    cases = [
        (
            "Cameron Boozer games with at least 16 points in 2026-27 from 2026-10-25 to 2026-10-25",
            "player_game_finder",
            "player_id",
            1643409,
            {"pts": 16, "fgm": 6},
        ),
        (
            "Memphis Grizzlies games with at least 50 rebounds in 2026-27 from 2026-10-25 to 2026-10-25",
            "game_finder",
            "team_abbr",
            "MEM",
            {"oreb": 18, "dreb": 36, "reb": 54},
        ),
    ]
    answers = []
    try:
        client = TestClient(app)
        for query, route, identity, identifier, expected in cases:
            natural = execute_natural_query(query)
            assert natural.result_status == "ok" and natural.route == route, natural.metadata
            response = client.post("/query", json={"query": query})
            assert response.status_code == 200
            body = response.json()
            assert body["result_status"] == "ok" and body["route"] == route
            for result in [natural.result.to_dict(), body["result"]]:
                rows = result["sections"]["finder"]
                assert len(rows) == 1 and rows[0][identity] == identifier
                assert rows[0]["game_id"] == 22600118
                for field, value in expected.items():
                    assert rows[0][field] == value
            answers.append(dict(query=query, response=body))
            (output / "answers.json").write_text(json.dumps(answers, indent=2) + "\n")
    finally:
        reset_data_source_cache()
        reset_latest_served_season_cache()
