"""C2: "most playoff wins by a player" ranks players by games won.

Fixture: three regular seasons, 2023-24 to 2025-26, plus the 2025-26 playoffs.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query]


@pytest.mark.parametrize(
    ("query", "season_type", "wins", "extra"),
    [
        ("most playoff wins by a player", "Playoffs", True, {}),
        ("which player has the most playoff wins", "Playoffs", True, {}),
        ("players with the most wins", "Regular Season", True, {}),
        ("players with the most losses this season", "Regular Season", False, {}),
        ("players with the most road wins", "Regular Season", True, {"away_only": True}),
        (
            "most wins in a single season by a player",
            "Regular Season",
            True,
            {"per_season": True, "start_season": "1996-97"},
        ),
        (
            "most playoff wins by a player in the 2020s",
            "Playoffs",
            True,
            {"start_season": "2020-21"},
        ),
    ],
)
def test_player_wins_rank_players(query, season_type, wins, extra):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "season_leaders"
    assert (kwargs["stat"], kwargs["season_type"]) == ("games_played", season_type)
    assert (kwargs["wins_only"], kwargs["losses_only"]) == (wins, not wins)
    for key, value in extra.items():
        assert kwargs[key] == value


@pytest.mark.parametrize(
    "query", ["most wins", "teams with the most wins", "Lakers most wins in a season"]
)
def test_team_wins_stay_team_boards(query):
    assert parse_query(query)["route"] != "season_leaders"


@pytest.mark.fixture_data
def test_player_playoff_wins_answer():
    result = execute_natural_query("most playoff wins by a player")
    assert result.result_status == "ok"
    rows = result.result.to_dict()["sections"]["leaderboard"]
    # Lakers and Nuggets players only; no one can exceed the series' games.
    assert rows and all(0 < row["games_played"] <= 7 for row in rows)
