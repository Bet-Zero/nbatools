"""Reviewer-authored controls; controlled data, not NBA tenure evidence."""

from datetime import date

import pandas as pd
import pytest

from nbatools.commands._dated_membership import (
    calendar_date,
    membership_on_date,
    validate_intervals,
)

pytestmark = pytest.mark.engine

SEASON = "2023-24"


def item(team, start, end, state="member", player=808):
    return dict(
        season=SEASON,
        player_id=player,
        player_name="Mica Transfer",
        team_id=team,
        start_date=start,
        end_date=end,
        membership_state=state,
        coverage_scope="explicit_dated_nba_membership",
        source="https://www.nba.com/controlled-review-fixture",
        source_sha256="d" * 64,
    )


def ledger(*items):
    return validate_intervals(pd.DataFrame(items), SEASON)


@pytest.mark.parametrize(
    "day,team,state,club",
    [
        ("2024-01-31", 501, "unknown", None),
        ("2024-02-01", 501, "member", 501),
        ("2024-02-06", 501, "member", 501),
        ("2024-02-07", 501, "unknown", None),
        ("2024-02-08", 501, "not_member", 502),
        ("2024-02-08", 502, "member", 502),
        ("2024-02-12", 502, "member", 502),
        ("2024-02-13", 502, "unknown", None),
    ],
)
def test_inclusive_boundaries_and_unproven_transfer_day(day, team, state, club):
    rows = ledger(item(501, "2024-02-01", "2024-02-06"), item(502, "2024-02-08", "2024-02-12"))
    actual = membership_on_date(rows, 808, calendar_date(day), team)
    assert (actual.state, actual.team_id) == (state, club)


@pytest.mark.parametrize("asked,state", [(501, "not_member"), (502, "unknown"), (None, "unknown")])
def test_negative_fact_does_not_identify_another_club(asked, state):
    rows = ledger(item(501, "2024-02-08", "2024-02-12", "not_member"))
    actual = membership_on_date(rows, 808, date(2024, 2, 9), asked)
    assert actual.state == state and actual.team_id is None


@pytest.mark.parametrize(
    "bad",
    [
        "20240209",
        "2024-W06-5",
        "2024-2-9",
        "2024-02-09T00:00:00Z",
        "02/09/2024",
        "2024-02-30",
        None,
        20240209,
    ],
)
def test_date_is_unambiguous_calendar_day(bad):
    with pytest.raises(ValueError):
        calendar_date(bad)


@pytest.mark.parametrize(
    "rows",
    [
        [item(501, "2024-02-01", "2024-02-08"), item(502, "2024-02-08", "2024-02-12")],
        [
            item(501, "2024-02-01", "2024-02-08"),
            item(501, "2024-02-08", "2024-02-12", "not_member"),
        ],
        [item(501, "2024-02-08", "2024-02-01")],
    ],
)
def test_conflicting_inclusive_facts_and_reversal_reject(rows):
    with pytest.raises(ValueError):
        ledger(*rows)


def test_exact_game_can_establish_team_but_cannot_override_intervals():
    rows = ledger(item(501, "2024-02-01", "2024-02-06"))
    actual = membership_on_date(rows, 808, date(2024, 2, 7), 501, exact_team_id=502)
    assert (actual.state, actual.team_id) == ("not_member", 502)
    with pytest.raises(ValueError, match="Contradictory"):
        membership_on_date(rows, 808, date(2024, 2, 6), 501, exact_team_id=502)


def test_negative_exact_game_conflict_rejects():
    rows = ledger(item(501, "2024-02-01", "2024-02-06", "not_member"))
    with pytest.raises(ValueError, match="Contradictory"):
        membership_on_date(rows, 808, date(2024, 2, 6), 501, exact_team_id=501)


def test_other_player_interval_does_not_fill_missing_identity():
    rows = ledger(item(501, "2024-02-01", "2024-02-06", player=999))
    assert membership_on_date(rows, 808, date(2024, 2, 3)).state == "unknown"


def test_opponent_interval_ownership_does_not_turn_unknown_into_false(monkeypatch):
    from nbatools.commands import _dated_membership as m
    from nbatools.commands import _participation_observations as p

    rows = ledger(item(502, "2024-02-01", "2024-02-06"))
    empty = pd.DataFrame(
        columns=[
            "game_id",
            "game_date",
            "team_id",
            "player_id",
            "player_name",
            "participation_state",
        ]
    )
    monkeypatch.setattr(p, "combined_observations", lambda *a: (empty, set()))
    monkeypatch.setattr(m, "load_membership", lambda *a: rows)
    monkeypatch.setattr(p, "player_ids_for_name", lambda *a: ["808"])
    candidates = pd.DataFrame(
        [dict(game_id=9001, team_id=501, opponent_team_id=502, game_date="2024-02-03")]
    )
    with pytest.raises(ValueError, match="Incomplete"):
        p.filter_absent(
            candidates, "Mica Transfer", [SEASON], "Regular Season", opponent_context=True
        )
