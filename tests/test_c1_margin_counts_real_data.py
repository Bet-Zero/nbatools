"""Win/loss margin counts against the real game rows.

"how many times did the Lakers win by 20" counts every 20+ win (it counted
games won by exactly 20), and "beat the Celtics by 15" keeps the margin
with the opponent (the beat rewrite dropped it).
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]

LAKERS, CELTICS = 1610612747, 1610612738


def _lakers_games(opponent: int | None = None):
    import pandas as pd

    from nbatools.data_source import data_read_csv

    games = data_read_csv("raw/team_game_stats/2023-24_regular_season.csv")
    games = games[pd.to_numeric(games["team_id"]) == LAKERS]
    if opponent is not None:
        games = games[pd.to_numeric(games["opponent_team_id"]) == opponent]
    return games, pd.to_numeric(games["plus_minus"])


def _count(query: str) -> int:
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok"
    return result.result.to_dict()["sections"]["count"][0]["count"]


@pytest.mark.parametrize(
    ("query", "floor", "outcome"),
    [
        ("how many times did the Lakers win by 15 in 2023-24", 15, "W"),
        ("how many times did the Lakers lose by 10 or more in 2023-24", 10, "L"),
    ],
)
def test_margin_count_is_a_floor(query, floor, outcome):
    games, margin = _lakers_games()
    expected = int(((games["wl"] == outcome) & (margin.abs() >= floor)).sum())
    assert expected > 0
    assert _count(query) == expected


def test_beat_opponent_by_margin():
    games, margin = _lakers_games(CELTICS)
    wins = int((games["wl"] == "W").sum())
    expected = int(((games["wl"] == "W") & (margin >= 5)).sum())
    assert (
        _count("how many times did the Lakers beat the Celtics by 5 or more in 2023-24") == expected
    )
    assert expected <= wins


def test_small_bare_margin_is_exact():
    games, margin = _lakers_games()
    expected = int(((games["wl"] == "W") & (margin == 3)).sum())
    assert _count("how many times did the Lakers win by 3 in 2023-24") == expected
