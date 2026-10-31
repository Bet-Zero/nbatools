"""Bounded offline retained-source producer for protected publication preparation."""

import csv
import io
import os
import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.pipeline import player_game_availability_report as report
from nbatools.data_source import data_path, reset_data_source_cache
from nbatools.query_service import execute_natural_query
from tools.prepare_k08_availability import BASE, CSV, HISTORICAL, build_overlay

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def test_build_retained_six_game_overlay(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Qualified originals must never be reacquired")

    monkeypatch.setattr(report.urllib.request, "urlopen", forbidden)
    output = tmp_path / "overlay"
    evidence = build_overlay(tmp_path / "stage", output, candidate_sha=os.environ["VALIDATION_SHA"])
    root = tmp_path / "stage/data"
    old = list(csv.DictReader(io.StringIO(data_path("data/" + CSV).read_text())))
    new = list(csv.DictReader(io.StringIO((output / CSV).read_text())))

    def key(row):
        return (row["game_id"], row["team_id"], row["player_id"])

    old_by_key, new_by_key = {key(r): r for r in old}, {key(r): r for r in new}
    assert len(old) == 102 and len(new) == 206
    assert all(new_by_key[k] == row for k, row in old_by_key.items())
    added = [r for k, r in new_by_key.items() if k not in old_by_key]
    assert len(added) == 104
    assert pd.Series([r["participation_state"] for r in added]).value_counts().to_dict() == {
        "played": 70,
        "did_not_play": 34,
    }
    expected = {"1997-98": (24, 20), "2004-05": (24, 21), "2014-15": (30, 23)}
    for season, game in HISTORICAL:
        frame = pd.read_csv(output / f"raw/player_game_availability/{season}_regular_season.csv")
        assert (len(frame), frame.participation_state.eq("played").sum()) == expected[season]
        assert set(frame.game_id) == {game}
    assert evidence["base_generation"] == BASE
    assert evidence["publication_state"] == "staged_only_no_writes"
    # Preserve the full compact artifact first, even if a consumer finding fails.
    target = os.environ.get("NBATOOLS_ACQUISITION_OUTPUT")
    if target:
        shutil.copytree(output, Path(target), dirs_exist_ok=True)
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.parent))
    monkeypatch.setenv("NBATOOLS_DATA_GENERATION", "legacy")
    reset_data_source_cache()
    try:
        for query, expected_record, game_ids in [
            (
                "Nets record without Kerry Kittles and Keith Van Horn in 1997-98 from 1997-10-31 to 1997-10-31",
                (1, 1, 0, 97),
                [29700002],
            ),
            (
                "Pistons record without Darko Milicic in 2004-05 from 2004-11-02 to 2004-11-02",
                (1, 1, 0, 87),
                [20400001],
            ),
            (
                "Pelicans record without Darius Miller and Patric Young in 2014-15 from 2014-10-28 to 2014-10-28",
                (1, 1, 0, 101),
                [21400001],
            ),
            (
                "Lakers record without LeBron James from 2025-10-24 to 2025-10-27 in 2025-26",
                (3, 2, 1, 121),
                [22500019, 22500113, 22500122],
            ),
        ]:
            result = execute_natural_query(query)
            assert result.result_status == "ok", (query, result.metadata)
            sections = result.result.to_dict()["sections"]
            row = sections["summary"][0]
            assert tuple(row[k] for k in ("games", "wins", "losses", "pts_avg")) == expected_record
            assert [int(r["game_id"]) for r in sections["game_log"]] == game_ids
        result = execute_natural_query(
            "how many games did LeBron miss on October 24 and October 27 in 2025-26"
        )
        assert result.result_status == "ok", result.metadata
        sections = result.result.to_dict()["sections"]
        assert sections["count"][0]["count"] == 2
        assert {int(r["game_id"]) for r in sections["finder"]} == {22500019, 22500122}
        result = execute_natural_query(
            "Without Darius Miller and Patric Young, Anthony Davis games with at least 20 points in 2014-15 from 2014-10-28 to 2014-10-28"
        )
        assert result.result_status == "ok" and result.route == "player_game_finder", (
            result.metadata
        )
        assert [
            (int(r["game_id"]), r["pts"]) for r in result.result.to_dict()["sections"]["finder"]
        ] == [(21400001, 26)]
        assert not (
            root / "raw/player_game_availability/2025-26_regular_season.partial.csv"
        ).exists()

    finally:
        reset_data_source_cache()
