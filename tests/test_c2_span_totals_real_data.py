"""C2 span totals against the real game rows: "most career points" is LeBron's total."""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.data_source import data_exists, data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_most_career_points_is_the_career_total():
    from nbatools.query_service import execute_natural_query

    total = 0.0
    for year in range(1996, 2026):
        path = f"raw/player_game_stats/{year}-{str(year + 1)[-2:]}_regular_season.csv"
        if not data_exists(path):
            continue
        games = data_read_csv(path)
        lebron = games[pd.to_numeric(games["player_id"], errors="coerce") == 2544]
        total += pd.to_numeric(lebron["pts"], errors="coerce").sum()
    assert total > 40000  # the all-time leader's regular-season total

    result = execute_natural_query("most career points")
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert rows[0]["player_name"] == "LeBron James"
    assert rows[0]["pts_total"] == pytest.approx(total)
