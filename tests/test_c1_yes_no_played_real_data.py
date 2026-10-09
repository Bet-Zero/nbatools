"""C1: "did LeBron play ..." against a season's real rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lebron_played_in_the_lakers_last_game_of_2023_24():
    from nbatools.commands.data_utils import (
        load_player_games_for_seasons,
        load_team_games_for_seasons,
    )
    from nbatools.query_service import execute_natural_query

    players = load_player_games_for_seasons(["2023-24"], "Regular Season")
    row = players[players["player_name"] == "LeBron James"].sort_values("game_date").iloc[-1]
    teams = load_team_games_for_seasons(["2023-24"], "Regular Season")
    team_last = teams[teams["team_abbr"] == row["team_abbr"]].sort_values("game_date").iloc[-1]
    played = str(row["game_date"])[:10] == str(team_last["game_date"])[:10]
    phrase = execute_natural_query("did LeBron play in his last game in 2023-24").metadata[
        "answer_phrase"
    ]
    assert phrase.startswith(f"{'Yes' if played else 'No'}: LeBron James ")
    assert str(team_last["game_date"])[:10] in phrase
