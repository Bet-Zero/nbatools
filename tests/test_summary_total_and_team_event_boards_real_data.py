"""Totals, team event boards and season-adjacent stats on the published generation.

Companion to ``test_summary_total_and_team_event_boards.py``. Expectations come
from the pinned raw ``player_game_stats``/``team_game_stats`` rows with pandas.
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.data_source import data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]

SEASON = "2024-25"
STATS = ["pts", "reb", "ast", "stl", "blk"]


def _players() -> pd.DataFrame:
    frame = data_read_csv(f"raw/player_game_stats/{SEASON}_regular_season.csv")
    for column in STATS + ["dreb"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.to_dict()


@pytest.mark.parametrize(
    "query,stat",
    [
        (f"Nikola Jokic defensive rebounds {SEASON} total", "dreb"),
        (f"Nikola Jokic total assists in {SEASON}", "ast"),
        (f"Nikola Jokic {SEASON} rebounds per game", "reb"),
    ],
)
def test_player_season_total_and_per_game_use_every_game(query, stat):
    rows = _players()
    mine = rows[rows.player_id.eq(203999)]
    (summary,) = _run(query)["sections"]["summary"]
    assert summary["games"] == len(mine) > 50
    assert summary[f"{stat}_sum"] == mine[stat].sum()


def test_team_season_total():
    teams = data_read_csv(f"raw/team_game_stats/{SEASON}_regular_season.csv")
    den = teams[teams.team_abbr.eq("DEN")]
    (summary,) = _run(f"Nuggets total rebounds {SEASON}")["sections"]["summary"]
    assert summary["games"] == len(den) == 82
    assert summary["reb_sum"] == pd.to_numeric(den.reb).sum()


@pytest.mark.parametrize(
    "query,team",
    [
        (f"most double doubles {SEASON} Nuggets", "DEN"),
        (f"Who led the Celtics in double-doubles in {SEASON}", "BOS"),
        (f"Who led the league in double-doubles in {SEASON}", None),
    ],
)
def test_double_double_boards_keep_the_named_team(query, team):
    rows = _players()
    population = rows[rows.team_abbr.eq(team)] if team else rows
    hits = population[(population[STATS] >= 10).sum(axis=1) >= 2]
    expected = hits.groupby("player_id").size()
    result = _run(query)
    board = result["sections"]["leaderboard"]
    assert result["metadata"].get("team") == team
    assert len(board) == min(10, len(expected))
    assert all(r["double doubles"] == expected[r["player_id"]] for r in board)
    assert [r["double doubles"] for r in board] == sorted(expected.values, reverse=True)[
        : len(board)
    ]
    if team:
        assert {r["team_abbr"] for r in board} == {team}
