"""Targeted runtime check against the already uploaded Cleveland generation."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.candidate_preview import MANIFEST_ENV
from nbatools.data_source import (
    DATA_GENERATION_MANIFEST_ENV,
    current_data_generation,
    reset_data_source_cache,
)
from nbatools.dataframe_cache import clear_frame_cache

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
GENERATION = "availability-cleveland-2024-v3-20261124"
MANIFEST = "d574144512821d202249e1d87926cbbfd053126b7f1e6960582f4a9b52149034"
SOURCES = (
    Path(__file__).resolve().parents[1] / "working/nba-tools-completion-program/source-evidence"
)
CLE = 1610612739


def test_verified_cleveland_generation_answers_against_independent_oracle(monkeypatch, tmp_path):
    assert current_data_generation() == GENERATION
    monkeypatch.delenv(DATA_GENERATION_MANIFEST_ENV, raising=False)
    monkeypatch.setenv(MANIFEST_ENV, MANIFEST)
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("NBATOOLS_R2_CACHE_DIR", str(tmp_path))
    reset_data_source_cache()
    clear_frame_cache()
    baseline = json.loads(
        (SOURCES / "cleveland-full-boxscore-2024/independent/oracle.json").read_bytes()
    )
    replacement = json.loads(
        (SOURCES / "cleveland-two-game-2024/independent/source-oracle.json").read_bytes()
    )
    points = {g["game_id"]: g["points_by_team"] for g in baseline["games"]}
    points.update({g["game_id"]: g["points_by_team"] for g in replacement["reports"]})
    rows = baseline["accepted_rows"] + replacement["accepted_rows"]
    played = {
        row["game_id"]
        for row in rows
        if row["player_name"] == "Caris LeVert"
        and row["team_id"] == CLE
        and row["participation_state"] == "played"
    }
    games = set(points) - played
    wins = sum(points[gid][str(CLE)] == max(points[gid].values()) for gid in games)
    assert (len(games), wins) == (44, 31)
    try:
        response = TestClient(app).post(
            "/query", json={"query": "What was Cleveland's record without Caris LeVert in 2024-25?"}
        )
        assert response.status_code == 200
        body = response.json()
        assert (body["result_status"], body["route"]) == ("ok", "team_record"), body
        result = body["result"]
        assert result["metadata"]["participation_scope"] == "team"
        summary = result["sections"]["summary"][0]
        assert (summary["games"], summary["wins"], summary["losses"]) == (44, 31, 13)
        assert {int(row["game_id"]) for row in result["sections"]["game_log"]} == games
        fetched = [path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")]
        assert not any("_sources/" in path for path in fetched)
    finally:
        clear_frame_cache()
        reset_data_source_cache()
