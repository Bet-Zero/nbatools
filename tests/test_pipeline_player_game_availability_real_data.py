"""Real-data contract: join a publicly reported ESPN game to pinned NBA rows.

Run explicitly through the existing read-only targeted R2 validation flow.
The source timestamp and a small collected CSV are evidence, not automatic
production publication or a claim that the whole NBA roster is complete.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.pipeline.pull_player_game_availability import backfill
from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.engine]


def test_2025_opening_lakers_warriors_explicit_dnp_and_nba_id_match(tmp_path):
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

    rows = backfill(season, root=root, source="espn", game_ids=[game_id])
    assert rows.game_id.eq(f"{game_id:010d}").all()
    assert rows.source.eq("espn_game_summary:401809244").all()
    assert rows.coverage_scope.eq("listed_player_rows_only").all()
    assert rows.team_id.isin([1610612747, 1610612744]).all()
    assert len(rows) >= 20
    assert rows.participation_state.eq("did_not_play").any()
    # The reported DNP is a source observation, not an invented injury or
    # an inference about athletes missing from the ESPN game box score.
    assert rows.loc[rows.participation_state.eq("did_not_play"), "source_comment"].str.startswith(
        "DNP - ESPN confirmed"
    ).all()

    evidence = Path("outputs/required_data_validation/player_game_availability_sample.csv")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(evidence, index=False)
