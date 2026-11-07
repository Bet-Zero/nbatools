"""Original ID18 is qualified empty over LAL9, never a no_data success."""

import asyncio
import io
import json
from pathlib import Path
from zipfile import ZipFile

import httpx
import pandas as pd
import pytest

from nbatools.api_handlers import natural_query_payload
from nbatools.commands import _reported_absence_reasons as reasons
from nbatools.commands.pipeline import reported_absence_reasons as producer
from nbatools.dataframe_cache import clear_frame_cache
from nbatools.development_data import MANIFEST, DevelopmentSnapshot, development_snapshot, sha256
from nbatools.query_service import execute_structured_query
from tools.development_query import create_app

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "working/nba-tools-completion-program/source-evidence/id18-current-required-20261107"
OLD = E.parent / "core-live-current-20261107"
DIGEST = "a92bc5734836bb1d86c865d2f9cbe4dd51c364aaf79504c8d730823430068a78"
SUFFIX = "2026-27_regular_season.csv"
pytestmark = [pytest.mark.served_seasons, pytest.mark.engine]


@pytest.fixture
def pinned_reason(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_SOURCE", "local")
    raw = (E / "current123-id18-v2.zip").read_bytes()
    assert sha256(raw) == "ac33da770c20a7a66506234aaff246a79a31478a8cc897ddae3f157a62145c13"
    with ZipFile(io.BytesIO(raw)) as z:
        assert all(not Path(n).is_absolute() and ".." not in Path(n).parts for n in z.namelist())
        z.extractall(tmp_path)
    DevelopmentSnapshot(tmp_path, DIGEST)
    return tmp_path


def test_original_source_replay_preserves_old_files_and_all_binary_facts(pinned_reason):
    root = pinned_reason
    producer.validate_publication(root / "data")
    assert not (root / "data/metadata/generation_manifest.json").exists()
    with ZipFile(OLD / "current123-provisional.zip") as z:
        for name in z.namelist():
            if name in {MANIFEST.as_posix(), f"data/raw/player_game_availability/{SUFFIX}"}:
                continue
            assert (root / name).read_bytes() == z.read(name)
        relative = f"data/raw/player_game_availability/{SUFFIX}"
        before = pd.read_csv(io.BytesIO(z.read(relative)), dtype=str, keep_default_na=False)
        after = pd.read_csv(root / relative, dtype=str, keep_default_na=False)
        assert before.drop(columns="source_sha256").equals(after.drop(columns="source_sha256"))
        changed = before.source_sha256.ne(after.source_sha256)
        assert not changed.any()
        assert (root / relative).read_bytes() == z.read(relative)
    with development_snapshot(root, DIGEST):
        people = reasons.load_observations(["2026-27"], "Regular Season")
        assert people[["player_id", "reported_reason", "reason_text"]].to_dict("records") == [
            {
                "player_id": 1629029,
                "reported_reason": "reported_other",
                "reason_text": "Injury/Illness - Other; Back Tightness",
            }
        ]
        teams = pd.read_csv(root / f"data/raw/team_game_stats/{SUFFIX}")
        parent = teams.loc[teams.team_id.eq(1610612747)]
        evidence = {}
        assert reasons.filter_reported_rest(
            parent, "Luka Doncic", ["2026-27"], "Regular Season", evidence=evidence
        ).empty
        assert evidence == dict(
            basis="officially reported Rest",
            complete=True,
            requested_games=9,
            qualified_nonparticipations=1,
            reported_rest=0,
            reported_other=1,
            unknown=0,
        )


@pytest.mark.parametrize(
    "route",
    ["team_record", "game_summary", "game_finder", "player_game_summary", "player_game_finder"],
)
def test_all_five_reason_consumers_qualified_empty(pinned_reason, route):
    kwargs = dict(
        team="LAL",
        season="2026-27",
        without_player="Luka Doncic",
        without_player_reason="reported_rest",
    )
    if route.startswith("player"):
        kwargs["player"] = "Austin Reaves"
    with development_snapshot(pinned_reason, DIGEST):
        result = execute_structured_query(route, **kwargs)
    assert result.result_status == "no_result" and result.result_reason == "no_match"
    assert not result.result.to_dict()["sections"]
    notes = " ".join(result.result.notes)
    assert "0 Rest, 1 reported other, 0 unknown" in notes
    assert "in 9 selected games" in notes
    assert result.metadata["data_quality"]["production_accepted"] is False


def test_original_natural_http_labels_and_distinct_generic_absence(pinned_reason):
    query = "Lakers record when Luka Doncic rests"
    with development_snapshot(pinned_reason, DIGEST):
        natural = natural_query_payload(query)
        generic = natural_query_payload("Lakers record when Luka Doncic sits")

    async def http():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(pinned_reason, DIGEST)),
            base_url="http://127.0.0.1",
        ) as client:
            response = await client.post("/query", json={"query": query})
            assert response.status_code == 200
            return response.json()

    for body in [natural, asyncio.run(http())]:
        assert body["route"] == "team_record"
        assert body["result_status"] == "no_result" and body["result_reason"] == "no_match"
        assert not body["result"]["sections"]
        meta = body["result"]["metadata"]
        assert (meta["team"], meta["season"], meta["without_player_reason"]) == (
            "LAL",
            "2026-27",
            "reported_rest",
        )
        assert {
            "label": "Reported absence reason",
            "value": "officially reported Rest",
            "kind": "reported_reason",
        } in meta["applied_filters"]
        assert meta["data_quality"]["manifest_sha256"] == DIGEST
        assert "PROVISIONAL" in " ".join(body["notes"])
        assert "0 Rest, 1 reported other, 0 unknown" in " ".join(body["notes"])
    row = generic["result"]["sections"]["summary"][0]
    assert (row["games"], row["wins"], row["losses"], row["pts_avg"]) == (1, 1, 0, 103)


@pytest.mark.parametrize("damage", ["source", "lineage", "missing_companion"])
def test_remanifested_corruption_does_not_become_qualified_empty(pinned_reason, damage):
    root = pinned_reason
    doc = json.loads((root / MANIFEST).read_bytes())
    if damage == "source":
        path = next((root / "data/raw/player_game_absence_reason_sources").glob("*.pdf"))
        path.write_bytes(b"%PDF-corrupt")
    elif damage == "lineage":
        path = (
            root / f"data/raw/player_game_availability/{SUFFIX.removesuffix('.csv')}.imports.json"
        )
        lineage = json.loads(path.read_bytes())
        lineage["22600143"]["sha256"] = "0" * 64
        path.write_text(json.dumps(lineage))
    else:
        path = root / f"data/raw/player_game_absence_reasons/{SUFFIX}"
        path.unlink()
    relative = path.relative_to(root).as_posix()
    if path.exists():
        doc["files"][relative] = sha256(path.read_bytes())
    else:
        del doc["files"][relative]
    (root / MANIFEST).write_text(json.dumps(doc))
    clear_frame_cache()
    with development_snapshot(root, sha256((root / MANIFEST).read_bytes())):
        body = natural_query_payload("Lakers record when Luka Doncic rests")
    assert body["result_status"] == "no_result" and body["result_reason"] == "no_data"


def test_old_version_reader_stays_pinned_and_production_cannot_opt_in(pinned_reason, monkeypatch):
    old_root = pinned_reason.parent / "old"
    with ZipFile(OLD / "current123-provisional.zip") as z:
        z.extractall(old_root)
    old_digest = sha256((old_root / MANIFEST).read_bytes())
    query = "Lakers record when Luka Doncic rests"
    with development_snapshot(old_root, old_digest):
        assert natural_query_payload(query)["result_reason"] == "no_data"
        with development_snapshot(pinned_reason, DIGEST):
            assert natural_query_payload(query)["result_reason"] == "no_match"
        assert natural_query_payload(query)["result_reason"] == "no_data"
    monkeypatch.setenv("VERCEL_ENV", "production")
    with pytest.raises(ValueError, match="isolated local development"):
        DevelopmentSnapshot(pinned_reason, DIGEST)
