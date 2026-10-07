"""C2 streak counts against the real game rows.

Companion to ``test_c2_streak_counts.py`` (fixture). Expected counts are taken
from the raw game rows of the pinned generation with a plain loop, never from
the code under test.
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def _games(kind: str, *seasons: str) -> pd.DataFrame:
    frame = pd.concat(
        data_read_csv(f"raw/{kind}/{season}_regular_season.csv", dtype={"game_id": str})
        for season in seasons
    )
    frame["game_date"] = pd.to_datetime(frame["game_date"])
    return frame.sort_values(["game_date", "game_id"])


def _run_lengths(flags) -> list[int]:
    runs, current = [], 0
    for ok in flags:
        if ok:
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return runs


def _count(query: str) -> tuple[int, dict]:
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]["count"][0]["count"], result.metadata


def test_heat_winning_streaks_of_5_in_2012_13():
    heat = _games("team_game_stats", "2012-13")
    heat = heat[heat["team_abbr"] == "MIA"]
    runs = _run_lengths(heat["wl"] == "W")
    assert max(runs) == 27  # the 27-game streak is in the rows

    count, metadata = _count("how many times did the Heat win 5 straight in 2012-13")
    assert metadata["route"] == "team_streak_finder"
    assert count == sum(run >= 5 for run in runs)
    assert "Miami Heat" in metadata["count_phrase"]


def test_curry_streaks_with_a_made_three_since_2015():
    seasons = [f"{year}-{str(year + 1)[-2:]}" for year in range(2015, 2019)]
    games = _games("player_game_stats", *seasons)
    curry = games[games["player_name"] == "Stephen Curry"]
    fg3m = pd.to_numeric(curry["fg3m"], errors="coerce")
    runs = _run_lengths(fg3m >= 1)

    count, metadata = _count(
        "how many times has Curry had 20 straight games with a three from 2015-16 to 2018-19"
    )
    assert metadata["route"] == "player_streak_finder"
    assert count == sum(run >= 20 for run in runs)


def test_teams_with_a_10_game_winning_streak_in_2023_24():
    games = _games("team_game_stats", "2023-24")
    expected = sum(
        max(_run_lengths(team["wl"] == "W"), default=0) >= 10
        for _, team in games.groupby("team_id")
    )
    count, metadata = _count("how many teams had a 10 game winning streak in 2023-24")
    assert metadata["route"] == "team_streak_finder"
    assert count == expected
