"""B1: "players with <game condition>" lists every player who had such a game.

"players with 25 points and 10 rebounds" refused as a compound request,
"players with 30 point games" was unrouted. Both now answer with each player
who had a qualifying game, most often first, with no top-10 cut. A bare
"players with 30 points" (a game or a season total) still does not route.

Expected counts come from the raw fixture player game rows, not the engine.
Fixture: three regular seasons, 2023-24 to 2025-26.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

_RAW = Path("qa/fixtures/query_engine_sample/data/raw/player_game_stats")


def _games() -> pd.DataFrame:
    return pd.concat(
        pd.read_csv(path).assign(season=path.name[:7])
        for path in sorted(_RAW.glob("*_regular_season.csv"))
    )


def _expected(mask) -> list[tuple[str, int]]:
    games = _games()
    counts = games[mask(games)].groupby("player_name").size()
    return sorted((name, int(n)) for name, n in counts.items())


def _answered(query: str) -> list[tuple[str, int]]:
    executed = execute_natural_query(query)
    assert executed.result_status == "ok"
    assert executed.route == "player_occurrence_leaders"
    rows = executed.to_dict()["sections"]["leaderboard"]
    column = next(c for c in rows[0] if c.startswith("games_") and c != "games_played")
    counts = [row[column] for row in rows]
    assert counts == sorted(counts, reverse=True)
    return sorted((row["player_name"], int(row[column])) for row in rows)


@pytest.mark.fixture_data
@pytest.mark.parametrize(
    ("query", "mask"),
    [
        (
            "players with 25 points and 10 rebounds",
            lambda g: (g.season == "2025-26") & (g.pts >= 25) & (g.reb >= 10),
        ),
        (
            "players with a 25 point 10 rebound game",
            lambda g: (g.season == "2025-26") & (g.pts >= 25) & (g.reb >= 10),
        ),
        ("players with 30 point games", lambda g: (g.season == "2025-26") & (g.pts >= 30)),
        (
            "players with 30 point games at home",
            lambda g: (g.season == "2025-26") & (g.pts >= 30) & (g.is_home == 1),
        ),
        (
            "players with 10 assists and 0 turnovers since 2024",
            lambda g: (g.season >= "2024-25") & (g.ast >= 10) & (g.tov <= 0),
        ),
        (
            "players with a 40 point game since 2024",
            lambda g: (g.season >= "2024-25") & (g.pts >= 40),
        ),
    ],
)
def test_players_with_lists_every_qualifying_player(query, mask):
    assert _answered(query) == _expected(mask)


@pytest.mark.fixture_data
def test_players_with_a_triple_double_lists_each_player():
    rows = execute_natural_query("players with a triple double").to_dict()["sections"][
        "leaderboard"
    ]
    assert rows


def test_a_stated_top_n_still_limits_the_list():
    assert parse_query("top 5 players with 30 point games")["route_kwargs"]["limit"] == 5


@pytest.mark.parametrize(
    "query",
    ["most 30 point games", "most 25 point 10 rebound games", "which players had 30 points"],
)
def test_other_phrasings_keep_their_routes(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs.get("limit") is not None or "limit" not in kwargs


def test_a_bare_stat_bound_is_not_read_as_games():
    # "players with 30 points" may mean a game or a season total; it is not
    # silently read as either.
    with pytest.raises(ValueError):
        parse_query("players with 30 points")
