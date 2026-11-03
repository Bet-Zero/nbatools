"""Real partial collection admission never promotes HTTP success to readiness."""

import json

import pandas as pd
import pytest

from tools.qualify_readiness_partial import qualify, retained_core


def test_original_partial_capture_pipeline_and_quarantines(tmp_path):
    report = qualify(tmp_path / "stage")
    assert report["successful_originals_preserved"] == 602
    assert len(report["admitted_windows"]) == 290
    assert len(report["quarantined_windows"]) == 11
    assert (report["player_rows"], report["team_rows"]) == (6588, 580)
    assert not report["full_snapshot_accepted"] and not report["readiness_accepted"]
    assert report["production_writes"] == 0
    assert [
        (w["game_id"], w["start_period"], w["end_period"]) for w in report["waiting_windows"]
    ] == [("0022600116", 1, 1)]
    assert {w["game_id"] for w in report["quarantined_windows"]} == {
        "0022600002",
        "0022600021",
        "0022600023",
        "0022600087",
        "0022600094",
        "0022600095",
        "0022600097",
        "0022600107",
        "0022600109",
        "0022600110",
    }
    player = report["actual_answers"]["player"][0]
    team = report["actual_answers"]["team"][0]
    assert (player["game_id"], player["pts"], player["fgm"], player["fga"]) == (22600001, 2, 1, 5)
    assert player["minutes"] == pytest.approx(7 + 34 / 60)
    assert player["ts_pct"] == pytest.approx(0.2)
    assert (team["games"], team["wins"], team["pts_avg"], team["plus_minus_avg"]) == (1, 1, 58, 13)
    assert report["actual_answers"]["quarantine_probe_status"] == "no_result"
    path = tmp_path / "stage/stage/data/raw/player_game_period_stats/2026-27_regular_season.csv"
    rows = pd.read_csv(path, dtype={"period_value": str})
    assert not rows.game_id.eq(22600116).any()
    assert not (
        rows.game_id.eq(22600095) & rows.period_family.eq("quarter") & rows.period_value.eq("1")
    ).any()
    assert not (tmp_path / "stage/stage/data/metadata/backfill_manifest.csv").exists()
    assert (
        json.loads((tmp_path / "stage/qualification.json").read_text())["transport_missing"] == 459
    )


def test_retained_context_preserves_old_population():
    players, teams = retained_core()
    assert (len(players), len(teams), players.GAME_ID.nunique()) == (1990, 176, 88)
    # Previously accepted source correction is preserved despite the newly
    # documented filtered-source disagreement; no automatic source precedence.
    naji = players[players.GAME_ID.eq("0022600091") & players.PLAYER_ID.eq(1630230)].iloc[0]
    assert naji.FGA == 13
