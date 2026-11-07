"""Qualified role/season source stage composes with ID18 without data acceptance bypass."""

import asyncio
import io
import json
from pathlib import Path
from zipfile import ZipFile

import httpx
import pandas as pd
import pytest

from nbatools.api_handlers import natural_query_payload
from nbatools.commands.pipeline.reported_absence_reasons import validate_publication
from nbatools.development_data import MANIFEST, DevelopmentSnapshot, development_snapshot, sha256
from nbatools.query_service import execute_structured_query
from tools.development_query import create_app

E = Path(__file__).resolve().parents[1] / (
    "working/nba-tools-completion-program/source-evidence/id18-current-required-20261107"
)
SUFFIX = "2026-27_regular_season.csv"
pytestmark = [pytest.mark.served_seasons, pytest.mark.engine]


@pytest.fixture
def integrated(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_SOURCE", "local")
    b = json.loads((E / "required-v3-binding.json").read_bytes())
    raw = (E / b["archive"]).read_bytes()
    assert sha256(raw) == b["archive_sha256"]
    with ZipFile(io.BytesIO(raw)) as z:
        assert all(n.startswith("data/") and ".." not in Path(n).parts for n in z.namelist())
        z.extractall(tmp_path)
    DevelopmentSnapshot(tmp_path, b["manifest_sha256"])
    return tmp_path, b["manifest_sha256"]


def test_required_contract_tracks_source_known_ot_and_retains_id18_sources(integrated):
    root, _ = integrated
    validate_publication(root / "data")
    report = json.loads((root / "data/metadata/required-current-validation.json").read_bytes())
    assert report["validation_state"] == "failed"
    failures = {
        r["name"]: r["validation"]["errors"]
        for r in report["datasets"]
        if r["validation"]["errors"]
    }
    assert failures == {
        "team_game_period_stats": ["coverage missing 196 requested keys"],
        "player_game_period_stats": ["coverage missing 2208 requested keys"],
    }
    team = next(r for r in report["datasets"] if r["name"] == "team_game_period_stats")
    assert team["coverage"]["expected_keys"] == 1490  # 745 complete team windows, both sides
    assert "overtime:ot" in team["coverage"]["missing_windows"]
    with ZipFile(E / "current123-id18-v2.zip") as old:
        preserved = [n for n in old.namelist() if "absence_reason" in n or "availability" in n]
        for name in preserved:
            assert (root / name).read_bytes() == old.read(name)
        for family in [
            "team_game_stats",
            "player_game_stats",
            "team_game_period_stats",
            "player_game_period_stats",
        ]:
            name = f"data/raw/{family}/{SUFFIX}"
            assert (root / name).read_bytes() == old.read(name)
    period = pd.read_csv(root / f"data/raw/player_game_period_stats/{SUFFIX}")
    assert period[["tov_pct", "usg_pct"]].isna().sum().to_dict() == {"tov_pct": 242, "usg_pct": 242}
    assert len(period.loc[period.period_family.eq("overtime")]) == 69
    assert not (root / "data/metadata/generation_manifest.json").exists()


def test_current_starter_natural_structured_http_and_id18_are_distinct_qualified_scopes(integrated):
    root, digest = integrated
    # Oracle from complete qualified appearance rows + separately qualified roles,
    # never from either query path. Only keys/counts/PTS are qualified here.
    players = pd.read_csv(root / f"data/raw/player_game_stats/{SUFFIX}")
    roles = pd.read_csv(root / f"data/raw/player_game_starter_roles/{SUFFIX}")
    expected = (
        players.drop(columns="starter_flag", errors="ignore")
        .loc[players.player_id.eq(1630559)]
        .merge(
            roles[["game_id", "team_id", "player_id", "starter_flag"]],
            on=["game_id", "team_id", "player_id"],
            validate="one_to_one",
        )
    )
    expected = expected.loc[expected.starter_flag.eq(1)]
    assert len(expected) == 9 and expected.pts.sum() == 210
    assert 22600185 in set(expected.game_id)  # one actual new16 role consumer
    query = "Austin Reaves stats as a starter this season"
    with development_snapshot(root, digest):
        natural = natural_query_payload(query)
        structured = execute_structured_query(
            "player_game_summary", player="Austin Reaves", season="2026-27", role="starter"
        )
        rest = natural_query_payload("Lakers record when Luka Doncic rests")

    async def http():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(root, digest)), base_url="http://127.0.0.1"
        ) as client:
            response = await client.post("/query", json={"query": query})
            assert response.status_code == 200
            return response.json()

    for body in [natural, asyncio.run(http())]:
        assert body["result_status"] == "ok"
        sections = body["result"]["sections"]
        assert {int(r["game_id"]) for r in sections["game_log"]} == set(expected.game_id)
        assert (sections["summary"][0]["games"], sections["summary"][0]["pts_sum"]) == (9, 210)
        assert body["result"]["metadata"]["role"] == "starter"
        quality = body["result"]["metadata"]["data_quality"]
        assert quality["state"] == "provisional" and quality["manifest_sha256"] == digest
        assert quality["numerical_acceptance"] is quality["production_accepted"] is False
    assert structured.result_status == "ok"
    assert {int(r["game_id"]) for r in structured.result.to_dict()["sections"]["game_log"]} == set(
        expected.game_id
    )
    assert rest["result_reason"] == "no_match"
    assert "0 Rest, 1 reported other, 0 unknown" in " ".join(rest["notes"])


@pytest.mark.parametrize("field", ["starter_flag", "role_source_trusted"])
def test_role_flags_cannot_become_nullable_metadata(integrated, field):
    root, digest = integrated
    path = root / f"data/raw/player_game_starter_roles/{SUFFIX}"
    f = pd.read_csv(path)
    f.loc[0, field] = float("nan")
    f.to_csv(path, index=False)
    doc = json.loads((root / MANIFEST).read_bytes())
    doc["files"][path.relative_to(root).as_posix()] = sha256(path.read_bytes())
    (root / MANIFEST).write_text(json.dumps(doc))
    with development_snapshot(root, sha256((root / MANIFEST).read_bytes())):
        body = natural_query_payload("Austin Reaves stats as a starter this season")
    assert body["result_reason"] == "no_data"
