"""Retained real structured sources: four eras, exact rows and public consumers."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.pipeline.pull_player_game_availability import validate_publication
from nbatools.commands.pipeline.structured_participation import stage_structured_game
from nbatools.data_source import data_read_csv, reset_data_source_cache
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "working/nba-tools-completion-program/source-evidence/k08-structured"
)
SOURCE = EVIDENCE / "sources"
PROVENANCE = json.loads((EVIDENCE / "sources.json").read_text())
# Expectations fixed separately from producer; checker rederives originals.
CASES = [
    ("1997-98", 29700002, "NJN", "Kerry Kittles", 24, 20, 97, 95),
    ("2004-05", 20400001, "DET", "Darko Milicic", 24, 21, 87, 79),
    ("2014-15", 21400001, "NOP", "Darius Miller", 30, 23, 101, 84),
    ("2025-26", 22500002, "LAL", "LeBron James", 34, 20, 109, 119),
]


def stage(tmp_path, season, gid, version=2):
    root = tmp_path / "data"
    suffix = f"{season}_regular_season.csv"
    for kind in ["games", "team_game_stats", "player_game_stats"]:
        target = root / "raw" / kind / suffix
        target.parent.mkdir(parents=True, exist_ok=True)
        data_read_csv("data/raw/" + kind + "/" + suffix).to_csv(target, index=False)
    paths = []
    for ep in ["boxscoretraditionalv3", f"boxscoresummaryv{version}"]:
        name = f"{ep}_{gid:010d}.json"
        record = PROVENANCE["files"][name]
        path = SOURCE / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
        assert path.stat().st_size == record["size_bytes"]
        paths.append(path)
    captured = max(PROVENANCE["files"][p.name]["retrieved_at"] for p in paths)
    rows = stage_structured_game(
        root,
        season=season,
        season_type="Regular Season",
        game_id=gid,
        traditional=paths[0],
        summary=paths[1],
        summary_version=version,
        revision=PROVENANCE["revision"],
        retrieved_at=captured,
    )
    return root, rows


@pytest.mark.parametrize("season,gid,team,person,count,played,points,opponent_points", CASES)
def test_retained_structured_game_and_answers(
    tmp_path, monkeypatch, season, gid, team, person, count, played, points, opponent_points
):
    root, rows = stage(tmp_path, season, gid)
    assert len(rows) == count and rows.participation_state.eq("played").sum() == played
    assert rows.participation_state.eq("did_not_play").sum() == count - played
    assert rows.coverage_scope.eq("listed_player_rows_only").all()
    assert rows.loc[rows.player_name.eq(person), "participation_state"].item() == "did_not_play"
    validate_publication(root)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    day = rows.game_date.iloc[0]
    for result in [
        execute_structured_query(
            "team_record",
            team=team,
            season=season,
            without_player=person,
            start_date=day,
            end_date=day,
        ),
        execute_natural_query(f"{team} record without {person} in {season} from {day} to {day}"),
    ]:
        assert result.result_status == "ok", result.metadata
        sections = result.result.to_dict()["sections"]
        summary = sections["summary"][0]
        assert (summary["games"], summary["wins"], summary["losses"], summary["pts_avg"]) == (
            1,
            int(points > opponent_points),
            int(points < opponent_points),
            points,
        )
        assert [int(r["game_id"]) for r in sections["game_log"]] == [gid]
        assert sections["game_log"][0]["opponent_pts"] == opponent_points
    wider = execute_structured_query("team_record", team=team, season=season, without_player=person)
    assert wider.result_status == "no_result"
    reset_data_source_cache()


def test_summary_v3_matches_v2_and_existing_qualified_official_rows(tmp_path, monkeypatch):
    root, rows = stage(tmp_path, "2025-26", 22500002, version=3)
    baseline = data_read_csv("data/raw/player_game_availability/2025-26_regular_season.csv")
    baseline = baseline.loc[pd.to_numeric(baseline.game_id).eq(22500002)]
    keys = ["game_id", "team_id", "player_id", "participation_state"]
    assert set(map(tuple, rows[keys].to_numpy())) == set(map(tuple, baseline[keys].to_numpy()))
    assert len(rows) == len(baseline) == 34
    validate_publication(root)
    from nbatools.commands import _participation_observations as observations

    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    game = pd.Series(
        dict(
            game_id=22500002,
            team_id=1610612747,
            opponent_team_id=1610612744,
            game_date="2025-10-21",
        )
    )
    with pytest.raises(ValueError, match="precise report time"):
        observations.qualified_report_seconds(
            game, "Luka Doncic", ["2025-26"], "Regular Season", played=True
        )
    reset_data_source_cache()


def test_legacy_invalid_duration_remains_unqualified(tmp_path):
    with pytest.raises(ValueError, match="29:60"):
        stage(tmp_path, "1997-98", 29700001)
    assert not (tmp_path / "data/raw/player_game_availability/1997-98_regular_season.csv").exists()


def test_historical_pair_bound_and_same_game_other_team(tmp_path, monkeypatch):
    root, rows = stage(tmp_path, "1997-98", 29700002)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    result = execute_natural_query(
        "Nets record with at least 95 points without Kerry Kittles and Keith Van Horn in 1997-98 from 1997-10-31 to 1997-10-31"
    )
    assert result.result_status == "ok", result.metadata
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert (summary["games"], summary["wins"], summary["pts_avg"]) == (1, 1, 97)
    result = execute_structured_query(
        "team_record",
        team="IND",
        season="1997-98",
        without_player="Kerry Kittles",
        start_date="1997-10-31",
        end_date="1997-10-31",
    )
    assert result.result_reason == "no_match"
    from fastapi.testclient import TestClient

    from nbatools.api import app

    response = TestClient(app).post(
        "/query",
        json={
            "query": "New Jersey Nets record without Kerry Kittles and Keith Van Horn in 1997-98 from 1997-10-31 to 1997-10-31"
        },
    )
    assert response.status_code == 200
    assert response.json()["result_status"] == "ok"
    assert response.json()["result"]["sections"]["summary"][0]["pts_avg"] == 97

    reset_data_source_cache()


def test_targeted_pdf_fallback_and_date_bounded_missed_counts(tmp_path, monkeypatch):
    from nbatools.commands.pipeline import player_game_availability_report as report
    from nbatools.commands.pipeline.pull_player_game_availability import backfill

    root, _ = stage(tmp_path, "2025-26", 22500002)
    for dataset, filename in [
        ("player_game_stats", "2024-25_regular_season.csv"),
        ("rosters", "2025-26.csv"),
        ("rosters", "2024-25.csv"),
    ]:
        destination = root / "raw" / dataset / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        data_read_csv(f"data/raw/{dataset}/{filename}").to_csv(destination, index=False)
    cache = EVIDENCE.parent / "k08-three-reports/acquired_data/raw/player_game_availability_sources"

    def no_fetch(*args, **kwargs):
        raise AssertionError("Retained fallback must never refetch any endpoint")

    monkeypatch.setattr(report.urllib.request, "urlopen", no_fetch)
    output = backfill(
        "2025-26",
        root=root,
        source="report",
        cached_reports=cache,
        game_ids=[22500019, 22500113, 22500122],
    )
    selected = output.loc[output.game_id.astype(int).isin([22500019, 22500113, 22500122])]
    # Checker used pdftotext and own ID/state parser: includes DND rows.
    assert selected.groupby("game_id").size().to_dict() == {
        "0022500019": 34,
        "0022500113": 35,
        "0022500122": 35,
    }
    assert selected.participation_state.eq("played").sum() == 70
    assert selected.participation_state.eq("did_not_play").sum() == 34
    validate_publication(root)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    record = execute_natural_query(
        "Lakers record without LeBron James from 2025-10-24 to 2025-10-27 in 2025-26"
    )
    assert record.result_status == "ok", record.metadata
    summary = record.result.to_dict()["sections"]["summary"][0]
    assert (summary["games"], summary["wins"], summary["losses"], summary["pts_avg"]) == (
        3,
        2,
        1,
        121,
    )
    assert [int(r["game_id"]) for r in record.result.to_dict()["sections"]["game_log"]] == [
        22500019,
        22500113,
        22500122,
    ]
    for query, expected in [
        ("how many games did LeBron James miss from 2025-10-24 to 2025-10-27 in 2025-26", 3),
        ("how many home games did LeBron miss between October 24 and October 27 in 2025-26", 2),
        ("number of games LeBron James missed on October 26, 2025", 1),
    ]:
        result = execute_natural_query(query)
        assert result.result_status == "ok", result.metadata
        assert result.route == "game_finder"
        assert result.result.to_dict()["sections"]["count"][0]["count"] == expected
        assert "LeBron James missed" in result.metadata["answer_phrase"]
    pair = execute_natural_query(
        "Austin Reaves games with at least 40 points without LeBron James and Luka Doncic from 2025-10-24 to 2025-10-27 in 2025-26"
    )
    assert pair.result_status == "ok", pair.metadata
    rows = pair.result.to_dict()["sections"]["finder"]
    assert [(int(r["game_id"]), r["pts"], r["reb"], r["ast"]) for r in rows] == [
        (22500113, 51, 11, 9),
        (22500122, 41, 4, 5),
    ]
    unknown = execute_structured_query(
        "team_record", team="LAL", season="2025-26", without_player="LeBron James"
    )
    assert unknown.result_status == "no_result"  # full-season remaining unknowns are not zero
    reset_data_source_cache()
