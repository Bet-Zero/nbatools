"""C2: team best single seasons, a player's own best seasons, ranked wins.

"most wins in a single season" and "most team points in a single season"
refused, "most wins this season" counted only won games (a 47-0 record), and
"LeBron best scoring season" listed his top games of the current season.

Fixture: three regular seasons, 2023-24 to 2025-26, and the 2025-26
Lakers-Nuggets first round.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.commands.season_leaders import build_result as season_leaders
from nbatools.commands.season_team_leaders import build_result as season_team_leaders
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")
SEASONS = ("2023-24", "2024-25", "2025-26")


def _leaders(query: str):
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.result.notes)
    return result.result.to_dict()


@pytest.mark.parametrize(
    ("query", "route", "stat", "ascending", "start"),
    [
        ("most wins in a single season", "team_record_leaderboard", "wins", False, "1996-97"),
        (
            "worst record in a single season since 2010",
            "team_record_leaderboard",
            "win_pct",
            True,
            "2010-11",
        ),
        ("most team points in a single season", "season_team_leaders", "pts", False, "1996-97"),
        (
            "which team scored the most points in a single season",
            "season_team_leaders",
            "pts",
            False,
            "1996-97",
        ),
        (
            "best net rating in a single season",
            "season_team_leaders",
            "net_rating",
            False,
            "1996-97",
        ),
    ],
)
def test_team_single_season_questions_rank_team_seasons(query, route, stat, ascending, start):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == route
    assert (kwargs["stat"], kwargs["ascending"], kwargs["start_season"]) == (stat, ascending, start)
    assert kwargs["per_season"] is True


def test_team_single_season_in_a_named_year_is_that_season():
    kwargs = parse_query("most wins in a single season in 2016")["route_kwargs"]
    assert kwargs["season"] == "2015-16"
    assert not kwargs.get("per_season")


@pytest.mark.parametrize(
    "query",
    ["most wins this season", "most playoff wins this season", "fewest losses since 2010"],
)
def test_ranked_wins_are_the_stat_not_a_filter(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert not kwargs.get("wins_only") and not kwargs.get("losses_only")


@pytest.mark.parametrize(
    "query", ["best win percentage in a single season", "best win percentage this season"]
)
def test_win_percentage_counts_every_game(query):
    assert not parse_query(query)["route_kwargs"].get("wins_only")


def test_team_single_season_without_a_player_refuses():
    parsed = parse_query("most wins in a single season without LeBron")
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == ["single_season"]


def test_wins_as_a_filter_stay_a_filter():
    assert parse_query("most points in wins this season")["route_kwargs"]["wins_only"] is True


@pytest.mark.fixture_data
def test_most_wins_board_counts_full_records():
    frames = [
        pd.read_csv(RAW / "team_game_stats" / f"{season}_regular_season.csv") for season in SEASONS
    ]
    games = pd.concat(frames)
    wins = games[games["wl"].eq("W")].groupby(["season", "team_abbr"]).size()
    leaders = _leaders("most wins in a single season")["sections"]["leaderboard"]
    top = leaders[0]
    assert top["wins"] == wins.max()
    assert (top["season"], top["team_abbr"]) == wins.idxmax()
    played = games.groupby(["season", "team_abbr"]).size()
    assert top["games_played"] == played[(top["season"], top["team_abbr"])]
    assert top["losses"] == top["games_played"] - top["wins"]


@pytest.mark.fixture_data
def test_team_points_board_ranks_each_team_season_on_its_own():
    best = [
        season_team_leaders(season=season, stat="pts", limit=1).leaders.iloc[0]
        for season in SEASONS
    ]
    top = max(best, key=lambda row: row["pts_per_game"])
    result = _leaders("most team points in a single season")
    leaders = result["sections"]["leaderboard"]
    assert leaders[0]["pts_per_game"] == pytest.approx(top["pts_per_game"])
    assert leaders[0]["season"] == top["season"]
    keys = [(row["team_abbr"], row["season"]) for row in leaders]
    assert len(keys) == len(set(keys))
    assert any("single seasons ranked across" in c for c in result["caveats"])


@pytest.mark.parametrize(
    ("query", "player", "stat", "ascending", "start"),
    [
        ("LeBron best scoring season", "LeBron James", "pts", False, "1996-97"),
        ("LeBron most points in a single season", "LeBron James", "pts", False, "1996-97"),
        ("LeBron lowest scoring season", "LeBron James", "pts", True, "1996-97"),
        ("Jokic best rebounding seasons", "Nikola Jokić", "reb", False, "1996-97"),
        ("LeBron highest scoring season since 2015", "LeBron James", "pts", False, "2015-16"),
    ],
)
def test_player_best_seasons_rank_that_players_seasons(query, player, stat, ascending, start):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "season_leaders"
    assert (kwargs["player"], kwargs["stat"], kwargs["ascending"]) == (player, stat, ascending)
    assert (kwargs["start_season"], kwargs["per_season"]) == (start, True)


@pytest.mark.parametrize(
    "query",
    [
        "LeBron most points in a game this season",
        "LeBron best scoring season in 2016",
        "LeBron season high",
        "LeBron best scoring season vs Curry",
        "LeBron best scoring season without Anthony Davis",
        "LeBron best scoring season in the clutch",
        "LeBron best scoring season as a starter",
        "LeBron best scoring season in the second half",
        "LeBron best scoring season against the West",
        "LeBron best scoring season with Luka",
    ],
)
def test_player_game_and_filtered_season_questions_stay(query):
    assert parse_query(query)["route"] != "season_leaders"


@pytest.mark.fixture_data
def test_player_best_seasons_list_only_that_player():
    expected = {
        season: season_leaders(
            season=season, stat="pts", player="LeBron James", limit=1
        ).leaders.iloc[0]["pts_per_game"]
        for season in SEASONS
    }
    leaders = _leaders("LeBron best scoring season")["sections"]["leaderboard"]
    assert {row["player_name"] for row in leaders} == {"LeBron James"}
    assert [row["season"] for row in leaders] == sorted(expected, key=expected.get, reverse=True)
    assert leaders[0]["pts_per_game"] == pytest.approx(max(expected.values()))
