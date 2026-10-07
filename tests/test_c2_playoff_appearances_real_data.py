"""C2 playoff appearances against the real game rows.

Companion to ``test_c2_playoff_appearances.py``. Expected values come from
the raw rows of the pinned generation by franchise ``team_id``, never from
the code under test.
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.data_source import data_exists, data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]

SEASONS = [f"{y}-{str(y + 1)[-2:]}" for y in range(1996, 2025)]
SAS, SAC, LAL = 1610612759, 1610612758, 1610612747


def _rows(kind: str, season: str, season_type: str) -> pd.DataFrame:
    path = f"raw/{kind}/{season}_{season_type}.csv"
    if not data_exists(path):
        return pd.DataFrame()
    return data_read_csv(path, dtype={"game_id": str})


def _appeared(team_id: int) -> list[str]:
    out = []
    for season in SEASONS:
        games = _rows("team_game_stats", season, "playoffs")
        if games.empty:
            continue
        games = games[~games["game_id"].str.zfill(10).str.startswith("005")]
        if (pd.to_numeric(games["team_id"]) == team_id).any():
            out.append(season)
    return out


def _runs(appeared: list[str]) -> tuple[int, int]:
    """(longest run of appearances, longest run of misses) over SEASONS."""
    best = worst = hit = miss = 0
    for season in SEASONS:
        if season in appeared:
            hit, miss = hit + 1, 0
        else:
            hit, miss = 0, miss + 1
        best, worst = max(best, hit), max(worst, miss)
    return best, worst


def _query(text: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(text)
    assert result.result_status == "ok", (text, result.result_reason, result.metadata)
    assert result.metadata["route"] == "playoff_appearances"
    return result


def test_lakers_made_the_playoffs_from_2000_to_2025():
    appeared = [s for s in _appeared(LAL) if s >= "2000-01"]
    result = _query("how many times have the Lakers made the playoffs from 2000-01 to 2024-25")
    assert result.result.to_dict()["sections"]["summary"][0]["appearances"] == len(appeared)


def test_spurs_longest_run_is_22_straight():
    best, _ = _runs(_appeared(SAS))
    assert best == 22  # 1997-98 through 2018-19
    result = _query("Spurs consecutive playoff appearances from 1996-97 to 2024-25")
    row = result.result.to_dict()["sections"]["summary"][0]
    assert (row["longest_streak"], row["longest_streak_start"], row["longest_streak_end"]) == (
        22,
        "1997-98",
        "2018-19",
    )
    board = _query("most consecutive playoff appearances").result.to_dict()["sections"]
    assert board["leaderboard"][0]["team_abbr"] == "SAS"


def test_kings_longest_drought():
    _, worst = _runs(_appeared(SAC))
    assert worst == 16  # 2006-07 through 2021-22
    result = _query("Kings playoff drought from 1996-97 to 2024-25")
    row = result.result.to_dict()["sections"]["summary"][0]
    assert row["longest_drought"] == worst


def test_lebron_finals_appearances():
    seasons = set()
    for season in SEASONS:
        players = _rows("player_game_stats", season, "playoffs")
        teams = _rows("team_game_stats", season, "playoffs")
        if players.empty:
            continue
        mine = players[(players["player_name"] == "LeBron James")]
        mine = mine[pd.to_numeric(mine["minutes"], errors="coerce").fillna(0) > 0]
        finals = teams[teams["game_id"].str.zfill(10).str[6:8] == "04"]
        if mine["game_id"].isin(finals["game_id"]).any():
            seasons.add(season)
    assert len(seasons) == 10  # 2007, 2011-2018, 2020

    result = _query("how many finals appearances does LeBron have")
    row = result.result.to_dict()["sections"]["leaderboard"][0]
    assert row["appearances"] == 10


def test_longest_playoff_drought_board_is_led_by_the_kings():
    rows = _query("which team has the longest playoff drought").result.to_dict()["sections"][
        "leaderboard"
    ]
    assert rows[0]["team_abbr"] == "SAC"
    assert rows[0]["longest_drought"] == 16


def test_fewest_playoff_appearances_counts_from_raw_rows():
    played: dict[int, set] = {}
    appeared: dict[int, set] = {}
    for season in SEASONS:
        regular = _rows("team_game_stats", season, "regular_season")
        playoffs = _rows("team_game_stats", season, "playoffs")
        for team_id in pd.to_numeric(regular["team_id"]).unique():
            played.setdefault(int(team_id), set()).add(season)
        if not playoffs.empty:
            playoffs = playoffs[~playoffs["game_id"].str.zfill(10).str.startswith("005")]
            for team_id in pd.to_numeric(playoffs["team_id"]).unique():
                appeared.setdefault(int(team_id), set()).add(season)
    fewest = min(len(appeared.get(team_id, set())) for team_id in played)

    rows = _query("fewest playoff appearances from 1996-97 to 2024-25").result.to_dict()[
        "sections"
    ]["leaderboard"]
    assert rows[0]["appearances"] == fewest
