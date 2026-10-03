"""Season rollover: a new season becomes current when its games are published.

The latest season used to be a constant ("2025-26"), so a refresh kept pulling
2025-26 and new games, once published, were never the default season. These
tests pin the calendar and build tiny local generations to prove that the
latest season follows the served data, the refresh follows the calendar, and
readiness reports a new season that should exist but is not loaded.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from nbatools import readiness
from nbatools.commands import _seasons
from nbatools.commands._parse_helpers import default_season_for_context
from nbatools.data_source import reset_data_source_cache
from nbatools.readiness import NEW_SEASON_NOT_LOADED, evaluate_readiness
from tests.test_readiness import _slice, _snapshot

pytestmark = [pytest.mark.engine, pytest.mark.served_seasons]

_GAMES_HEADER = "game_id,season,season_type,game_date,is_final\n"


def _write_games(root: Path, season: str, kind: str, rows: list[tuple[str, str, int]]) -> None:
    path = root / "data" / "raw" / "games" / f"{season}_{kind}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    label = "Playoffs" if kind == "playoffs" else "Regular Season"
    body = "".join(f"{gid},{season},{label},{day},{final}\n" for gid, day, final in rows)
    path.write_text(_GAMES_HEADER + body)


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(tmp_path))
    monkeypatch.delenv("DATA_SOURCE", raising=False)
    monkeypatch.delenv("NBATOOLS_DATA_GENERATION", raising=False)
    reset_data_source_cache()
    _seasons.reset_latest_served_season_cache()
    yield tmp_path
    reset_data_source_cache()
    _seasons.reset_latest_served_season_cache()


@pytest.mark.parametrize(
    ("day", "season"),
    [
        (date(2026, 4, 12), "2025-26"),
        (date(2026, 6, 13), "2025-26"),
        (date(2026, 7, 31), "2025-26"),
        (date(2026, 8, 1), "2026-27"),
        (date(2026, 10, 21), "2026-27"),
        (date(2027, 1, 1), "2026-27"),
    ],
)
def test_season_for_date(day, season):
    assert _seasons.season_for_date(day) == season


def test_latest_season_follows_published_games(data_root):
    _write_games(data_root, "2025-26", "regular_season", [("0022500001", "2025-10-21", 1)])
    _write_games(data_root, "2025-26", "playoffs", [("0042500101", "2026-04-18", 1)])
    # Published before tip-off: scheduled rows only, so not yet the current season.
    _write_games(data_root, "2026-27", "regular_season", [("0022600001", "2026-10-20", 0)])

    assert _seasons.default_end_season("Regular Season") == "2025-26"
    assert default_season_for_context("Regular Season") == "2025-26"

    _write_games(data_root, "2026-27", "regular_season", [("0022600001", "2026-10-20", 1)])
    _seasons.reset_latest_served_season_cache()

    assert _seasons.default_end_season("Regular Season") == "2026-27"
    assert default_season_for_context("Regular Season") == "2026-27"
    assert _seasons.previous_season("Regular Season") == "2025-26"
    # The new season's playoffs do not exist yet, and "last season's playoffs"
    # are the 2025-26 playoffs, not the season before them.
    assert _seasons.default_end_season("Playoffs") == "2025-26"
    assert _seasons.previous_season("Playoffs") == "2025-26"
    assert _seasons.resolve_career("Regular Season") == ("1996-97", "2026-27")


def test_a_season_written_in_place_is_seen_by_the_same_process(data_root):
    # The local refresh loop writes the legacy (unversioned) layout in place.
    _write_games(data_root, "2025-26", "regular_season", [("0022500001", "2025-10-21", 1)])
    assert _seasons.default_end_season("Regular Season") == "2025-26"

    _write_games(data_root, "2026-27", "regular_season", [("0022600001", "2026-10-20", 1)])

    assert _seasons.default_end_season("Regular Season") == "2026-27"


def test_without_game_data_the_fallback_constants_apply(data_root):
    assert _seasons.default_end_season("Regular Season") == _seasons.LATEST_REGULAR_SEASON
    assert _seasons.default_end_season("Playoffs") == _seasons.LATEST_PLAYOFF_SEASON


def test_a_failed_read_is_not_cached(data_root, monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("transient")

    monkeypatch.setattr("nbatools.data_source.data_glob", boom)
    assert _seasons.latest_served_season("Regular Season") is None
    monkeypatch.undo()
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(data_root))
    _write_games(data_root, "2025-26", "regular_season", [("0022500001", "2025-10-21", 1)])
    assert _seasons.latest_served_season("Regular Season") == "2025-26"


# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------


@pytest.fixture
def served_2025_26(monkeypatch):
    monkeypatch.setattr(_seasons, "default_end_season", lambda season_type: "2025-26")
    published: set[str] = set()
    monkeypatch.setattr(
        readiness,
        "_slice_files_exist",
        lambda season, season_type, data_root: season in published,
    )
    return published


def _at(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, 12, tzinfo=UTC)


def test_readiness_keeps_judging_the_finished_season_in_the_offseason(served_2025_26):
    assert readiness._readiness_season(_at(2026, 7, 14), Path("data")) == ("2025-26", None)
    assert readiness._readiness_season(_at(2026, 10, 3), Path("data")) == ("2025-26", None)


def test_a_schedule_published_before_tip_off_keeps_the_finished_season(served_2025_26):
    served_2025_26.add("2026-27")
    assert readiness._readiness_season(_at(2026, 10, 3), Path("data")) == ("2025-26", None)


def test_readiness_judges_the_new_season_once_its_games_are_served(monkeypatch):
    monkeypatch.setattr(_seasons, "default_end_season", lambda season_type: "2026-27")
    assert readiness._readiness_season(_at(2026, 10, 22), Path("data")) == ("2026-27", None)


def test_readiness_reports_a_new_season_that_is_overdue(served_2025_26):
    assert readiness._readiness_season(_at(2026, 10, 31), Path("data")) == ("2025-26", None)
    assert readiness._readiness_season(_at(2026, 11, 1), Path("data")) == (
        "2025-26",
        "2026-27",
    )


def test_missing_new_season_blocks_readiness_and_only_an_exception_waives_it():
    offseason = _snapshot(playoffs=_slice("Playoffs", postseason_complete=True))
    overdue = replace(offseason, missing_current_season="2026-27")
    now = _at(2026, 11, 2)

    info = evaluate_readiness(overdue, checked_at=now, env={})
    assert info.ready is False
    assert [item.code for item in info.blockers] == [NEW_SEASON_NOT_LOADED]
    assert "2026-27" in info.blockers[0].detail

    env = {
        "NBATOOLS_READINESS_EXCEPTION_REASON": "Lockout: no 2026-27 games yet",
        "NBATOOLS_READINESS_EXCEPTION_CREATED_AT": "2026-11-02T10:00:00Z",
        "NBATOOLS_READINESS_EXCEPTION_EXPIRES_AT": "2026-11-03T10:00:00Z",
    }
    waived = evaluate_readiness(overdue, checked_at=now, env=env)
    assert waived.ready is True
    assert waived.exception.applied is True
