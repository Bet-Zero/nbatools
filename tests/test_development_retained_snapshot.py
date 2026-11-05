"""Retained flagged NBA inputs exercise the app without certifying their accuracy."""

import io
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from nbatools.api_handlers import natural_query_payload
from nbatools.data_source import DataSourceConfigError, data_path
from nbatools.development_data import MANIFEST, development_snapshot, sha256
from tools.development_snapshot import prepare

EVIDENCE = Path(
    "working/nba-tools-completion-program/source-evidence/rollover-2026-27/official-gamebooks-20261105"
)


def test_pr582_flagged_input_query_preserves_unknowns_and_production_boundary(
    tmp_path, monkeypatch
):
    archive = EVIDENCE / "normalized-snapshot.zip"
    original = archive.read_bytes()
    assert sha256(original) == "b43546c6e911b98b303a81bc23072d5ea08c2cd71a6175f48959c25886f8d8b2"
    source = tmp_path / "source"
    with ZipFile(archive) as z:
        for name in z.namelist():
            assert not Path(name).is_absolute() and ".." not in Path(name).parts
        z.extractall(source)
        core = pd.read_csv(
            io.BytesIO(z.read("data/raw/player_game_stats/2026-27_regular_season.csv"))
        )
        expected = core.loc[core.player_id.eq(1630559)]
        assert len(expected) == 8 and expected.pts.sum() == 189
    root = tmp_path / "development"
    digest = prepare(
        source,
        root,
        version="pr582-retained-provisional",
        season="2026-27",
        season_type="Regular Season",
        scope="107 historical due games at 2026-11-05T06:59:31.715470Z; not current freshness",
        source_evidence={
            "reference": "https://github.com/Bet-Zero/nbatools/pull/582",
            "sha256": sha256(original),
        },
        backlog=tmp_path / "backlog",
        exceptions=["DQ-001", "DQ-002", "DQ-003"],
    )
    manifest = json.loads((root / MANIFEST).read_bytes())
    assert manifest["validation_reports"][0]["state"] == "passed"
    period = "data/raw/player_game_period_stats/2026-27_regular_season.csv"
    assert (root / period).read_bytes() == (source / period).read_bytes()
    rates = pd.read_csv(root / period)
    assert rates[["ast_pct", "reb_pct", "tov_pct", "usg_pct"]].isna().sum().sum() >= 484
    with development_snapshot(root, digest):
        payload = natural_query_payload("Austin Reaves average points in 2026-27")
        assert payload["result_status"] == "ok"
        summary = payload["result"]["sections"]["summary"][0]
        assert summary["games"] == 8 and summary["pts_sum"] == 189
        assert summary["pts_avg"] == pytest.approx(23.625)
        quality = payload["result"]["metadata"]["data_quality"]
        assert quality["state"] == "provisional" and not quality["fixture"]
        assert not quality["numerical_acceptance"] and not quality["production_accepted"]
        assert quality["exceptions"] == ["DQ-001", "DQ-002", "DQ-003"]
        unavailable = natural_query_payload(
            "Austin Reaves average points in the third quarter in 2026-27"
        )
        assert unavailable["result_status"] == "no_result"
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root))
    with pytest.raises(DataSourceConfigError, match="explicit local"):
        data_path("data/raw/player_game_stats/2026-27_regular_season.csv")
    assert archive.read_bytes() == original
