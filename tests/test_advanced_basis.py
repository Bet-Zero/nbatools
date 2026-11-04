"""Independent source-basis and bounded NBA possession exposure regressions."""

import json
from fractions import Fraction

import pytest

from tools.qualify_advanced_basis import (
    SOURCE_SHA,
    bound_zip,
    possession_exposure,
    qualify,
    true_shooting,
)
from tools.stage_current_season import CURRENT, PARTIAL, RECOVERY, _whole_original


@pytest.fixture(scope="module")
def qualified(tmp_path_factory):
    return qualify(tmp_path_factory.mktemp("advanced") / "qualified")


@pytest.fixture(scope="module")
def usage_inputs():
    with bound_zip(CURRENT / "current-sources.zip", SOURCE_SHA) as z:
        events = z.read("playbyplayv3-0022600116.json")
    with bound_zip(
        PARTIAL / "collection.zip",
        "03ee634189d3f245badbd0baadc60ddaeac4b9efd978c5d2bd62d02aa7d4ceb3",
    ) as z:
        traditional = z.read("sources/boxscoretraditionalv3_0022600116_q1.json")
    with bound_zip(
        RECOVERY / "collection.zip",
        "7eb2f30f0afa7806fd2e7a7bca98c1a42c1b3d480134c226f577f99f1415bf17",
    ) as z:
        advanced = z.read("sources/boxscoreadvancedv3_0022600116_q1.json")
    return events, _whole_original("0022600116"), traditional, advanced


def test_all_reported_ts_resolves_to_retained_original_count_basis(qualified):
    assert qualified["raw_basis_player_ts_qualified"] == 448
    assert qualified["raw_basis_team_ts_qualified"] == 30
    assert qualified["canonical_player_ts_differences"] == 12
    assert qualified["canonical_team_ts_differences"] == 3
    assert not qualified["accepted_values_rewritten"]
    assert not qualified["full_snapshot_accepted"]
    boozer = next(r for r in qualified["true_shooting"]["player"] if r["identity"] == 1643409)
    assert boozer["canonical_counts"] == [124, 96, 36]
    assert Fraction(boozer["canonical_exact_ts"]) == Fraction(775, 1398)
    assert boozer["reported_matches_original_basis"]
    assert boozer["reported_differs_canonical_basis"]


def test_real_clock_rounding_uncertainty_stays_unknown(qualified):
    assert qualified["minute_states"] == {
        "raw_basis_rounding_matches": 441,
        "real_clock_boundary_unknown": 7,
    }
    cases = {
        r["player_id"]
        for r in qualified["minute_basis"]
        if r["state"] == "real_clock_boundary_unknown"
    }
    assert cases == {201144, 203081, 1629162, 1630192, 1630695, 1641712, 1642854}
    for row in qualified["minute_basis"]:
        assert set(row["retained_event_game_ids"]) | set(row["missing_event_game_ids"]) == set(
            row["game_ids"]
        )
        if row["state"] == "real_clock_boundary_unknown":
            assert row["precise_clock_requirement"]


def test_exposure_denominators_include_partial_and_unfinished_possessions(qualified):
    sample = qualified["independent_usage"]
    assert sample["sample_usage_accepted"]
    assert not sample["full_independent_NBA_usage_accepted"]
    assert not sample["reported_possessions_used_as_oracle"]
    denominators = {r["player_id"]: r["exposure_denominator"] for r in sample["cases"]}
    assert denominators == {
        1627884: 19,
        1629060: 17,
        1630543: 14,
        1627739: 20,
        1629636: 21,
        1643413: 15,
        1642394: 5,
        201572: 12,
        1642920: 9,
        1641711: 9,
    }
    terminal = sample["possessions"][-1]
    assert terminal["start_action"] == 123 and terminal["end_action"] == 124
    assert terminal["incomplete"]
    assert terminal["players"] == [201572, 1627739, 1641711, 1642920, 1643413]
    crossing = next(p for p in sample["possessions"] if p["start_action"] == 69)
    assert crossing["end_action"] == 75
    assert 1629060 in crossing["players"] and 201572 in crossing["players"]


def test_reported_possessions_cannot_drive_the_oracle(usage_inputs):
    events, whole, traditional, advanced = usage_inputs
    doc = json.loads(advanced)
    for p in doc["boxScoreAdvanced"]["awayTeam"]["players"]:
        p["statistics"]["possessions"] = 999
    result = possession_exposure(
        events, whole, traditional, json.dumps(doc).encode(), team_id=1610612746, period=1
    )
    assert all(r["matches"] for r in result["cases"])
    assert not any(r["reported_possessions_corroborates"] for r in result["cases"])


def test_team_with_free_throws_requires_other_qualified_oracle(usage_inputs):
    with pytest.raises(ValueError, match="requires no own FTA or OREB"):
        possession_exposure(*usage_inputs, team_id=1610612760, period=1)


@pytest.mark.parametrize("counts", [(-1, 1, 0), (1, 0.5, 0), (1, 1, -1), (1, 0, 0)])
def test_true_shooting_refuses_invalid_counts(counts):
    with pytest.raises(ValueError, match="Invalid TS count basis"):
        true_shooting(*counts)


@pytest.mark.parametrize("action_id,owner,person", [(3, 0, 1631096), (9, 0, 123456)])
def test_unknown_possession_ownership_is_not_opponent_evidence(
    usage_inputs, action_id, owner, person
):
    events, whole, traditional, advanced = usage_inputs
    doc = json.loads(events)
    row = next(a for a in doc["game"]["actions"] if a["actionId"] == action_id)
    row["teamId"], row["personId"] = owner, person
    with pytest.raises(ValueError, match="unknown team ownership"):
        possession_exposure(
            json.dumps(doc).encode(), whole, traditional, advanced, team_id=1610612746, period=1
        )


def test_gp1_boundary_has_independent_exact_clock_with_existing_inclusive_limit(qualified):
    assert qualified["independent_real_clock_qualified_count"] == 1
    case = qualified["independent_real_clock_qualifications"][0]
    assert case["player_id"] == 1641712
    assert case["game_ids"] == ["0022600163"] and case["games"] == 1
    assert case["exact_seconds"] == "123"
    assert Fraction(case["exact_mean_minutes"]) == Fraction(41, 20)
    assert Fraction(case["reported_minutes"]) == Fraction(21, 10)
    assert case["absolute_residual_minutes"] == case["unchanged_inclusive_limit_minutes"] == "1/20"
    assert case["state"] == "qualified_exact_clock_boundary"
    assert case["original_event_order_preserved"] and not case["rounding_policy_invented"]
    assert set(qualified["remaining_real_clock_boundary_unknown_player_ids"]) == {
        201144,
        203081,
        1629162,
        1630192,
        1630695,
        1642854,
    }
