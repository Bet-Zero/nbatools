"""C1: team games ranked by the opponent's number on the real team rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lakers_games_with_the_most_opponent_turnovers_in_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    other = games[["game_id", "team_abbr", "tov"]].rename(
        columns={"team_abbr": "opp", "tov": "opp_tov"}
    )
    lakers = games[games["team_abbr"] == "LAL"].merge(other, on="game_id")
    lakers = lakers[lakers["opp"] != "LAL"]
    rows = execute_natural_query(
        "Lakers top 5 games by opponent turnovers in 2023-24"
    ).result.to_dict()["sections"]["finder"]
    assert [r["opponent_tov"] for r in rows] == sorted(lakers["opp_tov"], reverse=True)[:5]
