"""Real retained originals through canonical import, validation and consumers."""

import copy
import json
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.pipeline import pull_game_period_stats as importer
from tools.qualify_rollover_q1 import qualify
from tools.stage_rollover_periods import import_window


def test_original_q1_pipeline_and_actual_consumers(tmp_path):
    report = qualify(tmp_path / "q1")
    assert report["staged_player_rows"] == 22
    assert report["staged_team_rows"] == 2
    assert report["zero_q1_player_ids"] == [1629750, 1630568, 1642864]
    assert report["windows"] == [["quarter", "1"]]
    assert report["production_writes"] == 0 and not report["readiness_accepted"]
    answers = {x.get("player", x.get("team")): x["result"][0] for x in report["answers"]}
    cade, tatum, huerter = [
        answers[name] for name in ["Cade Cunningham", "Jayson Tatum", "Kevin Huerter"]
    ]
    assert all(x["game_id"] == 22600001 for x in [cade, tatum, huerter])
    assert (cade["pts"], cade["fgm"], cade["fga"], cade["minutes"]) == (6, 3, 5, 9.25)
    assert (cade["usg_pct"], cade["ast_pct"], cade["tov_pct"]) == (0.318, 0.333, 0.222)
    assert (tatum["pts"], tatum["ast"], tatum["reb"], tatum["minutes"]) == (7, 4, 3, 12)
    assert tatum["ts_pct"] == pytest.approx(7 / (2 * (9 + 0.44)))
    assert (huerter["efg_pct"], huerter["ts_pct"]) == (1.5, 1.5)
    assert answers["Luka Garza"]["minutes"] == answers["Luka Garza"]["pts"] == 0
    assert (answers["BOS"]["games"], answers["BOS"]["wins"], answers["BOS"]["pts_avg"]) == (
        1,
        1,
        28,
    )
    assert report["unobserved_q2_consumer_status"] == "no_result"
    assert not (tmp_path / "q1/stage/data/metadata/backfill_manifest.csv").exists()


@pytest.mark.parametrize("ratio", [0, 0.5, 1, 22.2, 100])
def test_v3_turnover_ratio_has_fixed_percent_point_units(ratio):
    raw = pd.DataFrame(
        [
            dict(
                gameId="0022600001",
                teamId=1,
                personId=2,
                usagePercentage=0.318,
                assistPercentage=0.333,
                reboundPercentage=0.13,
                turnoverRatio=ratio,
            )
        ]
    )
    row = importer.normalize_boxscore_player_advanced_rows(raw).iloc[0]
    assert row.tov_pct == pytest.approx(ratio / 100)
    assert (row.usg_pct, row.ast_pct, row.reb_pct) == (0.318, 0.333, 0.13)


@pytest.mark.parametrize("damage", ["clock", "score", "rate", "identity", "margin"])
def test_window_admission_rejects_source_damage(tmp_path, damage):
    qualify(tmp_path / "q1")
    original = tmp_path / "q1/original/sources"
    t = json.loads((original / "boxscoretraditionalv3_0022600001_q1.json").read_text())
    a = json.loads((original / "boxscoreadvancedv3_0022600001_q1.json").read_text())
    p = t["boxScoreTraditional"]["homeTeam"]["players"][0]
    if damage == "clock":
        p["statistics"]["minutes"] = "8:60"
    elif damage == "score":
        p["statistics"]["points"] += 1
    elif damage == "rate":
        a["boxScoreAdvanced"]["homeTeam"]["players"][0]["statistics"]["usagePercentage"] = 2
    elif damage == "margin":
        t["boxScoreTraditional"]["homeTeam"]["statistics"]["plusMinusPoints"] = 1
    else:
        p["personId"] = 1
    root = tmp_path / "q1/stage/data/raw"
    players = pd.read_csv(root / "player_game_stats/2026-27_regular_season.csv")
    teams = pd.read_csv(root / "team_game_stats/2026-27_regular_season.csv")
    if "wl" not in players:
        players = players.merge(teams[["game_id", "team_id", "wl"]], on=["game_id", "team_id"])
    summary = json.loads(
        (
            Path(__file__).parents[1]
            / "working/nba-tools-completion-program/source-evidence/rollover-2026-27/period-q1-0022600001/summary.json"
        ).read_text()
    )
    with pytest.raises(ValueError):
        import_window(
            json.dumps(t).encode(),
            json.dumps(a).encode(),
            game_id="0022600001",
            window=importer.PERIOD_WINDOWS[0],
            summary=copy.deepcopy(summary),
            player_context=players,
            team_context=teams,
        )
