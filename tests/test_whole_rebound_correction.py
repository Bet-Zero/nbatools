"""Immutable v7 whole-game rebound correction (DQ-auto-e148abf7...) and its consumers.

Expectations come from the official scorer FINAL BOX line and from plain pandas
over the pinned snapshot rows, never from application output. v6 stays loadable
with its original values, so a pinned reader of the old version is unaffected.
"""

import asyncio
import io
import json
from pathlib import Path
from zipfile import ZipFile

import httpx
import pandas as pd
import pytest

from nbatools.api_handlers import natural_query_payload
from nbatools.development_data import DevelopmentSnapshot, development_snapshot, sha256
from nbatools.query_service import execute_structured_query
from tools.development_query import create_app

pytestmark = [pytest.mark.served_seasons, pytest.mark.engine]

EVIDENCE = (
    Path(__file__).resolve().parents[1] / "working/nba-tools-completion-program/source-evidence"
)
V7 = EVIDENCE / "whole-rebound-correction-20261111"
V6 = EVIDENCE / "player-period-reader-20261110"
BOOK = EVIDENCE / "current123-periods-20261107/hosted-initial/acquired_data/current123-game184-book"
DATASET = "data/raw/player_game_stats/2026-27_regular_season.csv"
PID, GAME, DAL = 1629023, 22600184, 1610612742
STATS = ["pts", "reb", "ast", "stl", "blk"]


def _unpack(directory, output):
    binding = json.loads((directory / "binding.json").read_bytes())
    raw = (directory / binding["archive"]).read_bytes()
    assert sha256(raw) == binding["archive_sha256"]
    with ZipFile(io.BytesIO(raw)) as z:
        assert all(n.startswith("data/") and ".." not in Path(n).parts for n in z.namelist())
        z.extractall(output)
    DevelopmentSnapshot(output, binding["manifest_sha256"])
    return output, binding["manifest_sha256"]


@pytest.fixture(scope="module")
def snapshots(tmp_path_factory):
    return {
        "v6": _unpack(V6, tmp_path_factory.mktemp("whole-reb-v6")),
        "v7": _unpack(V7, tmp_path_factory.mktemp("whole-reb-v7")),
    }


@pytest.fixture(autouse=True)
def local(monkeypatch):
    monkeypatch.setenv("DATA_SOURCE", "local")


def _rows(snapshot):
    return pd.read_csv(snapshot[0] / DATASET)


def _book_whole_line():
    page = (BOOK / "page-00.txt").read_text()
    assert "FINAL BOX" in page.splitlines()[0]
    (line,) = [x for x in page.splitlines() if "P.J. Washington" in x]
    oreb, dreb, reb = map(int, line.split()[11:14])
    return oreb, dreb, reb


def test_new_version_changes_only_two_cells_and_preserves_v6(snapshots):
    (v6_root, v6_sha), (v7_root, v7_sha) = snapshots["v6"], snapshots["v7"]
    v6_doc = DevelopmentSnapshot(v6_root, v6_sha).document
    v7_doc = DevelopmentSnapshot(v7_root, v7_sha).document
    assert v7_doc["version"] != v6_doc["version"] and v7_doc["quality"] == "provisional"
    assert v7_doc["exceptions"] == v6_doc["exceptions"]
    added = set(v7_doc["files"]) - set(v6_doc["files"])
    assert added == {
        "data/metadata/corrections/game184-whole-rebound.json",
        "data/metadata/whole-rebound-validation.json",
    }
    assert not set(v6_doc["files"]) - set(v7_doc["files"])
    changed = {p for p in v6_doc["files"] if v6_doc["files"][p] != v7_doc["files"][p]}
    assert changed == {DATASET}
    old, new = (
        pd.read_csv(snapshots[v][0] / DATASET, dtype=str, keep_default_na=False)
        for v in ("v6", "v7")
    )
    assert old.shape == new.shape and list(old.columns) == list(new.columns)
    diff = (old != new).stack()
    cells = sorted((new.loc[i, "player_id"], c) for (i, c), v in diff.items() if v)
    assert cells == [(str(PID), "dreb"), (str(PID), "reb")]
    old, new = _rows(snapshots["v6"]), _rows(snapshots["v7"])
    row = new[new.game_id.eq(GAME) & new.player_id.eq(PID) & new.team_id.eq(DAL)].iloc[0]
    assert (row.oreb, row.dreb, row.reb) == _book_whole_line() == (4, 6, 10)
    old_row = old[old.game_id.eq(GAME) & old.player_id.eq(PID)].iloc[0]
    assert (old_row.oreb, old_row.dreb, old_row.reb) == (4, 5, 9)
    record = json.loads(
        (v7_root / "data/metadata/corrections/game184-whole-rebound.json").read_text()
    )
    assert record["base_manifest_sha256"] == v6_sha and record["production_writes"] == 0
    assert record["source_sha256"] == v6_doc["files"][DATASET]
    assert [(c["field"], c["before"], c["after"]) for c in record["changes"]] == [
        ("dreb", 5, 6),
        ("reb", 9, 10),
    ]


def test_corrected_whole_row_reconciles_team_and_period_totals(snapshots):
    root = snapshots["v7"][0]
    players = _rows(snapshots["v7"])
    teams = pd.read_csv(root / "data/raw/team_game_stats/2026-27_regular_season.csv")
    sums = players.groupby(["game_id", "team_id"])[["dreb", "reb"]].sum()
    team = teams.set_index(["game_id", "team_id"])[["dreb", "reb"]]
    assert sums.sort_index().equals(team.sort_index())
    old = _rows(snapshots["v6"]).groupby(["game_id", "team_id"])[["dreb", "reb"]].sum()
    assert (old != team.sort_index()).any(axis=1).sum() == 1  # only game184 DAL
    periods = pd.read_csv(root / "data/raw/player_game_period_stats/2026-27_regular_season.csv")
    q = periods[
        periods.game_id.eq(GAME)
        & periods.player_id.eq(PID)
        & periods.period_family.isin(["quarter", "overtime"])
    ]
    assert (q.dreb.sum(), q.reb.sum()) == (6, 10)


def _natural(snapshot, query):
    with development_snapshot(*snapshot):
        body = natural_query_payload(query)
    assert body["result_status"] == "ok", body
    assert body["result"]["metadata"]["data_quality"]["manifest_sha256"] == snapshot[1]
    return body


@pytest.mark.parametrize("version,expected", [("v6", 9), ("v7", 10)])
def test_whole_game_rebounds_natural_structured_http(snapshots, version, expected):
    snapshot = snapshots[version]
    raw = _rows(snapshot)
    assert raw.loc[raw.game_id.eq(GAME) & raw.player_id.eq(PID), "reb"].item() == expected
    query = "How many rebounds did P.J. Washington have on 2026-11-04?"
    body = _natural(snapshot, query)
    assert body["result"]["sections"]["count"] == [{"count": expected}]
    with development_snapshot(*snapshot):
        structured = execute_structured_query(
            "player_game_finder",
            player="P.J. Washington",
            season="2026-27",
            start_date="2026-11-04",
            end_date="2026-11-04",
            stat="reb",
        )
    rows = structured.result.to_dict()["sections"]["finder"]
    assert [(r["game_id"], r["player_id"], r["reb"]) for r in rows] == [(GAME, PID, expected)]

    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(*snapshot)), base_url="http://127.0.0.1"
        ) as client:
            r = await client.post("/query", json={"query": query})
            assert r.status_code == 200
            assert r.json()["result"]["sections"]["count"] == [{"count": expected}]

    asyncio.run(request())


@pytest.mark.parametrize("version", ["v6", "v7"])
def test_season_totals_means_filters_and_double_doubles(snapshots, version):
    snapshot = snapshots[version]
    raw = _rows(snapshot)
    mine = raw[raw.player_id.eq(PID)]
    summary = _natural(snapshot, "P.J. Washington rebounds per game 2026-27")
    (row,) = summary["result"]["sections"]["summary"]
    assert row["games"] == len(mine)
    assert row["reb_sum"] == mine.reb.sum() and row["dreb_sum"] == mine.dreb.sum()
    assert row["reb_avg"] == pytest.approx(round(mine.reb.mean(), 3))
    assert row["dreb_avg"] == pytest.approx(round(mine.dreb.mean(), 3))
    assert (row["reb_sum"], row["dreb_sum"]) == ((63, 46) if version == "v6" else (64, 47))

    tens = _natural(snapshot, "P.J. Washington games with 10+ rebounds in 2026-27")
    found = {r["game_id"] for r in tens["result"]["sections"]["finder"]}
    assert found == set(mine.loc[mine.reb.ge(10), "game_id"])
    assert (GAME in found) is (version == "v7")

    doubles = mine[(mine[STATS] >= 10).sum(axis=1) >= 2]
    dd = _natural(snapshot, "How many double-doubles does P.J. Washington have in 2026-27?")
    assert dd["result"]["sections"]["count"] == [{"count": len(doubles)}]
    assert {r["game_id"] for r in dd["result"]["sections"]["finder"]} == set(doubles.game_id)
    assert len(doubles) == (1 if version == "v6" else 2)


def _rank_bounds(values, mine):
    return int((values > mine).sum()) + 1, int((values >= mine).sum())


@pytest.mark.parametrize("version", ["v6", "v7"])
def test_rankings_use_the_corrected_whole_game_value(snapshots, version):
    snapshot = snapshots[version]
    raw = _rows(snapshot)
    totals = raw.groupby("player_id").reb.sum()
    board = _natural(snapshot, "Top 50 players in total rebounds in 2026-27")
    (me,) = [r for r in board["result"]["sections"]["leaderboard"] if r["player_id"] == PID]
    assert me["reb_total"] == totals[PID] == (63 if version == "v6" else 64)
    low, high = _rank_bounds(totals, totals[PID])
    assert low <= me["rank"] <= high

    flags = (raw[STATS] >= 10).sum(axis=1) >= 2
    counts = raw[flags].groupby("player_id").size()
    board = _natural(snapshot, "Top 100 players by double-doubles in 2026-27")
    (me,) = [r for r in board["result"]["sections"]["leaderboard"] if r["player_id"] == PID]
    assert me["double doubles"] == counts[PID] == (1 if version == "v6" else 2)
    low, high = _rank_bounds(counts, counts[PID])
    assert low <= me["rank"] <= high
