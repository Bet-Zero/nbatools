"""C2 player shooting stretches against the real regular-season rows."""

from __future__ import annotations

import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_curry_three_point_stretch_counts_raw_games():
    from nbatools.query_service import execute_natural_query

    rows = data_read_csv("raw/player_game_stats/2015-16_regular_season.csv", dtype={"game_id": str})
    games = rows[rows["player_name"] == "Stephen Curry"].sort_values(["game_date", "game_id"])
    shots = list(zip(games["fg3m"], games["fg3a"], strict=True))
    best = max(
        round(sum(m for m, _ in shots[i : i + 5]) / sum(a for _, a in shots[i : i + 5]), 3)
        for i in range(len(shots) - 4)
        if sum(a for _, a in shots[i : i + 5])
    )

    result = execute_natural_query("Stephen Curry best 5 game 3 point shooting stretch in 2015-16")
    assert result.metadata["route"] == "player_stretch_leaderboard"
    top = result.result.to_dict()["sections"]["leaderboard"][0]
    assert top["stretch_metric"] == "fg3_pct"
    assert top["stretch_value"] == pytest.approx(best)
