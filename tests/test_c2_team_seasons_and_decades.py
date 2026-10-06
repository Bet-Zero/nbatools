"""C2: a team's own best seasons, shooting seasons, decade order, low team games.

"Lakers best scoring season" listed the Lakers' top games this season,
"LeBron best three point shooting season" ranked points, "worst record by
decade" ranked wins from the top, "fewest playoff wins by decade" could not
be mapped, "LeBron and Curry best scoring season" ranked LeBron only, and
"lowest scoring team games" ranked team season averages.

Fixture: three regular seasons, 2023-24 to 2025-26, and the 2025-26
Lakers-Nuggets first round.
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


def _leaders(query: str) -> list[dict]:
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.result.notes)
    return result.result.to_dict()["sections"]["leaderboard"]


@pytest.mark.parametrize(
    ("query", "route", "stat", "ascending", "start"),
    [
        ("Lakers best scoring season", "season_team_leaders", "pts", False, "1996-97"),
        ("Lakers most points in a single season", "season_team_leaders", "pts", False, "1996-97"),
        ("Lakers most threes in a single season", "season_team_leaders", "fg3m", False, "1996-97"),
        ("Lakers best 3 point shooting season", "season_team_leaders", "fg3_pct", False, "1996-97"),
        (
            "Lakers best record in a single season",
            "team_record_leaderboard",
            "win_pct",
            False,
            "1996-97",
        ),
        ("Lakers best season", "team_record_leaderboard", "win_pct", False, "1996-97"),
        ("Lakers worst season since 2000", "team_record_leaderboard", "win_pct", True, "2000-01"),
        ("Lakers most wins in a season", "team_record_leaderboard", "wins", False, "1996-97"),
    ],
)
def test_team_best_seasons_rank_that_teams_seasons(query, route, stat, ascending, start):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == route
    assert (kwargs["team"], kwargs["stat"], kwargs["ascending"]) == ("LAL", stat, ascending)
    assert (kwargs["start_season"], kwargs["per_season"]) == (start, True)


@pytest.mark.parametrize(
    "query",
    [
        "Lakers best season vs Celtics",
        "Lakers best season in 2016",
        "Lakers best games this season",
        "Lakers record this season",
    ],
)
def test_team_season_questions_that_stay(query):
    assert parse_query(query)["route_kwargs"].get("per_season") is not True


@pytest.mark.fixture_data
def test_team_best_record_seasons_are_that_teams_records():
    frames = [
        pd.read_csv(RAW / "team_game_stats" / f"{season}_regular_season.csv") for season in SEASONS
    ]
    games = pd.concat(frames)
    lakers = games[games["team_abbr"].eq("LAL")]
    wins = lakers[lakers["wl"].eq("W")].groupby("season").size()
    leaders = _leaders("Lakers best season")
    assert {row["team_abbr"] for row in leaders} == {"LAL"}
    assert len(leaders) == len(SEASONS)
    assert leaders[0]["season"] == wins.idxmax()
    assert leaders[0]["wins"] == wins.max()


@pytest.mark.parametrize(
    ("query", "player", "stat"),
    [
        ("LeBron best three point shooting season", "LeBron James", "fg3_pct"),
        ("Curry best 3 point percentage season", "Stephen Curry", "fg3_pct"),
        ("Curry best shooting season", "Stephen Curry", "fg_pct"),
        ("LeBron best free throw shooting season", "LeBron James", "ft_pct"),
    ],
)
def test_player_shooting_seasons_rank_the_rate(query, player, stat):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "season_leaders"
    assert (kwargs["player"], kwargs["stat"], kwargs["per_season"]) == (player, stat, True)


def test_two_players_best_seasons_rank_both():
    kwargs = parse_query("LeBron and Curry best scoring season")["route_kwargs"]
    assert kwargs["player"] == ["LeBron James", "Stephen Curry"]


@pytest.mark.fixture_data
def test_two_players_best_seasons_list_only_those_players():
    leaders = _leaders("LeBron and Curry best scoring season")
    assert {row["player_name"] for row in leaders} == {"LeBron James", "Stephen Curry"}
    assert len(leaders) == 2 * len(SEASONS)


@pytest.mark.parametrize(
    ("query", "stat", "ascending", "season_type"),
    [
        ("worst record by decade", "win_pct", True, "Regular Season"),
        ("lowest win% by decade", "win_pct", True, "Regular Season"),
        ("best record by decade", "win_pct", False, "Regular Season"),
        ("most wins by decade since 2000", "wins", False, "Regular Season"),
        ("winningest team of the 2010s", "wins", False, "Regular Season"),
        ("fewest losses by decade", "losses", True, "Regular Season"),
        ("teams with at least 50 wins by decade", "wins", False, "Regular Season"),
        ("fewest playoff wins by decade", "wins", True, "Playoffs"),
    ],
)
def test_decade_boards_rank_what_is_asked(query, stat, ascending, season_type):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "record_by_decade_leaderboard"
    assert (kwargs["stat"], kwargs["ascending"], kwargs["season_type"]) == (
        stat,
        ascending,
        season_type,
    )


@pytest.mark.parametrize(
    ("query", "stat", "season_type"),
    [
        ("most playoff wins this season", "wins", "Playoffs"),
        ("most playoff wins since 2000", "wins", "Playoffs"),
        ("fewest playoff losses since 2010", "losses", "Playoffs"),
    ],
)
def test_playoff_win_counts_are_record_boards(query, stat, season_type):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "team_record_leaderboard"
    assert (kwargs["stat"], kwargs["season_type"]) == (stat, season_type)


@pytest.mark.fixture_data
def test_lowest_scoring_team_games_are_single_games():
    frames = [
        pd.read_csv(RAW / "team_game_stats" / f"{season}_regular_season.csv") for season in SEASONS
    ]
    parsed = parse_query("lowest scoring team games since 2023")
    assert parsed["route"] == "top_team_games"
    leaders = _leaders("lowest scoring team games since 2023")
    assert leaders[0]["pts"] == pd.concat(frames)["pts"].min()


@pytest.mark.parametrize(
    "query",
    [
        "Lakers best scoring season by a player",
        "best scoring season by a Lakers player",
        "Lakers player with the best scoring season",
        "Lakers best individual scoring season",
        "who had the best season for the Lakers",
        "Lakers most points allowed in a season",
    ],
)
def test_player_and_allowed_questions_are_not_team_seasons(query):
    assert parse_query(query)["route_kwargs"].get("per_season") is not True


@pytest.mark.parametrize(
    ("query", "season_type", "limit"),
    [
        ("Lakers best playoff season", "Playoffs", 10),
        ("Lakers best regular season", "Regular Season", 10),
        ("Lakers top 3 seasons", "Regular Season", 3),
        ("Lakers best winning season", "Regular Season", 10),
    ],
)
def test_team_season_wording_variants(query, season_type, limit):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "team_record_leaderboard"
    assert (kwargs["team"], kwargs["season_type"], kwargs["limit"]) == ("LAL", season_type, limit)


def test_effective_field_goal_shooting_season():
    kwargs = parse_query("LeBron best effective field goal shooting season")["route_kwargs"]
    assert (kwargs["stat"], kwargs["per_season"]) == ("efg_pct", True)


@pytest.mark.fixture_data
@pytest.mark.parametrize(
    "query", ["most playoff wins since 2000", "fewest playoff wins since 2023"]
)
def test_playoff_win_counts_over_a_span_keep_every_playoff_team(query):
    leaders = _leaders(query)
    assert {row["team_abbr"] for row in leaders} == {"LAL", "DEN"}
