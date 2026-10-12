"""C1: "how many Lakers games where the opponent shot under 45 percent" on
real rows (2023-24)."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lakers_opponent_shooting_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    opp = games[["game_id", "team_abbr", "fgm", "fga"]].rename(
        columns={"team_abbr": "opp_abbr", "fgm": "opp_fgm", "fga": "opp_fga"}
    )
    merged = games.merge(opp, on="game_id")
    merged = merged[(merged["team_abbr"] == "LAL") & (merged["opp_abbr"] != "LAL")]
    expected = int((merged["opp_fgm"] / merged["opp_fga"] < 0.45).sum())
    result = execute_natural_query(
        "how many Lakers games where the opponent shot under 45 percent in 2023-24"
    )
    assert result.result.to_dict()["sections"]["count"][0]["count"] == expected
