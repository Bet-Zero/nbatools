"""New scorer evidence resolves the finite rebound conflict without erasing unknowns."""

import asyncio
import csv
import importlib.util
import io
import json
from fractions import Fraction
from zipfile import ZipFile

import httpx
import pandas as pd
import pytest

from nbatools.api_handlers import natural_query_payload
from nbatools.commands.validation_control import build_slice_manifest
from nbatools.development_data import MANIFEST, DevelopmentSnapshot, development_snapshot, sha256
from nbatools.query_service import execute_structured_query
from tests.test_current123_period_integration import SUFFIX, E
from tools.development_query import create_app

RATE_SHA = "7d054703091f5f0334d2b01dd7bd978e619d2e36a11eead390fdb23cf0646698"
pytestmark = [pytest.mark.served_seasons, pytest.mark.engine]


@pytest.fixture
def corrected(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_SOURCE", "local")
    binding = json.loads((E / "v5-binding.json").read_bytes())
    raw = (E / binding["archive"]).read_bytes()
    assert sha256(raw) == binding["archive_sha256"]
    with ZipFile(io.BytesIO(raw)) as z:
        assert all(n.startswith("data/") and ".." not in n.split("/") for n in z.namelist())
        z.extractall(tmp_path)
    DevelopmentSnapshot(tmp_path, binding["manifest_sha256"])
    return tmp_path, binding["manifest_sha256"]


def test_scorer_count_and_rebound_exposure_facts_are_applied_exactly(corrected):
    root, _ = corrected
    raw = (E / "independent-book-rebound-oracle.json").read_bytes()
    assert sha256(raw) == RATE_SHA
    oracle = json.loads(raw)
    frames = {
        g: pd.read_csv(
            root / f"data/raw/{g}_game_period_stats/{SUFFIX}", dtype={"period_value": str}
        )
        for g in ("player", "team")
    }
    for fact in oracle["count_corrections"]:
        frame = frames[fact["dataset"]]
        family, value = ("quarter", "2") if fact["window"] == "q2" else ("half", "first")
        chosen = frame.loc[
            frame.game_id.eq(fact["game_id"])
            & frame.team_id.eq(fact["team_id"])
            & frame.period_family.eq(family)
            & frame.period_value.eq(value)
        ]
        if fact["dataset"] == "player":
            chosen = chosen.loc[chosen.player_id.eq(fact["player_id"])]
        field = {"reboundsDefensive": "dreb", "reboundsTotal": "reb"}[fact["field"]]
        assert len(chosen) == 1 and chosen[field].item() == fact["after"]
    for fact in oracle["rates"]:
        family, value = ("quarter", "2") if fact["window"] == "q2" else ("half", "first")
        f = frames["player"]
        row = f.loc[
            f.game_id.eq(fact["game_id"])
            & f.team_id.eq(fact["team_id"])
            & f.player_id.eq(fact["player_id"])
            & f.period_family.eq(family)
            & f.period_value.eq(value)
        ]
        assert len(row) == 1
        assert row.reb.item() == fact["numerator"]
        assert row.reb_pct.item() == pytest.approx(
            float(Fraction(fact["numerator"], fact["denominator"])), abs=1e-14
        )
    p = frames["player"]
    w = p.loc[p.game_id.eq(22600184) & p.player_id.eq(1629023) & p.period_family.eq("quarter")]
    assert (w.dreb.sum(), w.reb.sum()) == (6, 10)
    t = frames["team"]
    d = t.loc[t.game_id.eq(22600184) & t.team_id.eq(1610612742) & t.period_family.eq("quarter")]
    assert (d.dreb.sum(), d.reb.sum()) == (32, 50)
    assert len(oracle["rates"]) == 38 and len(oracle["count_corrections"]) == 8


def test_only_declared_tokens_change_and_all_old_versions_unknowns_survive(corrected):
    root, digest = corrected
    ledger = json.loads((E / "book-correction.json").read_bytes())
    with ZipFile(E / "current123-period-v4.zip") as z:
        old_doc = json.loads(z.read(MANIFEST.as_posix()))
        for name in z.namelist():
            if name == MANIFEST.as_posix():
                continue
            raw = z.read(name)
            if "_game_period_stats/" not in name:
                assert (root / name).read_bytes() == raw
                continue
            grain = "player" if "/player_" in name else "team"
            before = list(csv.reader(io.StringIO(raw.decode())))
            after = list(csv.reader(io.StringIO((root / name).read_text())))
            assert len(before) == len(after)
            allowed = {
                (r["row"] + 1, before[0].index(r["field"]))
                for r in ledger["count_changes"]
                if r["dataset"] == grain
            }
            if grain == "player":
                for index, row in enumerate(before[1:], 1):
                    values = dict(zip(before[0], row, strict=True))
                    if values["game_id"] == "22600184" and (
                        values["period_family"],
                        values["period_value"],
                    ) in {("quarter", "2"), ("half", "first")}:
                        allowed.add((index, before[0].index("reb_pct")))
            for index, (a, b) in enumerate(zip(before, after, strict=True)):
                assert len(a) == len(b)
                for column, (old, new) in enumerate(zip(a, b, strict=True)):
                    assert old == new or (index, column) in allowed
        assert (
            "DQ-auto-4294464123002d61e11cd59f7cdebfd1690b172d28b608f26d934e725ecc6c7a"
            in old_doc["exceptions"]
        )
    doc = DevelopmentSnapshot(root, digest).document
    assert set(doc["exceptions"]) == {"DQ-001", "DQ-002", "DQ-003", "DQ-006"}
    f = pd.read_csv(root / f"data/raw/player_game_period_stats/{SUFFIX}")
    assert f[["usg_pct", "tov_pct", "reb_pct"]].isna().sum().to_dict() == {
        "usg_pct": 242,
        "tov_pct": 242,
        "reb_pct": 0,
    }
    assert (len(f), len(pd.read_csv(root / f"data/raw/team_game_period_stats/{SUFFIX}"))) == (
        16783,
        1490,
    )
    assert json.loads(
        (root / "data/metadata/corrections/game184-rebound-oracle.json").read_bytes()
    ) == json.loads((E / "independent-book-rebound-oracle.json").read_bytes())
    report = build_slice_manifest(
        "2026-27", "Regular Season", data_root=root / "data", generation_id="scorer-check"
    )
    assert report["validation_state"] == "passed"
    assert DevelopmentSnapshot(root, digest).status()["numerical_acceptance"] is False


def test_existing_versioned_correction_replays_and_rejects_stale_oracle(tmp_path):
    spec = importlib.util.spec_from_file_location("book_replay", E / "apply_book_correction.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _, report = module.apply(
        tmp_path / "correct", E / "independent-book-rebound-oracle.json", RATE_SHA
    )
    assert len(report["count_changes"]) == 8 and len(report["rate_changes"]) == 38
    assert all(r["independent_exposure"]["denominator"] > 0 for r in report["rate_changes"])
    with pytest.raises(AssertionError):
        module.apply(tmp_path / "stale", E / "independent-book-rebound-oracle.json", "0" * 64)
    assert not (tmp_path / "stale/current123-period-v5.zip").exists()


@pytest.mark.parametrize(
    "window,points,rebounds,label",
    [(dict(quarter="2"), 25, 8, "second quarter"), (dict(half="first"), 51, 20, "first half")],
)
def test_corrected_rebounds_reach_actual_natural_structured_http_consumers(
    corrected, window, points, rebounds, label
):
    root, digest = corrected
    query = f"Mavericks {label} record on 2026-11-04"
    with development_snapshot(root, digest):
        natural = natural_query_payload(query)
        structured = execute_structured_query(
            "team_record",
            team="DAL",
            season="2026-27",
            start_date="2026-11-04",
            end_date="2026-11-04",
            **window,
        )

    async def http():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(root, digest)), base_url="http://127.0.0.1"
        ) as client:
            response = await client.post("/query", json={"query": query})
            assert response.status_code == 200
            return response.json()

    assert structured.result_status == "ok"
    for body in (natural, asyncio.run(http())):
        assert body["result_status"] == "ok"
        row = body["result"]["sections"]["summary"][0]
        assert (row["games"], row["wins"], row["losses"], row["pts_avg"], row["reb_avg"]) == (
            1,
            0,
            1,
            points,
            rebounds,
        )
        quality = body["result"]["metadata"]["data_quality"]
        assert (
            quality["manifest_sha256"] == digest
            and quality["numerical_acceptance"] is False
            and quality["production_accepted"] is False
        )
        assert "PROVISIONAL" in " ".join(body["notes"])
    row = structured.result.to_dict()["sections"]["summary"][0]
    assert (row["pts_avg"], row["reb_avg"]) == (points, rebounds)


def test_original_rate_unknown_guard_and_production_isolation_still_apply(corrected, monkeypatch):
    root, digest = corrected
    with development_snapshot(root, digest):
        result = execute_structured_query(
            "player_game_finder",
            player="P.J. Washington",
            season="2026-27",
            quarter="2",
            start_date="2026-11-04",
            end_date="2026-11-04",
        )
    assert result.result_status == "no_result" and result.result_reason == "no_data"
    assert "unknown numeric fields" in " ".join(result.result.notes)
    monkeypatch.setenv("VERCEL_ENV", "production")
    with pytest.raises(ValueError, match="isolated local development"):
        with development_snapshot(root, digest):
            pass
