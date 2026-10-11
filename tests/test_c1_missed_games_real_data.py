"""C1: "how many games did Anthony Davis miss in 2023-24" on real rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_davis_missed_games_in_2023_24():
    from nbatools.commands.data_utils import (
        load_player_games_for_seasons,
        load_team_games_for_seasons,
    )
    from nbatools.query_service import execute_natural_query

    team = load_team_games_for_seasons(["2023-24"], "Regular Season")
    team = team[team["team_abbr"] == "LAL"]
    played = load_player_games_for_seasons(["2023-24"], "Regular Season", player="Anthony Davis")
    played = played[played["player_name"] == "Anthony Davis"]
    expected = len(set(team["game_id"]) - set(played["game_id"]))
    result = execute_natural_query("how many games did Anthony Davis miss in 2023-24")
    assert result.result.to_dict()["sections"]["count"][0]["count"] == expected
    assert "missed" in result.metadata["answer_phrase"] or expected == 0
