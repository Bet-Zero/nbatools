"""C1: an OR game list against the real player rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lebron_30_points_or_10_assists_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_player_games_for_seasons(["2023-24"], "Regular Season", player="LeBron James")
    games = games[games["player_name"] == "LeBron James"]
    either = games[(games["pts"] >= 30) | (games["ast"] >= 10)]
    rows = execute_natural_query("LeBron 30 points or 10 assists in 2023-24").result.to_dict()
    assert sorted(r["game_id"] for r in rows["sections"]["finder"]) == sorted(either["game_id"])
