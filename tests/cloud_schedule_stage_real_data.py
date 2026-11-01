"""Existing published guard preservation and retained current-season team questions.

The isolated four-file source stage is deliberately untrusted/unpublished. It
cannot satisfy the full eleven-raw/five-processed publication contract.
"""

import hashlib
import json
import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands._seasons import reset_latest_served_season_cache
from nbatools.commands.pipeline import pull_games, pull_schedule, pull_team_game_stats
from nbatools.commands.pipeline.official_schedule import (
    normalize_official_schedule,
    official_final_rows,
    validate_schedule_game_coverage,
    validate_schedule_team_coverage,
)
from nbatools.data_source import data_read_text, reset_data_source_cache
from nbatools.query_service import execute_natural_query
from nbatools.readiness import (
    NEW_SEASON_NOT_LOADED,
    _missing_due_game_ids,
    build_readiness_info,
)
from tools.r2_publication import verify_answer
from tools.season_rollover_source_stats import retained_stats_documents

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "working/nba-tools-completion-program/source-evidence/rollover-2026-27"
BASE = "availability-lebron-season-v1-20261031"
BASE_SHA = "3073653a50872a4c25bb573c3b4c0540e6e3204e8a4caef5c548eb2dff1e0cf3"


def test_retained_schedule_and_team_records_preserve_strict_production_readiness(
    tmp_path, monkeypatch
):
    assert os.environ["NBATOOLS_DATA_GENERATION"] == BASE
    assert (
        hashlib.sha256(
            data_read_text("data/metadata/generation_manifest.json").encode()
        ).hexdigest()
        == BASE_SHA
    )
    now = datetime.now(UTC)
    published = build_readiness_info(checked_at=now, env={})
    assert published.active_generation == BASE and not published.ready
    assert [b.code for b in published.blockers] == [NEW_SEASON_NOT_LOADED]
    assert all(item.missing_due_game_ids == () for item in published.slices)
    assert not published.exception.applied
    documents, _, bundle_hash = retained_stats_documents(EVIDENCE)
    table = documents["finder"]["resultSets"][0]
    finder = pd.DataFrame(table["rowSet"], columns=table["headers"])
    with zipfile.ZipFile(EVIDENCE / "schedule-capture.zip") as archive:
        original = archive.read(
            "acquired_data/rollover-2026-27-schedule/scheduleleaguev2-2027.json"
        )
    assert (
        hashlib.sha256(original).hexdigest()
        == "edf45e0c7f06ba0f5c842a333d054b617f23244443514fb4aa9771a6b32b75cf"
    )
    schedule = normalize_official_schedule(original, "2026-27")
    final = official_final_rows(schedule)
    assert len(schedule) == 1206 and len(final) == 81
    root = tmp_path / "stage"
    root.mkdir()
    monkeypatch.chdir(root)
    pull_games.run("2026-27", "Regular Season", raw_frame=finder)
    pull_team_game_stats.run("2026-27", "Regular Season", raw_frame=finder)
    pull_schedule.run("2026-27", "Regular Season", official_original=original)
    games = pd.read_csv("data/raw/games/2026-27_regular_season.csv")
    teams = pd.read_csv("data/raw/team_game_stats/2026-27_regular_season.csv")
    validate_schedule_game_coverage(schedule, games)
    validate_schedule_team_coverage(schedule, teams)
    assert _missing_due_game_ids(schedule, games, now, "2026-27", "Regular Season") == ()
    # The independent oracle uses original schedule scores/sides, not Finder WL.
    oracle = {}
    for _, game in final.iterrows():
        for side, opponent in [("home", "away"), ("away", "home")]:
            team = int(game[f"source_{side}_team_id"])
            row = oracle.setdefault(team, dict(games=0, wins=0, losses=0, points=0))
            row["games"] += 1
            row["wins"] += int(game[f"{side}_score"] > game[f"{opponent}_score"])
            row["losses"] += int(game[f"{side}_score"] < game[f"{opponent}_score"])
            row["points"] += int(game[f"{side}_score"])
    assert len(oracle) == 30 and sum(r["games"] for r in oracle.values()) == 162
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    reset_latest_served_season_cache()
    answers = []
    try:
        abbreviations = finder.drop_duplicates("TEAM_ID").set_index("TEAM_ID").TEAM_ABBREVIATION
        for team, expected in sorted(oracle.items()):
            question = f"{abbreviations.loc[team]} record in 2026-27"
            result = execute_natural_query(question)
            assert result.result_status == "ok", result.metadata
            actual = result.result.to_dict()["sections"]["summary"][0]
            assert result.route == "team_record"
            assert actual["season_start"] == actual["season_end"] == "2026-27"
            for field in ["games", "wins", "losses"]:
                assert actual[field] == expected[field]
            assert actual["pts_avg"] == pytest.approx(
                expected["points"] / expected["games"], abs=0.001
            )
            answers.append(dict(query=question, summary=actual))
        from fastapi.testclient import TestClient

        from nbatools.api import app

        client = TestClient(app)
        api_answers = []
        for abbreviation in ["BOS", "LAL", "CHA"]:
            case = next(r for r in answers if r["query"] == f"{abbreviation} record in 2026-27")
            response = client.post("/query", json={"query": case["query"]})
            assert response.status_code == 200
            api_answers.append(verify_answer(case, response.json()))
        staged_readiness = build_readiness_info(checked_at=now, env={})
        assert not staged_readiness.ready
        assert {b.code for b in staged_readiness.blockers} >= {
            "immutable_generation_required",
            "regular_season_slice_untrusted",
        }
        assert not (root / "data/metadata/backfill_manifest.csv").exists()
        receipt = dict(
            classification="partial_development_stage_team_questions_only_not_publication",
            base_generation=BASE,
            base_manifest_sha256=BASE_SHA,
            source_stats_bundle_sha256=bundle_hash,
            observed_final_games=81,
            team_rows=162,
            observed_schedule_games=1206,
            team_question_answers=answers,
            api_answers=api_answers,
            production_readiness=published.to_dict(),
            staged_readiness=staged_readiness.to_dict(),
            full_required_slice_accepted=False,
            player_statistical_qualification=False,
            period_qualification=False,
            production_writes=0,
        )
        destination = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "schedule-stage-consumers"
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    finally:
        reset_data_source_cache()
        reset_latest_served_season_cache()
