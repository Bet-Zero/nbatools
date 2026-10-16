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
    from pathlib import Path

    import pandas as pd

    from nbatools.data_source import data_read_csv
    from nbatools.query_service import execute_natural_query
    from tests.shooting_rate_oracle import assert_shooting_rows

    result = execute_natural_query(
        "worst free throw shooting games over 90% from 2022-23 to 2023-24"
    )
    assert result.result_status == "ok"
    listed = result.result.to_dict()["sections"]["finder"]
    rows = pd.concat(
        [
            data_read_csv(Path(f"data/raw/player_game_stats/{season}_regular_season.csv"))
            for season in ("2022-23", "2023-24")
        ],
        ignore_index=True,
    )
    rows = rows[(rows["fta"] >= 5) & (rows["ft_pct"] > 0.9)]
    assert listed and all(row["ft_pct"] > 0.9 and row["fta"] >= 5 for row in listed)
    assert {row["season"] for row in listed} <= {"2022-23", "2023-24"}
    assert_shooting_rows(rows, listed, percentage="ft_pct", made="ftm", attempts="fta")
