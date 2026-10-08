"""C1: teams by season win total against the real team rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_teams_with_50_wins_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    wins = games[games["wl"] == "W"].groupby("team_id").size()
    expected = int((wins >= 50).sum())
    result = execute_natural_query("how many teams had 50 wins in 2023-24")
    assert result.result.to_dict()["sections"]["count"] == [{"count": expected}]
