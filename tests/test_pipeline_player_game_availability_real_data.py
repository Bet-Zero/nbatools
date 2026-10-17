"""Real-data contract: join a publicly reported ESPN game to pinned NBA rows.

Run explicitly through the existing read-only targeted R2 validation flow.
The source timestamp and a small collected CSV are evidence, not automatic
production publication or a claim that the whole NBA roster is complete.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.pipeline.pull_player_game_availability import (
    backfill,
    validate_publication,
)
from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def _stage_opening_game(tmp_path):
    season = "2025-26"
    suffix = f"{season}_regular_season.csv"
    source = {
        "games": data_read_csv(f"data/raw/games/{suffix}"),
        "team_game_stats": data_read_csv(f"data/raw/team_game_stats/{suffix}"),
        "player_game_stats": data_read_csv(f"data/raw/player_game_stats/{suffix}"),
    }
    game_log = source["games"]
    required = {"game_id", "game_date", "home_team_id", "away_team_id", "is_final"}
    assert required.issubset(game_log.columns), required - set(game_log.columns)
    target = game_log[
        game_log["game_date"].astype(str).eq("2025-10-21")
        & game_log["home_team_id"].eq(1610612747)
        & game_log["away_team_id"].eq(1610612744)
    ]
    assert len(target) == 1
    game = target.iloc[0]
    assert bool(game["is_final"])
    game_id = int(game["game_id"])

    scores = source["team_game_stats"]
    scoped = scores[pd.to_numeric(scores["game_id"], errors="raise").eq(game_id)]
    assert dict(zip(scoped.team_abbr, scoped.pts)) == {"LAL": 109, "GSW": 119}

    root = tmp_path / "data"
    for label, df in source.items():
        folder = root / "raw" / label
        folder.mkdir(parents=True)
        df.to_csv(folder / suffix, index=False)
    try:
        rosters = data_read_csv(f"data/raw/rosters/{season}.csv")
    except (FileNotFoundError, OSError):
        rosters = None
    if rosters is not None:
        roster_path = root / "raw/rosters"
        roster_path.mkdir(parents=True)
        rosters.to_csv(roster_path / f"{season}.csv", index=False)

    # Some source-listed inactives have no current-season appearances or were
    # absent from the later roster snapshot. Prior qualified rows resolve IDs;
    # only this game's report establishes their membership/nonparticipation.
    prior = data_read_csv("data/raw/player_game_stats/2024-25_regular_season.csv")
    prior.to_csv(root / "raw/player_game_stats/2024-25_regular_season.csv", index=False)

    return root, game_id


def test_2025_opening_lakers_warriors_explicit_dnp_and_nba_id_match(tmp_path):
    root, game_id = _stage_opening_game(tmp_path)
    rows = backfill("2025-26", root=root, source="espn", game_ids=[game_id])
    validate_publication(root)
    assert rows.game_id.eq(f"{game_id:010d}").all()
    assert rows.source.eq("espn_game_summary:401809244").all()
    assert rows.coverage_scope.eq("listed_player_rows_only").all()
    assert rows.team_id.isin([1610612747, 1610612744]).all()
    assert len(rows) >= 20
    assert rows.participation_state.eq("did_not_play").any()
    # The reported DNP is a source observation, not an invented injury or
    # an inference about athletes missing from the ESPN game box score.
    assert (
        rows.loc[rows.participation_state.eq("did_not_play"), "source_comment"]
        .str.startswith("DNP - ESPN confirmed")
        .all()
    )
    print(
        "Verified game-day observations:",
        len(rows),
        "source-reported DNP:",
        int(rows.participation_state.eq("did_not_play").sum()),
        "NBA IDs verified:",
        int(rows.player_id.nunique()),
    )


def test_official_opening_report_retains_real_source_and_explicit_absences(tmp_path):
    """Acquire one actual scorer report; retain publication inputs in CI evidence."""
    root, game_id = _stage_opening_game(tmp_path)
    evidence = Path(os.environ.get("NBATOOLS_ACQUISITION_OUTPUT", str(tmp_path / "evidence")))
    try:
        rows = backfill("2025-26", root=root, source="report", game_ids=[game_id])
    finally:
        # These are fetched NBA bytes and derived rows, never fixture data.
        # The existing validation workflow retains this directory as evidence;
        # an artifact is staging, not permanent R2 publication.
        for directory in ("player_game_availability_sources", "player_game_availability"):
            source = root / "raw" / directory
            if source.exists():
                shutil.copytree(source, evidence / "raw" / directory, dirs_exist_ok=True)
    validate_publication(root)
    assert rows.game_id.eq(f"{game_id:010d}").all()
    assert rows.source.eq("nba_official_finalbox:20251021_GSWLAL").all()
    assert rows.coverage_scope.eq("listed_player_rows_only").all()
    assert rows.team_id.isin([1610612747, 1610612744]).all()
    assert len(rows) >= 24
    for name in (
        "LeBron James",
        "Moses Moody",
        "Bronny James",
        "Trayce Jackson-Davis",
        "Alex Toohey",
    ):
        player = rows[rows.player_name.eq(name)]
        assert len(player) == 1, name
        assert player.iloc[0].participation_state == "did_not_play", name
    receipt = evidence / "raw/player_game_availability_sources/20251021_GSWLAL.json"
    manifest = json.loads(receipt.read_text())
    assert rows.source_sha256.eq(manifest["sha256"]).all()
    import hashlib

    raw = receipt.parent / manifest["raw_file"]
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == manifest["sha256"]
    assert raw.stat().st_size == manifest["size_bytes"]
    assert manifest["source_url"].endswith("/20251021/20251021_GSWLAL.pdf")
    (evidence / "validation.json").write_text(
        json.dumps(
            {
                "game_id": f"{game_id:010d}",
                "base_generation": os.environ.get("NBATOOLS_DATA_GENERATION"),
                "candidate_sha": os.environ.get("VALIDATION_SHA"),
                "rows": len(rows),
                "source_receipt": str(receipt.relative_to(evidence)),
                "publication_state": "staged_only",
                "identity_source_sha256": rows.identity_source_sha256.fillna("").unique().tolist(),
            },
            indent=2,
        )
        + "\n"
    )
    print("Verified official report rows:", len(rows), "source SHA256:", manifest["sha256"])
