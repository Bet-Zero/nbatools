"""C1: "how many games was LeBron over 30 points" against the real rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_how_many_games_was_lebron_over_30_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_player_games_for_seasons(["2023-24"], "Regular Season", player="LeBron James")
    games = games[games["player_name"] == "LeBron James"]
    result = execute_natural_query("how many games was LeBron over 30 points in 2023-24")
    assert result.result.to_dict()["sections"]["count"] == [
        {"count": int((games["pts"] > 30).sum())}
    ]
