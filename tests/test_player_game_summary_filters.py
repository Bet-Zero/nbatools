from __future__ import annotations

import pandas as pd
import pytest

import nbatools.commands.player_game_summary as player_game_summary
from nbatools.commands.player_game_summary import _apply_filters

pytestmark = pytest.mark.engine


def test_player_filter_normalizes_accents_spacing_case_and_dash_variants():
    df = pd.DataFrame(
        [
            {
                "game_date": "2026-01-01",
                "player_name": "  NIKOLA JOKIC ",
                "pts": 30,
            },
            {
                "game_date": "2026-01-02",
                "player_name": "Shai Gilgeous\u2011Alexander",
                "pts": 31,
            },
            {
                "game_date": "2026-01-03",
                "player_name": "Stephen Curry",
                "pts": 32,
            },
        ]
    )

    jokic = _apply_filters(df, player="Nikola Jokić")
    sga = _apply_filters(df, player="Shai Gilgeous-Alexander")

    assert jokic["pts"].tolist() == [30]
    assert sga["pts"].tolist() == [31]


def test_special_event_summary_record_uses_filtered_rows(monkeypatch):
    rows = [
        {"game_id": 1, "wl": "W", "pts": 12, "reb": 11, "ast": 10},
        {"game_id": 2, "wl": "L", "pts": 10, "reb": 10, "ast": 10},
        {"game_id": 3, "wl": "W", "pts": 30, "reb": 8, "ast": 9},
        {"game_id": 4, "wl": "W", "pts": 8, "reb": 10, "ast": 10},
    ]
    player_df = pd.DataFrame(
        [
            {
                **row,
                "game_date": f"2026-01-0{row['game_id']}",
                "season": "2025-26",
                "season_type": "Regular Season",
                "player_id": 203999,
                "player_name": "Nikola Jokić",
                "team_id": 1610612743,
                "team_abbr": "DEN",
                "team_name": "Denver Nuggets",
                "opponent_team_id": 1610612744,
                "opponent_team_abbr": "GSW",
                "opponent_team_name": "Golden State Warriors",
                "is_home": 1,
                "is_away": 0,
                "minutes": 35,
                "fgm": 8,
                "fga": 15,
                "fg3m": 1,
                "fg3a": 4,
                "ftm": 3,
                "fta": 4,
                "stl": 0,
                "blk": 0,
                "tov": 3,
                "pf": 2,
                "plus_minus": 5,
            }
            for row in rows
        ]
    )
    team_df = pd.DataFrame(
        [
            {
                "game_id": row["game_id"],
                "team_id": team_id,
                "team_abbr": team_abbr,
                "team_name": team_name,
                "opponent_team_id": opponent_id,
                "opponent_team_abbr": opponent_abbr,
                "season": "2025-26",
                "season_type": "Regular Season",
                "minutes": 240,
                "fgm": 42,
                "fga": 88,
                "fta": 22,
                "tov": 12,
                "reb": 45,
                "wl": (row["wl"] if team_abbr == "DEN" else ("L" if row["wl"] == "W" else "W")),
            }
            for row in rows
            for team_id, team_abbr, team_name, opponent_id, opponent_abbr in [
                (1610612743, "DEN", "Denver Nuggets", 1610612744, "GSW"),
                (1610612744, "GSW", "Golden State Warriors", 1610612743, "DEN"),
            ]
        ]
    )

    monkeypatch.setattr(
        player_game_summary,
        "load_team_games_for_seasons",
        lambda seasons, season_type: team_df,
    )
    monkeypatch.setattr(
        player_game_summary,
        "compute_current_through_for_seasons",
        lambda seasons, season_type: "2026-01-04",
    )

    result = player_game_summary.build_result(
        season="2025-26",
        season_type="Regular Season",
        player="Nikola Jokić",
        team="DEN",
        special_event="triple_double",
        df=player_df,
    )

    summary = result.summary.iloc[0].to_dict()
    game_log = result.game_log.to_dict("records")

    assert summary["games"] == 2
    assert summary["wins"] == 1
    assert summary["losses"] == 1
    assert len(game_log) == 2
    assert [row["game_id"] for row in game_log] == [1, 2]
