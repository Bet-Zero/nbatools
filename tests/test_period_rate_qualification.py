"""Grouped rate recovery, independent input boundaries and literal preservation."""

import copy
import csv
import io
import json
import zipfile
from datetime import UTC, datetime
from fractions import Fraction

import pandas as pd
import pytest

from tools.qualify_period_counts import EVIDENCE as PRIOR
from tools.qualify_period_rates import (
    SUFFIX,
    free_throw_facts,
    play_exposure,
    qualify,
    rebound_facts,
    retained_sources,
)
from tools.qualify_rollover_q1 import _local_stage


@pytest.fixture(scope="module")
def qualified(tmp_path_factory):
    out = tmp_path_factory.mktemp("grouped-rates") / "qualified"
    return out, qualify(out, now=datetime(2026, 11, 5, 12, tzinfo=UTC))


def test_complete_withheld_population_and_unknowns(qualified):
    out, report = qualified
    assert report["original_withheld"] == 1365
    assert report["qualified_by_field"] == dict(ast_pct=226, reb_pct=277, tov_pct=180, usg_pct=128)
    assert report["qualified"] == 811 and report["unresolved"] == 554
    keys = {(c["row"], c["field"]) for c in report["changes"]}
    missing = {(c["row"], c["field"]) for c in report["unknown"]}
    assert len(keys) == 811 and len(missing) == 554 and not keys & missing
    assert not report["production_ready"] and not report["full_numerical_acceptance"]
    assert not report["reported_rates_used_as_oracle"]
    assert not report["reported_possessions_used_as_oracle"]
    frame = pd.read_csv(out / f"stage/data/raw/player_game_period_stats/{SUFFIX}")
    for row, field in missing:
        assert pd.isna(frame.loc[row, field])
    assert len([d for d in report["dataset_assessment"]["datasets"] if d["required"]]) == 16


def test_every_undeclared_cell_and_dataset_survives(qualified):
    out, report = qualified
    name = f"stage/data/raw/player_game_period_stats/{SUFFIX}"
    with zipfile.ZipFile(PRIOR / "qualification-evidence.zip") as z:
        before = list(csv.reader(io.StringIO(z.read(name).decode())))
        after = list(csv.reader(io.StringIO((out / name).read_text())))
        allowed = {(c["row"] + 1, before[0].index(c["field"])) for c in report["changes"]}
        for i, (left, right) in enumerate(zip(before, after, strict=True)):
            for j, (old, new) in enumerate(zip(left, right, strict=True)):
                assert old == new or (i, j) in allowed
        for member in z.namelist():
            if member.startswith("stage/data/") and member.endswith(".csv") and member != name:
                assert (out / member).read_bytes() == z.read(member)


def test_actual_finder_restores_rates_on_corrected_counts(qualified):
    from nbatools.commands.player_game_finder import build_result

    out, report = qualified
    with _local_stage(out / "stage"):
        result = build_result(
            player="Austin Reaves",
            season="2026-27",
            quarter="3",
            start_date="2026-10-23",
            end_date="2026-10-23",
        )
        assert result.result_status == "ok"
        assert result.games.game_id.tolist() == [22600102]
        assert result.games.iloc[0].tov_pct == pytest.approx(float(Fraction(1, 11)))
    assert all(c["denominator"] >= 0 for c in report["changes"])


def test_defensive_three_seconds_is_not_live_rebound():
    actions = json.loads(retained_sources()["0022600092"])["game"]["actions"]
    q1 = [a for a in actions if a["period"] == 1]
    assert 110 in rebound_facts(q1, {1610612756, 1610612757})


def test_incomplete_and_unsupported_trips_remain_unknown():
    actions = json.loads(retained_sources()["0022600118"])["game"]["actions"]
    with pytest.raises(ValueError, match="Incomplete or conflicting FT trip"):
        free_throw_facts([a for a in actions if a["period"] == 4], {1610612758, 1610612763})


@pytest.mark.parametrize("subtype", ["Flagrant Type 1", "Away From Play", "Unknown"])
def test_ordinary_ft_labels_do_not_override_unsupported_foul(subtype):
    actions = json.loads(retained_sources()["0022600109"])["game"]["actions"]
    q4 = copy.deepcopy([a for a in actions if a["period"] == 4])
    next(a for a in q4 if a["actionId"] == 463)["subType"] = subtype
    with pytest.raises(ValueError, match="Unsupported FT foul semantics"):
        free_throw_facts(q4, {1610612742, 1610612759})


def action(aid, kind, clock, tid=0, pid=0, description="", subtype=""):
    return dict(
        actionId=aid,
        actionType=kind,
        clock=f"PT{clock // 60:02}M{clock % 60:02}S",
        teamId=tid,
        personId=pid,
        description=description,
        subType=subtype,
    )


def test_substitution_at_new_clock_preserves_both_players_exposure():
    acts = [
        action(1, "period", 720, subtype="start"),
        action(2, "Made Shot", 710, 1, 11),
        action(3, "Substitution", 705, 2, 21),
        action(4, "Made Shot", 700, 2, 22),
        action(5, "period", 0, subtype="end"),
    ]
    before = {1: [11, 12, 13, 14, 15], 2: [21, 22, 23, 24, 25]}
    after = {1: before[1], 2: [26, 22, 23, 24, 25]}
    lineups = {1: before, 2: before, 3: before, 4: after, 5: after}
    plays = play_exposure(acts, {1, 2}, lineups, dict(credit={}, andones={}, dead=set()), {})
    own = next(p for p in plays if p["team_id"] == 2)
    assert {21, 26} <= set(own["players"])
    assert own["elapsed_seconds"][21] == own["elapsed_seconds"][26] == "5"


def test_jump_winner_must_independently_establish_owner():
    acts = [
        action(1, "period", 720, subtype="start"),
        action(2, "Jump Ball", 720, description="Jump Ball A vs B: Tip to Other"),
        action(3, "Made Shot", 710, 1, 11),
        action(4, "period", 0, subtype="end"),
    ]
    lineups = {a["actionId"]: {1: [11, 12, 13, 14, 15], 2: [21, 22, 23, 24, 25]} for a in acts}
    with pytest.raises(ValueError, match="Jump ball ownership"):
        play_exposure(
            acts,
            {1, 2},
            lineups,
            dict(credit={}, andones={}, dead=set()),
            {1: {}, 2: {"other": {21}}},
        )


def test_typed_awards_choose_unique_statistically_eligible_fouls():
    sources = retained_sources()
    q1 = [a for a in json.loads(sources["0022600118"])["game"]["actions"] if a["period"] == 1]
    ft = free_throw_facts(q1, {1610612758, 1610612763})
    assert ft["credit"][11] == ft["credit"][12] == 10
    assert ft["trips"][1627734] == 1  # Sabonis's other award is an and-one.
    q3 = [a for a in json.loads(sources["0022600138"])["game"]["actions"] if a["period"] == 3]
    ft = free_throw_facts(q3, {1610612745, 1610612749})
    assert ft["credit"][366] == 365  # Burries technical, separate from Ament's trip.
    assert ft["credit"][367] == ft["credit"][369] == 364
    assert ft["trips"][1643415] == 0 and ft["trips"][1643417] == 1


@pytest.mark.parametrize(
    "subtype,description",
    [
        ("Shooting", "S.FOUL"),
        ("Personal", "P.FOUL (P1.PN)"),
        ("Flagrant Type 1", "FLAGRANT.FOUL.TYPE1"),
    ],
)
def test_competing_eligible_or_unsupported_foul_is_never_discarded(subtype, description):
    q1 = [
        a
        for a in json.loads(retained_sources()["0022600118"])["game"]["actions"]
        if a["period"] == 1
    ]
    q1 = copy.deepcopy(q1)
    extra = next(a for a in q1 if a["actionId"] == 9)
    extra["subType"], extra["description"] = subtype, description
    with pytest.raises(ValueError, match="FT lacks unique same-clock foul"):
        free_throw_facts(q1, {1610612758, 1610612763})


def test_pr580_qualified_values_and_every_other_token_remain_exact(qualified):
    out, report = qualified
    prior_dir = PRIOR.parent / "grouped-rates-20261105"
    name = f"stage/data/raw/player_game_period_stats/{SUFFIX}"
    with zipfile.ZipFile(prior_dir / "qualification-evidence.zip") as z:
        prior = json.loads(z.read("qualification.json"))
        before = list(csv.reader(io.StringIO(z.read(name).decode())))
    after = list(csv.reader(io.StringIO((out / name).read_text())))
    old = {(c["row"], c["field"]) for c in prior["changes"]}
    new = {(c["row"], c["field"]) for c in report["changes"]} - old
    assert len(old) == 701 and len(new) == 110
    assert {(c["row"], c["field"]) for c in prior["unknown"]} == new | {
        (c["row"], c["field"]) for c in report["unknown"]
    }
    for i, (left, right) in enumerate(zip(before, after, strict=True)):
        for j, (a, b) in enumerate(zip(left, right, strict=True)):
            assert a == b or (i - 1, before[0][j]) in new
    assert sum(not g["qualified"] for g in report["groups"]) == 22
