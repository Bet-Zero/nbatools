"""Promote an obsolete refusal only with raw same-game opponent and rank oracles."""

from pathlib import Path

import pandas as pd
import pytest

from nbatools.data_source import reset_data_source_cache
from nbatools.query_service import execute_natural_query


@pytest.mark.parametrize(
    "name,threshold,expected_ids,expected_points",
    [
        ("LeBron James", 5, [425, 376, 453, 416, 531], [36, 35, 33, 33, 32]),
        ("Stephen Curry", 18, [517, 432, 489, 367, 368], [39, 31, 30, 27, 26]),
    ],
)
def test_ranked_player_games_apply_opponent_count_not_player_count(
    monkeypatch, name, threshold, expected_ids, expected_points
):
    root = Path("qa/fixtures/query_engine_sample")
    raw = root / "data/raw"
    players = pd.read_csv(raw / "player_game_stats/2025-26_regular_season.csv")
    teams = pd.read_csv(raw / "team_game_stats/2025-26_regular_season.csv")
    opponent = teams[["game_id", "team_id", "fg3m"]].rename(
        columns={"team_id": "opponent_team_id", "fg3m": "opponent_fg3m"}
    )
    sample = players.loc[players.player_name.eq(name)].merge(
        opponent, on=["game_id", "opponent_team_id"], validate="one_to_one"
    )
    qualifying = sample.loc[sample.opponent_fg3m.ge(threshold)]
    expected = qualifying.sort_values(["pts", "game_date"], ascending=[False, False]).head(5)
    assert expected.game_id.astype(int).tolist() == expected_ids
    assert expected.pts.tolist() == expected_points
    if name == "Stephen Curry":
        assert len(qualifying) == 11
        assert sample.loc[sample.fg3m.ge(threshold)].empty
        assert (
            sample.sort_values(["pts", "game_date"], ascending=[False, False])
            .head(5)
            .game_id.tolist()
            != expected_ids
        )
    monkeypatch.setenv("DATA_SOURCE", "local")
    monkeypatch.setenv("NBATOOLS_DATA_ROOT", str(root.resolve()))
    reset_data_source_cache()
    try:
        answer = execute_natural_query(
            f"{name} most points in a game with {threshold} threes allowed"
        )
        assert answer.result_status == "ok", answer.metadata
        rows = answer.result.to_dict()["sections"]["finder"]
        assert [int(row["game_id"]) for row in rows] == expected_ids
        assert [row["pts"] for row in rows] == expected_points
        assert answer.metadata["stat"] == "pts"
        assert answer.metadata["min_value"] is None
        assert answer.metadata["max_value"] is None
        assert answer.metadata["conditions"] == [
            {"stat": "opponent_fg3m", "min_value": float(threshold), "max_value": None}
        ]
        assert any("OPP FG3M" in item["label"] for item in answer.metadata["applied_filters"])
    finally:
        reset_data_source_cache()
