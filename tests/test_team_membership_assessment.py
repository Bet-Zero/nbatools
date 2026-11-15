"""Unfamiliar whole-team source gaps, independent of the two real NBA samples."""

from datetime import date

import pandas as pd
import pytest

from tools.assess_team_membership import assess_team, normalize_movements


def row(kind, player, day="2023-11-02", team=10, sender=0, description="contract"):
    return dict(
        Transaction_Type=kind,
        TRANSACTION_DATE=day + "T00:00:00",
        TRANSACTION_DESCRIPTION=description,
        TEAM_ID=float(team),
        TEAM_SLUG="club",
        PLAYER_ID=float(player),
        PLAYER_SLUG="person",
        Additional_Sort=float(sender),
        GroupSort="source-group",
    )


def native(rows):
    return {"NBA_Player_Movement": {"columns": [{"Name": k} for k in rows[0]], "rows": rows}}


def normalize(rows):
    return normalize_movements(native(rows), [10, 20], date(2023, 10, 23), date(2023, 11, 20))


def assess(events=(), baseline=(1,), appearances=(), disputes=()):
    games = pd.DataFrame(
        [
            dict(game_id=i, game_date=d)
            for i, d in enumerate(
                ["2023-10-24", "2023-11-01", "2023-11-02", "2023-11-03", "2023-11-20"], 1
            )
        ]
    )
    stats = pd.DataFrame(appearances, columns=["game_id", "player_id", "game_date", "minutes"])
    return assess_team(
        team_id=10,
        opening=[dict(player_id=i) for i in baseline],
        document_date="2023-10-23",
        anchor_date="2023-10-24",
        end_date="2023-11-20",
        events=list(events),
        games=games,
        appearances=stats,
        disputes=disputes,
    )


def states(report, player):
    return [r["conditional_membership"] for r in report["cells"] if r["player_id"] == player]


def test_trade_has_departure_and_receipt_while_nonplayer_draft_does_not():
    result = normalize([row("Trade", 2, team=20, sender=10), row("Trade", 0, team=20, sender=10)])
    assert [(e["team_id"], e["action"]) for e in result["events"]] == [
        (10, "not_member"),
        (20, "member"),
    ]
    assert len(result["ignored"]) == 1
    report = assess(result["events"], baseline=(1, 2))
    assert states(report, 2) == ["member", "member", "unknown", "not_member", "not_member"]


def test_opening_conflicts_are_not_silently_repaired_or_assumed_idempotent():
    events = normalize(
        [
            row("Waive", 1, "2023-10-23"),
            row("Signing", 2, "2023-10-23"),
            row("Waive", 3, "2023-10-23"),
        ]
    )["events"]
    report = assess(events)
    assert {x["player_id"] for x in report["opening_conflicts"]} == {1, 2}
    assert states(report, 1) == ["unknown"] * 5
    assert states(report, 2) == ["unknown"] * 5
    assert states(report, 3) == ["not_member"] * 5  # conditional pre-anchor removal
    assert report["accepted_intervals"] == [] and not report["complete_membership"]


def test_conversion_does_not_end_membership_or_invent_a_join():
    events = normalize([row("ContractConverted", 1), row("ContractConverted", 2)])["events"]
    report = assess(events)
    assert states(report, 1) == ["member"] * 5
    assert states(report, 2) == ["unknown"] * 5


def test_preopening_conversion_requires_a_membership_anchor():
    events = normalize(
        [row("ContractConverted", 1, "2023-10-23"), row("ContractConverted", 2, "2023-10-23")]
    )["events"]
    report = assess(events)
    assert states(report, 1) == ["member"] * 5
    assert states(report, 2) == ["unknown"] * 5
    assert {r["player_id"] for r in report["opening_conflicts"]} == {2}


@pytest.mark.parametrize("event", [row("Waive", 2), row("Trade", 2, team=20, sender=10)])
def test_departure_without_a_join_exposes_the_unanchored_earlier_span(event):
    report = assess(normalize([event])["events"])
    assert states(report, 2) == ["unknown", "unknown", "unknown", "not_member", "not_member"]
    assert report["continuity_conflicts"][0]["reason"] == "departure_without_membership_anchor"
    assert report["verified_missed_games"] is None


def test_temporary_contract_without_expiry_stays_unknown_including_season_end():
    events = normalize([row("Signing", 2, description="Signed to a 10-Day Contract.")])["events"]
    report = assess(events)
    assert states(report, 2) == ["not_member", "not_member", "unknown", "unknown", "unknown"]
    assert report["verified_missed_games"] is None


def test_unknown_kind_and_same_day_opposing_events_remain_unknown():
    events = normalize([row("UnknownKind", 1), row("Signing", 2), row("Waive", 2)])["events"]
    report = assess(events)
    for player in (1, 2):
        assert states(report, player)[2:] == ["unknown"] * 3
    assert any(e["action"] == "unknown" for e in report["events"])


def test_exact_facts_and_missing_rows_are_separate_from_the_conditional_history():
    report = assess(appearances=[(2, 1, "2023-11-01", 9), (3, 1, "2023-11-02", 0)])
    assert states(report, 1) == ["member"] * 5
    assert report["participation_cells"] == {"unknown": 4, "played": 1}
    assert report["exact_game_membership_cells"] == {"unknown": 4, "member": 1}
    assert report["accepted_intervals"] == []
    orphan = assess(appearances=[(4, 8, "2023-11-03", 8)])
    assert orphan["unexplained_appearance_people"] == [8]
    assert states(orphan, 8) == ["unknown"] * 5  # never first/last appearance tenure


def test_disputed_dates_remain_unknown_and_actual_appearance_survives():
    events = normalize([row("Waive", 1)])["events"]
    report = assess(
        events,
        appearances=[(4, 1, "2023-11-03", 3)],
        disputes=[dict(player_id=1, start_date="2023-11-02", end_date="2023-11-03")],
    )
    assert states(report, 1) == ["member", "member", "unknown", "unknown", "not_member"]
    cell = next(c for c in report["cells"] if c["game_id"] == 4)
    assert cell["membership_from_appearance"] == "member"
    assert cell["participation"] == "played"


@pytest.mark.parametrize("value", [True, -1, 2.5, float("nan")])
def test_native_decimal_ids_must_be_finite_nonnegative_integers(value):
    bad = row("Signing", 2)
    bad["PLAYER_ID"] = value
    with pytest.raises(ValueError, match="identities"):
        normalize([bad])
