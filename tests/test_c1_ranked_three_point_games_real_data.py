"""C1: "Curry top 3 three point games" on real rows (2023-24)."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_curry_top_three_point_games_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    rows = load_player_games_for_seasons(["2023-24"], "Regular Season", player="Stephen Curry")
    rows = rows[rows["player_name"] == "Stephen Curry"]
    expected = rows["fg3m"].nlargest(3).tolist()
    result = execute_natural_query("Curry top 3 three point games in 2023-24")
    got = [r["fg3m"] for r in result.result.to_dict()["sections"]["finder"]]
    assert got == expected
