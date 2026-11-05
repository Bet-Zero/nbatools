"""Controlled software tests; these fixtures certify no NBA source values."""

import asyncio
import json
import shutil
from pathlib import Path

import httpx
import pandas as pd
import pytest

from nbatools.api_handlers import query_result_to_payload
from nbatools.commands.aggregate_metrics import aggregate_metric_value
from nbatools.data_source import DataSourceConfigError, data_path, data_source_cache_key
from nbatools.development_data import MANIFEST, development_snapshot, sha256
from nbatools.query_output_snapshot import build_query_ui_snapshot
from nbatools.query_service import execute_natural_query, execute_structured_query
from tools.development_query import create_app
from tools.development_snapshot import intake, prepare

FIXTURE = Path("qa/fixtures/query_engine_sample")
RAW = "data/raw/player_game_stats/2025-26_regular_season.csv"


@pytest.fixture
def snapshot(tmp_path):
    source = tmp_path / "fixture-source"
    shutil.copytree(FIXTURE / "data", source / "data")
    frame = pd.read_csv(source / RAW)
    frame["fg_pct"] = frame.fgm / frame.fga
    frame["fg3_pct"] = frame.fg3m / frame.fg3a
    frame.to_csv(source / RAW, index=False)
    root = tmp_path / "v1"
    digest = prepare(
        source,
        root,
        version="controlled-v1",
        season="2025-26",
        season_type="Regular Season",
        scope="controlled fixture, 2025-26; not NBA evidence",
        source_evidence={"reference": str(FIXTURE), "sha256": sha256((FIXTURE / RAW).read_bytes())},
        backlog=tmp_path / "backlog",
        exceptions=["DQ-fixture-discrepancy"],
        fixture=True,
    )
    return root, digest


def test_flagged_rows_stay_in_average_filter_api_and_visible_output(snapshot):
    root, digest = snapshot
    raw = pd.read_csv(root / RAW)
    expected = raw.loc[raw.player_id.eq(2544) & raw.is_home.eq(1) & raw.pts.ge(25)]
    assert not expected.empty
    with development_snapshot(root, digest):
        result = execute_structured_query(
            "player_game_summary",
            player="LeBron James",
            season="2025-26",
            home_only=True,
            stat="pts",
            min_value=25,
        )
        payload = query_result_to_payload(result)
        summary = payload["result"]["sections"]["summary"][0]
        assert summary["games"] == len(expected)
        assert summary["pts_avg"] == pytest.approx(expected.pts.mean(), abs=0.001)
        assert payload["result"]["metadata"]["data_quality"]["state"] == "provisional"
        assert payload["result"]["metadata"]["data_quality"]["manifest_sha256"] == digest
        assert "DQ-fixture-discrepancy" in payload["notes"][0]
        assert "PROVISIONAL" in str(build_query_ui_snapshot(payload))
        natural = execute_natural_query("LeBron average points at home in 2025-26 with 25+ points")
        assert natural.result.to_dict()["sections"]["summary"][0]["pts_avg"] == summary["pts_avg"]

    async def request():
        transport = httpx.ASGITransport(app=create_app(root, digest))
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
            response = await client.post("/query", json={"query": "LeBron stats in 2025-26"})
            assert response.status_code == 200
            assert (
                response.json()["result"]["metadata"]["data_quality"]["snapshot"] == "controlled-v1"
            )

    asyncio.run(request())


@pytest.mark.parametrize("environment", ["production", "prod", "preview"])
def test_production_rejects_same_snapshot_even_with_explicit_opt_in(
    snapshot, monkeypatch, environment
):
    root, digest = snapshot
    monkeypatch.setenv("ENVIRONMENT", environment)
    with pytest.raises(ValueError, match="isolated local"):
        with development_snapshot(root, digest):
            pass
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    with pytest.raises(DataSourceConfigError, match="explicit local"):
        data_path(RAW)


def test_no_configuration_leak_mutation_or_missing_value_fill(snapshot, monkeypatch):
    root, digest = snapshot
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(FIXTURE.resolve()))
    before = data_source_cache_key()
    with development_snapshot(root, digest):
        assert data_source_cache_key() != before
        assert aggregate_metric_value(pd.DataFrame({"pts": [23, 25]}), "pts") == 24
        assert aggregate_metric_value(pd.DataFrame({"pts": [23, None]}), "pts") is None
        assert (
            aggregate_metric_value(pd.DataFrame({"fgm": [2, None], "fga": [4, 4]}), "fg_pct")
            is None
        )
        with pytest.raises(FileNotFoundError):
            data_path("data/not-manifested.csv")
        (root / RAW).write_text("tampered")
        with pytest.raises(ValueError, match="bytes changed"):
            data_path(RAW)
    assert data_source_cache_key() == before


def test_failure_rerun_keeps_claim_and_resolution(tmp_path):
    failure = dict(
        dataset="player_game_stats",
        source_sha256="a" * 64,
        scope={"game_id": "controlled-game", "field": "pts"},
        check="source comparison",
        observed=0,
        expected=25,
        impact=["pts_avg"],
        evidence={"reference": "fixture"},
        next_evidence="controlled reviewed correction",
    )
    first = intake(tmp_path, failure)
    path = tmp_path / (first + ".json")
    document = json.loads(path.read_bytes())
    document["status"] = "claimed"
    document["claim"] = "fixture-worker"
    path.write_text(json.dumps(document))
    assert intake(tmp_path, failure) == first
    assert json.loads(path.read_bytes())["claim"] == "fixture-worker"
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_reviewed_correction_rebuilds_new_version_preserves_pinned_reader(snapshot, tmp_path):
    old, digest = snapshot
    old_bytes = (old / RAW).read_bytes()
    frame = pd.read_csv(old / RAW, dtype=str, keep_default_na=False)
    target = frame.loc[frame.player_id.eq("2544")].sort_values(["game_date", "game_id"]).iloc[0]
    correction = dict(
        author="controlled-test-author",
        base_manifest_sha256=digest,
        source_sha256=sha256(old_bytes),
        independent_review={
            "reviewer": "controlled-test-oracle",
            "reference": "synthetic test; not actual NBA review",
        },
        changes=[
            dict(
                key={k: target[k] for k in ["game_id", "player_id", "team_id"]},
                field="ast",
                before=target.ast,
                after=int(target.ast) + 2,
                evidence="controlled oracle",
            )
        ],
    )
    new = tmp_path / "v2"
    with development_snapshot(old, digest):
        original_key = data_source_cache_key()
        revised = prepare(
            old,
            new,
            version="controlled-v2",
            season="2025-26",
            season_type="Regular Season",
            scope="controlled correction; not NBA evidence",
            fixture=True,
            correction=correction,
            source_evidence={"reference": "controlled correction", "sha256": digest},
            backlog=tmp_path / "backlog",
            exceptions=["DQ-fixture-discrepancy"],
        )
        assert data_source_cache_key() == original_key
        assert data_path(RAW).read_bytes() == old_bytes
        with development_snapshot(new, revised):
            assert data_source_cache_key() != original_key
            updated = pd.read_csv(data_path(RAW))
            assert updated.ast.sum() == pd.to_numeric(frame.ast).sum() + 2
            features = pd.read_csv(
                new / "data/processed/player_game_features/2025-26_regular_season.csv"
            )
            next_game = (
                features.loc[features.player_id.eq(2544)]
                .sort_values(["game_date", "game_id"])
                .iloc[1]
            )
            assert next_game.ast_last_5 == int(target.ast) + 2
        assert data_path(RAW).read_bytes() == old_bytes
    duplicate = json.loads(json.dumps(correction))
    again = dict(duplicate["changes"][0])
    again["key"] = {k: int(v) for k, v in again["key"].items()}
    again["before"] = str(again["after"])
    again["after"] += 1
    duplicate["changes"].append(again)
    with pytest.raises(ValueError, match="conflict"):
        prepare(
            old,
            tmp_path / "duplicate",
            version="duplicate",
            season="2025-26",
            season_type="Regular Season",
            scope="controlled duplicate",
            source_evidence={"reference": "fixture", "sha256": digest},
            backlog=tmp_path / "backlog",
            exceptions=[],
            correction=duplicate,
        )
    assert not (tmp_path / "duplicate").exists()
    correction["changes"][0]["before"] = "999"
    with pytest.raises(ValueError, match="stale old"):
        prepare(
            old,
            tmp_path / "bad",
            version="bad",
            season="2025-26",
            season_type="Regular Season",
            scope="controlled",
            source_evidence={"reference": "fixture", "sha256": digest},
            backlog=tmp_path / "backlog",
            exceptions=[],
            correction=correction,
        )
    assert not (tmp_path / "bad").exists()
    assert sha256((old / MANIFEST).read_bytes()) == digest


def test_unknown_numeric_file_cannot_produce_partial_sum_or_average(snapshot, tmp_path):
    root, digest = snapshot
    # New controlled source version preserves a missing value and its failure.
    source = tmp_path / "unknown-source"
    shutil.copytree(root / "data", source / "data")
    (source / MANIFEST).unlink()  # a new declared source, not mutation of a pinned version
    frame = pd.read_csv(source / RAW)
    frame.loc[frame.player_id.eq(2544).idxmax(), "pts"] = None
    frame.to_csv(source / RAW, index=False)
    target = tmp_path / "unknown-version"
    unknown = prepare(
        source,
        target,
        version="unknown-controlled",
        season="2025-26",
        season_type="Regular Season",
        scope="controlled missing value",
        source_evidence={
            "reference": "controlled fixture",
            "sha256": sha256((source / RAW).read_bytes()),
        },
        backlog=tmp_path / "backlog",
        exceptions=["DQ-fixture-unknown"],
        fixture=True,
    )
    with development_snapshot(target, unknown):
        for query in [
            "LeBron average points in 2025-26",
            "How many points did LeBron score in 2025-26",
        ]:
            result = execute_natural_query(query)
            assert result.result_status == "no_result"
            assert result.result_reason == "no_data"
            assert result.metadata["data_quality"]["state"] == "provisional"
            assert not result.to_dict().get("sections")
    assert pd.read_csv(target / RAW).pts.isna().sum() == 1


def test_contract_failure_is_quarantined_and_registered_once(tmp_path):
    source = tmp_path / "bad-source"
    shutil.copytree(FIXTURE / "data", source / "data")
    frame = pd.read_csv(source / RAW)
    frame.loc[0, "game_id"] = 9999999999
    frame.to_csv(source / RAW, index=False)
    for version in ["bad-v1", "bad-v2"]:
        with pytest.raises(ValueError, match="identity outside catalog"):
            prepare(
                source,
                tmp_path / version,
                version=version,
                season="2025-26",
                season_type="Regular Season",
                scope="controlled corrupt identity",
                source_evidence={
                    "reference": "fixture",
                    "sha256": sha256((source / RAW).read_bytes()),
                },
                backlog=tmp_path / "backlog",
                exceptions=[],
            )
        assert not (tmp_path / version).exists()
    assert len(list((tmp_path / "backlog").glob("*.json"))) == 1


def test_selected_scope_and_path_aliases_are_explicit(snapshot, monkeypatch, tmp_path):
    from nbatools.data_source import data_glob

    root, digest = snapshot
    with development_snapshot(root, digest):
        assert data_glob("raw/player_game_stats/*.csv") == data_glob(
            "data/raw/player_game_stats/*.csv"
        )
        assert len(data_glob("raw/player_game_stats/*.csv")) == 1
        assert data_path(RAW) == data_path(RAW.removeprefix("data/"))
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(DataSourceConfigError, match="explicit local"):
        data_path(root / RAW)
    alias = tmp_path / "provisional-alias.csv"
    alias.symlink_to(root / RAW)
    with pytest.raises(DataSourceConfigError, match="explicit local"):
        data_path(alias)


@pytest.mark.parametrize(
    "key,value", [("VERCEL", "1"), ("VERCEL_ENV", "preview"), ("DATA_SOURCE", "r2")]
)
def test_hosted_and_remote_configuration_cannot_select_development(
    snapshot, monkeypatch, key, value
):
    root, digest = snapshot
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError, match="isolated local"):
        with development_snapshot(root, digest):
            pass
