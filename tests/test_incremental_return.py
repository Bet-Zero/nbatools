"""Real returned-source qualification and append-only regression controls."""

import hashlib
import zipfile

import pandas as pd
import pytest

from tools.qualify_incremental_return import OUTER_SHA, qualify
from tools.readiness_refresh import SourceCache
from tools.stage_current_season import CURRENT, SUFFIX


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    work = tmp_path_factory.mktemp("incremental-return")
    cache = SourceCache(work / "cache")
    for folder in ["q1-laptop-capture", "partial-capture-20261103", "recovery-capture-20261104"]:
        archive = CURRENT.parent / folder / "collection.zip"
        cache.import_collection(archive, hashlib.sha256(archive.read_bytes()).hexdigest())
    archive = CURRENT.parent / "incremental-return-20261104/current-run.zip"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == OUTER_SHA
    report = qualify(archive, work / "cache", work / "qualified")
    return report, work / "qualified/stage"


def test_real_missing_windows_and_metadata_remain_honest(result):
    r, _ = result
    assert r["retained_direct_successes"] == 1537
    assert len(r["admitted"]) == 90
    assert r["known_expected_windows"] == 647
    assert r["admitted_windows"] == 641
    assert len(r["missing_windows"]) == 6
    assert r["period_counts"]["0022600161"] == 4
    assert not r["full_snapshot_accepted"]
    assert r["dataset_assessment"]["validation_state"] == "failed"
    assert sum(d["required"] for d in r["dataset_assessment"]["datasets"]) == 16
    assert not r["reported_usage_independently_accepted"]
    assert r["production_writes"] == 0


def test_preserved_cells_and_overtime_scores(result):
    _, root = result
    with zipfile.ZipFile(CURRENT / "qualification-evidence.zip") as z:
        for grain in ["player", "team"]:
            path = f"data/raw/{grain}_game_period_stats/{SUFFIX}"
            assert (root / path).read_bytes().startswith(z.read("stage/" + path))
            path = f"data/raw/{grain}_game_stats/{SUFFIX}"
            assert (root / path).read_bytes() == z.read("stage/" + path)
    teams = pd.read_csv(root / f"data/raw/team_game_period_stats/{SUFFIX}")
    for gid, scores in [(22600128, [7, 8]), (22600165, [10, 11])]:
        selected = teams[teams.game_id.eq(gid) & teams.period_family.eq("overtime")]
        assert sorted(selected.pts.tolist()) == scores


def test_reported_advanced_values_survive_derived_basis(result):
    r, root = result
    assert len(r["source_basis"]["ts_conflicts"]) == 12
    advanced = pd.read_csv(root / f"data/raw/player_season_advanced/{SUFFIX}")
    for row in r["source_basis"]["ts_conflicts"]:
        observed = advanced.loc[advanced.player_id.eq(row["player_id"])].iloc[0]
        assert observed.reported_ts_pct == row["source_ts"]
        assert observed.ts_pct == pytest.approx(row["expected_ts"])
    assert all(d["state"] != "admitted" for d in r["alternate_range_diagnostics"])


def test_event_clock_refinement_is_entire_vector_and_explicit(result):
    r, _ = result
    by_game = {x["game_id"]: x for x in r["event_clock_refinements"]}
    assert set(by_game) == {"0022600158", "0022600163", "0022600168"}
    for gid, pid, expected in [
        ("0022600158", 1642272, "13:59.60"),
        ("0022600163", 1641737, "6:59.70"),
        ("0022600168", 1642868, "1:59.80"),
    ]:
        rows = [x for x in by_game[gid]["ledger"] if x["player_id"] == pid]
        assert len(rows) == 2
        assert all(x["original_literal"].endswith(":60") for x in rows)
        assert all(x["derived_literal"] == expected for x in rows)
