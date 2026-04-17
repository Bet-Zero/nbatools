"""Tests for the auto-refresh automation runner.

Tests cover:
- parse_interval for various formats
- run_auto_refresh iteration control
- refresh log writing after each run
- error handling during refresh
- signal handling / clean stop
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from nbatools.commands.pipeline.auto_refresh import parse_interval, run_auto_refresh
from nbatools.commands.pipeline.orchestrator import PipelineResult, SeasonResult, StageResult, StageStatus

pytestmark = pytest.mark.engine

# ---------------------------------------------------------------------------
# parse_interval
# ---------------------------------------------------------------------------


class TestParseInterval:
    def test_hours(self):
        assert parse_interval("6h") == 21600
        assert parse_interval("1H") == 3600

    def test_minutes(self):
        assert parse_interval("30m") == 1800
        assert parse_interval("5M") == 300

    def test_seconds(self):
        assert parse_interval("90s") == 90
        assert parse_interval("120S") == 120

    def test_plain_number(self):
        assert parse_interval("3600") == 3600

    def test_whitespace_stripped(self):
        assert parse_interval("  6h  ") == 21600

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_interval("")

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_interval("abc")

    def test_zero_hours(self):
        assert parse_interval("0h") == 0


# ---------------------------------------------------------------------------
# run_auto_refresh with max_iterations
# ---------------------------------------------------------------------------


class TestRunAutoRefresh:
    def _make_success_result(self) -> PipelineResult:
        sr = SeasonResult(
            season="2025-26",
            season_type="Regular Season",
            started_at="2026-04-14T10:00:00",
            finished_at="2026-04-14T10:05:00",
        )
        sr.stages = [StageResult(name="pull_games", status=StageStatus.SUCCESS)]
        sr.current_through = "2026-04-13"
        return PipelineResult(
            mode="current_season_refresh",
            seasons=[sr],
            started_at="2026-04-14T10:00:00",
            finished_at="2026-04-14T10:05:00",
        )

    def _make_failure_result(self) -> PipelineResult:
        sr = SeasonResult(
            season="2025-26",
            season_type="Regular Season",
            started_at="2026-04-14T10:00:00",
            finished_at="2026-04-14T10:05:00",
        )
        sr.stages = [
            StageResult(
                name="pull_games",
                status=StageStatus.FAILED,
                error="API timeout",
            )
        ]
        return PipelineResult(
            mode="current_season_refresh",
            seasons=[sr],
            started_at="2026-04-14T10:00:00",
            finished_at="2026-04-14T10:05:00",
        )

    @patch("nbatools.commands.pipeline.auto_refresh.refresh_current_season")
    @patch("nbatools.commands.pipeline.auto_refresh.write_refresh_log")
    def test_single_iteration_success(self, mock_log, mock_refresh):
        mock_refresh.return_value = self._make_success_result()
        run_auto_refresh(60, max_iterations=1)
        mock_refresh.assert_called_once_with(include_playoffs=False)
        mock_log.assert_called_once()
        args = mock_log.call_args
        assert args.kwargs.get("success") is True or args[1].get("success") is True

    @patch("nbatools.commands.pipeline.auto_refresh.refresh_current_season")
    @patch("nbatools.commands.pipeline.auto_refresh.write_refresh_log")
    def test_single_iteration_failure(self, mock_log, mock_refresh):
        mock_refresh.return_value = self._make_failure_result()
        run_auto_refresh(60, max_iterations=1)
        mock_refresh.assert_called_once()
        mock_log.assert_called_once()
        # The log should be called; check it was invoked
        assert mock_log.called

    @patch("nbatools.commands.pipeline.auto_refresh.refresh_current_season")
    @patch("nbatools.commands.pipeline.auto_refresh.write_refresh_log")
    def test_multiple_iterations(self, mock_log, mock_refresh):
        mock_refresh.return_value = self._make_success_result()
        run_auto_refresh(60, max_iterations=3)
        assert mock_refresh.call_count == 3
        assert mock_log.call_count == 3

    @patch("nbatools.commands.pipeline.auto_refresh.refresh_current_season")
    @patch("nbatools.commands.pipeline.auto_refresh.write_refresh_log")
    def test_includes_playoffs_option(self, mock_log, mock_refresh):
        mock_refresh.return_value = self._make_success_result()
        run_auto_refresh(60, include_playoffs=True, max_iterations=1)
        mock_refresh.assert_called_once_with(include_playoffs=True)

    @patch("nbatools.commands.pipeline.auto_refresh.refresh_current_season")
    @patch("nbatools.commands.pipeline.auto_refresh.write_refresh_log")
    def test_exception_during_refresh(self, mock_log, mock_refresh):
        mock_refresh.side_effect = RuntimeError("crash")
        run_auto_refresh(60, max_iterations=1)
        # Should still log the failure
        mock_log.assert_called_once()
        call_args = mock_log.call_args
        assert call_args[1].get("success") is False or call_args[0][0] is False
