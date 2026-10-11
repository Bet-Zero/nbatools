"""C1: "Curry games with 5 3-pointers" on the real player rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_curry_games_with_5_3_pointers_and_10_free_throw_attempts_in_2023_24():
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    games = load_player_games_for_seasons(["2023-24"], "Regular Season", player="Stephen Curry")
    games = games[games["player_name"] == "Stephen Curry"]
    for query, expected in (
        ("how many games did Curry have 5 3-pointers in 2023-24", (games["fg3m"] >= 5).sum()),
        (
            "how many Curry games with 10 three point attempts in 2023-24",
            (games["fg3a"] >= 10).sum(),
        ),
    ):
        sections = execute_natural_query(query).result.to_dict()["sections"]
        assert sections["count"][0]["count"] == int(expected), query
