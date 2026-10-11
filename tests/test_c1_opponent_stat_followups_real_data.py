"""C1: own and opponent bounds together on the real team rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lakers_own_and_opponent_turnover_floors_in_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    other = games[["game_id", "team_abbr", "tov", "ftm"]].rename(
        columns={"team_abbr": "opp", "tov": "opp_tov", "ftm": "opp_ftm"}
    )
    lakers = games[games["team_abbr"] == "LAL"].merge(other, on="game_id")
    lakers = lakers[lakers["opp"] != "LAL"]
    both = lakers[(lakers["tov"] >= 15) & (lakers["opp_tov"] >= 15)]
    sections = execute_natural_query(
        "how many Lakers games had at least 15 turnovers and at least 15 opponent turnovers "
        "in 2023-24"
    ).result.to_dict()["sections"]
    assert sections["count"][0]["count"] == len(both)

    rows = execute_natural_query(
        "Lakers top 5 games by opponent free throws in 2023-24"
    ).result.to_dict()["sections"]["finder"]
    assert [r["opponent_ftm"] for r in rows] == sorted(lakers["opp_ftm"], reverse=True)[:5]
