"""Leading named-season population lists preserve scope and all owners."""

import pytest

from nbatools.commands.natural_query import parse_query


@pytest.mark.parametrize(
    ("query", "season", "position", "rookies", "opponent"),
    [
        ("In 1998-99, rookies top 5 scoring performances", "1998-99", None, True, None),
        (
            "During the 2023-24 season, top 3 assist games by guards vs Celtics",
            "2023-24",
            "guards",
            False,
            "BOS",
        ),
        ("For 2023-24, top 3 scoring games by rookie guards", "2023-24", "guards", True, None),
    ],
)
def test_leading_named_season_group_list(query, season, position, rookies, opponent):
    parsed = parse_query(query)
    assert parsed["route"] == "player_game_finder"
    kwargs = parsed["route_kwargs"]
    assert kwargs["season"] == season
    assert kwargs.get("position") == position
    assert bool(kwargs.get("rookies_only")) is rookies
    assert kwargs.get("opponent") == opponent
    assert not kwargs.get("team") and not kwargs.get("player")
    assert not kwargs.get("unsupported_filters")
