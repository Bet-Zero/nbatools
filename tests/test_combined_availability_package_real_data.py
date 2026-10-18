"""Read-only producer for the opening + four BOS/LAL report publication artifact."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.pipeline.pull_player_game_availability import validate_publication
from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]
ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "working/nba-tools-completion-program"


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_combined_rows(root):
    expected = {"2023-24": {22300403, 22300684}, "2025-26": {22500002, 22500338, 22500823}}
    # Opening NBA game ID is 0022500002 (22500002 numerically).
    for season, games in expected.items():
        frame = pd.read_csv(root / f"raw/player_game_availability/{season}_regular_season.csv")
        assert set(frame.game_id.astype(int)) == games
        assert len(frame) == (68 if season == "2023-24" else 102)
        assert frame.participation_state.value_counts().to_dict() == (
            {"played": 41, "did_not_play": 27}
            if season == "2023-24"
            else {"played": 70, "did_not_play": 32}
        )
        assert not frame.duplicated(["game_id", "player_id"]).any()
        assert frame.coverage_scope.eq("listed_player_rows_only").all()
        played = frame.loc[frame.participation_state.eq("played")]
        canonical = pd.read_csv(root / f"raw/player_game_stats/{season}_regular_season.csv")
        canonical = canonical.loc[canonical.game_id.isin(games)]
        keys = ["game_id", "team_id", "player_id"]
        assert set(map(tuple, played[keys].values)) == set(map(tuple, canonical[keys].values))
        assert played.groupby(
            ["game_id", "team_id"]
        ).source_minutes.sum().tolist() == pytest.approx([240] * (2 * len(games)), abs=0.02)
        tatum = frame.loc[frame.player_id.eq(1628369)]
        assert len(tatum) == 2
        assert tatum.participation_state.eq(
            "played" if season == "2023-24" else "did_not_play"
        ).all()
        if season == "2025-26":
            opening = frame.loc[frame.game_id.eq(22500002)]
            assert opening.participation_state.value_counts().to_dict() == {
                "played": 20,
                "did_not_play": 14,
            }
            for player, name in ((2544, "LeBron James"), (1630541, "Moses Moody")):
                assert opening.loc[opening.player_id.eq(player), "player_name"].tolist() == [name]
                assert opening.loc[
                    opening.player_id.eq(player), "participation_state"
                ].tolist() == ["did_not_play"]
    validate_publication(root)


def test_combined_reviewed_availability_source_package(tmp_path):
    gate, builder = load_tool("r2_publication"), load_tool("combine_availability_package")
    sources = []
    for name in ("opening-availability-inventory.json", "s4-availability-source-inventory.json"):
        inventory = json.loads((PROGRAM / name).read_text())
        assert inventory["base_generation"] == os.environ["NBATOOLS_DATA_GENERATION"]
        destination = tmp_path / name.removesuffix(".json")
        gate.acquire_overlay(inventory, destination)
        sources.append((destination, inventory))
    output = tmp_path / "combined"
    builder.combine(sources, output, candidate_sha=os.environ["VALIDATION_SHA"])
    validation = tmp_path / "validation"
    shutil.copytree(output, validation)
    for season in ("2023-24", "2025-26"):
        for kind in ("games", "team_game_stats", "player_game_stats"):
            name = f"raw/{kind}/{season}_regular_season.csv"
            path = validation / name
            path.parent.mkdir(parents=True, exist_ok=True)
            data_read_csv("data/" + name).to_csv(path, index=False)
    # Prior season rows resolve identities only; never establish participation.
    data_read_csv("data/raw/player_game_stats/2024-25_regular_season.csv").to_csv(
        validation / "raw/player_game_stats/2024-25_regular_season.csv", index=False
    )
    verify_combined_rows(validation)
    evidence = os.environ.get("NBATOOLS_ACQUISITION_OUTPUT")
    if evidence:
        shutil.copytree(output, Path(evidence), dirs_exist_ok=True)
