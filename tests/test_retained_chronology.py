"""Real-source and adversarial proof checks for unchanged same-clock chronology."""

import copy
import json
from fractions import Fraction

import pytest

from tools.period_event_evidence import (
    clock_facts,
    period_facts,
    same_clock_score_evidence,
)
from tools.qualify_incremental_return import CLOCK_SHA, SUMMARY_ARCHIVES, bound_zip
from tools.stage_current_season import CURRENT


@pytest.fixture(scope="module")
def sources():
    with bound_zip(
        CURRENT.parent / "incremental-return-20261104/clock-source-originals.zip", CLOCK_SHA
    ) as z:
        raw = z.read("0022600161.json")
    with bound_zip(CURRENT / "current-sources.zip", SUMMARY_ARCHIVES["current-sources.zip"]) as z:
        whole = z.read("boxscoretraditionalv3-0022600161.json")
    box = json.loads(whole)["boxScoreTraditional"]
    final = {box[s]["teamId"]: box[s]["statistics"]["points"] for s in ["homeTeam", "awayTeam"]}
    return raw, whole, final


def test_real_replay_snapshot_does_not_change_event_order_or_clock(sources):
    raw, whole, final = sources
    with pytest.raises(ValueError, match="Unexplained event score change"):
        period_facts(raw, game_id="0022600161", final_teams=final)
    proof = same_clock_score_evidence(raw, game_id="0022600161", final_teams=final)
    obs = proof["observations"]
    assert len(obs) == 1 and obs[0]["action_id"] == 235
    assert obs[0]["explaining_scoring_action_ids"] == [239]
    facts = period_facts(raw, game_id="0022600161", final_teams=final, score_snapshots=proof)
    clocks = clock_facts(raw, whole, period_report=facts)
    assert facts["period_scores"][2] == {1610612752: 24, 1610612751: 23}
    assert facts["period_scores"][3] == {1610612752: 24, 1610612751: 35}
    assert all(sum(v.values()) == 3600 for q in [2, 3] for v in clocks[q].values())
    assert clocks[2][1610612751][1641730] == Fraction(1798, 5)
    assert clocks[3][1610612752][1628384] == Fraction(5399, 10)


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong_score",
        "different_clock",
        "actor_snapshot",
        "scoring_snapshot",
        "reordered",
        "missing_ft",
    ],
)
def test_unexplained_or_reordered_events_stay_rejected(sources, mutation):
    raw, _, final = sources
    doc = json.loads(raw)
    rows = doc["game"]["actions"]
    if mutation == "wrong_score":
        rows[234]["scoreHome"] = "52"
    elif mutation == "different_clock":
        rows[238]["clock"] = "PT00M00.40S"
    elif mutation == "actor_snapshot":
        rows[234]["personId"] = 1628973
    elif mutation == "scoring_snapshot":
        rows[234]["actionType"] = "Made Shot"
    elif mutation == "reordered":
        rows[234], rows[235] = rows[235], rows[234]
    elif mutation == "missing_ft":
        rows.pop(238)
    altered = json.dumps(doc).encode()
    with pytest.raises((ValueError, KeyError)):
        proof = same_clock_score_evidence(altered, game_id="0022600161", final_teams=final)
        period_facts(altered, game_id="0022600161", final_teams=final, score_snapshots=proof)


def test_certificate_cannot_authorize_another_body_or_score(sources):
    raw, _, final = sources
    proof = same_clock_score_evidence(raw, game_id="0022600161", final_teams=final)
    forged = copy.deepcopy(proof)
    forged["observations"][0]["event_prefix_score"][1610612752] = 51
    with pytest.raises(ValueError, match="Score snapshot evidence differs"):
        period_facts(raw, game_id="0022600161", final_teams=final, score_snapshots=forged)


@pytest.fixture(scope="module")
def qualified_stage(tmp_path_factory):
    import hashlib

    from tools.qualify_retained_periods import stage
    from tools.readiness_refresh import SourceCache

    work = tmp_path_factory.mktemp("retained-stage")
    cache = SourceCache(work / "cache")
    for folder in ["q1-laptop-capture", "partial-capture-20261103", "recovery-capture-20261104"]:
        archive = CURRENT.parent / folder / "collection.zip"
        cache.import_collection(archive, hashlib.sha256(archive.read_bytes()).hexdigest())
    from tools.qualify_incremental_return import OUTER_SHA, SEED_SHA

    cache.import_run(
        CURRENT.parent / "incremental-return-20261104/current-run.zip", OUTER_SHA, SEED_SHA
    )
    r = stage(work / "cache", work / "qualified")
    return r, work


def test_two_quarters_are_delivered_without_claiming_full_readiness(qualified_stage):
    r, _ = qualified_stage
    assert r["admitted_windows"] == 643
    assert len(r["admissions"]) == 2
    assert all(x["player_rows"] == 22 and x["team_rows"] == 2 for x in r["admissions"])
    assert r["raw_bytes_preserved"] and r["prior_period_prefixes_preserved"]
    assert not r["full_snapshot_accepted"] and r["production_writes"] == 0
    assert len(r["remaining_period_windows"]) == 4
    assert all(x["state"] == "passed" for x in r["executed_stages"][1:])
    assert sum(x["required"] for x in r["dataset_assessment"]["datasets"]) == 16
    assert [x["rows"][0]["pts"] for x in r["consumers"]] == [4.0, 5.0]


def test_scoring_fields_qualified_without_guessing_period_rates(qualified_stage):
    from tools.qualify_scoring_basis import qualify

    r, work = qualified_stage
    evidence = qualify(work / "cache", work / "scoring")
    by_key = {(w["game_id"], w["start"], w["end"]): w for w in evidence["windows"]}
    q2 = by_key["0022600144", 2, 2]
    johnson = next(x for x in q2["exact_ts_count_basis"] if x["player_id"] == 1630552)
    assert johnson["independent_count_basis"]["pts"] == 3
    assert johnson["independent_count_basis"]["fta"] == 1
    assert Fraction(johnson["derived_ts"]) == Fraction(75, 122)
    assert johnson["reported_ts"] == 0.5
    assert len(q2["changes"]) == 6
    assert q2["clock_qualification"]["unique"]
    q3 = by_key["0022600142", 3, 3]
    assert q3["missing_positive_identities"][0]["player_id"] == 1628997
    assert q3["missing_positive_identities"][0]["shooting_counts"]["pts"] == 2
    assert not q3["clock_qualification"]["unique"]
    assert all(not w["period_admitted"] and not w["advanced_repaired"] for w in evidence["windows"])
