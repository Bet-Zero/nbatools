"""C2: "from 2019" and an owner after an opponent, checked on the real player rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_best_scoring_games_from_2019_are_the_2018_19_games():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    rows = load_player_games_for_seasons(["2018-19"], "Regular Season")
    top = sorted(rows["pts"], reverse=True)[:10]
    listed = execute_natural_query("best scoring games from 2019").result.to_dict()["sections"][
        "leaderboard"
    ]
    assert [row["pts"] for row in listed] == top
    assert {row["season"] for row in listed} == {"2018-19"}


def test_lakers_players_best_scoring_games_vs_the_celtics_in_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    rows = load_player_games_for_seasons(["2023-24"], "Regular Season")
    rows = rows[(rows["team_abbr"] == "LAL") & (rows["opponent_team_abbr"] == "BOS")]
    top = sorted(rows["pts"], reverse=True)[:5]
    listed = execute_natural_query(
        "top 5 scoring games vs the Celtics by Lakers players in 2023-24"
    ).result.to_dict()["sections"]["finder"]
    assert [row["pts"] for row in listed] == top
    assert {row["team_abbr"] for row in listed} == {"LAL"}
    assert {row["opponent_team_abbr"] for row in listed} == {"BOS"}
