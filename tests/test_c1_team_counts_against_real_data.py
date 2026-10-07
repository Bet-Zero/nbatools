"""C1: "how many teams beat the Lakers" against the real team rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


@pytest.mark.parametrize(
    ("query", "wl"),
    [
        ("how many teams beat the Lakers in 2023-24", "L"),
        ("how many teams did the Lakers beat in 2023-24", "W"),
    ],
)
def test_team_count_2023_24(query, wl):
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    mine = games[(games["team_abbr"] == "LAL") & (games["wl"] == wl)]
    expected = mine["opponent_team_abbr"].nunique()
    sections = execute_natural_query(query).result.to_dict()["sections"]
    assert sections["count"] == [{"count": expected}]
