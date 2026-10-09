"""C1: players by season average against the real player rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_lakers_players_averaging_15_points_in_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_player_games_for_seasons(["2023-24"], "Regular Season")
    games = games[games["team_abbr"] == "LAL"]
    by_player = games.groupby("player_id")["pts"].agg(["mean", "size"])
    result = execute_natural_query("how many Lakers players averaged 15 points in 2023-24")
    rows = result.result.to_dict()["sections"]["count"]
    phrase = result.metadata["count_phrase"]
    # The season board's games floor is named in the answer.
    floor = int(phrase.split("(at least ")[1].split(" games")[0])
    expected = int(((by_player["mean"] >= 15) & (by_player["size"] >= floor)).sum())
    assert rows == [{"count": expected}]
