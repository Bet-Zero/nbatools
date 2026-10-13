"""C2: named-team and season-span game lists, checked on the real game rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lakers_worst_shooting_game_in_2023_24():
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.query_service import execute_natural_query

    rows = load_team_games_for_seasons(["2023-24"], "Regular Season")
    rows = rows[rows["team_abbr"] == "LAL"]
    worst = (rows["fgm"] / rows["fga"]).min()
    listed = execute_natural_query("Lakers worst shooting games in 2023-24").result.to_dict()[
        "sections"
    ]["finder"]
    assert len(listed) == 10
    assert {row["team_abbr"] for row in listed} == {"LAL"}
    rates = [row["fg_pct"] for row in listed]
    assert rates == sorted(rates)
    assert rates[0] == pytest.approx(float(worst), abs=1e-3)


def test_best_free_throw_games_over_90_percent_over_two_seasons():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    listed = execute_natural_query(
        "worst free throw shooting games over 90% from 2022-23 to 2023-24"
    ).result.to_dict()["sections"]["finder"]
    rows = load_player_games_for_seasons(["2022-23", "2023-24"], "Regular Season")
    rows = rows[rows["fta"] >= 5]
    rates = rows["ftm"] / rows["fta"]
    assert listed and all(row["ft_pct"] > 0.9 and row["fta"] >= 5 for row in listed)
    assert {row["season"] for row in listed} <= {"2022-23", "2023-24"}
    assert listed[0]["ft_pct"] == pytest.approx(float(rates[rates > 0.9].min()))
