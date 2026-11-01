"""Team observations retain team grain and source authority during rollover."""

import copy

import pandas as pd
import pytest

from tests.test_season_rollover_core_bridge import fixture, source
from tools.season_rollover_core_bridge import FIELDS, bridge_teams


def team_fixture():
    _, schedule, primary, box, _, _ = fixture()
    for side in ["homeTeam", "awayTeam"]:
        team = box[side]
        for key in FIELDS:
            team["statistics"][key] = sum(p["statistics"][key] for p in team["players"])
        mask = primary.TEAM_ID.eq(team["teamId"])
        for key, field in FIELDS.items():
            primary.loc[mask, field] = team["statistics"][key]
        for prefix in ["FG", "FG3", "FT"]:
            primary.loc[mask, prefix + "_PCT"] = (
                1.0 if primary.loc[mask, prefix + "A"].iloc[0] else 0.0
            )
    primary["TEAM_NAME"] = ["Home identity", "Away identity"]
    return primary, schedule, box


def run(data, boxes=None):
    primary, schedule, box = data
    return bridge_teams(
        primary,
        schedule,
        [
            source(f"traditional-{i}.json", dict(boxScoreTraditional=b))
            for i, b in enumerate(boxes or [box])
        ],
    )


def test_direct_team_counts_and_rates_preserve_identity_order_and_primary_bytes():
    data = team_fixture()
    primary, _, box = data
    primary.loc[0, ["AST", "FGA", "FG_PCT"]] = [8, 6, 0.833]
    box["homeTeam"]["statistics"]["assists"] = 9
    original = primary.copy(deep=True)
    staged, ledger = run(data)
    pd.testing.assert_frame_equal(primary, original)
    assert staged.loc[0, ["AST", "FGA", "FG_PCT"]].tolist() == [9, 5, 1.0]
    assert staged.TEAM_NAME.tolist() == original.TEAM_NAME.tolist()
    pd.testing.assert_series_equal(staged.iloc[1], original.iloc[1])
    changed = [x for x in ledger if x["before"] != x["after"]]
    assert {x["field"] for x in changed} == {"AST", "FGA", "FG_PCT"}
    assert all("player_id" not in x and x["team_id"] == 1 for x in changed)
    assert next(x for x in changed if x["field"] == "AST")["source_field"] == "assists"
    assert all(len(x["source_sha256"]) == 64 for x in changed)


def test_explicit_team_rebounds_are_not_inferred_from_player_rebound_sum():
    data = team_fixture()
    stats = data[2]["homeTeam"]["statistics"]
    stats.update(reboundsOffensive=1, reboundsDefensive=2, reboundsTotal=3)
    staged, _ = run(data)
    assert staged.loc[0, ["OREB", "DREB", "REB"]].tolist() == [1, 2, 3]


def test_missing_explicit_team_count_is_not_filled_from_players():
    data = team_fixture()
    del data[2]["homeTeam"]["statistics"]["assists"]
    with pytest.raises(ValueError, match="fields are missing"):
        run(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("points", 12),
        ("reboundsTotal", 1),
        ("fieldGoalsAttempted", 0),
        ("threePointersAttempted", 6),
        ("assists", -1),
    ],
)
def test_invalid_explicit_team_count_cannot_replace_primary(field, value):
    data = team_fixture()
    data[2]["homeTeam"]["statistics"][field] = value
    original = data[0].copy(deep=True)
    with pytest.raises(ValueError):
        run(data)
    pd.testing.assert_frame_equal(data[0], original)


def test_conflicting_team_observations_fail_without_a_last_source_winner():
    data = team_fixture()
    conflicting = copy.deepcopy(data[2])
    conflicting["homeTeam"]["statistics"]["assists"] += 1
    with pytest.raises(ValueError, match="same team field"):
        run(data, [data[2], conflicting])


def test_duplicate_primary_team_key_and_wrong_source_side_fail():
    data = team_fixture()
    data = [pd.concat([data[0], data[0].iloc[[0]]], ignore_index=True), data[1], data[2]]
    with pytest.raises(ValueError, match="Duplicate authoritative"):
        run(data)
    data = team_fixture()
    data[2]["homeTeam"]["teamId"] = 3
    with pytest.raises(ValueError, match="side identity"):
        run(data)


def test_team_reconciliation_keeps_strict_player_clock_admission():
    data = team_fixture()
    data[2]["homeTeam"]["players"][0]["statistics"]["minutes"] = "pt41m60s"
    with pytest.raises(ValueError, match="duration"):
        run(data)


def test_empty_source_selection_preserves_primary():
    primary, schedule, _ = team_fixture()
    result, ledger = bridge_teams(primary, schedule)
    pd.testing.assert_frame_equal(result, primary)
    assert ledger == []
