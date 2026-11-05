"""Regression gates for the retained real, unpublished normalized NBA snapshot."""

import hashlib
import io
import json
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "working/nba-tools-completion-program/source-evidence/rollover-2026-27/official-gamebooks-20261105"
)


def test_portable_snapshot_integrity_and_explicit_unknowns():
    with ZipFile(EVIDENCE / "normalized-snapshot.zip") as z:
        manifest = json.loads(z.read("dataset-manifest.json"))
        assert len([r for r in manifest["files"] if r["path"].endswith(".csv")]) == 16
        for item in manifest["files"]:
            raw = z.read(item["path"])
            assert len(raw) == item["size_bytes"]
            assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        frame = pd.read_csv(
            io.BytesIO(z.read("data/raw/player_game_period_stats/2026-27_regular_season.csv"))
        )
        unknown = json.loads(z.read("lineage/unknown-rate-keys.json"))
        assert len(unknown) == 484
        assert sum(r["original_1365_member"] for r in unknown) == 412
        for item in unknown:
            row = frame.loc[
                frame.game_id.eq(int(item["game_id"]))
                & frame.player_id.eq(item["player_id"])
                & frame.team_id.eq(item["team_id"])
                & frame.period_family.eq(item["period_family"])
                & frame.period_value.astype(str).eq(item["period_value"])
            ]
            assert len(row) == 1 and pd.isna(row.iloc[0][item["field"]])
        assert not manifest["full_numerical_readiness"]
        assert not manifest["production_published"]


@pytest.mark.parametrize("game_id,players", [(22600142, 24), (22600009, 19)])
def test_corrected_games_have_complete_cross_grain_counts_and_clocks(game_id, players):
    with ZipFile(EVIDENCE / "normalized-snapshot.zip") as z:
        core = pd.read_csv(
            io.BytesIO(z.read("data/raw/player_game_stats/2026-27_regular_season.csv"))
        )
        period = pd.read_csv(
            io.BytesIO(z.read("data/raw/player_game_period_stats/2026-27_regular_season.csv"))
        )
    core = core.loc[core.game_id.eq(game_id)]
    period = period.loc[period.game_id.eq(game_id)]
    assert len(core) == players and len(period) == players * 6
    fields = [
        "pts",
        "fgm",
        "fga",
        "fg3m",
        "fg3a",
        "ftm",
        "fta",
        "oreb",
        "dreb",
        "reb",
        "ast",
        "stl",
        "blk",
        "tov",
        "pf",
        "plus_minus",
    ]
    for whole in core.itertuples():
        rows = period.loc[period.player_id.eq(whole.player_id)]
        quarters = rows.loc[rows.period_family.eq("quarter")]
        assert len(quarters) == 4
        for field in fields:
            assert quarters[field].sum() == getattr(whole, field)
        assert abs(quarters.minutes.sum() - whole.minutes) * 60 <= 2
        for half, values in [("first", ["1", "2"]), ("second", ["3", "4"])]:
            selected = rows.loc[rows.period_family.eq("half") & rows.period_value.eq(half)]
            assert len(selected) == 1
            qs = quarters.loc[quarters.period_value.astype(str).isin(values)]
            for field in fields:
                assert qs[field].sum() == selected.iloc[0][field]
            assert abs(qs.minutes.sum() - selected.iloc[0].minutes) * 60 <= 2
    if game_id == 22600142:
        sasser = core.loc[core.player_id.eq(1631204)].iloc[0]
        martin = core.loc[core.player_id.eq(1628997)].iloc[0]
        assert sasser.plus_minus == 11 and martin.plus_minus == 8


def test_five_official_originals_have_replayable_custody():
    artifact = (EVIDENCE / "original-capture.zip").read_bytes()
    assert hashlib.sha256(artifact).hexdigest() == (
        "8ff6e2052f89cf6e0070aee22c5fcee4c83edc7a285a6d7f4c6209135e8b7190"
    )
    with ZipFile(io.BytesIO(artifact)) as z:
        receipts = [n for n in z.namelist() if n.endswith("/capture.json")]
        assert len(receipts) == 5
        for name in receipts:
            receipt = json.loads(z.read(name))
            original = z.read(name.removesuffix("capture.json") + receipt["raw_file"])
            assert original.startswith(b"%PDF") and len(original) == receipt["size_bytes"]
            assert hashlib.sha256(original).hexdigest() == receipt["sha256"]
            assert receipt["http_status"] == 200 and receipt["attempts"] == 1
            assert receipt["redirects_followed"] == 0
            assert receipt["source_url"] == receipt["response_url"]
            assert datetime.fromisoformat(receipt["started_at"]).tzinfo is not None
            assert receipt["source_generation_independence"] == "unestablished"
