"""C1: OR yes/no about a season's last game against the real player rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lebron_30_or_10_assists_in_his_last_game_of_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_player_games_for_seasons(["2023-24"], "Regular Season")
    row = games[games["player_name"] == "LeBron James"].sort_values("game_date").iloc[-1]
    result = execute_natural_query("did LeBron score 30 or 10 assists in his last game in 2023-24")
    rows = result.result.to_dict()["sections"]["finder"]
    assert [str(r["game_date"])[:10] for r in rows] == [str(row["game_date"])[:10]]
    answer = "Yes" if row["pts"] >= 30 or row["ast"] >= 10 else "No"
    assert result.metadata["answer_phrase"].startswith(f"{answer}: LeBron James had")
