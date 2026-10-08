"""C1: ranked stat games with a condition against the real game rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lebron_top_assist_games_with_25_points_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_player_games_for_seasons(["2023-24"], "Regular Season", player="LeBron James")
    games = games[(games["player_name"] == "LeBron James") & (games["pts"] >= 25)]
    rows = execute_natural_query(
        "LeBron top 5 assist games with 25 points in 2023-24"
    ).result.to_dict()["sections"]["finder"]
    assert [row["ast"] for row in rows] == games["ast"].nlargest(5).tolist()


def test_celtics_top_scoring_games_with_20_threes_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    games = games[(games["team_abbr"] == "BOS") & (games["fg3m"] >= 20)]
    rows = execute_natural_query(
        "Celtics top 3 scoring games with 20 threes in 2023-24"
    ).result.to_dict()["sections"]["finder"]
    assert [row["pts"] for row in rows] == games["pts"].nlargest(3).tolist()
