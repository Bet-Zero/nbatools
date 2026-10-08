"""C1: teams by record and opponents played against the real team rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_winning_records_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    records = games.groupby("team_id")["wl"].value_counts().unstack(fill_value=0)
    winning = int((records["W"] > records["L"]).sum())
    at_most = int((records["W"] <= records["L"]).sum())
    result = execute_natural_query("how many teams had a winning record in 2023-24")
    assert result.result.to_dict()["sections"]["count"] == [{"count": winning}]
    result = execute_natural_query("how many teams were .500 or worse in 2023-24")
    assert result.result.to_dict()["sections"]["count"] == [{"count": at_most}]


def test_lakers_opponents_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    expected = games[games["team_abbr"] == "LAL"]["opponent_team_abbr"].nunique()
    result = execute_natural_query("how many teams did the Lakers play in 2023-24")
    assert result.result.to_dict()["sections"]["count"] == [{"count": expected}]
