"""Field-qualified current facts on a pinned, explicitly provisional local snapshot.

This is not full-snapshot or production acceptance. Expected populations were
frozen independently from original NBA source bodies before consumer execution.
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
from nbatools.development_data import MANIFEST, development_snapshot, sha256
from tools.development_query import create_app

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "working/nba-tools-completion-program/source-evidence/core-live-current-20261107"
SUFFIX = "2026-27_regular_season.csv"
pytestmark = pytest.mark.served_seasons


@pytest.fixture
def pinned_current(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_SOURCE", "local")
    archive = (E / "current123-provisional.zip").read_bytes()
    assert sha256(archive) == "eb60f64204a089d0d5a9083496aa44e172e3fe511b71d7980a0649e0e3778c17"
    with ZipFile(io.BytesIO(archive)) as z:
        assert all(not Path(n).is_absolute() and ".." not in Path(n).parts for n in z.namelist())
        z.extractall(tmp_path)
    digest = sha256((tmp_path / MANIFEST).read_bytes())
    assert digest == "373e0b5c1e53f7e60dbfdb2c2799bf7b661f439fbd5e6662f9d6dcedadf5fe95"
    return tmp_path, digest


def _oracle():
    raw = (E / "independent/current-population-freeze.json").read_bytes()
    assert sha256(raw) == "6d382d91e1ee6e5ee21e63ec22fcd74d6461692d885912d4e6e63b5014bab97d"
    return json.loads(raw)


def test_canonical_append_preserves_every_old_core_cell_and_exact_due_population(pinned_current):
    root, _ = pinned_current
    old = E.parent / "rollover-2026-27/official-gamebooks-20261105/normalized-snapshot.zip"
    preservation = json.loads((E / "preservation.json").read_bytes())
    with ZipFile(old) as z:
        for family, receipt in preservation.items():
            relative = f"data/raw/{family}/{SUFFIX}"
            before = pd.read_csv(io.BytesIO(z.read(relative)), dtype=str, keep_default_na=False)
            after = pd.read_csv(root / relative, dtype=str, keep_default_na=False)
            assert sha256(z.read(relative)) == receipt["base_sha256"]
            assert sha256((root / relative).read_bytes()) == receipt["new_sha256"]
            assert after.iloc[: len(before)].equals(before)
            assert len(after) == receipt["rows_before"] + receipt["rows_added"]
    games = pd.read_csv(root / f"data/raw/games/{SUFFIX}")
    assert set(games.game_id.astype(str).str.zfill(10)) == set(_oracle()["exact_due_game_ids"])
    assert len(games) == games.game_id.nunique() == 123


@pytest.mark.parametrize("index", range(5))
def test_frozen_unfamiliar_current_queries_through_natural_and_http(pinned_current, index):
    root, digest = pinned_current
    queries = [
        "How many games has LeBron James missed this season?",
        "How many home games has LeBron James missed this season?",
        "Lakers win-loss record when Luka Doncic did not play this season",
        "Lakers record with Austin Reaves not playing this season",
        "Lakers record against either Celtics or Knicks without Tatum this season",
    ]
    query = queries[index]
    with development_snapshot(root, digest):
        payload = natural_query_payload(query)

    async def http():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(root, digest)), base_url="http://127.0.0.1"
        ) as client:
            response = await client.post("/query", json={"query": query})
            assert response.status_code == 200
            return response.json()

    for body in (payload, asyncio.run(http())):
        meta, sections = body["result"]["metadata"], body["result"]["sections"]
        assert body["query"] == query and meta["season"] == "2026-27"
        quality = meta["data_quality"]
        assert quality["state"] == "provisional" and quality["manifest_sha256"] == digest
        assert quality["numerical_acceptance"] is False and quality["production_accepted"] is False
        if index < 2:
            population = _oracle()["populations"]["LeBron_PHI"]["games"]
            expected = {
                int(r["game_id"])
                for r in population
                if r["state"] == "did_not_play" and (index == 0 or r["is_home"])
            }
            assert body["result_status"] == "ok" and body["route"] == "game_finder"
            assert sections["count"] == [{"count": len(expected)}]
            assert {int(r["game_id"]) for r in sections["finder"]} == expected
            assert all(r["team_abbr"] == "PHI" for r in sections["finder"])
        elif index == 2:
            expected = [
                r
                for r in _oracle()["populations"]["Luka_LAL"]["games"]
                if r["state"] == "did_not_play"
            ]
            assert body["result_status"] == "ok" and body["route"] == "team_record"
            row = sections["summary"][0]
            assert (row["games"], row["wins"], row["losses"], row["pts_avg"]) == (1, 1, 0, 103)
            assert {int(r["game_id"]) for r in sections["game_log"]} == {
                int(r["game_id"]) for r in expected
            }
        else:
            assert body["result_status"] == "no_result" and body["result_reason"] == "no_match"
            assert not sections  # covered empty, no invented 0PPG/0–0 record
            if index == 3:
                assert all(
                    r["state"] == "played" for r in _oracle()["populations"]["Reaves_LAL"]["games"]
                )
                assert meta["without_player"] == "Austin Reaves"
            else:
                assert _oracle()["LAL_vs_BOS_or_NYK_parent_game_ids"] == []
                assert meta["opponents"] == ["BOS", "NYK"]
                assert meta["without_player"] == "Jayson Tatum"


def test_full_snapshot_failures_and_484_unknown_rates_are_preserved(pinned_current):
    root, _ = pinned_current
    report = json.loads((root / "data/metadata/initial-validation.json").read_bytes())
    assert report["validation_state"] == "failed"
    failures = {
        r["name"]: r["validation"]["errors"]
        for r in report["datasets"]
        if r["validation"]["errors"]
    }
    # This is the immutable initial report, whose unpopulated new OT catalog
    # understates period coverage. Source-qualified release needs196/2249 keys,
    # as recorded separately in new16-window-denominator.json.
    assert failures == {
        "player_game_starter_roles": ["coverage missing 368 requested keys"],
        "player_game_period_stats": ["coverage missing 2208 requested keys"],
        "team_game_period_stats": ["coverage missing 192 requested keys"],
        "player_season_advanced": ["coverage missing 4 requested keys"],
    }
    frame = pd.read_csv(root / f"data/raw/player_game_period_stats/{SUFFIX}")
    assert frame[["tov_pct", "usg_pct"]].isna().sum().to_dict() == {"tov_pct": 242, "usg_pct": 242}
    old = E.parent / "rollover-2026-27/official-gamebooks-20261105/normalized-snapshot.zip"
    with ZipFile(old) as z:
        relative = f"data/raw/player_game_period_stats/{SUFFIX}"
        assert (root / relative).read_bytes() == z.read(relative)
