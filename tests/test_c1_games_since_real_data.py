"""C1: games since a player's last qualifying game against the real rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_games_since_lebrons_last_30_point_game_of_2023_24():
    from nbatools.commands._seasons import default_end_season, resolve_seasons
    from nbatools.commands.data_utils import load_player_games_for_seasons
    from nbatools.query_service import execute_natural_query

    seasons = resolve_seasons(None, "2023-24", default_end_season("Regular Season"))
    games = load_player_games_for_seasons(seasons, "Regular Season")
    games = games[games["player_name"] == "LeBron James"]
    in_season = games[(games["season"] == "2023-24") & (games["pts"] >= 30)]
    last = in_season["game_date"].max()
    since = int((games["game_date"] > last).sum())
    phrase = execute_natural_query(
        "how many games since LeBron's last 30 point game in 2023-24"
    ).metadata["answer_phrase"]
    assert f"has played {since} game" in phrase
    assert str(last)[:10] in phrase
