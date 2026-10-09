"""C1: a player's last qualifying game against the real player rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lebron_last_30_point_game_in_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_player_games_for_seasons(["2023-24"], "Regular Season")
    games = games[(games["player_name"] == "LeBron James") & (games["pts"] >= 30)]
    expected = str(games.sort_values("game_date")["game_date"].iloc[-1])[:10]
    result = execute_natural_query("LeBron's last 30 point game in 2023-24")
    rows = result.result.to_dict()["sections"]["finder"]
    assert [str(r["game_date"])[:10] for r in rows] == [expected]
