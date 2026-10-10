"""C1: "LeBron points when the Celtics scored 100" on the real game rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lebron_points_when_the_celtics_scored_100():
    from nbatools.commands._seasons import latest_served_season
    from nbatools.commands.data_utils import (
        load_player_games_for_seasons,
        load_team_games_for_seasons,
    )
    from nbatools.commands.natural_query import parse_query
    from nbatools.query_service import execute_natural_query

    query = "LeBron points when the Celtics scored 100"
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs.get("team"), kwargs.get("opponent")) == (None, "BOS")

    season = latest_served_season("Regular Season")
    players = load_player_games_for_seasons([season], "Regular Season", player="LeBron James")
    teams = load_team_games_for_seasons([season], "Regular Season")
    celtics = teams[teams["team_abbr"] == "BOS"][["game_id", "pts"]].rename(
        columns={"pts": "bos_pts"}
    )
    games = players[players["player_name"] == "LeBron James"].merge(celtics, on="game_id")
    games = games[(games["opponent_team_abbr"] == "BOS") & (games["bos_pts"] >= 100)]
    sections = execute_natural_query(query).result.to_dict()["sections"]
    if games.empty:
        assert not sections.get("summary")
        return
    summary = sections["summary"][0]
    assert summary["games"] == len(games)
    assert summary["pts_avg"] == pytest.approx(games["pts"].mean(), abs=0.01)
