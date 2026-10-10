"""C1: a clause about the other team against the real team rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lakers_games_when_the_celtics_scored_110_in_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    other = games[["game_id", "team_abbr", "pts"]].rename(
        columns={"team_abbr": "opp", "pts": "opp_pts"}
    )
    lakers = games[games["team_abbr"] == "LAL"].merge(other, on="game_id")
    lakers = lakers[(lakers["opp"] == "BOS") & (lakers["opp_pts"] >= 110)]
    result = execute_natural_query("Lakers games when the Celtics scored 110 in 2023-24")
    rows = result.result.to_dict()["sections"].get("finder") or []
    assert sorted(str(r["game_date"])[:10] for r in rows) == sorted(
        str(d)[:10] for d in lakers["game_date"]
    )
