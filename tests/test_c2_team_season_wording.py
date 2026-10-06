"""C2: more ways to ask for a team's best seasons.

"Lakers top 3 seasons by wins" listed Lakers wins this season, "Lakers best
season with the most wins" read "the most wins" as a teammate, "best scoring
season by points per game" read "game" as a single game, "Lakers best offensive
rating season" ranked every team, "Celtics best defensive seasons" had no stat,
and "who won the most games in a season" could not be mapped.

Fixture: three regular seasons, 2023-24 to 2025-26.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")
SEASONS = ("2023-24", "2024-25", "2025-26")


@pytest.mark.parametrize(
    ("query", "route", "stat", "ascending", "limit"),
    [
        ("Lakers top 3 seasons by wins", "team_record_leaderboard", "wins", False, 3),
        ("Lakers best season with the most wins", "team_record_leaderboard", "wins", False, 10),
        ("Lakers seasons ranked by wins", "team_record_leaderboard", "wins", False, 10),
        ("Lakers best season by win %", "team_record_leaderboard", "win_pct", False, 10),
        (
            "Lakers best scoring season by points per game",
            "season_team_leaders",
            "pts",
            False,
            10,
        ),
        ("Lakers best offensive rating season", "season_team_leaders", "off_rating", False, 10),
        ("Celtics best defensive seasons", "season_team_leaders", "def_rating", True, 10),
        ("Celtics worst defensive season", "season_team_leaders", "def_rating", False, 10),
    ],
)
def test_team_season_wording_ranks_that_teams_seasons(query, route, stat, ascending, limit):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == route
    assert (kwargs["stat"], kwargs["ascending"], kwargs["limit"]) == (stat, ascending, limit)
    assert kwargs["per_season"] is True
    assert kwargs["team"] in ("LAL", "BOS")
    assert not kwargs.get("wins_only")


def test_player_season_by_points_per_game():
    kwargs = parse_query("LeBron best season by points per game")["route_kwargs"]
    assert (kwargs["player"], kwargs["stat"], kwargs["per_season"]) == ("LeBron James", "pts", True)


@pytest.mark.parametrize(
    ("query", "stat", "start"),
    [
        ("who won the most games in a season", "wins", "1996-97"),
        ("which team won the most games in a season", "wins", "1996-97"),
        ("which team lost the most games in a single season since 2010", "losses", "2010-11"),
    ],
)
def test_won_the_most_games_in_a_season_is_most_wins(query, stat, start):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "team_record_leaderboard"
    assert (kwargs["stat"], kwargs["start_season"], kwargs["per_season"]) == (stat, start, True)


@pytest.mark.parametrize(
    "query",
    ["Lakers record with LeBron", "Lakers record without LeBron"],
)
def test_real_availability_players_still_resolve(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert "unresolved_player_availability" not in (kwargs.get("unsupported_filters") or [])


def test_team_record_by_wins_is_not_a_season_list():
    parsed = parse_query("Lakers record by wins")
    assert parsed["route"] == "team_record"


def _team_seasons() -> pd.DataFrame:
    frames = [
        pd.read_csv(RAW / "team_game_stats" / f"{season}_regular_season.csv").assign(season=season)
        for season in SEASONS
    ]
    return pd.concat(frames)


def _leaders(query: str) -> list[dict]:
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    return result.result.to_dict()["sections"]["leaderboard"]


@pytest.mark.fixture_data
def test_lakers_seasons_by_wins_match_the_games():
    games = _team_seasons()
    lal = games[games["team_abbr"].eq("LAL")]
    wins = lal.groupby("season")["wl"].apply(lambda s: int(s.eq("W").sum()))
    leaders = _leaders("Lakers top 2 seasons by wins since 2023")
    assert len(leaders) == 2
    assert [row["wins"] for row in leaders] == sorted(wins, reverse=True)[:2]
    assert {row["team_abbr"] for row in leaders} == {"LAL"}


@pytest.mark.fixture_data
def test_most_wins_in_a_season_across_teams():
    games = _team_seasons()
    wins = games[games["wl"].eq("W")].groupby(["season", "team_abbr"]).size()
    leaders = _leaders("which team won the most games in a season since 2023")
    assert leaders[0]["wins"] == wins.max()
    assert (leaders[0]["season"], leaders[0]["team_abbr"]) == wins.idxmax()


@pytest.mark.fixture_data
def test_best_defensive_seasons_are_lowest_rating_first():
    leaders = _leaders("Celtics best defensive seasons since 2023")
    ratings = [row["def_rating"] for row in leaders]
    assert ratings == sorted(ratings)
    assert {row["team_abbr"] for row in leaders} == {"BOS"}
    assert len({row["season"] for row in leaders}) == len(leaders) == 3


@pytest.mark.fixture_data
def test_offensive_rating_seasons_keep_the_team():
    leaders = _leaders("Lakers best offensive rating season since 2023")
    ratings = [row["off_rating"] for row in leaders]
    assert ratings == sorted(ratings, reverse=True)
    assert {row["team_abbr"] for row in leaders} == {"LAL"}
