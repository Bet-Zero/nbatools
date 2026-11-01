"""Exact due-game coverage is independent of the latest completed date."""

from dataclasses import replace
from datetime import UTC, datetime

import pandas as pd
import pytest

from nbatools import readiness
from tests.test_readiness import _snapshot

NOW = datetime(2026, 11, 1, 12, tzinfo=UTC)


def frames():
    schedule = pd.DataFrame(
        {
            "game_id": ["0022600001", "0022600002", "0022600003"],
            "game_date": ["2026-10-29", "2026-10-30", "2026-11-01"],
            "game_datetime": [
                "2026-10-29T23:00:00Z",
                "2026-10-30T23:00:00Z",
                "2026-11-01T23:00:00Z",
            ],
            "status": ["Final", "Final", "Scheduled"],
        }
    )
    games = pd.DataFrame(
        {
            "game_id": [22600001, 22600002],
            "game_date": ["2026-10-29", "2026-10-30"],
            "is_final": [1, 1],
        }
    )
    return schedule, games


def collect(monkeypatch, schedule, games):
    monkeypatch.setattr(
        readiness,
        "manifest_entry",
        lambda *a: dict(validation_state="passed", raw_complete=True, processed_complete=True),
    )
    monkeypatch.setattr(
        readiness,
        "_read_slice_csv",
        lambda root, layer, dataset, season, kind: {"schedule": schedule, "games": games}[dataset],
    )
    return readiness._collect_slice("2026-27", "Regular Season", None, NOW)


def evaluate(item, **kwargs):
    return readiness.evaluate_readiness(_snapshot(regular=item), checked_at=NOW, env=kwargs)


def test_later_final_does_not_hide_an_earlier_missing_game(monkeypatch):
    schedule, games = frames()
    item = collect(monkeypatch, schedule, games.iloc[1:])
    assert item.current_through == item.expected_current_through == "2026-10-30"
    assert item.missing_due_game_ids == ("0022600001",)
    result = evaluate(item)
    assert not result.ready
    assert [b.code for b in result.blockers] == ["active_season_lag"]
    assert "0022600001" in result.blockers[0].detail


def test_same_date_hole_and_nonfinal_game_are_both_missing(monkeypatch):
    schedule, games = frames()
    schedule.loc[0, ["game_date", "game_datetime"]] = ["2026-10-30", "2026-10-30T23:00:00Z"]
    games.loc[0, "game_date"] = "2026-10-30"
    for partial in (games.iloc[1:], games.assign(is_final=[0, 1])):
        item = collect(monkeypatch, schedule, partial)
        assert item.current_through == item.expected_current_through
        assert item.missing_due_game_ids == ("0022600001",)
        assert not evaluate(item).ready


def test_complete_due_population_is_ready_and_future_rows_need_no_final(monkeypatch):
    schedule, games = frames()
    item = collect(monkeypatch, schedule, games)
    assert item.missing_due_game_ids == ()
    assert evaluate(item).ready
    assert item.to_dict()["missing_due_game_ids"] == []


def test_grace_window_and_exact_utc_boundary_remain_24_hours(monkeypatch):
    schedule, games = frames()
    schedule.loc[0, ["game_date", "game_datetime"]] = ["2026-10-31", "2026-10-31T12:00:01Z"]
    assert collect(monkeypatch, schedule, games.iloc[1:]).missing_due_game_ids == ()
    schedule.loc[0, "game_datetime"] = "2026-10-31T12:00:00Z"
    assert collect(monkeypatch, schedule, games.iloc[1:]).missing_due_game_ids == ("0022600001",)


@pytest.mark.parametrize(
    "damage",
    [
        "schedule_id",
        "schedule_date",
        "duplicate_schedule",
        "game_id",
        "game_date",
        "wrong_game_day",
        "duplicate_game",
        "final_flag",
        "missing_column",
        "wrong_season",
        "unscheduled_game",
    ],
)
def test_bad_identity_or_date_is_unknown_not_complete(monkeypatch, damage):
    schedule, games = frames()
    if damage == "schedule_id":
        schedule.loc[0, "game_id"] = "bad"
    elif damage == "schedule_date":
        schedule.loc[0, "game_date"] = "bad"
    elif damage == "duplicate_schedule":
        schedule = pd.concat([schedule, schedule.iloc[:1]], ignore_index=True)
    elif damage == "game_id":
        games["game_id"] = games.game_id.astype(str)
        games.loc[0, "game_id"] = "22600001.5"
    elif damage == "game_date":
        games.loc[0, "game_date"] = "bad"
    elif damage == "wrong_game_day":
        games.loc[0, "game_date"] = "2026-10-28"
    elif damage == "duplicate_game":
        games = pd.concat([games, games.iloc[:1]], ignore_index=True)
    elif damage == "final_flag":
        games.loc[0, "is_final"] = 2
    elif damage == "missing_column":
        games = games.drop(columns="game_id")
    elif damage == "unscheduled_game":
        games.loc[0, "game_id"] = 22600999
    else:
        games.loc[0, "game_id"] = 22500001
    item = collect(monkeypatch, schedule, games)
    assert item.missing_due_game_ids is None
    assert item.to_dict()["missing_due_game_ids"] is None
    result = evaluate(item)
    assert not result.ready
    assert [b.code for b in result.blockers] == ["active_schedule_coverage_unknown"]


def test_unknown_exact_population_cannot_be_waived_by_lag_exception(monkeypatch):
    schedule, games = frames()
    item = replace(collect(monkeypatch, schedule, games), missing_due_game_ids=None)
    result = evaluate(
        item,
        NBATOOLS_READINESS_EXCEPTION_REASON="Fixture exception",
        NBATOOLS_READINESS_EXCEPTION_CREATED_AT="2026-11-01T11:00:00Z",
        NBATOOLS_READINESS_EXCEPTION_EXPIRES_AT="2026-11-02T11:00:00Z",
    )
    assert not result.ready and not result.exception.applied
    assert [b.code for b in result.blockers] == ["active_schedule_coverage_unknown"]


def test_contradictory_future_instant_cannot_hide_missing_earlier_game(monkeypatch):
    schedule, games = frames()
    schedule.loc[0, "game_datetime"] = "2026-11-05T23:00:00Z"
    item = collect(monkeypatch, schedule, games.iloc[1:])
    assert item.current_through == item.expected_current_through == "2026-10-30"
    assert item.missing_due_game_ids is None
    result = evaluate(item)
    assert not result.ready
    assert [b.code for b in result.blockers] == ["active_schedule_coverage_unknown"]


def test_eastern_date_and_blank_legacy_fallback_are_preserved(monkeypatch):
    schedule, games = frames()
    schedule.loc[0, "game_datetime"] = "2026-10-30T01:00:00Z"
    assert collect(monkeypatch, schedule, games).missing_due_game_ids == ()
    schedule["game_datetime"] = ""
    assert collect(monkeypatch, schedule, games).missing_due_game_ids == ()
    assert collect(monkeypatch, schedule, games.iloc[1:]).missing_due_game_ids == ("0022600001",)
