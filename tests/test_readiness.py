from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from nbatools.readiness import (
    ReadinessSnapshot,
    SeasonState,
    SliceEvidence,
    _expected_current_through,
    _postseason_complete,
    evaluate_readiness,
)

NOW = datetime(2026, 7, 14, 12, tzinfo=UTC)


def _slice(
    season_type: str,
    *,
    trusted: bool = True,
    current: str | None = "2026-06-13",
    expected: str | None = "2026-06-13",
    schedule_complete: bool = True,
    postseason_complete: bool = False,
) -> SliceEvidence:
    return SliceEvidence(
        season="2025-26",
        season_type=season_type,
        trusted=trusted,
        validation_state="passed" if trusted else "legacy_unverified",
        generation_id="slice-generation" if trusted else None,
        current_through=current,
        expected_current_through=expected,
        schedule_complete=schedule_complete,
        postseason_complete=postseason_complete,
        errors=() if trusted else ("versioned dataset manifest missing",),
    )


def _snapshot(
    *,
    immutable: bool = True,
    regular: SliceEvidence | None = None,
    playoffs: SliceEvidence | None = None,
    last_refresh_ok: bool | None = True,
) -> ReadinessSnapshot:
    return ReadinessSnapshot(
        active_generation="release-2026-07" if immutable else "legacy",
        immutable_generation=immutable,
        generation_error=None if immutable else "mutable legacy paths",
        regular_season=regular or _slice("Regular Season"),
        playoffs=playoffs,
        last_refresh_ok=last_refresh_ok,
    )


def test_completed_postseason_is_ready_in_immutable_offseason_generation() -> None:
    info = evaluate_readiness(
        _snapshot(playoffs=_slice("Playoffs", postseason_complete=True)),
        checked_at=NOW,
        env={},
    )

    assert info.ready is True
    assert info.status == "ready"
    assert info.season_state is SeasonState.OFFSEASON
    assert info.blockers == ()


def test_completed_season_does_not_become_stale_from_age_alone() -> None:
    old_regular = _slice("Regular Season", current="2026-04-12", expected="2026-04-12")
    old_playoffs = _slice(
        "Playoffs",
        current="2026-06-13",
        expected="2026-06-13",
        postseason_complete=True,
    )

    info = evaluate_readiness(
        _snapshot(regular=old_regular, playoffs=old_playoffs),
        checked_at=datetime(2027, 9, 1, tzinfo=UTC),
        env={},
    )

    assert info.ready is True
    assert info.season_state is SeasonState.OFFSEASON


def test_postseason_complete_still_requires_immutable_generation() -> None:
    info = evaluate_readiness(
        _snapshot(
            immutable=False,
            playoffs=_slice("Playoffs", postseason_complete=True),
        ),
        checked_at=NOW,
        env={},
    )

    assert info.ready is False
    assert info.season_state is SeasonState.POSTSEASON_COMPLETE
    assert [item.code for item in info.blockers] == ["immutable_generation_required"]


def test_active_season_uses_24_hour_schedule_lag_budget() -> None:
    active = _slice(
        "Regular Season",
        current="2026-01-10",
        expected="2026-01-11",
        schedule_complete=False,
    )

    info = evaluate_readiness(_snapshot(regular=active, playoffs=None), checked_at=NOW, env={})

    assert info.ready is False
    assert info.season_state is SeasonState.ACTIVE
    assert [item.code for item in info.blockers] == ["active_season_lag"]


def test_valid_exception_can_waive_only_active_lag_for_at_most_24_hours() -> None:
    active = _slice(
        "Regular Season",
        current="2026-07-12",
        expected="2026-07-13",
        schedule_complete=False,
    )
    env = {
        "NBATOOLS_READINESS_EXCEPTION_REASON": "Upstream schedule outage",
        "NBATOOLS_READINESS_EXCEPTION_CREATED_AT": "2026-07-14T10:00:00Z",
        "NBATOOLS_READINESS_EXCEPTION_EXPIRES_AT": "2026-07-15T10:00:00Z",
    }

    info = evaluate_readiness(_snapshot(regular=active), checked_at=NOW, env=env)

    assert info.ready is True
    assert info.exception.applied is True
    assert info.exception.owner == "John Matthew, project owner"


def test_exception_never_waives_untrusted_playoff_or_immutable_generation() -> None:
    env = {
        "NBATOOLS_READINESS_EXCEPTION_REASON": "Requested waiver",
        "NBATOOLS_READINESS_EXCEPTION_CREATED_AT": "2026-07-14T10:00:00Z",
        "NBATOOLS_READINESS_EXCEPTION_EXPIRES_AT": "2026-07-15T10:00:00Z",
    }
    info = evaluate_readiness(
        _snapshot(immutable=False, playoffs=_slice("Playoffs", trusted=False)),
        checked_at=NOW,
        env=env,
    )

    assert info.ready is False
    assert info.exception.applied is False
    assert {item.code for item in info.blockers} == {
        "immutable_generation_required",
        "season_state_unknown",
        "playoff_slice_untrusted",
    }


def test_expected_coverage_ignores_games_inside_24_hour_grace_window() -> None:
    schedule = pd.DataFrame(
        {
            "game_date": ["2026-01-10", "2026-01-11", "2026-01-12"],
            "game_datetime": [
                "2026-01-10T23:00:00Z",
                "2026-01-11T23:00:00Z",
                "2026-01-12T23:00:00Z",
            ],
        }
    )

    assert (
        _expected_current_through(schedule, datetime(2026, 1, 12, 12, tzinfo=UTC)) == "2026-01-10"
    )


def test_postseason_completion_requires_four_finals_wins_and_full_final_coverage() -> None:
    game_ids = [f"4250040{number}" for number in range(1, 6)]
    schedule = pd.DataFrame({"game_id": game_ids, "status": ["Final"] * 5})
    games = pd.DataFrame({"game_id": game_ids, "is_final": [1] * 5})
    team_stats = pd.DataFrame(
        {
            "game_id": [item for game_id in game_ids for item in (game_id, game_id)],
            "team_id": [1, 2] * 5,
            "wl": ["W", "L", "W", "L", "L", "W", "W", "L", "W", "L"],
        }
    )

    assert _postseason_complete(schedule, games, team_stats) is True

    incomplete_games = games.iloc[:-1]
    assert _postseason_complete(schedule, incomplete_games, team_stats) is False
