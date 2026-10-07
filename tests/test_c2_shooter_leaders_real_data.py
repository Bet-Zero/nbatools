"""C2: "best three point shooters" against the real player game rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_best_three_point_shooters_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_player_games_for_seasons(["2023-24"], "Regular Season")
    totals = games.groupby("player_id").agg(
        games=("game_id", "nunique"), made=("fg3m", "sum"), tried=("fg3a", "sum")
    )
    # A full season's board: 20 games and 100 three point attempts.
    qualified = totals[(totals["games"] >= 20) & (totals["tried"] >= 100)]
    pct = (qualified["made"] / qualified["tried"]).sort_values(ascending=False)

    result = execute_natural_query("best three point shooters in 2023-24")
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert [row["player_id"] for row in rows[:5]] == [int(i) for i in pct.index[:5]]
    assert rows[0]["fg3_pct"] == pytest.approx(pct.iloc[0])
