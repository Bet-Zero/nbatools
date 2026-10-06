"""C2: road/home win and loss counts, fewest wins, "win %", apostrophe years.

"most road wins this season", "fewest wins in a single season" and "best win
% at home" could not be mapped; "most home losses" ranked win percentage; and
"Lakers record in '16" answered the current season.

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


@pytest.mark.parametrize(
    ("query", "stat", "ascending", "home", "away"),
    [
        ("most road wins this season", "wins", False, False, True),
        ("most home wins this season", "wins", False, True, False),
        ("most home losses this season", "losses", False, True, False),
        ("most losses this season", "losses", False, False, False),
        ("fewest losses since 2010", "losses", True, False, False),
        ("fewest wins in a single season", "wins", True, False, False),
        ("most road wins in a single season", "wins", False, False, True),
        ("best win % at home", "win_pct", False, True, False),
        ("worst road record since 2010", "win_pct", True, False, True),
    ],
)
def test_record_counts_rank_the_count(query, stat, ascending, home, away):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "team_record_leaderboard"
    assert (kwargs["stat"], kwargs["ascending"]) == (stat, ascending)
    assert (kwargs["home_only"], kwargs["away_only"]) == (home, away)
    assert not kwargs["wins_only"] and not kwargs["losses_only"]


@pytest.mark.fixture_data
def test_most_road_wins_counts_road_games():
    games = pd.read_csv(RAW / "team_game_stats" / "2025-26_regular_season.csv")
    road = games[games["is_away"].astype(str).eq("True")]
    wins = road[road["wl"].eq("W")].groupby("team_abbr").size()
    result = execute_natural_query("most road wins in 2025-26")
    assert result.result_status == "ok"
    top = result.result.to_dict()["sections"]["leaderboard"][0]
    assert top["wins"] == wins.max()
    assert top["games_played"] == len(road[road["team_abbr"].eq(top["team_abbr"])])


@pytest.mark.parametrize(
    ("query", "season"),
    [
        ("Lakers record in '16", "2015-16"),
        ("Lakers record in ’16", "2015-16"),
        ("most points in a game in '16", "2015-16"),
        ("most points in a game ever in '16", "2015-16"),
        ("LeBron stats in '15-16", "2015-16"),
        ("who won the title in '98", "1997-98"),
    ],
)
def test_apostrophe_years_name_the_season(query, season):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs["season"], kwargs.get("start_season")) == (season, None)
    assert not kwargs.get("unsupported_filters")


def test_apostrophe_decade():
    kwargs = parse_query("best teams of the '90s")["route_kwargs"]
    assert (kwargs["start_season"], kwargs["end_season"]) == ("1996-97", "1999-00")


def test_possessives_are_not_years():
    assert parse_query("Jokic's 16 points")["normalized_query"] == "jokic's 16 points"


@pytest.mark.parametrize("query", ["Lakers win%", "Lakers win% at home", "best win% this season"])
def test_win_percent_without_a_space_counts_every_game(query):
    assert not parse_query(query)["route_kwargs"].get("wins_only")


@pytest.mark.fixture_data
def test_team_win_percent_is_the_full_record():
    games = pd.read_csv(RAW / "team_game_stats" / "2025-26_regular_season.csv")
    home = games[games["team_abbr"].eq("LAL") & games["is_home"].astype(str).eq("True")]
    result = execute_natural_query("Lakers win% at home")
    row = result.result.to_dict()["sections"]["summary"][0]
    assert (row["games"], row["wins"]) == (len(home), int(home["wl"].eq("W").sum()))


@pytest.mark.parametrize(
    ("query", "ascending"),
    [
        ("fewest losses by decade", True),
        ("least losses in the 2020s", True),
        ("most wins by decade since 2000", False),
        ("teams with at least 50 wins by decade", False),
    ],
)
def test_decade_record_boards_follow_fewest(query, ascending):
    parsed = parse_query(query)
    assert parsed["route"] == "record_by_decade_leaderboard"
    assert parsed["route_kwargs"]["ascending"] is ascending
