"""Returned period sources: finite numerical truth, actual consumers and honest blockers."""

import asyncio
import importlib.util
import io
import json
from pathlib import Path
from zipfile import ZipFile

import httpx
import pandas as pd
import pytest

from nbatools.api_handlers import natural_query_payload
from nbatools.commands.validation_control import build_slice_manifest
from nbatools.development_data import MANIFEST, DevelopmentSnapshot, development_snapshot, sha256
from nbatools.query_service import execute_structured_query
from tools.development_query import create_app

E = (
    Path(__file__).resolve().parents[1]
    / "working/nba-tools-completion-program/source-evidence/current123-periods-20261107"
)
SUFFIX = "2026-27_regular_season.csv"
WINDOW = {
    "q1": ("quarter", "1"),
    "q2": ("quarter", "2"),
    "q3": ("quarter", "3"),
    "q4": ("quarter", "4"),
    "h1": ("half", "first"),
    "h2": ("half", "second"),
    "ot": ("overtime", "ot"),
}
pytestmark = [pytest.mark.served_seasons, pytest.mark.engine]


@pytest.fixture
def snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_SOURCE", "local")
    binding = json.loads((E / "binding.json").read_bytes())
    archive = (E / binding["archive"]).read_bytes()
    assert sha256(archive) == binding["archive_sha256"]
    with ZipFile(io.BytesIO(archive)) as z:
        assert all(n.startswith("data/") and ".." not in Path(n).parts for n in z.namelist())
        z.extractall(tmp_path)
    DevelopmentSnapshot(tmp_path, binding["manifest_sha256"])
    return tmp_path, binding["manifest_sha256"]


def check_oracle(root):
    raw = (E / "independent-oracle.json").read_bytes()
    assert sha256(raw) == "59fd69280de504dc656611988f074b49eeecb35e1830d1cbbb0db07f9e1bec1a"
    oracle = json.loads(raw)
    for grain, reference in (("player", "canonical_player_rows"), ("team", "team_rows")):
        frame = pd.read_csv(
            root / f"data/raw/{grain}_game_period_stats/{SUFFIX}", dtype={"period_value": str}
        )
        frame = frame.loc[frame.game_id.ge(22600173)]
        keys = [
            "game_id",
            "team_id",
            *(["player_id"] if grain == "player" else []),
            "period_family",
            "period_value",
        ]
        assert len(frame) == len(oracle[reference])
        actual = frame.set_index(keys)
        assert not actual.index.has_duplicates
        for row in oracle[reference]:
            key = (
                row["game_id"],
                row["team_id"],
                *([row["player_id"]] if grain == "player" else []),
                *WINDOW[row["window"]],
            )
            observed = actual.loc[key]
            for field, expected in row.items():
                if field in observed and isinstance(expected, (int, float)) and field not in keys:
                    assert observed[field] == pytest.approx(expected, abs=1e-12), (key, field)
    assert len(oracle["failures"]) == 4  # Precisely retained conflict, not four accepted cells.


def test_all_new_canonical_values_match_independent_original_byte_oracle(snapshot):
    check_oracle(snapshot[0])


def test_existing_importer_replays_all_sources_and_explicit_clock_ledger(tmp_path):
    spec = importlib.util.spec_from_file_location("period_replay", E / "integrate_periods.py")
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)
    _, quality = replay.qualify(tmp_path / "replay", tmp_path / "backlog")
    check_oracle(tmp_path / "replay/stage")
    assert (
        quality["directly_imported"] == 95 and quality["independently_derived_clock_windows"] == 3
    )
    assert len(quality["derived_clock_ledger"]) == 6
    assert quality["period_numerical_complete"] is False


def test_parent_versions_bytes_unknowns_and_required_coverage_preserved(snapshot):
    root, digest = snapshot
    parent = E.parent / "id18-current-required-20261107/current123-required-v3.zip"
    with ZipFile(parent) as z:
        for name in z.namelist():
            if name == MANIFEST.as_posix():
                continue
            before, after = z.read(name), (root / name).read_bytes()
            if "/player_game_period_stats/" in name or "/team_game_period_stats/" in name:
                assert after.startswith(before)
            else:
                assert after == before
    player = pd.read_csv(root / f"data/raw/player_game_period_stats/{SUFFIX}")
    team = pd.read_csv(root / f"data/raw/team_game_period_stats/{SUFFIX}")
    assert (len(player), len(team)) == (16783, 1490)
    assert len(team[["game_id", "period_family", "period_value"]].drop_duplicates()) == 745
    assert player[["tov_pct", "usg_pct"]].isna().sum().to_dict() == {"tov_pct": 242, "usg_pct": 242}
    assert len(player.loc[player.game_id.ge(22600173) & player.period_family.eq("overtime")]) == 28
    report = build_slice_manifest(
        "2026-27", "Regular Season", data_root=root / "data", generation_id="period-admission-check"
    )
    assert report["validation_state"] == "passed"
    assert all(not d["validation"]["errors"] for d in report["datasets"])
    status = DevelopmentSnapshot(root, digest).status()
    assert status["numerical_acceptance"] is status["production_accepted"] is False
    assert "DQ-006" in status["exceptions"]
    assert not (root / "data/metadata/generation_manifest.json").exists()


CASES = [
    ("Lakers second quarter record on 2026-11-04", "LAL", {"quarter": "2"}, 1, 0, 33),
    ("Lakers first half record on 2026-11-04", "LAL", {"half": "first"}, 1, 0, 61),
    ("Pelicans overtime record on 2026-11-04", "NOP", {"quarter": "OT"}, 1, 0, 16),
    ("Clippers overtime record on 2026-11-04", "LAC", {"quarter": "OT"}, 0, 1, 9),
]


@pytest.mark.parametrize("query,team,window,wins,losses,points", CASES)
def test_qualified_period_record_natural_structured_http_and_labels(
    snapshot, query, team, window, wins, losses, points
):
    root, digest = snapshot
    with development_snapshot(root, digest):
        natural = natural_query_payload(query)
        structured = execute_structured_query(
            "team_record",
            team=team,
            season="2026-27",
            start_date="2026-11-04",
            end_date="2026-11-04",
            **window,
        )

    async def http():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(root, digest)), base_url="http://127.0.0.1"
        ) as client:
            result = await client.post("/query", json={"query": query})
            assert result.status_code == 200
            return result.json()

    assert structured.result_status == "ok"
    for body in (natural, asyncio.run(http())):
        assert body["result_status"] == "ok"
        row = body["result"]["sections"]["summary"][0]
        assert (row["games"], row["wins"], row["losses"], row["pts_avg"]) == (
            1,
            wins,
            losses,
            points,
        )
        quality = body["result"]["metadata"]["data_quality"]
        assert quality["manifest_sha256"] == digest and quality["state"] == "provisional"
        assert quality["numerical_acceptance"] is quality["production_accepted"] is False
        assert "PROVISIONAL" in " ".join(body["notes"])
        expected_caveat = {
            "LAL": "record computed from quarter 2 scores"
            if "quarter" in window
            else "record computed from first half scores",
            "NOP": "record computed from overtime scores",
            "LAC": "record computed from overtime scores",
        }[team]
        assert expected_caveat in body["caveats"]
        assert body["result"]["metadata"][next(iter(window))] == next(iter(window.values()))
    row = structured.result.to_dict()["sections"]["summary"][0]
    assert (row["wins"], row["losses"], row["pts_avg"]) == (wins, losses, points)


def test_old_rate_unknowns_still_block_strict_player_period_delivery(snapshot):
    root, digest = snapshot
    with development_snapshot(root, digest):
        result = execute_structured_query(
            "player_game_finder",
            player="Austin Reaves",
            season="2026-27",
            quarter="2",
            start_date="2026-11-04",
            end_date="2026-11-04",
        )
    assert result.result_status == "no_result" and result.result_reason == "no_data"
    assert "unknown numeric fields" in " ".join(result.result.notes)
    # This refusal is retained containment, never a successful positive.


def test_production_cannot_select_provisional_period_snapshot(snapshot, monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "production")
    with pytest.raises(ValueError, match="isolated local development"):
        with development_snapshot(*snapshot):
            pass
