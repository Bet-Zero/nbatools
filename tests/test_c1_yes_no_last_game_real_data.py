"""C1: "did LeBron score 30 in his last game" against the real rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lebron_last_game_of_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_player_games_for_seasons(["2023-24"], "Regular Season", player="LeBron James")
    games = games[games["player_name"] == "LeBron James"].sort_values("game_date")
    last = games.iloc[-1]
    result = execute_natural_query("did LeBron score 30 points in his last game in 2023-24")
    rows = result.result.to_dict()["sections"]["finder"]
    assert [row["game_id"] for row in rows] == [last["game_id"]]
    assert result.metadata["answer_phrase"].startswith("Yes" if last["pts"] >= 30 else "No")
