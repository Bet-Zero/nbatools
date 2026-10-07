"""C1: "Lakers losses to the Celtics" / "wins over" against the real team rows."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


@pytest.mark.parametrize(
    ("query", "outcome"),
    [
        ("Lakers losses to the Celtics since 2020", "L"),
        ("Lakers wins over the Celtics since 2020", "W"),
        ("Lakers games beaten by the Celtics since 2020", "L"),
    ],
)
def test_named_team_against_the_other(query, outcome):
    from nbatools.commands._seasons import resolve_seasons
    from nbatools.commands.data_utils import load_team_games_for_seasons
    from nbatools.commands.natural_query import parse_query
    from nbatools.query_service import execute_natural_query

    kwargs = parse_query(query)["route_kwargs"]
    seasons = resolve_seasons(None, kwargs["start_season"], kwargs["end_season"])
    games = load_team_games_for_seasons(seasons, "Regular Season")
    mine = games[
        (games["team_abbr"] == "LAL")
        & (games["opponent_team_abbr"] == "BOS")
        & (games["wl"] == outcome)
    ]
    rows = execute_natural_query(query).result.to_dict()["sections"]["finder"]
    assert len(rows) == len(mine) > 0
