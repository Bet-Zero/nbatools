"""Checker-authored held-outs, frozen before candidate review; controlled data only."""

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.commands.natural_query import parse_query
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query

HERE = Path(__file__).parent
HOLDOUTS = json.loads((HERE / "holdouts-frozen.json").read_text())
AMENDMENTS = json.loads((HERE / "oracle-amendments.json").read_text())
for item in HOLDOUTS["cases"]:
    if item["id"] == "H11":
        item.update({key: AMENDMENTS["H11"][key] for key in ["expected_ids", "expected_games"]})
ABSENCE = json.loads((HERE / "absence-holdouts-frozen.json").read_text())
SEASON = "2025-26"


@pytest.fixture(autouse=True)
def controlled_data(monkeypatch):
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(Path("qa/fixtures/query_engine_sample").resolve()))
    reset_data_source_cache()
    yield
    reset_data_source_cache()


def condition_check(query, expected):
    parsed = parse_query(query)
    kwargs = parsed.get("route_kwargs") or {}
    conditions = list(kwargs.get("conditions") or [])
    if kwargs.get("stat") and (
        kwargs.get("min_value") is not None or kwargs.get("max_value") is not None
    ):
        conditions.append({k: kwargs.get(k) for k in ("stat", "min_value", "max_value")})
    for stat, lo, hi in expected:
        assert any(
            c.get("stat") == stat
            and c.get("min_value") == pytest.approx(lo)
            and c.get("max_value") == pytest.approx(hi)
            for c in conditions
        ), (query, expected, kwargs)


def ids(sections):
    return sorted(
        {
            int(row["game_id"])
            for section in sections.values()
            if isinstance(section, list)
            for row in section
            if "game_id" in row
        }
    )


@pytest.mark.parametrize("case", HOLDOUTS["cases"], ids=lambda c: c["id"])
def test_held_out_interpretation_and_raw_fixture_oracle(case):
    condition_check(case["query"], case["conditions"])
    result = execute_natural_query(case["query"])
    assert result.result_status == "ok", (case["query"], result.metadata)
    sections = result.result.to_dict()["sections"]
    if case["kind"] in ("finder", "summary"):
        actual = ids(sections)
        expected = case["expected_ids"]
        # Generic finders display 25 rows by established default; no broader
        # sample is claimed from that truncated display.
        if case["kind"] == "finder" and len(expected) > 25:
            assert len(actual) == 25 and set(actual) <= set(expected), (
                case["id"],
                actual,
                expected,
            )
        else:
            assert actual == expected, (case["id"], actual, expected)
    if case["kind"] == "summary":
        row = sections["summary"][0]
        assert row["games"] == case["expected_games"]
        assert row["pts_avg"] == pytest.approx(round(case["expected_points_avg"], 3))
    if case["kind"] == "record":
        row = sections["summary"][0]
        assert row["games"] == case["expected_games"]
        assert row["wins"] == case["expected_wins"]
        assert row["losses"] == case["expected_games"] - case["expected_wins"]
    if case["kind"] == "split":
        rows = sections["split_comparison"]
        assert sum(row["games"] for row in rows) == case["expected_games"]
        # Derive each bucket independently from raw CSV joins, never the engine.
        raw = Path("qa/fixtures/query_engine_sample/data/raw")
        players = pd.read_csv(raw / "player_game_stats/2025-26_regular_season.csv")
        teams = pd.read_csv(raw / "team_game_stats/2025-26_regular_season.csv")
        sample = players.loc[players.player_name.eq(case["player"])].merge(
            teams[["game_id", "team_id", "ast"]], on=["game_id", "team_id"], suffixes=("", "_team")
        )
        sample = sample.loc[sample.ast_team.ge(20)]
        for row in rows:
            bucket = row["bucket"].lower()
            own = sample.loc[sample.is_home.eq(1 if bucket == "home" else 0)]
            assert row["games"] == len(own)
            assert row["pts_avg"] == pytest.approx(round(own.pts.mean(), 3))


@pytest.fixture
def absent_bam(tmp_path, monkeypatch):
    root = tmp_path / "independent-missed"
    shutil.copytree("qa/fixtures/query_engine_sample", root)
    path = root / "data/raw/player_game_stats/2025-26_regular_season.csv"
    players = pd.read_csv(path)
    mine = players.loc[players.player_id.eq(ABSENCE["player_id"])].copy()
    assert len(mine) == ABSENCE["candidates"]
    missed = ABSENCE["missed_ids"]
    observed = mine.assign(
        participation_state=["did_not_play" if gid in missed else "played" for gid in mine.game_id],
        coverage_scope="listed_player_rows_only",
        source="nba_official_finalbox:20251029_LALMIA",
        source_sha256="c" * 64,
    )
    target = root / "data/raw/player_game_availability/2025-26_regular_season.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    observed.to_csv(target, index=False)
    players.loc[
        ~(players.player_id.eq(ABSENCE["player_id"]) & players.game_id.isin(missed))
    ].to_csv(path, index=False)
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    reset_data_source_cache()
    return root


@pytest.mark.parametrize("case", ABSENCE["cases"], ids=lambda c: c["id"])
def test_missed_population_not_played_population(absent_bam, case):
    condition_check(case["query"], case["conditions"])
    r = execute_natural_query(case["query"])
    assert r.result_status == "ok", r.metadata
    d = r.result.to_dict()
    assert ids(d["sections"]) == case["expected_ids"]
    assert d["sections"]["count"] == [{"count": case["expected_games"]}]
    assert r.metadata.get("without_player") == "Bam Adebayo", r.metadata
    assert "missed" in r.metadata["answer_phrase"]
    response = TestClient(app).post("/query", json={"query": case["query"]})
    assert response.status_code == 200
    payload = response.json()
    assert payload["result_status"] == "ok"
    assert ids(payload["result"]["sections"]) == case["expected_ids"]
    assert payload["result"]["sections"]["count"] == [{"count": case["expected_games"]}]
