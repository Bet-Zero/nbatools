"""C1: games a player missed.

"how many games has LeBron missed" counted the games he played (60). It is
his team's games he did not play; on the fixture every player played every
game, so the counts are 0 and the phrase says so.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


@pytest.mark.parametrize(
    ("query", "team", "player"),
    [
        ("how many games has LeBron missed this season", "LAL", "LeBron James"),
        ("how many games did Tatum miss in 2024-25", "BOS", "Jayson Tatum"),
        ("games LeBron missed", "LAL", "LeBron James"),
        ("how many home games did LeBron miss", "LAL", "LeBron James"),
    ],
)
def test_missed_games_are_team_games_without_him(query, team, player):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "game_finder"
    assert (kwargs["team"], kwargs["without_player"]) == (team, player)
    result = execute_natural_query(query)
    assert result.result.to_dict()["sections"]["count"][0]["count"] == 0
    assert result.metadata["answer_phrase"].startswith(f"{player} did not miss a")


@pytest.mark.parametrize(
    "query",
    [
        "LeBron missed shots",
        "did LeBron miss the playoffs",
        "LeBron missed free throws",
        # Another player's games, missed stats, records and streaks.
        "Reaves points in games LeBron missed",
        "LeBron stats in games Davis missed",
        "how many free throws did LeBron miss in home games",
        "how many shots did LeBron miss per game",
        "games LeBron missed more than 10 shots",
        "how many games did the Lakers win when LeBron missed",
        "Lakers record in games LeBron missed",
        "how many consecutive games has LeBron missed",
    ],
)
def test_other_misses_are_not_missed_games(query):
    try:
        parsed = parse_query(query)
    except ValueError:
        return
    assert not any(str(n).startswith("missed_games:") for n in parsed.get("notes") or [])


@pytest.mark.parametrize(
    "query",
    [
        "how many games did LeBron miss in the 2024-25 season",
        "how many games did LeBron miss from 2023-24 to 2025-26",
        "how many games did LeBron miss over the last 3 seasons",
        "number of games LeBron James missed this season",
        "LeBron games missed",
    ],
)
def test_season_wordings_are_missed_games(query):
    parsed = parse_query(query)
    assert any(str(n).startswith("missed_games:") for n in parsed.get("notes") or [])


def test_two_named_seasons_refuse():
    result = execute_natural_query("how many games did LeBron miss in 2024-25 and 2025-26")
    assert result.result_status == "no_result"
