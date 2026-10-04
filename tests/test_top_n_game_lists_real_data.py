"""Top-N game lists against the real 2015-16 rows: "Stephen Curry top 5 scoring games"."""

from __future__ import annotations

import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_curry_top_five_scoring_games_in_2016_are_his_five_best():
    from nbatools.query_service import execute_natural_query

    rows = data_read_csv("raw/player_game_stats/2015-16_regular_season.csv")
    curry = rows[rows["player_name"] == "Stephen Curry"]
    expected = sorted(curry["pts"].astype(int), reverse=True)[:5]

    result = execute_natural_query("Stephen Curry top 5 scoring games in 2016")
    assert result.result_status == "ok", result.result_reason
    games = result.result.to_dict()["sections"]["finder"]
    assert [int(row["pts"]) for row in games] == expected
