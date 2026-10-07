"""Playoff-team opponent clauses against the real game rows.

"when playing teams that made the playoffs" must filter the same opponents as
"vs teams that made the playoffs" (it switched to playoff games).
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


@pytest.mark.parametrize(
    "variant",
    [
        "Lakers record when playing teams that made the playoffs in 2023-24",
        "Lakers record facing teams that made the playoffs in 2023-24",
    ],
)
def test_playing_clause_matches_the_vs_clause(variant):
    from nbatools.query_service import execute_natural_query

    base = execute_natural_query("Lakers record vs teams that made the playoffs in 2023-24")
    other = execute_natural_query(variant)
    assert base.result_status == other.result_status == "ok"
    first = base.result.to_dict()["sections"]["summary"][0]
    second = other.result.to_dict()["sections"]["summary"][0]
    assert (second["wins"], second["losses"]) == (first["wins"], first["losses"])
    assert first["wins"] + first["losses"] < 82


@pytest.mark.parametrize(
    ("query", "outcome"),
    [
        ("how many times did the Lakers beat the Celtics in 2023-24", "W"),
        ("how many times did the Lakers lose to the Celtics in 2023-24", "L"),
    ],
)
def test_beat_and_lose_to_count_the_meetings(query, outcome):
    import pandas as pd

    from nbatools.data_source import data_read_csv
    from nbatools.query_service import execute_natural_query

    games = data_read_csv("raw/team_game_stats/2023-24_regular_season.csv")
    meetings = games[
        (pd.to_numeric(games["team_id"]) == 1610612747)
        & (pd.to_numeric(games["opponent_team_id"]) == 1610612738)
    ]
    result = execute_natural_query(query)
    assert result.result_status == "ok"
    count = result.result.to_dict()["sections"]["count"][0]["count"]
    assert count == int((meetings["wl"] == outcome).sum())
