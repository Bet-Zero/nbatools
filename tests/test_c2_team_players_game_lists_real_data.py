"""C2: a team's players' game lists, checked on the real player rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lakers_players_best_scoring_games_in_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    rows = load_player_games_for_seasons(["2023-24"], "Regular Season")
    rows = rows[rows["team_abbr"] == "LAL"]
    top = sorted(rows["pts"], reverse=True)[:5]
    listed = execute_natural_query(
        "Lakers players top 5 scoring games in 2023-24"
    ).result.to_dict()["sections"]["finder"]
    assert [row["pts"] for row in listed] == top
    assert {row["team_abbr"] for row in listed} == {"LAL"}


def test_lakers_players_worst_shooting_game_in_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    rows = load_player_games_for_seasons(["2023-24"], "Regular Season")
    rows = rows[(rows["team_abbr"] == "LAL") & (rows["fga"] >= 10)]
    listed = execute_natural_query(
        "Lakers players worst shooting games in 2023-24"
    ).result.to_dict()["sections"]["finder"]
    assert listed[0]["fg_pct"] == pytest.approx(float((rows["fgm"] / rows["fga"]).min()))
    assert all(row["fga"] >= 10 for row in listed)
