"""B1: games floors on player season leaderboards.

A season total ("most total points") applied the 20-game floor a per-game
average needs, and early in a season, when no player has 20 games, per-game
boards were empty. Totals now need one game; the per-game floor stays 20 but
is at most half of the most games any player has in the sample.
"""

from __future__ import annotations

import pandas as pd

from nbatools.commands.season_leaders import _apply_default_guardrails


def _players(games: list[int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "player_name": [f"P{i}" for i in range(len(games))],
            "games_played": games,
            "pts_per_game": [10.0] * len(games),
            "pts_total": [10.0 * g for g in games],
            "fg_pct": [0.5] * len(games),
            "fga_total": [15 * g for g in games],
        }
    )


def _kept(games: list[int], target: str, **kwargs) -> list[int]:
    out = _apply_default_guardrails(_players(games), target, min_games=1, **kwargs)
    return sorted(out["games_played"].tolist())


def test_a_full_season_keeps_the_twenty_game_floor():
    assert _kept([82, 60, 25, 19, 5], "pts_per_game") == [25, 60, 82]


def test_early_in_a_season_the_floor_is_half_the_leaders_games():
    # Ten games in: the floor is 5, not 20 (which left the board empty).
    assert _kept([10, 9, 6, 5, 4, 1], "pts_per_game") == [5, 6, 9, 10]


def test_a_season_total_needs_no_games_floor():
    assert _kept([82, 19, 5, 1], "pts_total") == [1, 5, 19, 82]


def test_a_stated_minimum_still_applies():
    out = _apply_default_guardrails(_players([10, 9, 6, 5]), "pts_per_game", min_games=8)
    assert sorted(out["games_played"].tolist()) == [9, 10]


def test_multi_season_samples_keep_the_twenty_game_floor():
    assert _kept([240, 150, 21, 19], "pts_per_game", num_seasons=3) == [21, 150, 240]


def test_opponent_and_window_samples_keep_their_three_game_floor():
    # Independent check of #382: a player meets one opponent a few times a
    # season, so half the leader's games (2) would have let a 2-game sample in.
    assert _kept([4, 4, 3, 2], "pts_per_game", opponent_active=True) == [3, 4, 4]
    assert _kept([3, 3, 2, 1], "pts_per_game", date_window_active=True) == [3, 3]


def test_playoff_samples_keep_their_floor():
    assert _kept([6, 5, 3, 2], "pts_per_game", season_type="Playoffs") == [5, 6]


def test_early_season_shooting_boards_scale_their_attempt_floor():
    # Ten games in, the leader has 150 field-goal attempts: the 200-attempt
    # season floor would leave the board empty; it is capped at half (75).
    assert _kept([10, 9, 6, 5, 4], "fg_pct") == [5, 6, 9, 10]


def test_a_full_season_keeps_the_attempt_floor():
    # 82 games x 15 = 1230 attempts for the leader: the 200 floor applies.
    assert _kept([82, 60, 13, 12], "fg_pct") == [60, 82]
