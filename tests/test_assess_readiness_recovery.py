"""Full-slice assessment retains missing obligations and source disagreements."""

import json
from datetime import UTC, datetime

import pandas as pd
import pytest

from tools.assess_readiness_recovery import SUFFIX, assess, due_population, source_basis_report


def save(root, name, rows):
    path = root / "data/raw" / name / SUFFIX
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def test_numeric_disagreement_cannot_rewrite_core_or_advanced(tmp_path):
    save(
        tmp_path,
        "player_game_stats",
        [
            dict(player_id=11, pts=10, fga=10, fta=0),
            dict(player_id=11, pts=2, fga=2, fta=0),
            dict(player_id=22, pts=0, fga=0, fta=0),
        ],
    )
    save(
        tmp_path,
        "player_season_advanced",
        [
            dict(player_id=11, player_name="Controlled One", ts_pct=0.6, usage_rate=0.2),
            dict(player_id=22, player_name="Controlled Zero", ts_pct=0.0, usage_rate=0.0),
        ],
    )
    before = {p: p.read_bytes() for p in tmp_path.rglob("*.csv")}
    report = source_basis_report(tmp_path)
    assert report["compared_player_ids"] == 2
    assert len(report["ts_conflicts"]) == 1
    conflict = report["ts_conflicts"][0]
    assert (
        conflict["player_id"],
        conflict["pts"],
        conflict["fga"],
        conflict["expected_ts"],
        conflict["source_ts"],
    ) == (11, 12, 12, 0.5, 0.6)
    assert report["usage_source_range_check"]
    assert report["usage_independent_numeric_basis"] == "not established by a range check"
    assert not report["full_source_coherence"] and not report["source_values_rewritten"]
    assert {p: p.read_bytes() for p in before} == before


def test_advanced_population_mismatch_blocks_assessment(tmp_path):
    save(tmp_path, "player_game_stats", [dict(player_id=11, pts=10, fga=10, fta=0)])
    save(
        tmp_path,
        "player_season_advanced",
        [dict(player_id=22, player_name="Wrong identity", ts_pct=0.5, usage_rate=0.2)],
    )
    with pytest.raises(ValueError, match="population differs"):
        source_basis_report(tmp_path)


def test_due_population_exact_twenty_four_hour_boundary(tmp_path):
    save(
        tmp_path,
        "schedule",
        [
            dict(game_id=22600001, game_date="2026-11-02", game_datetime="2026-11-02T23:00:00Z"),
            dict(game_id=22600002, game_date="2026-11-03", game_datetime="2026-11-03T00:00:01Z"),
        ],
    )
    # The second UTC instant still belongs to November 2 in Eastern time.
    schedule_path = tmp_path / "data/raw/schedule" / SUFFIX
    schedule = pd.read_csv(schedule_path)
    schedule.loc[1, "game_date"] = "2026-11-02"
    schedule.to_csv(schedule_path, index=False)
    save(tmp_path, "games", [dict(game_id=22600001, game_date="2026-11-02", is_final=1)])
    result = due_population(tmp_path, datetime(2026, 11, 4, 0, 0, 1, tzinfo=UTC))
    assert result["due_game_ids"] == ["0022600001", "0022600002"]
    assert result["missing_due_game_ids"] == ["0022600002"]
    earlier = due_population(tmp_path, datetime(2026, 11, 4, 0, 0, 0, tzinfo=UTC))
    assert earlier["due_game_ids"] == ["0022600001"]
    assert earlier["missing_due_game_ids"] == []


def test_all_sixteen_obligations_remain_when_period_sources_are_missing(tmp_path):
    """Real retained core can build features; absent period rows still block."""
    from nbatools.commands.pipeline import pull_games, pull_player_game_stats, pull_team_game_stats
    from tools.qualify_readiness_recovery import (
        RECOVERY,
        SUPPLEMENT_SHA,
        checked_archive,
        recovery_context,
    )
    from tools.qualify_rollover_q1 import _local_stage

    with checked_archive(RECOVERY / "supplementary-sources.zip", SUPPLEMENT_SHA) as z:
        schedule = json.loads(z.read("schedule-current.json"))
    players, teams, _, _ = recovery_context(schedule)
    stage = tmp_path / "input"
    stage.mkdir()
    with _local_stage(stage):
        pull_games.run("2026-27", "Regular Season", raw_frame=teams)
        pull_team_game_stats.run("2026-27", "Regular Season", raw_frame=teams)
        pull_player_game_stats.run("2026-27", "Regular Season", raw_frame=players)
    result = assess(
        stage, tmp_path / "assessment", checked_at=datetime(2026, 11, 4, 3, 40, tzinfo=UTC)
    )
    assert (result["required_raw"], result["required_processed"]) == (11, 5)
    assert len(result["required_records"]) == 16
    assert result["required_present"] == 14
    assert result["manifest_state"] == "failed"
    failed = {r["name"] for r in result["required_records"] if r["validation"]["state"] == "failed"}
    assert failed == {"schedule", "player_game_period_stats", "team_game_period_stats"}
    assert len(result["numerical_source_basis"]["ts_conflicts"]) == 12
    minutes = result["snapshot_record_consistency"]
    unresolved = {r["identity"] for r in minutes["precision_boundary_unresolved"]}
    assert unresolved == {1629656, 1630192, 1630695, 1642942, 1643544}
    assert {
        r["identity"] for r in minutes["conflicts"] if r["field"] == "minutes_per_game"
    }.isdisjoint({1629656, 1643544})
    assert len(minutes["conflicts"]) == 9
    assert not minutes["passed"]
    assert len(result["exact_due_population"]["due_game_ids"]) == 107
    assert result["exact_due_population"]["missing_due_game_ids"] == [
        f"0022600{n}" for n in range(158, 173)
    ]
    assert result["source_input_preserved"]
    assert not result["full_snapshot_accepted"] and not result["readiness_accepted"]
    assert not result["trusted_acceptance_receipt_created"] and result["production_writes"] == 0
    assert not (stage / "data/metadata/backfill_manifest.csv").exists()


def test_snapshot_count_and_record_conflicts_stay_visible(tmp_path):
    from tools.assess_readiness_recovery import snapshot_record_checks

    save(
        tmp_path,
        "player_game_stats",
        [dict(player_id=11, minutes=1.06), dict(player_id=11, minutes=1.06)],
    )
    save(tmp_path, "team_game_stats", [dict(team_id=22, wl="W"), dict(team_id=22, wl="L")])
    save(
        tmp_path,
        "player_season_advanced",
        [dict(player_id=11, games_played=1, minutes_per_game=1.0)],
    )
    save(
        tmp_path,
        "team_season_advanced",
        [
            dict(
                team_id=22,
                games_played=2,
                wins=1,
                losses=1,
                off_rating=110.0,
                def_rating=105.0,
                net_rating=4.0,
            )
        ],
    )
    save(tmp_path, "standings_snapshots", [dict(team_id=22, wins=2, losses=0)])
    result = snapshot_record_checks(tmp_path)
    assert not result["passed"]
    assert {(r["dataset"], r["field"]) for r in result["conflicts"]} == {
        ("player_season_advanced", "games_played"),
        ("player_season_advanced", "minutes_per_game"),
        ("team_season_advanced", "net_rating"),
        ("standings_snapshots", "wins"),
        ("standings_snapshots", "losses"),
    }


def test_minute_interval_preserves_subseconds_and_inclusive_boundary_uncertainty():
    from fractions import Fraction

    from tools.assess_readiness_recovery import minute_mean_interval

    # This is a tenth-second primary clock, not a whole-second clock.
    low, high = minute_mean_interval(["27.473333333333333"])
    assert low <= Fraction(8242, 300) <= high
    assert low != high
    # These serialized clocks represent an unresolved exact 4.75 minute mean.
    # It must never be called a contradiction to source4.8's inclusive0.05 bound.
    low, high = minute_mean_interval(["8.133333333333333", "1.3666666666666667"])
    assert low < Fraction(19, 4) <= high
    with pytest.raises(ValueError, match="empty minute"):
        minute_mean_interval([])
    with pytest.raises(ValueError, match="Invalid serialized"):
        minute_mean_interval([float("nan")])
