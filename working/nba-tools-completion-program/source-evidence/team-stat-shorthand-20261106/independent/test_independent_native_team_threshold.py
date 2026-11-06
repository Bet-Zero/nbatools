"""Retained exact-population NBA replay against independently frozen JSON oracle."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.commands.natural_query import parse_query
from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query

HERE = Path(__file__).parent
ORACLE = json.loads((HERE / "native-holdouts-frozen.json").read_text())


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    archive = Path(
        "working/nba-tools-completion-program/source-evidence/multi-team-absence-20261106/archive-originals.zip"
    )
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == ORACLE["archive_sha256"]
    spec = importlib.util.spec_from_file_location(
        "review_native_stage_helper", Path("tests/cloud_multi_team_absence_real_data.py")
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    with pytest.MonkeyPatch.context() as monkeypatch:
        root, teams, players = helper.build_native_stage(
            tmp_path_factory.mktemp("review-native"), monkeypatch
        )
    return root


@pytest.mark.parametrize("case", ORACLE["cases"], ids=lambda c: c["id"])
def test_native_exact_scope_counts_and_http(native, monkeypatch, case):
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(native))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    try:
        parsed = parse_query(case["query"])
        kwargs = parsed.get("route_kwargs") or {}
        conditions = list(kwargs.get("conditions") or [])
        if kwargs.get("stat") and (
            kwargs.get("min_value") is not None or kwargs.get("max_value") is not None
        ):
            conditions.append({k: kwargs.get(k) for k in ["stat", "min_value", "max_value"]})
        assert any(
            all(c.get(k) == case[k] for k in ["stat", "min_value", "max_value"]) for c in conditions
        ), (case["id"], kwargs)
        answer = execute_natural_query(case["query"])
        assert answer.result_status == "ok", answer.metadata
        data = answer.result.to_dict()
        rows = data["sections"].get("finder", [])
        assert sorted(int(r["game_id"]) for r in rows) == case["expected_ids"]
        if case["kind"] == "missed":
            assert data["sections"]["count"] == [{"count": case["expected_games"]}]
            assert sum(r["pts"] for r in rows) == case["expected_team_points"]
            assert data["metadata"]["membership_coverage"]["complete"]
        response = TestClient(app).post("/query", json={"query": case["query"]})
        assert response.status_code == 200
        payload = response.json()
        assert payload["result_status"] == "ok"
        assert (
            sorted(int(r["game_id"]) for r in payload["result"]["sections"]["finder"])
            == case["expected_ids"]
        )
    finally:
        reset_data_source_cache()
