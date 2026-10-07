"""Count headlines for player wins/losses and single games.

"how many times did LeBron lose in the playoffs" read "LeBron James has
recorded 1 game"; a one-game count read "has had 1 games with 30+ points".
Expected counts come from the fixture CSVs.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _jokic_games() -> pd.DataFrame:
    players = pd.read_csv(RAW / "player_game_stats" / "2025-26_regular_season.csv")
    teams = pd.read_csv(RAW / "team_game_stats" / "2025-26_regular_season.csv")
    jokic = players[players["player_name"].str.contains("Joki")]
    den = teams[teams["team_abbr"] == "DEN"][["game_id", "wl", "plus_minus"]]
    return jokic.drop(columns=["wl", "plus_minus"], errors="ignore").merge(den, on="game_id")


def _phrase(query: str) -> tuple[int, str]:
    result = execute_natural_query(query)
    return result.result.to_dict()["sections"]["count"][0]["count"], result.metadata["count_phrase"]


def test_player_win_count_reads_won():
    wins = int((_jokic_games()["wl"] == "W").sum())
    count, phrase = _phrase("how many games has Jokic won this season")
    assert count == wins
    assert phrase == f"Nikola Jokić has won {wins} games this season."


def test_player_margin_count_names_the_margin():
    games = _jokic_games()
    expected = int(((games["wl"] == "W") & (games["plus_minus"] >= 20)).sum())
    count, phrase = _phrase("how many times did Jokic win by 20")
    assert count == expected
    assert f"has won {expected} games by 20+ points" in phrase


def test_player_playoff_loss_count_reads_lost():
    count, phrase = _phrase("how many times did LeBron lose in the playoffs")
    games = pd.read_csv(RAW / "team_game_stats" / "2025-26_playoffs.csv")
    losses = int(((games["team_abbr"] == "LAL") & (games["wl"] == "L")).sum())
    assert count == losses == 1
    assert phrase == "LeBron James has lost 1 game in the 2025-26 playoffs."


def test_one_game_count_is_singular():
    count, phrase = _phrase("how many times did LeBron lose when scoring 30")
    if count == 1:
        assert "has had 1 game with 30+ points" in phrase
    assert "1 games" not in phrase
