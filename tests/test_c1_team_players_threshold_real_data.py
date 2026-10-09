"""C1: a team's players' games against the real player rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_how_many_lakers_players_scored_30_in_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_player_games_for_seasons(["2023-24"], "Regular Season")
    games = games[(games["team_abbr"] == "LAL") & (games["pts"] >= 30)]
    result = execute_natural_query("how many Lakers players scored 30 in 2023-24")
    assert result.result.to_dict()["sections"]["count"] == [
        {"count": int(games["player_id"].nunique())}
    ]
