"""C2: a player's own games ranked by one stat.

"Curry best 3 point shooting game" ranked points with a 3-point floor, "LeBron
top 5 games" and "Curry worst shooting game" gave season summaries, and "LeBron
best shooting game since 2023" averaged the span. Rate lists ranked 1-for-1
games first.

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
    ("query", "stat", "ascending", "limit"),
    [
        ("Curry best 3 point shooting game", "fg3_pct", False, 10),
        ("Curry best 3-point shooting night", "fg3_pct", False, 10),
        ("Curry best free throw shooting game", "ft_pct", False, 10),
        ("Curry worst shooting game", "fg_pct", True, 10),
        ("LeBron best shooting game since 2023", "fg_pct", False, 10),
        ("LeBron top 5 games", "pts", False, 5),
        ("Curry top 5 games this season", "pts", False, 5),
        ("LeBron top 10 games of his career", "pts", False, 10),
    ],
)
def test_player_game_lists_rank_the_stat_asked(query, stat, ascending, limit):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "player_game_finder"
    assert (kwargs["stat"], kwargs["ascending"], kwargs["limit"]) == (stat, ascending, limit)
    assert kwargs["sort_by"] == "stat"
    assert kwargs.get("min_value") is None


@pytest.mark.parametrize(
    ("query", "route"),
    [
        ("LeBron last 10 games", "player_game_summary"),
        ("LeBron games with 30 points", "player_game_finder"),
    ],
)
def test_other_game_questions_keep_their_route(query, route):
    assert parse_query(query)["route"] == route


def test_filters_ride_along():
    kwargs = parse_query("LeBron best shooting game vs Celtics")["route_kwargs"]
    assert (kwargs["opponent"], kwargs["stat"]) == ("BOS", "fg_pct")


def _games(player: str) -> pd.DataFrame:
    frames = [
        pd.read_csv(RAW / "player_game_stats" / f"{season}_regular_season.csv")
        for season in SEASONS
    ]
    games = pd.concat(frames)
    return games[games["player_name"].eq(player)]


@pytest.mark.fixture_data
def test_best_three_point_game_needs_five_attempts():
    games = _games("LeBron James")
    eligible = games[games["fg3a"] >= 5]
    result = execute_natural_query("LeBron best 3 point shooting game since 2023")
    assert result.result_status == "ok"
    data = result.result.to_dict()
    rows = data["sections"]["finder"]
    assert all(row["fg3a"] >= 5 for row in rows)
    best = (eligible["fg3m"] / eligible["fg3a"]).max()
    assert rows[0]["fg3_pct"] == pytest.approx(best)
    top = [row for row in rows if row["fg3_pct"] == rows[0]["fg3_pct"]]
    assert [row["fg3a"] for row in top] == sorted((row["fg3a"] for row in top), reverse=True)
    assert "games with fewer than 5 three-point attempts left out" in data["caveats"]


@pytest.mark.fixture_data
def test_worst_shooting_game_is_lowest_first():
    games = _games("LeBron James")
    eligible = games[games["fga"] >= 10]
    rows = execute_natural_query("LeBron worst shooting game since 2023").result.to_dict()[
        "sections"
    ]["finder"]
    assert rows[0]["fg_pct"] == pytest.approx((eligible["fgm"] / eligible["fga"]).min())


@pytest.mark.fixture_data
def test_threshold_lists_keep_every_game():
    result = execute_natural_query("LeBron games shooting over 60% since 2023")
    caveats = result.result.to_dict().get("caveats") or []
    assert not any("left out" in caveat for caveat in caveats)


@pytest.mark.parametrize(
    ("query", "stat", "limit"),
    [
        ("Jokic top 3 shooting performances", "fg_pct", 3),
        ("LeBron top 3 shooting games", "fg_pct", 3),
        ("LeBron 3 best shooting games", "fg_pct", 3),
    ],
)
def test_top_n_is_a_count_not_three_point_shooting(query, stat, limit):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs["stat"], kwargs["limit"]) == (stat, limit)


def test_top_three_shooting_seasons_rank_field_goal_percentage():
    kwargs = parse_query("LeBron top 3 shooting seasons")["route_kwargs"]
    assert (kwargs["stat"], kwargs["limit"]) == ("fg_pct", 3)


def test_a_bound_on_another_stat_keeps_that_stat():
    kwargs = parse_query("LeBron best shooting games over 25 points")["route_kwargs"]
    assert kwargs["stat"] == "fg_pct"
    assert kwargs["conditions"] == [{"stat": "pts", "min_value": 25.0001, "max_value": None}]


def test_defensive_games_are_not_ranked_by_points():
    parsed = parse_query("Jokic best defensive games")
    assert parsed["route_kwargs"].get("stat") != "pts" or parsed["route"] != "player_game_finder"


@pytest.mark.fixture_data
def test_last_n_lists_keep_every_game():
    result = execute_natural_query("LeBron last 20 games sorted by 3pt%")
    data = result.result.to_dict()
    assert len(data["sections"]["finder"]) == 20
    assert not any("left out" in caveat for caveat in data.get("caveats") or [])
