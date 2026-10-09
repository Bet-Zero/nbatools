"""C1: ranked game lists keep their direction and condition on real rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _rows(query: str) -> list[dict]:
    from nbatools.query_service import execute_natural_query

    return execute_natural_query(query).result.to_dict()["sections"]["finder"]


def test_lebron_lowest_3_scoring_games_in_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons

    games = load_player_games_for_seasons(["2023-24"], "Regular Season")
    games = games[games["player_name"] == "LeBron James"]
    rows = _rows("LeBron lowest 3 scoring games in 2023-24")
    assert [r["pts"] for r in rows] == games["pts"].nsmallest(3).tolist()


def test_celtics_top_scoring_games_where_they_made_20_threes_in_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    games = games[(games["team_abbr"] == "BOS") & (games["fg3m"] >= 20)]
    rows = _rows("Celtics top 3 scoring games where they made 20 threes in 2023-24")
    assert [r["pts"] for r in rows] == games["pts"].nlargest(3).tolist()
