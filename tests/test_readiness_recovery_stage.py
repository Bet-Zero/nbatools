"""Retained recovery execution and clock evidence preserve fail-closed gates."""

import copy
import json

import pandas as pd
import pytest

from tools.qualify_readiness_recovery import RECOVERY, authenticate, qualify
from tools.reconcile_period_clocks import KEYS, derive_clocks
from tools.season_rollover_core_bridge import FIELDS


def complement_jobs():
    jobs = {}
    for bounds, literal, count in [((1, 1), "4:60", 2), ((1, 2), "7:57", 5), ((2, 2), "2:57", 3)]:
        bodies = {}
        for endpoint, root in KEYS.items():
            box = {"gameId": "0022600002"}
            for side, tid, pid in [("homeTeam", 1, 10), ("awayTeam", 2, 20)]:
                stats = {f: count for f in [*FIELDS, "plusMinusPoints"]}
                stats.update(minutes=literal if tid == 1 else "1:00", usagePercentage=0.7)
                box[side] = dict(teamId=tid, players=[dict(personId=pid, statistics=stats)])
            bodies[endpoint] = json.dumps({root: box, "meta": {"retained": True}}).encode()
        jobs[("0022600002", *bounds)] = bodies
    return jobs


def mutate(jobs, key, endpoint, fn):
    doc = json.loads(jobs[key][endpoint])
    fn(doc[KEYS[endpoint]])
    jobs[key][endpoint] = json.dumps(doc).encode()


def test_complement_uses_two_observations_and_preserves_all_other_cells():
    jobs = complement_jobs()
    before = copy.deepcopy(jobs)
    target = ("0022600002", 1, 1)
    admitted = {("0022600002", 1, 2), ("0022600002", 2, 2)}
    derived, ledger = derive_clocks(target, jobs, admitted)
    assert jobs == before
    assert len(ledger) == 2
    assert all(r["derived_seconds"] == 300 for r in ledger)
    assert all([r["terms"][i]["coefficient"] for i in range(2)] == [1, -1] for r in ledger)
    for endpoint, root in KEYS.items():
        doc = json.loads(derived[endpoint])
        stats = doc[root]["homeTeam"]["players"][0]["statistics"]
        assert stats["minutes"] == "5:00" and stats["usagePercentage"] == 0.7
        stats["minutes"] = "4:60"
        assert doc == json.loads(before[target][endpoint])


@pytest.mark.parametrize(
    "damage", ["count", "team", "player", "game", "clock", "unadmitted", "cycle", "valid_residual"]
)
def test_clock_evidence_rejects_unproven_or_inconsistent_inputs(damage):
    jobs = complement_jobs()
    target = ("0022600002", 1, 1)
    term = ("0022600002", 1, 2)
    admitted = {term, ("0022600002", 2, 2)}
    endpoint = "boxscoretraditionalv3"
    if damage == "count":
        mutate(
            jobs,
            term,
            endpoint,
            lambda b: b["homeTeam"]["players"][0]["statistics"].update(points=6),
        )
    elif damage == "team":
        mutate(jobs, term, endpoint, lambda b: b["homeTeam"].update(teamId=3))
    elif damage == "player":
        mutate(jobs, term, endpoint, lambda b: b["homeTeam"]["players"][0].update(personId=11))
    elif damage == "game":
        mutate(jobs, term, endpoint, lambda b: b.update(gameId="0022600003"))
    elif damage == "clock":
        mutate(
            jobs,
            term,
            "boxscoreadvancedv3",
            lambda b: b["homeTeam"]["players"][0]["statistics"].update(minutes="7:58"),
        )
    elif damage == "unadmitted":
        admitted.remove(term)
    elif damage == "cycle":
        admitted = {target}
    else:
        for endpoint in KEYS:
            mutate(
                jobs,
                target,
                endpoint,
                lambda b: b["homeTeam"]["players"][0]["statistics"].update(minutes="5:00"),
            )
    with pytest.raises(ValueError):
        derive_clocks(target, jobs, admitted)


@pytest.mark.parametrize(
    "field,value",
    [("http_status", 503), ("attempts", 2), ("parameters", {}), ("response_sha256", "0" * 64)],
)
def test_authenticated_outer_archive_does_not_hide_attempt_damage(
    tmp_path, monkeypatch, field, value
):
    from tools import qualify_readiness_recovery as module

    original = module.unpack

    def damaged_unpack(*args):
        result = original(*args)
        path = args[2] / "acquisition.json"
        report = json.loads(path.read_bytes())
        report["attempts"][0][field] = value
        payload = json.dumps(report).encode()
        path.write_bytes(payload)
        (args[2] / "sources/capture-attempt.json").write_bytes(payload)
        return result

    monkeypatch.setattr(module, "unpack", damaged_unpack)
    with pytest.raises(ValueError):
        authenticate(RECOVERY / "collection.zip", tmp_path / "bad")


def test_all_recovery_periods_execute_without_clock_or_readiness_waiver(tmp_path):
    report = qualify(RECOVERY / "collection.zip", tmp_path / "qualified")
    assert report["authentication"]["recovery_successes"] == 517
    assert report["authentication"]["prior_successes"] == 602
    assert report["authentication"]["repeated_successes"] == 0
    assert report["paired_windows"] == 555
    assert len(report["original_quarantined_windows"]) == 19
    assert len(report["derived_clock_windows"]) == 13
    assert len(report["admitted_windows"]) == 549
    assert {
        (r["game_id"], r["start_period"], r["end_period"]) for r in report["quarantined_windows"]
    } == {
        ("0022600097", 3, 4),
        ("0022600097", 4, 4),
        ("0022600142", 3, 3),
        ("0022600142", 3, 4),
        ("0022600144", 1, 2),
        ("0022600144", 2, 2),
    }
    assert report["context"]["prior88_cells_preserved"]
    assert not report["full_snapshot_accepted"] and not report["readiness_accepted"]
    assert report["production_writes"] == 0
    root = tmp_path / "qualified/stage/data"
    assert not (root / "metadata/backfill_manifest.csv").exists()
    rows = pd.read_csv(root / "raw/player_game_period_stats/2026-27_regular_season.csv")
    assert len(rows) == report["player_rows"]
    assert not (
        rows.game_id.eq(22600097)
        & rows.period_family.eq("quarter")
        & rows.period_value.astype(str).eq("4")
    ).any()
