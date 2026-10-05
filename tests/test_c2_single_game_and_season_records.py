"""C2: single-game lists in series situations, team single games, best single seasons.

"most points in an elimination game" ranked season totals in elimination games,
"most threes in a game by a team" ranked player games, "fewest points by a team
in a game" listed the most, "most points in a single season since 2000" summed
every season together, and "Celtics vs Heat in the eastern conference finals"
compared whole postseasons.

Fixture: the 2025-26 Lakers-Nuggets first round, Lakers W W W L W; games 4 and
5 (ids 544, 545) are Nuggets elimination games. Three regular seasons, 2023-24
to 2025-26.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.commands.season_leaders import build_result as season_leaders
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")
SEASONS = ("2023-24", "2024-25", "2025-26")


def _ok(query: str):
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.result.notes)
    return result.result.to_dict()


@pytest.mark.parametrize(
    ("query", "situation", "stat"),
    [
        ("most points in an elimination game", "elimination", "pts"),
        ("most points in a closeout game", "closeout", "pts"),
        ("most rebounds in a single elimination game", "elimination", "reb"),
        ("most points in a deciding game since 2010", "deciding", "pts"),
    ],
)
def test_single_game_in_a_series_situation(query, situation, stat):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "top_player_games"
    assert (kwargs["series_situation"], kwargs["stat"]) == (situation, stat)


@pytest.mark.parametrize(
    ("query", "stat", "ascending"),
    [
        ("most threes in a game by a team", "fg3m", False),
        ("most assists by a team in a single game", "ast", False),
        ("fewest points by a team in a game since 2000", "pts", True),
        ("most points by a team in a game", "pts", False),
    ],
)
def test_team_single_game_lists(query, stat, ascending):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "top_team_games"
    assert (kwargs["stat"], kwargs["ascending"]) == (stat, ascending)


@pytest.mark.parametrize(
    "query",
    [
        "Celtics vs Heat in the eastern conference finals",
        "Celtics vs Heat in the 2012 eastern conference finals",
    ],
)
def test_comparison_that_cannot_take_the_round_refuses(query):
    parsed = parse_query(query)
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == ["playoff_round"]


@pytest.mark.parametrize(
    "query",
    ["Lakers and Celtics record in the finals", "Lakers and Celtics record in the 2010 finals"],
)
def test_two_team_round_record_is_their_series_history(query):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "playoff_matchup_history"
    assert (kwargs["team_a"], kwargs["team_b"], kwargs["playoff_round"]) == ("LAL", "BOS", "04")


@pytest.mark.parametrize(
    ("query", "start"),
    [
        ("most points in a single season", "1996-97"),
        ("most points in a season since 2000", "2000-01"),
        ("most points in a season ever", "1996-97"),
        ("best fg% in a single season since 2010", "2010-11"),
    ],
)
def test_single_season_questions_rank_player_seasons(query, start):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "season_leaders"
    assert (kwargs["start_season"], kwargs["per_season"]) == (start, True)


def test_single_season_in_a_named_year_is_that_season():
    kwargs = parse_query("most points in a single season in 2016")["route_kwargs"]
    assert kwargs["season"] == "2015-16"
    assert not kwargs.get("per_season")


@pytest.mark.fixture_data
def test_elimination_game_list_uses_only_elimination_games():
    raw = pd.read_csv(RAW / "player_game_stats" / "2025-26_playoffs.csv")
    elimination = raw[raw["game_id"].isin([544, 545]) & raw["team_abbr"].eq("DEN")]
    result = _ok("most points in an elimination game this season")
    leaders = result["sections"]["leaderboard"]
    assert leaders[0]["pts"] == elimination["pts"].max()
    assert {row["team_abbr"] for row in leaders} == {"DEN"}
    assert {int(row["game_id"]) for row in leaders} <= {544, 545}


@pytest.mark.fixture_data
def test_fewest_team_points_in_a_game():
    frames = [
        pd.read_csv(RAW / "team_game_stats" / f"{season}_regular_season.csv") for season in SEASONS
    ]
    result = _ok("fewest points by a team in a game since 2023")
    leaders = result["sections"]["leaderboard"]
    assert leaders[0]["pts"] == pd.concat(frames)["pts"].min()
    assert [row["pts"] for row in leaders] == sorted(row["pts"] for row in leaders)


@pytest.mark.fixture_data
def test_best_single_seasons_rank_each_season_on_its_own():
    best = {
        season: season_leaders(season=season, stat="pts", limit=1).leaders.iloc[0]
        for season in SEASONS
    }
    top = max(best.values(), key=lambda row: row["pts_per_game"])
    result = _ok("most points in a season since 2023")
    leaders = result["sections"]["leaderboard"]
    assert leaders[0]["pts_per_game"] == pytest.approx(top["pts_per_game"])
    assert leaders[0]["season"] == top["season"]
    keys = [(row["player_name"], row["season"]) for row in leaders]
    assert len(keys) == len(set(keys))
    assert any("single seasons ranked across 2023-24 to 2025-26" in c for c in result["caveats"])


@pytest.mark.parametrize(
    "query",
    [
        "most points in a game in a single season",
        "most points off the bench by a team in a single season",
    ],
)
def test_single_season_questions_without_a_season_board_refuse(query):
    parsed = parse_query(query)
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == ["single_season"]


def test_at_least_does_not_flip_a_team_game_list():
    kwargs = parse_query("most points by a team in a game, at least 2023-24")["route_kwargs"]
    assert kwargs["ascending"] is False


@pytest.mark.parametrize(
    ("query", "route"),
    [
        ("most points per game in an elimination game", "season_leaders"),
        ("fewest points in an elimination game", "season_leaders"),
    ],
)
def test_averages_and_fewest_in_a_situation_keep_the_season_board(query, route):
    parsed = parse_query(query)
    assert parsed["route"] == route
    assert parsed["route_kwargs"]["series_situation"] == "elimination"


@pytest.mark.fixture_data
def test_best_single_seasons_metadata_names_the_span():
    result = execute_natural_query("most points in a single season")
    assert (result.metadata["season"], result.metadata["start_season"]) == (None, "1996-97")
