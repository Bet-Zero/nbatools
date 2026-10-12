"""C2: league single-game lists in new wordings, checked on the real game rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_worst_free_throw_games_in_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    rows = load_player_games_for_seasons(["2023-24"], "Regular Season")
    rows = rows[rows["fta"] >= 5]
    worst = rows["ftm"] / rows["fta"]
    data = execute_natural_query("worst free throw shooting games in 2023-24").result.to_dict()
    listed = data["sections"]["finder"]
    assert len(listed) == 10
    assert all(row["fta"] >= 5 for row in listed)
    rates = [row["ft_pct"] for row in listed]
    assert rates == sorted(rates)
    assert rates[0] == pytest.approx(float(worst.min()))


def test_best_team_shooting_games_in_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    rows = load_team_games_for_seasons(["2023-24"], "Regular Season")
    best = (rows["fgm"] / rows["fga"]).max()
    listed = execute_natural_query("best shooting games by a team in 2023-24").result.to_dict()[
        "sections"
    ]["finder"]
    rates = [row["fg_pct"] for row in listed]
    assert rates == sorted(rates, reverse=True)
    assert rates[0] == pytest.approx(float(best), abs=1e-3)
    assert all("player_name" not in row for row in listed)
