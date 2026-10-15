"""Named seasons on real rows: one row per season, gaps left out."""

from __future__ import annotations

import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _split(query: str) -> dict:
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    rows = result.result.to_dict()["sections"]["split_comparison"]
    return {row["bucket"]: row for row in rows}


@pytest.mark.parametrize(
    ("query", "seasons"),
    [
        ("Lakers record 2022-23 vs 2023-24", ["2022-23", "2023-24"]),
        ("Celtics record in 2016 and 2020", ["2015-16", "2019-20"]),
        ("Warriors record in 2016 vs 2017", ["2015-16", "2016-17"]),
    ],
)
def test_team_records_per_season(query, seasons):
    abbr = {"Lakers": "LAL", "Celtics": "BOS", "Warriors": "GSW"}[query.split()[0]]
    rows = _split(query)
    assert sorted(rows) == seasons
    for season in seasons:
        team = data_read_csv(f"data/raw/team_game_stats/{season}_regular_season.csv")
        team = team[team["team_abbr"] == abbr]
        assert (rows[season]["wins"], rows[season]["losses"]) == (
            int((team["wl"] == "W").sum()),
            int((team["wl"] == "L").sum()),
        )


def test_lebron_points_per_season():
    rows = _split("LeBron James points 2015-16 vs 2017-18")
    assert sorted(rows) == ["2015-16", "2017-18"]
    for season, row in rows.items():
        games = data_read_csv(f"data/raw/player_game_stats/{season}_regular_season.csv")
        games = games[games["player_name"] == "LeBron James"]
        assert row["games"] == len(games)
        assert row["pts_avg"] == pytest.approx(games["pts"].mean(), abs=1e-3)
