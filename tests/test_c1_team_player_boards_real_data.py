"""C1: a team's players' boards on the real player rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lakers_30_point_games_and_counts_in_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    rows = load_player_games_for_seasons(["2023-24"], "Regular Season")
    rows = rows[rows["team_abbr"] == "LAL"]
    counts = rows[rows["pts"] >= 30].groupby("player_name").size().sort_values(ascending=False)
    board = execute_natural_query(
        "which Lakers player has the most 30 point games in 2023-24"
    ).result.to_dict()["sections"]["leaderboard"]
    assert board[0]["player_name"] == counts.index[0]
    sections = execute_natural_query(
        "how many 30 point games did Lakers players have in 2023-24"
    ).result.to_dict()["sections"]
    assert sections["count"][0]["count"] == int((rows["pts"] >= 30).sum())
