"""C1: "Celtics biggest wins in 2023-24" on the real team rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_celtics_biggest_wins_in_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_team_games_for_seasons(["2023-24"], "Regular Season")
    games = games[(games["team_abbr"] == "BOS") & (games["plus_minus"] > 0)]
    rows = execute_natural_query("Celtics 5 biggest wins in 2023-24").result.to_dict()["sections"][
        "finder"
    ]
    assert [r["plus_minus"] for r in rows] == sorted(games["plus_minus"], reverse=True)[:5]
