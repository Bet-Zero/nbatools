"""C2 streak rankings against the real 1996-97+ game rows.

Companion to ``test_c2_streaks.py`` (fixture). Expected streaks are counted
from the raw game rows of the pinned generation with a plain loop, never from
the code under test.
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]

SEASON = "2023-24"


def _games(kind: str) -> pd.DataFrame:
    frame = data_read_csv(f"raw/{kind}/{SEASON}_regular_season.csv", dtype={"game_id": str})
    frame["game_date"] = pd.to_datetime(frame["game_date"])
    return frame.sort_values(["game_date", "game_id"])


def _longest(flags) -> int:
    longest = current = 0
    for ok in flags:
        current = current + 1 if ok else 0
        longest = max(longest, current)
    return longest


def _streaks(query: str) -> list[dict]:
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]["streak"]


def test_league_30_point_streaks_match_raw_rows():
    games = _games("player_game_stats")
    games["pts"] = pd.to_numeric(games["pts"], errors="coerce")
    longest = {pid: _longest((g["pts"] >= 30).tolist()) for pid, g in games.groupby("player_id")}
    names = games.drop_duplicates("player_id", keep="last").set_index("player_id")["player_name"]
    by_name = {names[pid]: n for pid, n in longest.items()}

    rows = _streaks(f"longest 30 point streak in {SEASON}")
    assert [row["streak_length"] for row in rows] == sorted(longest.values(), reverse=True)[:10]
    for row in rows:
        assert by_name[row["player_name"]] == row["streak_length"], row


def test_league_winning_streaks_match_raw_rows():
    games = _games("team_game_stats")
    longest = {name: _longest((g["wl"] == "W").tolist()) for name, g in games.groupby("team_name")}

    rows = _streaks(f"longest winning streak in {SEASON}")
    assert [row["streak_length"] for row in rows] == sorted(longest.values(), reverse=True)[:10]
    for row in rows:
        assert longest[row["team_name"]] == row["streak_length"], row
