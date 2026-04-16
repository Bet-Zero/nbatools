"""Tests for freshness status semantics, structured freshness info, and refresh log.

Tests cover:
- FreshnessStatus enum values
- classify_freshness logic (fresh, stale, unknown thresholds)
- SeasonFreshness / FreshnessInfo dataclasses
- FreshnessInfo.to_dict serialization
- write_refresh_log / read_refresh_log round-trip
- build_freshness_info integration with manifest + games data
- build_freshness_info with failed refresh log
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.freshness import (
    FreshnessInfo,
    FreshnessStatus,
    SeasonFreshness,
    build_freshness_info,
    classify_freshness,
    read_refresh_log,
    write_refresh_log,
)

pytestmark = pytest.mark.engine

# ---------------------------------------------------------------------------
# classify_freshness
# ---------------------------------------------------------------------------


class TestClassifyFreshness:
    def test_fresh_when_recent(self):
        today = date(2026, 4, 14)
        assert (
            classify_freshness("2026-04-13", manifest_complete=True, reference_date=today)
            == FreshnessStatus.FRESH
        )

    def test_fresh_on_boundary(self):
        today = date(2026, 4, 14)
        assert (
            classify_freshness("2026-04-11", manifest_complete=True, reference_date=today)
            == FreshnessStatus.FRESH
        )

    def test_stale_beyond_threshold(self):
        today = date(2026, 4, 14)
        assert (
            classify_freshness("2026-04-10", manifest_complete=True, reference_date=today)
            == FreshnessStatus.STALE
        )

    def test_unknown_when_no_current_through(self):
        assert classify_freshness(None, manifest_complete=True) == FreshnessStatus.UNKNOWN

    def test_unknown_when_manifest_incomplete(self):
        assert classify_freshness("2026-04-13", manifest_complete=False) == FreshnessStatus.UNKNOWN

    def test_unknown_on_bad_date(self):
        assert classify_freshness("not-a-date", manifest_complete=True) == FreshnessStatus.UNKNOWN

    def test_custom_stale_days(self):
        today = date(2026, 4, 14)
        # 7-day threshold — 2026-04-06 is 8 days ago → stale
        assert (
            classify_freshness(
                "2026-04-06",
                manifest_complete=True,
                stale_days=7,
                reference_date=today,
            )
            == FreshnessStatus.STALE
        )
        # 2026-04-07 is 7 days ago → fresh (within threshold)
        assert (
            classify_freshness(
                "2026-04-07",
                manifest_complete=True,
                stale_days=7,
                reference_date=today,
            )
            == FreshnessStatus.FRESH
        )


# ---------------------------------------------------------------------------
# FreshnessStatus enum
# ---------------------------------------------------------------------------


class TestFreshnessStatusEnum:
    def test_values(self):
        assert FreshnessStatus.FRESH.value == "fresh"
        assert FreshnessStatus.STALE.value == "stale"
        assert FreshnessStatus.UNKNOWN.value == "unknown"
        assert FreshnessStatus.FAILED.value == "failed"

    def test_string_comparison(self):
        assert FreshnessStatus.FRESH == "fresh"
        assert FreshnessStatus.STALE == "stale"


# ---------------------------------------------------------------------------
# FreshnessInfo.to_dict
# ---------------------------------------------------------------------------


class TestFreshnessInfoToDict:
    def test_serialization(self):
        info = FreshnessInfo(
            status=FreshnessStatus.FRESH,
            current_through="2026-04-13",
            checked_at="2026-04-14T10:00:00",
            seasons=[
                SeasonFreshness(
                    season="2025-26",
                    season_type="Regular Season",
                    status=FreshnessStatus.FRESH,
                    current_through="2026-04-13",
                    raw_complete=True,
                    processed_complete=True,
                    loaded_at="2026-04-14T09:00:00",
                )
            ],
            last_refresh_ok=True,
            last_refresh_at="2026-04-14T09:00:00",
        )
        d = info.to_dict()
        assert d["status"] == "fresh"
        assert d["current_through"] == "2026-04-13"
        assert len(d["seasons"]) == 1
        assert d["seasons"][0]["status"] == "fresh"
        assert d["seasons"][0]["raw_complete"] is True
        assert d["last_refresh_ok"] is True
        assert d["last_refresh_error"] is None

    def test_unknown_status_serialization(self):
        info = FreshnessInfo(status=FreshnessStatus.UNKNOWN)
        d = info.to_dict()
        assert d["status"] == "unknown"
        assert d["current_through"] is None
        assert d["seasons"] == []


# ---------------------------------------------------------------------------
# Refresh log read/write
# ---------------------------------------------------------------------------


class TestRefreshLog:
    def test_write_and_read_success(self, tmp_path):
        write_refresh_log(
            success=True,
            timestamp="2026-04-14T10:00:00",
            data_root=tmp_path,
        )
        log = read_refresh_log(data_root=tmp_path)
        assert log is not None
        assert log["success"] is True
        assert log["timestamp"] == "2026-04-14T10:00:00"
        assert log["error"] is None

    def test_write_and_read_failure(self, tmp_path):
        write_refresh_log(
            success=False,
            timestamp="2026-04-14T10:05:00",
            error="pull_games failed: API timeout",
            data_root=tmp_path,
        )
        log = read_refresh_log(data_root=tmp_path)
        assert log["success"] is False
        assert "API timeout" in log["error"]

    def test_read_returns_none_when_missing(self, tmp_path):
        assert read_refresh_log(data_root=tmp_path) is None

    def test_read_returns_none_on_corrupt_json(self, tmp_path):
        path = tmp_path / "metadata" / "last_refresh.json"
        path.parent.mkdir(parents=True)
        path.write_text("not json at all")
        assert read_refresh_log(data_root=tmp_path) is None

    def test_creates_metadata_dir(self, tmp_path):
        write_refresh_log(success=True, timestamp="2026-01-01T00:00:00", data_root=tmp_path)
        assert (tmp_path / "metadata" / "last_refresh.json").exists()


# ---------------------------------------------------------------------------
# build_freshness_info (integration with file fixtures)
# ---------------------------------------------------------------------------


def _setup_manifest(data_root: Path, season: str, season_type: str, *, raw=1, proc=1):
    """Create a minimal manifest CSV."""
    manifest = data_root / "metadata" / "backfill_manifest.csv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        [
            {
                "season": season,
                "season_type": season_type,
                "raw_complete": raw,
                "processed_complete": proc,
                "loaded_at": "2026-04-14T10:00:00",
            }
        ]
    )
    if manifest.exists():
        old = pd.read_csv(manifest)
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(manifest, index=False)


def _setup_games(data_root: Path, season: str, season_type: str, game_date: str):
    """Create a minimal games CSV with a single final game."""
    from nbatools.commands.data_utils import normalize_season_type

    safe = normalize_season_type(season_type)
    games_dir = data_root / "raw" / "games"
    games_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        [
            {
                "game_date": game_date,
                "is_final": 1,
                "home_team": "DEN",
                "away_team": "LAL",
            }
        ]
    )
    df.to_csv(games_dir / f"{season}_{safe}.csv", index=False)


class TestBuildFreshnessInfo:
    def test_fresh_status(self, tmp_path):
        _setup_manifest(tmp_path, "2025-26", "Regular Season")
        _setup_games(tmp_path, "2025-26", "Regular Season", "2026-04-13")

        info = build_freshness_info(
            seasons=["2025-26"],
            data_root=tmp_path,
            reference_date=date(2026, 4, 14),
        )
        assert info.status == FreshnessStatus.FRESH
        assert info.current_through == "2026-04-13"
        assert len(info.seasons) == 1
        assert info.seasons[0].status == FreshnessStatus.FRESH

    def test_stale_status(self, tmp_path):
        _setup_manifest(tmp_path, "2025-26", "Regular Season")
        _setup_games(tmp_path, "2025-26", "Regular Season", "2026-04-01")

        info = build_freshness_info(
            seasons=["2025-26"],
            data_root=tmp_path,
            reference_date=date(2026, 4, 14),
        )
        assert info.status == FreshnessStatus.STALE

    def test_unknown_when_manifest_missing(self, tmp_path):
        info = build_freshness_info(
            seasons=["2025-26"],
            data_root=tmp_path,
            reference_date=date(2026, 4, 14),
        )
        assert info.status == FreshnessStatus.UNKNOWN
        assert info.current_through is None

    def test_unknown_when_manifest_incomplete(self, tmp_path):
        _setup_manifest(tmp_path, "2025-26", "Regular Season", raw=1, proc=0)
        _setup_games(tmp_path, "2025-26", "Regular Season", "2026-04-13")

        info = build_freshness_info(
            seasons=["2025-26"],
            data_root=tmp_path,
            reference_date=date(2026, 4, 14),
        )
        assert info.status == FreshnessStatus.UNKNOWN

    def test_failed_when_refresh_log_failed(self, tmp_path):
        _setup_manifest(tmp_path, "2025-26", "Regular Season")
        _setup_games(tmp_path, "2025-26", "Regular Season", "2026-04-13")
        write_refresh_log(
            success=False,
            timestamp="2026-04-14T09:00:00",
            error="API down",
            data_root=tmp_path,
        )

        info = build_freshness_info(
            seasons=["2025-26"],
            data_root=tmp_path,
            reference_date=date(2026, 4, 14),
        )
        assert info.status == FreshnessStatus.FAILED
        assert info.last_refresh_ok is False
        assert info.last_refresh_error == "API down"

    def test_multiple_seasons_worst_status(self, tmp_path):
        _setup_manifest(tmp_path, "2025-26", "Regular Season")
        _setup_games(tmp_path, "2025-26", "Regular Season", "2026-04-13")
        # Second season has no manifest → unknown
        # Overall should be unknown (worst of fresh+unknown)

        info = build_freshness_info(
            seasons=["2025-26", "2024-25"],
            data_root=tmp_path,
            reference_date=date(2026, 4, 14),
        )
        assert info.status == FreshnessStatus.UNKNOWN
        # But we still get current_through from the season that has it
        assert info.current_through == "2026-04-13"

    def test_to_dict_roundtrip(self, tmp_path):
        _setup_manifest(tmp_path, "2025-26", "Regular Season")
        _setup_games(tmp_path, "2025-26", "Regular Season", "2026-04-13")

        info = build_freshness_info(
            seasons=["2025-26"],
            data_root=tmp_path,
            reference_date=date(2026, 4, 14),
        )
        d = info.to_dict()
        # Verify JSON-serializable
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        assert parsed["status"] == "fresh"
        assert parsed["current_through"] == "2026-04-13"
