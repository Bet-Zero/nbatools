"""Read-only retention of pinned historical rows needed by the fixed K01 binding."""

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import data_path

pytestmark = [pytest.mark.needs_data, pytest.mark.query]
GENERATION = "queue-d-production-0574735-20260716"
MANIFEST_SHA = "4bfa194ad102f0ab7b257fafdc66e2d9d5af1bfe95318196f5e20a46fdc5b28e"
PLAYER_SEASONS = ["1996-97", "1997-98", "1998-99", "1999-00", "2000-01", "2001-02", "2007-08"]
TEAM_SEASONS = ["2007-08", "2008-09", "2024-25"]


def test_retain_k01_historical_sources(tmp_path):
    assert os.environ.get("NBATOOLS_DATA_GENERATION") == GENERATION
    manifest_bytes = data_path("metadata/generation_manifest.json").read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == MANIFEST_SHA
    manifest = json.loads(manifest_bytes)
    assert manifest["generation_id"] == GENERATION
    inventory = {item["path"]: item for item in manifest["files"]}
    output = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path))) / "k01-source"
    output.mkdir(parents=True, exist_ok=True)
    (output / "generation_manifest.json").write_bytes(manifest_bytes)
    paths = [f"raw/player_game_stats/{s}_regular_season.csv" for s in PLAYER_SEASONS]
    paths += [f"raw/team_game_stats/{s}_regular_season.csv" for s in TEAM_SEASONS]
    # Its absence is recorded honestly; do not invent or publish an identity index.
    if "metadata/player_names.csv" in inventory:
        paths.append("metadata/player_names.csv")
    receipts = []
    for relative in paths:
        item = inventory[relative]  # Required history must not be silently skipped.
        source = data_path(relative)
        raw = source.read_bytes()
        assert len(raw) == item["size_bytes"]
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        frame = pd.read_csv(source)
        assert not frame.empty
        keys = ["game_id", "team_id"] + (["player_id"] if "/player_game_stats/" in relative else [])
        if relative.startswith("raw/"):
            assert not frame.duplicated(keys).any()
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        receipts.append(dict(item, rows=len(frame)))
    assert len(receipts) >= 10
    (output / "receipt.json").write_text(
        json.dumps(
            {
                "generation": GENERATION,
                "manifest_sha256": MANIFEST_SHA,
                "identity_index_present": "metadata/player_names.csv" in inventory,
                "files": receipts,
                "purpose": "source qualification only; no query or feature acceptance",
            },
            indent=2,
        )
        + "\n"
    )
