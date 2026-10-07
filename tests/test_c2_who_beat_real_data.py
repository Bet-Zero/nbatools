"""C2: "which teams beat the Lakers" against the real game rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]

LAKERS = 1610612747


def _record_vs(seasons: list[str]):
    import pandas as pd

    from nbatools.data_source import data_read_csv

    games = pd.concat(
        data_read_csv(f"raw/team_game_stats/{season}_regular_season.csv") for season in seasons
    )
    games = games[pd.to_numeric(games["opponent_team_id"]) == LAKERS]
    games = games.assign(win=games["wl"] == "W", team_id=pd.to_numeric(games["team_id"]))
    grouped = games.groupby("team_id")["win"]
    return {
        int(t): (int(w), int(n - w))
        for t, w, n in zip(grouped.sum().index, grouped.sum(), grouped.size())
    }


def _rows(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok"
    rows = result.result.to_dict()["sections"]["leaderboard"]
    return {int(row["team_id"]): (row["wins"], row["losses"]) for row in rows}


def test_teams_that_beat_the_lakers_in_a_season():
    record = _record_vs(["2023-24"])
    expected = {team: wl for team, wl in record.items() if wl[0] >= 1}
    assert len(expected) > 10
    assert _rows("which teams beat the Lakers in 2023-24") == expected


def test_beaten_the_lakers_the_most_since_2021():
    record = _record_vs(["2021-22", "2022-23", "2023-24", "2024-25"])
    rows = _rows("which teams have beaten the Lakers the most from 2021-22 to 2024-25")
    top = max(wins for wins, _ in record.values())
    first = next(iter(rows.values()))
    assert first[0] == top
    for team, wl in rows.items():
        assert record[team] == wl
