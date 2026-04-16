"""Tests for the data refresh pipeline orchestration layer.

Tests cover:
- PipelineResult / SeasonResult / StageResult data structures
- Stage ordering and deterministic execution
- Failure propagation (early stop on failed stage)
- Skip-existing behavior
- Dry-run mode
- Season-range handling
- Manifest / current-through integration
- CLI command surface wiring
- Freshness report
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from nbatools.commands.pipeline import (
    PipelineResult,
    SeasonResult,
    StageResult,
    StageStatus,
    _raw_pull_stages,
    _run_stage,
    backfill_seasons,
    pipeline_status,
    rebuild_season,
    refresh_current_season,
    refresh_season,
)

pytestmark = pytest.mark.engine

# ---------------------------------------------------------------------------
# Result dataclass tests
# ---------------------------------------------------------------------------


class TestStageResult:
    def test_success_stage(self):
        s = StageResult(name="pull_games", status=StageStatus.SUCCESS, duration_ms=120)
        assert s.status == StageStatus.SUCCESS
        assert s.error is None

    def test_failed_stage(self):
        s = StageResult(name="validate_raw", status=StageStatus.FAILED, error="bad data")
        assert s.status == StageStatus.FAILED
        assert "bad data" in s.error

    def test_skipped_stage(self):
        s = StageResult(name="pull_standings_snapshots", status=StageStatus.SKIPPED)
        assert s.status == StageStatus.SKIPPED


class TestSeasonResult:
    def test_success_property(self):
        sr = SeasonResult(season="2025-26", season_type="Regular Season")
        sr.stages = [
            StageResult(name="a", status=StageStatus.SUCCESS),
            StageResult(name="b", status=StageStatus.SKIPPED),
        ]
        assert sr.success is True

    def test_failure_property(self):
        sr = SeasonResult(season="2025-26", season_type="Regular Season")
        sr.stages = [
            StageResult(name="a", status=StageStatus.SUCCESS),
            StageResult(name="b", status=StageStatus.FAILED, error="boom"),
        ]
        assert sr.success is False
        assert len(sr.failed_stages) == 1
        assert sr.failed_stages[0].name == "b"

    def test_empty_stages_is_success(self):
        sr = SeasonResult(season="2024-25", season_type="Playoffs")
        assert sr.success is True


class TestPipelineResult:
    def test_overall_success(self):
        pr = PipelineResult(mode="test")
        sr = SeasonResult(season="2025-26", season_type="Regular Season")
        sr.stages = [StageResult(name="a", status=StageStatus.SUCCESS)]
        pr.seasons = [sr]
        assert pr.success is True

    def test_overall_failure(self):
        pr = PipelineResult(mode="test")
        sr_ok = SeasonResult(season="2024-25", season_type="Regular Season")
        sr_ok.stages = [StageResult(name="a", status=StageStatus.SUCCESS)]
        sr_bad = SeasonResult(season="2025-26", season_type="Regular Season")
        sr_bad.stages = [StageResult(name="b", status=StageStatus.FAILED, error="err")]
        pr.seasons = [sr_ok, sr_bad]
        assert pr.success is False
        assert len(pr.failed_seasons) == 1

    def test_summary_lines(self):
        pr = PipelineResult(
            mode="current_season_refresh",
            started_at="2026-04-12T10:00:00",
            finished_at="2026-04-12T10:05:00",
        )
        sr = SeasonResult(season="2025-26", season_type="Regular Season")
        sr.stages = [StageResult(name="a", status=StageStatus.SUCCESS)]
        sr.current_through = "2026-04-11"
        pr.seasons = [sr]
        lines = pr.summary_lines
        assert any("current_season_refresh" in line for line in lines)
        assert any("2026-04-11" in line for line in lines)
        assert any("Succeeded: 1" in line for line in lines)


# ---------------------------------------------------------------------------
# _run_stage tests
# ---------------------------------------------------------------------------


class TestRunStage:
    def test_success(self):
        result = _run_stage("test_stage", lambda: None)
        assert result.status == StageStatus.SUCCESS
        assert result.duration_ms is not None

    def test_failure_captures_error(self):
        def bad():
            raise ValueError("something broke")

        result = _run_stage("test_stage", bad)
        assert result.status == StageStatus.FAILED
        assert "ValueError" in result.error
        assert "something broke" in result.error

    def test_passes_args(self):
        called_with = {}

        def fn(a, b, c=None):
            called_with["a"] = a
            called_with["b"] = b
            called_with["c"] = c

        result = _run_stage("test_stage", fn, "x", "y", c="z")
        assert result.status == StageStatus.SUCCESS
        assert called_with == {"a": "x", "b": "y", "c": "z"}


# ---------------------------------------------------------------------------
# Raw pull stages tests
# ---------------------------------------------------------------------------


class TestRawPullStages:
    """Test raw pull stages by patching at the actual module.run path."""

    @patch("nbatools.commands.pull_player_season_advanced.run")
    @patch("nbatools.commands.pull_team_season_advanced.run")
    @patch("nbatools.commands.pull_standings_snapshots.run")
    @patch("nbatools.commands.pull_player_game_stats.run")
    @patch("nbatools.commands.pull_team_game_stats.run")
    @patch("nbatools.commands.pull_rosters.run")
    @patch("nbatools.commands.pull_schedule.run")
    @patch("nbatools.commands.pull_games.run")
    def test_all_stages_run_in_order(self, *mocks):
        results = _raw_pull_stages("2025-26", "Regular Season")
        assert len(results) == 8
        assert all(r.status == StageStatus.SUCCESS for r in results)
        assert results[0].name == "pull_games"
        assert results[1].name == "pull_schedule"
        assert results[2].name == "pull_rosters"
        assert results[3].name == "pull_team_game_stats"
        assert results[4].name == "pull_player_game_stats"
        assert results[5].name == "pull_standings_snapshots"
        assert results[6].name == "pull_team_season_advanced"
        assert results[7].name == "pull_player_season_advanced"

    @patch("nbatools.commands.pull_player_season_advanced.run")
    @patch("nbatools.commands.pull_team_season_advanced.run")
    @patch("nbatools.commands.pull_standings_snapshots.run")
    @patch("nbatools.commands.pull_player_game_stats.run")
    @patch("nbatools.commands.pull_team_game_stats.run")
    @patch("nbatools.commands.pull_rosters.run")
    @patch("nbatools.commands.pull_schedule.run")
    @patch("nbatools.commands.pull_games.run")
    def test_standings_skipped_for_playoffs(self, *mocks):
        results = _raw_pull_stages("2024-25", "Playoffs")
        assert len(results) == 8
        standings = next(r for r in results if r.name == "pull_standings_snapshots")
        assert standings.status == StageStatus.SKIPPED

    @patch("nbatools.commands.pull_schedule.run")
    @patch("nbatools.commands.pull_games.run")
    def test_games_failure_stops_pipeline(self, mock_games, mock_schedule):
        mock_games.side_effect = RuntimeError("API timeout")
        results = _raw_pull_stages("2025-26", "Regular Season")
        assert len(results) == 1
        assert results[0].status == StageStatus.FAILED
        assert "API timeout" in results[0].error

    @patch("nbatools.commands.pull_games.run")
    def test_no_data_skip_for_playoffs(self, mock_games):
        mock_games.side_effect = ValueError("No data returned for season=2025-26")
        results = _raw_pull_stages("2025-26", "Playoffs", allow_no_data_skip=True)
        assert len(results) == 1
        assert results[0].status == StageStatus.SKIPPED
        assert "No data available" in results[0].error

    @patch("nbatools.commands.pull_games.run")
    def test_no_data_without_skip_flag_is_failure(self, mock_games):
        mock_games.side_effect = ValueError("No data returned for season=2025-26")
        results = _raw_pull_stages("2025-26", "Playoffs", allow_no_data_skip=False)
        assert len(results) == 1
        assert results[0].status == StageStatus.FAILED


# ---------------------------------------------------------------------------
# Season refresh tests
# ---------------------------------------------------------------------------


class TestRefreshSeason:
    @patch("nbatools.commands.pull_player_season_advanced.run")
    @patch("nbatools.commands.pull_team_season_advanced.run")
    @patch("nbatools.commands.pull_standings_snapshots.run")
    @patch("nbatools.commands.pull_player_game_stats.run")
    @patch("nbatools.commands.pull_team_game_stats.run")
    @patch("nbatools.commands.pull_rosters.run")
    @patch("nbatools.commands.pull_schedule.run")
    @patch("nbatools.commands.pull_games.run")
    @patch("nbatools.commands.validate_raw.run")
    @patch("nbatools.commands.build_team_game_features.run")
    @patch("nbatools.commands.build_game_features.run")
    @patch("nbatools.commands.build_player_game_features.run")
    @patch("nbatools.commands.build_league_season_stats.run")
    @patch("nbatools.commands.update_manifest.run")
    @patch("nbatools.commands.pipeline.compute_current_through", return_value="2026-04-11")
    def test_full_success(self, mock_ct, *mocks):
        result = refresh_season("2025-26", "Regular Season")
        assert result.success
        assert result.current_through == "2026-04-11"
        assert result.started_at is not None
        assert result.finished_at is not None
        # Should have: 8 raw + 1 validate + 4 build + 1 manifest = 14 stages
        assert len(result.stages) == 14

    @patch("nbatools.commands.pull_games.run")
    def test_games_failure_stops_early(self, mock_games):
        mock_games.side_effect = RuntimeError("API down")
        result = refresh_season("2025-26", "Regular Season")
        assert not result.success
        # Only 1 stage (games failed, nothing else ran)
        assert len(result.stages) == 1
        assert result.stages[0].name == "pull_games"
        assert result.current_through is None

    @patch("nbatools.commands.pull_player_season_advanced.run")
    @patch("nbatools.commands.pull_team_season_advanced.run")
    @patch("nbatools.commands.pull_standings_snapshots.run")
    @patch("nbatools.commands.pull_player_game_stats.run")
    @patch("nbatools.commands.pull_team_game_stats.run")
    @patch("nbatools.commands.pull_rosters.run")
    @patch("nbatools.commands.pull_schedule.run")
    @patch("nbatools.commands.pull_games.run")
    @patch("nbatools.commands.validate_raw.run")
    def test_validation_failure_stops_before_build(self, mock_val, *pull_mocks):
        mock_val.side_effect = ValueError("schema mismatch")
        result = refresh_season("2025-26", "Regular Season")
        assert not result.success
        # 8 raw + 1 validate = 9 stages (no build, no manifest)
        assert len(result.stages) == 9
        val_stage = next(s for s in result.stages if s.name == "validate_raw")
        assert val_stage.status == StageStatus.FAILED

    @patch("nbatools.commands.backfill_season.outputs_exist", return_value=True)
    @patch("nbatools.commands.pipeline.compute_current_through", return_value="2026-04-10")
    def test_skip_existing(self, mock_ct, mock_exists):
        result = refresh_season("2025-26", "Regular Season", skip_existing=True)
        assert result.success
        assert len(result.stages) == 1
        assert result.stages[0].status == StageStatus.SKIPPED
        assert result.current_through == "2026-04-10"

    def test_dry_run(self):
        result = refresh_season("2025-26", "Regular Season", dry_run=True)
        assert len(result.stages) == 14
        assert all(s.status == StageStatus.SKIPPED for s in result.stages)
        assert all(s.error == "dry_run" for s in result.stages)

    @patch("nbatools.commands.pull_games.run")
    def test_no_data_skip_for_playoffs(self, mock_games):
        mock_games.side_effect = ValueError("No data returned for season=2025-26")
        result = refresh_season("2025-26", "Playoffs", allow_no_data_skip=True)
        assert result.success  # Skipped cleanly
        assert len(result.stages) == 1
        assert result.stages[0].status == StageStatus.SKIPPED


# ---------------------------------------------------------------------------
# Pipeline workflow tests
# ---------------------------------------------------------------------------


class TestRefreshCurrentSeason:
    def test_dry_run_regular_only(self):
        result = refresh_current_season(dry_run=True)
        assert result.mode == "current_season_refresh"
        assert len(result.seasons) == 1
        assert result.seasons[0].season == "2025-26"
        assert result.seasons[0].season_type == "Regular Season"

    def test_dry_run_with_playoffs(self):
        result = refresh_current_season(include_playoffs=True, dry_run=True)
        assert len(result.seasons) == 2
        # Second season should be playoffs
        assert result.seasons[1].season_type == "Playoffs"


class TestRebuildSeason:
    def test_dry_run(self):
        result = rebuild_season("2024-25", dry_run=True)
        assert result.mode == "season_rebuild"
        assert len(result.seasons) == 1
        assert result.seasons[0].season == "2024-25"

    def test_dry_run_with_playoffs(self):
        result = rebuild_season("2024-25", include_playoffs=True, dry_run=True)
        assert len(result.seasons) == 2
        assert result.seasons[1].season_type == "Playoffs"


class TestBackfillSeasons:
    def test_dry_run_range(self):
        result = backfill_seasons("2022-23", "2024-25", dry_run=True)
        assert result.mode == "historical_backfill"
        assert len(result.seasons) == 3
        assert result.seasons[0].season == "2022-23"
        assert result.seasons[1].season == "2023-24"
        assert result.seasons[2].season == "2024-25"

    def test_dry_run_range_with_playoffs(self):
        result = backfill_seasons("2023-24", "2024-25", include_playoffs=True, dry_run=True)
        # 2 seasons × 2 types = 4
        assert len(result.seasons) == 4
        types = [s.season_type for s in result.seasons]
        assert types == [
            "Regular Season",
            "Playoffs",
            "Regular Season",
            "Playoffs",
        ]

    def test_single_season_backfill(self):
        result = backfill_seasons("2024-25", "2024-25", dry_run=True)
        assert len(result.seasons) == 1


# ---------------------------------------------------------------------------
# Pipeline status tests
# ---------------------------------------------------------------------------


class TestPipelineStatus:
    def test_status_with_real_data(self):
        """Smoke test: should not crash with actual data on disk."""
        info = pipeline_status()
        assert "season" in info
        assert "current_through" in info
        assert "raw_complete" in info
        assert "processed_complete" in info
        assert "raw_files" in info
        assert "processed_files" in info

    def test_status_specific_season(self):
        info = pipeline_status(season="2024-25", season_type="Regular Season")
        assert info["season"] == "2024-25"
        assert info["season_type"] == "Regular Season"


# ---------------------------------------------------------------------------
# Freshness report tests
# ---------------------------------------------------------------------------


class TestFreshnessReport:
    def test_report_with_real_data(self):
        from nbatools.commands.freshness import freshness_report

        report = freshness_report(["2024-25", "2025-26"])
        assert "overall_current_through" in report
        assert "seasons" in report
        assert len(report["seasons"]) == 2

    def test_report_unknown_season(self):
        from nbatools.commands.freshness import freshness_report

        report = freshness_report(["1990-91"])
        assert report["overall_current_through"] is None
        assert len(report["seasons"]) == 1
        assert report["seasons"][0]["current_through"] is None


# ---------------------------------------------------------------------------
# Manifest entry tests
# ---------------------------------------------------------------------------


class TestManifestEntry:
    def test_existing_season(self):
        from nbatools.commands.freshness import manifest_entry

        entry = manifest_entry("2025-26", "Regular Season")
        # May or may not exist depending on test environment
        if entry is not None:
            assert "raw_complete" in entry
            assert "processed_complete" in entry
            assert "loaded_at" in entry

    def test_nonexistent_season(self):
        from nbatools.commands.freshness import manifest_entry

        entry = manifest_entry("1990-91", "Regular Season")
        assert entry is None


# ---------------------------------------------------------------------------
# Stage ordering invariants
# ---------------------------------------------------------------------------


class TestStageOrdering:
    """Verify that stage ordering matches data_freshness_plan.md §4."""

    EXPECTED_STAGE_ORDER = [
        "pull_games",
        "pull_schedule",
        "pull_rosters",
        "pull_team_game_stats",
        "pull_player_game_stats",
        "pull_standings_snapshots",
        "pull_team_season_advanced",
        "pull_player_season_advanced",
        "validate_raw",
        "build_team_game_features",
        "build_game_features",
        "build_player_game_features",
        "build_league_season_stats",
        "update_manifest",
    ]

    def test_dry_run_stage_order(self):
        result = refresh_season("2025-26", "Regular Season", dry_run=True)
        actual_names = [s.name for s in result.stages]
        assert actual_names == self.EXPECTED_STAGE_ORDER

    def test_dry_run_playoffs_skips_standings(self):
        result = refresh_season("2024-25", "Playoffs", dry_run=True)
        actual_names = [s.name for s in result.stages]
        # Same order but standings is skipped in dry_run
        # (dry_run doesn't differentiate — it plans all stages)
        assert "pull_standings_snapshots" in actual_names


# ---------------------------------------------------------------------------
# CLI surface tests (Typer commands are importable and callable)
# ---------------------------------------------------------------------------


class TestCLISurface:
    def test_pipeline_app_exists(self):
        from nbatools.cli_apps.pipeline import app

        assert app is not None

    def test_pipeline_commands_registered(self):
        from typer.testing import CliRunner

        from nbatools.cli_apps.pipeline import app

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "refresh" in result.output
        assert "rebuild" in result.output
        assert "backfill" in result.output
        assert "status" in result.output

    def test_status_command_runs(self):
        from typer.testing import CliRunner

        from nbatools.cli_apps.pipeline import app

        runner = CliRunner()
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Season:" in result.output
        assert "Current through:" in result.output

    def test_refresh_dry_run(self):
        from typer.testing import CliRunner

        from nbatools.cli_apps.pipeline import app

        runner = CliRunner()
        result = runner.invoke(app, ["refresh", "--dry-run"])
        assert result.exit_code == 0
        assert "current_season_refresh" in result.output

    def test_rebuild_dry_run(self):
        from typer.testing import CliRunner

        from nbatools.cli_apps.pipeline import app

        runner = CliRunner()
        result = runner.invoke(app, ["rebuild", "--season", "2024-25", "--dry-run"])
        assert result.exit_code == 0
        assert "season_rebuild" in result.output

    def test_backfill_dry_run(self):
        from typer.testing import CliRunner

        from nbatools.cli_apps.pipeline import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["backfill", "--start-season", "2023-24", "--end-season", "2024-25", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "historical_backfill" in result.output

    def test_pipeline_registered_in_main_cli(self):
        from typer.testing import CliRunner

        from nbatools.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["pipeline", "--help"])
        assert result.exit_code == 0
        assert "refresh" in result.output


# ---------------------------------------------------------------------------
# Guard: pipeline doesn't execute sys.exit (unlike old backfill_season)
# ---------------------------------------------------------------------------


class TestNoSysExit:
    """The new pipeline must never call sys.exit — it returns results."""

    @patch("nbatools.commands.pull_games.run")
    def test_failure_returns_result_not_exit(self, mock_games):
        mock_games.side_effect = RuntimeError("boom")
        # Old backfill_season.py called sys.exit on failure.
        # New pipeline must return a result.
        result = refresh_season("2025-26", "Regular Season")
        assert not result.success
        assert len(result.failed_stages) == 1


# ---------------------------------------------------------------------------
# Integration: verify current_through is grounded in manifest after refresh
# ---------------------------------------------------------------------------


class TestCurrentThroughIntegration:
    @patch("nbatools.commands.pull_player_season_advanced.run")
    @patch("nbatools.commands.pull_team_season_advanced.run")
    @patch("nbatools.commands.pull_standings_snapshots.run")
    @patch("nbatools.commands.pull_player_game_stats.run")
    @patch("nbatools.commands.pull_team_game_stats.run")
    @patch("nbatools.commands.pull_rosters.run")
    @patch("nbatools.commands.pull_schedule.run")
    @patch("nbatools.commands.pull_games.run")
    @patch("nbatools.commands.validate_raw.run")
    @patch("nbatools.commands.build_team_game_features.run")
    @patch("nbatools.commands.build_game_features.run")
    @patch("nbatools.commands.build_player_game_features.run")
    @patch("nbatools.commands.build_league_season_stats.run")
    @patch("nbatools.commands.update_manifest.run")
    @patch("nbatools.commands.pipeline.compute_current_through")
    def test_current_through_computed_after_successful_refresh(self, mock_ct, *mocks):
        mock_ct.return_value = "2026-04-12"
        result = refresh_season("2025-26", "Regular Season")
        assert result.success
        assert result.current_through == "2026-04-12"
        mock_ct.assert_called_once_with("2025-26", "Regular Season")

    @patch("nbatools.commands.pull_games.run")
    def test_current_through_none_on_failure(self, mock_games):
        mock_games.side_effect = RuntimeError("fail")
        result = refresh_season("2025-26", "Regular Season")
        assert not result.success
        assert result.current_through is None
