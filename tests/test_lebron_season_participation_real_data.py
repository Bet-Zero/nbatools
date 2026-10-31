"""Authorized retained originals close an observed-season sample in staging only."""

import hashlib
import json
import os
import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_path, data_read_csv, reset_data_source_cache
from nbatools.query_service import execute_natural_query
from tools.participation_coverage import build_report
from tools.stage_participation_collection import build_stage

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"
REQUEST = PROGRAM / "collection-requests/lebron-structured-remaining-2025-26.json"
SOURCES = PROGRAM / "source-evidence/k08-lebron-remaining"
CSV = "raw/player_game_availability/2025-26_regular_season.csv"


def test_authorized_sources_qualify_full_observed_season_and_home_counts(tmp_path, monkeypatch):
    request = json.loads(REQUEST.read_text())
    proposed = {int(row["game_id"]) for row in request["requirements"]}
    published_dnp = {22500002, 22500338, 22500019, 22500113, 22500122}
    expected_ids = proposed | published_dnp
    assert len(proposed) == 17 and len(expected_ids) == 22
    # Independent source-reader oracle: all17SummaryV3 bodies explicitly list
    # 2544 on LAL. Traditional omission is never the absence predicate.
    new_home = set()
    for gid in sorted(proposed):
        box = json.loads((SOURCES / f"sources/boxscoresummaryv3_{gid:010d}.json").read_bytes())[
            "boxScoreSummary"
        ]
        listed = [
            (side, p)
            for side in ("homeTeam", "awayTeam")
            for p in box[side]["inactives"]
            if int(p["personId"]) == 2544
        ]
        assert len(listed) == 1 and int(box[listed[0][0]]["teamId"]) == 1610612747
        if listed[0][0] == "homeTeam":
            new_home.add(gid)
    assert len(new_home) == 8
    expected_home = new_home | {22500002, 22500019, 22500122}
    assert len(expected_home) == 11
    teams = data_read_csv("data/raw/team_game_stats/2025-26_regular_season.csv")
    own = teams.loc[teams.team_id.eq(1610612747)]
    assert len(own) == own.game_id.nunique() == 82
    missed = own.loc[own.game_id.isin(expected_ids)]
    assert len(missed) == 22
    home = missed.loc[missed.is_home.astype(str).str.lower().isin(["1", "1.0", "true"])]
    assert set(home.game_id) == expected_home
    new = missed.loc[missed.game_id.isin(proposed)]
    assert (int(new.wl.eq("W").sum()), int(new.wl.eq("L").sum()), int(new.pts.sum())) == (
        12,
        5,
        1933,
    )
    core = {
        f"raw/{kind}/2025-26_regular_season.csv": hashlib.sha256(
            data_path(f"data/raw/{kind}/2025-26_regular_season.csv").read_bytes()
        ).hexdigest()
        for kind in ("games", "team_game_stats", "player_game_stats")
    }
    work = tmp_path / "stage"
    destination = tmp_path / "lebron17-overlay"
    validation = build_stage(
        REQUEST, SOURCES, work, destination, candidate_sha=os.environ["VALIDATION_SHA"]
    )
    root = work / "data"
    for path, digest in core.items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest
    states = pd.read_csv(root / CSV)
    added = states.loc[states.game_id.isin(proposed)]
    assert len(added) == 598
    assert added.participation_state.value_counts().to_dict() == {
        "played": 372,
        "did_not_play": 226,
    }
    lebron = states.loc[states.player_id.eq(2544) & states.participation_state.eq("did_not_play")]
    assert set(lebron.game_id) == expected_ids
    assert added.loc[added.player_id.eq(2544), "team_id"].eq(1610612747).all()

    # A test-only local manifest binds the isolated staged view for the report.
    # It is outside the exported overlay and is never a production generation.
    entries = []
    for path in sorted(root.rglob("*")):
        if (
            path.is_file()
            and path.relative_to(root).as_posix() != "metadata/generation_manifest.json"
        ):
            raw = path.read_bytes()
            entries.append(
                dict(
                    path=path.relative_to(root).as_posix(),
                    size_bytes=len(raw),
                    sha256=hashlib.sha256(raw).hexdigest(),
                )
            )
    manifest = json.dumps(
        dict(generation_id="legacy", classification="test_only_development_staging", files=entries)
    ).encode()
    (root / "metadata/generation_manifest.json").write_bytes(manifest)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(work))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    try:
        report = build_report(
            generation="legacy",
            manifest_sha256=hashlib.sha256(manifest).hexdigest(),
            season="2025-26",
            team_id=1610612747,
            player_id=2544,
        )
        assert report["requested_games"] == 82 and report["complete_requested_population"]
        assert report["counts"] == dict(
            played=60, did_not_play=22, same_game_other_side=0, unknown=0
        )
        assert report["missed_games"] == 22 and not report["missing_keys"]
        queries = [
            ("how many games has LeBron missed this season", expected_ids),
            ("how many home games did LeBron miss in 2025-26", expected_home),
        ]
        for question, expected in queries:
            result = execute_natural_query(question)
            assert result.result_status == "ok", result.metadata
            sections = result.result.to_dict()["sections"]
            assert result.route == "game_finder" and sections["count"] == [{"count": len(expected)}]
            assert {int(row["game_id"]) for row in sections["finder"]} == expected
        record = execute_natural_query("Lakers record without LeBron James in 2025-26")
        assert record.result_status == "ok", record.metadata
        summary = record.result.to_dict()["sections"]["summary"][0]
        assert (summary["games"], summary["wins"], summary["losses"]) == (
            22,
            int(missed.wl.eq("W").sum()),
            int(missed.wl.eq("L").sum()),
        )
        assert summary["pts_avg"] == pytest.approx(missed.pts.mean(), abs=0.001)
        from fastapi.testclient import TestClient

        from nbatools.api import app

        response = TestClient(app).post("/query", json={"query": queries[1][0]})
        assert response.status_code == 200 and response.json()["result_status"] == "ok"
        assert response.json()["result"]["sections"]["count"] == [{"count": 11}]
        receipt = dict(
            classification="qualified_development_staging_only_no_publication",
            base_generation=request["base_generation"],
            base_manifest_sha256=request["base_manifest_sha256"],
            validation=validation,
            coverage=report,
            missed_game_ids=sorted(expected_ids),
            home_missed_game_ids=sorted(expected_home),
            team_record=summary,
        )
        (destination / "consumer-acceptance.json").write_text(
            json.dumps(receipt, indent=2, default=str) + "\n"
        )
        if output := os.environ.get("NBATOOLS_ACQUISITION_OUTPUT"):
            # The existing protected publisher consumes acquired_data/raw/... .
            # Export only after every consumer assertion passes, preserving the
            # original overlay bytes and excluding the test-only local manifest.
            export = Path(output)
            export.mkdir(parents=True, exist_ok=True)
            if any(export.iterdir()):
                raise ValueError("Publication transport requires a new empty export directory")
            shutil.copytree(destination, export, dirs_exist_ok=True)
    finally:
        reset_data_source_cache()
