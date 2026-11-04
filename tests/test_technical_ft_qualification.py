"""Retained-source credit qualification and adversarial acceptance boundaries."""

import hashlib
import json
from fractions import Fraction

import pytest

from tools.qualify_technical_ft import event_basis, qualify_pair, retained_inputs, stage
from tools.readiness_refresh import SourceCache
from tools.stage_current_season import CURRENT


@pytest.fixture(scope="module")
def retained(tmp_path_factory):
    path = tmp_path_factory.mktemp("technical-ft")
    cache = SourceCache(path / "cache")
    for folder in [
        "q1-laptop-capture",
        "partial-capture-20261103",
        "recovery-capture-20261104",
        "incremental-return-20261104",
    ]:
        archive = CURRENT.parent / folder / "collection.zip"
        cache.import_collection(archive, hashlib.sha256(archive.read_bytes()).hexdigest())
    events, summary, whole, read = retained_inputs(cache)
    return path, events, summary, whole, read


@pytest.fixture(scope="module")
def qualified(retained):
    _, events, _, whole, read = retained
    return {
        (start, end): qualify_pair(
            events,
            whole,
            read("boxscoretraditionalv3", start, end, 1),
            read("boxscoreadvancedv3", start, end, 1),
            start=start,
            end=end,
        )
        for start, end in [(1, 1), (2, 2), (1, 2)]
    }


def test_complete_actual_rate_populations_match_independent_event_counts(qualified):
    assert [len(qualified[window][1]["cases"]) for window in [(1, 1), (2, 2), (1, 2)]] == [
        17,
        19,
        19,
    ]
    q2 = {p["player_id"]: p for p in qualified[2, 2][1]["cases"]}
    johnson = q2[1630552]
    assert johnson["rates"]["usagePercentage"] == dict(
        numerator=3, denominator=16, exact="3/16", reported=0.188
    )
    assert johnson["rates"]["assistPercentage"]["exact"] == "3/7"
    assert johnson["rates"]["reboundPercentage"]["exact"] == "1/13"
    assert johnson["rates"]["turnoverRatio"]["exact"] == "50/3"
    assert johnson["credited_points_for"] == 19 and johnson["credited_points_against"] == 9
    assert Fraction(johnson["independent_offensive_rating"]) == Fraction(475, 4)
    assert johnson["original_ts"] == 0.5
    assert q2[1630598]["rates"]["usagePercentage"]["denominator"] == 22
    assert q2[1630598]["independent_possessions"] == 20
    assert q2[1642281]["rates"]["usagePercentage"]["denominator"] == 14
    assert q2[1629111]["rates"]["usagePercentage"]["denominator"] == 13
    q1 = {p["player_id"]: p for p in qualified[1, 1][1]["cases"]}
    assert q1[1630596]["rates"]["usagePercentage"]["denominator"] == 20
    assert q1[201935]["rates"]["usagePercentage"]["denominator"] == 20


def test_foul_credit_does_not_move_events_or_redefine_elapsed_lineups(qualified):
    proof = qualified[2, 2][1]
    credits = {r["action_id"]: r for r in proof["periods"][2]["ft_credit"]}
    technical = credits[168]
    assert technical["foul_action_id"] == 162
    assert technical["technical"]
    assert 1629652 in technical["credit_lineups"][1610612737]
    assert 1630552 not in technical["credit_lineups"][1610612737]
    assert 1630552 in technical["elapsed_lineups"][1610612737]
    assert credits[186]["foul_action_id"] == 183
    assert proof["periods"][2]["deadball_rebound_ids"] == [121, 149, 230]
    plays = proof["periods"][2]["plays"]
    assert len([p for p in plays if p["team_id"] == 1610612737]) == 28
    assert len([p for p in plays if p["team_id"] == 1610612739]) == 30
    assert any(p["end_action"] == 236 for p in plays)
    assert any(p["start_action"] == 237 and p["incomplete"] for p in plays)
    assert not proof["reported_possessions_used_as_oracle"]
    assert not proof["advanced_rates_rewritten"]
    assert not proof["full_general_credit_model_accepted"]


def test_only_explicit_missing_shooting_fields_and_clocks_are_copied(qualified):
    for window in [(2, 2), (1, 2)]:
        proof = qualified[window][1]
        assert len(proof["changes"]) == 8
        assert {r["field"] for r in proof["changes"]} == {
            "points",
            "freeThrowsMade",
            "freeThrowsAttempted",
            "freeThrowsPercentage",
        }
        assert {r["player_id"] for r in proof["changes"]} == {0, 1630552}
        assert not proof["full_snapshot_accepted"]
        assert proof["production_writes"] == 0


def test_reported_possessions_are_corroboration_never_the_oracle(retained, qualified):
    _, events, _, whole, read = retained
    advanced = json.loads(read("boxscoreadvancedv3", 2, 2, 1))
    for side in ["homeTeam", "awayTeam"]:
        for person in advanced["boxScoreAdvanced"][side]["players"]:
            person["statistics"]["possessions"] = 999
    _, proof = qualify_pair(
        events,
        whole,
        read("boxscoretraditionalv3", 2, 2, 1),
        json.dumps(advanced).encode(),
        start=2,
        end=2,
    )
    assert not any(p["reported_possessions_corroborate"] for p in proof["cases"])
    assert [p["rates"] for p in proof["cases"]] == [p["rates"] for p in qualified[2, 2][1]["cases"]]


@pytest.mark.parametrize(
    "field",
    [
        "usagePercentage",
        "assistPercentage",
        "reboundPercentage",
        "turnoverRatio",
        "offensiveRating",
    ],
)
def test_changed_reported_rates_cannot_be_promoted(retained, field):
    _, events, _, whole, read = retained
    advanced = json.loads(read("boxscoreadvancedv3", 2, 2, 1))
    p = next(
        p for p in advanced["boxScoreAdvanced"]["homeTeam"]["players"] if p["personId"] == 1630552
    )
    p["statistics"][field] += 0.1
    with pytest.raises(ValueError, match="Independent .* differs"):
        qualify_pair(
            events,
            whole,
            read("boxscoretraditionalv3", 2, 2, 1),
            json.dumps(advanced).encode(),
            start=2,
            end=2,
        )


@pytest.mark.parametrize(
    "mutation",
    ["missing_foul", "conflicting_trip", "wrong_jump_winner", "ambiguous_assist", "reordered"],
)
def test_unsupported_event_evidence_stays_rejected(retained, mutation):
    _, events, _, whole, _ = retained
    document = json.loads(events)
    rows = document["game"]["actions"]
    if mutation == "missing_foul":
        rows[161]["subType"] = "Bench"
    elif mutation == "conflicting_trip":
        rows[121]["subType"] = "Free Throw 2 of 3"
    elif mutation == "wrong_jump_winner":
        rows[117]["description"] = "Jump Ball Landale vs. Allen: Tip to Johnson"
    elif mutation == "ambiguous_assist":
        rows[156]["description"] = "Wiggins 3PT (7 PTS) (Unknown 2 AST)"
    else:
        rows[162], rows[167] = rows[167], rows[162]
    with pytest.raises(ValueError):
        event_basis(json.dumps(document).encode(), whole)


def test_real_pipeline_consumers_and_all_sixteen_requirements(retained):
    work, *_ = retained
    report = stage(work / "cache", work / "stage")
    assert report["admitted_windows"] == 645
    assert report["retained_direct_successes"] == 1537
    assert report["raw_bytes_preserved"] and report["prior_period_prefixes_preserved"]
    assert report["remaining_period_windows"] == [
        ["0022600142", "quarter", "3"],
        ["0022600142", "half", "second"],
    ]
    assert [r["rows"][0]["pts"] for r in report["consumers"]] == [3, 5]
    assert report["consumers"][0]["rows"][0]["ts_pct"] == pytest.approx(75 / 122)
    assert report["consumers"][1]["rows"][0]["ts_pct"] == pytest.approx(125 / 272)
    assert all(p["state"] == "passed" for p in report["executed_stages"][1:])
    assert report["executed_stages"][0]["state"] == "failed"
    assert "missing 48 requested keys" in report["executed_stages"][0]["error"]
    assert sum(d["required"] for d in report["dataset_assessment"]["datasets"]) == 16
    assert not report["full_snapshot_accepted"]
    assert report["production_writes"] == 0
