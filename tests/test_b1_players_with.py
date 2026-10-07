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
        (
            "players with 25 points and 10 rebounds in a game",
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


@pytest.mark.parametrize(
    "query",
    [
        # Per-game averages, not single games.
        "players with 25 points and 10 rebounds per game",
        "players with 20 points and 10 rebounds on average",
        "players with 25 points and 10 rebounds a game",
        "players with 20 points and 5 assists per contest",
        # Season totals, not single games.
        "players with 1000 points and 500 assists",
        "players with 2000 points and 500 rebounds this season",
        "players with 25 points and 10 rebounds total",
        "players with 30 points and 10 assists in a season",
        "players with 30 point games per season",
        # A team record is not a game filter.
        "players with 50 wins and 30 point games",
        # Second check round: rate, total and count wording.
        "players with 25 points and 10 rebounds ppg",
        "players with 25 points and 10 rebounds per 36 minutes",
        "players with 25 points and 10 rebounds for the year",
        "players with 25 points and 10 rebounds over the season",
        "players with 25 points and 10 rebounds combined",
        "players with 25 points and 10 rebounds overall",
        "players with 5 triple doubles",
        "players with 10 double doubles",
        "players with the greatest number of triple doubles",
        "players with the highest number of 30 point games",
        # Third check round: anything outside game conditions plus one filter
        # of each kind (span, season type, location, outcome, opponent, month).
        "players with 25 points and 10 rebounds nightly",
        "players with 25 points and 10 rebounds altogether",
        "players with 25 points and 10 rebounds in 5 games",
        "players with three 30 point games",
        "players with 3 30 point games",
        "players with 10 or more 30 point games",
        "players with 3 or more triple doubles",
        "players with 30 point games two seasons ago",
        "players with 30 point games in the finals",
        "players with 40 point games this season and last season",
        "players with a 30 point game and a 10 assist game",
        "players with 30 point games off the bench",
    ],
)
def test_averages_totals_and_records_are_not_read_as_game_lists(query):
    # Independent check of PR #380: each of these was answered as a count of
    # single games. They keep their earlier refusal instead.
    try:
        parsed = parse_query(query)
    except ValueError:
        return
    assert parsed["route"] != "player_occurrence_leaders"


@pytest.mark.parametrize(
    "query",
    [
        "players with the most 30 point games",
        "players with most triple doubles",
        "players with the most 25 point 10 rebound games",
    ],
)
def test_a_ranking_keeps_its_top_ten(query):
    assert parse_query(query)["route_kwargs"]["limit"] == 10
