"""C2: players over a season total ("how many players scored 2000 points").

No player has had 2000 points, 500 rebounds or 100 steals in a game, so the
number is a season total. These read "scored 200" (a cut-off number) as a
per-game bound, refused, or counted games. Expected values are summed from the
fixture's player game rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/player_game_stats")


def _totals(seasons: list[str], stat: str, team: str | None = None) -> pd.DataFrame:
    frames = [pd.read_csv(RAW / f"{season}_regular_season.csv") for season in seasons]
    games = pd.concat(frames, ignore_index=True)
    if team:
        games = games[games["team_abbr"] == team]
    return games.groupby(["player_id", "season"])[stat].sum().reset_index()


def _players_over(seasons: list[str], stat: str, line: float, **kw) -> set[int]:
    totals = _totals(seasons, stat, **kw)
    if len(seasons) > 1:
        totals = totals.groupby("player_id")[stat].sum().reset_index()
    return set(totals.loc[totals[stat] >= line, "player_id"])


@pytest.mark.parametrize(
    ("query", "stat", "line", "season"),
    [
        ("players with 1000 points this season", "pts", 1000, "2025-26"),
        ("which players scored 1500 points in 2024-25", "pts", 1500, "2024-25"),
        ("players with 500 rebounds", "reb", 500, "2025-26"),
        ("players with 100 steals", "stl", 100, "2025-26"),
        ("players with 100 threes this season", "fg3m", 100, "2025-26"),
    ],
)
def test_lists_every_player_over_the_season_total(query, stat, line, season):
    result = execute_natural_query(query)
    assert result.result_status == "ok"
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert {row["player_id"] for row in rows} == _players_over([season], stat, line)


def test_how_many_counts_players():
    expected = _players_over(["2025-26"], "pts", 1000)
    result = execute_natural_query("how many players have 1000 points this season")
    sections = result.result.to_dict()["sections"]
    assert sections["count"] == [{"count": len(expected)}]
    # The counted players come with the count.
    assert {row["player_id"] for row in sections["leaderboard"]} == expected
    phrase = result.metadata["answer_phrase"]
    assert phrase.startswith(f"{len(expected)} players have 1,000+ points this season: ")


def test_a_number_no_one_reached_is_zero():
    for query in ("how many players scored 2000 points", "how many players scored 2000"):
        kwargs = parse_query(query)["route_kwargs"]
        assert (kwargs["stat"], kwargs["min_total"]) == ("pts_total", 2000.0)
        result = execute_natural_query(query)
        assert result.result.to_dict()["sections"]["count"] == [{"count": 0}]
        assert result.metadata["answer_phrase"] == (
            "No player has 2,000+ points in the 2025-26 regular season."
        )


def test_team_players():
    expected = _players_over(["2025-26"], "pts", 1000, team="LAL")
    result = execute_natural_query("how many Lakers players have 1000 points")
    assert result.result.to_dict()["sections"]["count"] == [{"count": len(expected)}]
    assert "Los Angeles Lakers players have" in result.metadata["answer_phrase"]


def test_in_a_season_counts_players_not_seasons():
    seasons = ["2024-25", "2025-26"]
    totals = _totals(seasons, "pts")
    over = totals[totals["pts"] >= 1000]
    result = execute_natural_query(
        "how many players have scored 1000 points in a season since 2024"
    )
    sections = result.result.to_dict()["sections"]
    assert sections["count"] == [{"count": over["player_id"].nunique()}]
    assert len(sections["leaderboard"]) == len(over)
    assert "in a single season from 2024-25 to 2025-26" in result.metadata["answer_phrase"]


def test_a_span_without_in_a_season_is_combined():
    expected = _players_over(["2024-25", "2025-26"], "pts", 2000)
    result = execute_natural_query("how many players have 2000 points since 2024")
    assert result.result.to_dict()["sections"]["count"] == [{"count": len(expected)}]
    assert "combined from 2024-25 to 2025-26" in result.metadata["answer_phrase"]


def test_playoff_points_number_is_not_the_2000_playoffs():
    kwargs = parse_query("players with 2000 playoff points")["route_kwargs"]
    assert kwargs["min_total"] == 2000.0
    assert kwargs["season"] != "1999-00"


@pytest.mark.parametrize(
    "query",
    [
        # Single-game numbers stay game thresholds.
        "how many players scored 50",
        "how many players scored 40 points this season",
        # Per-game wording is never a total.
        "players averaging 2000 points",
        # "in scoring 2016" is a season.
        "who led the league in scoring 2016",
    ],
)
def test_game_sized_numbers_keep_their_routes(query):
    try:
        parsed = parse_query(query)
    except ValueError:
        return
    assert "min_total" not in parsed["route_kwargs"]


def test_thousands_comma_is_one_number():
    kwargs = parse_query("players with 1,500 points")["route_kwargs"]
    assert kwargs["min_total"] == 1500.0


@pytest.mark.parametrize(
    "query",
    [
        # Single-game wording, or a number just above a game record.
        "players who scored 101 points in a single game",
        "who scored 120 points in one game",
        "how many players had 12 steals",
        "players with 31 assists",
        "who scored 105 points last night",
        # A repeat, window, game total or second condition the list would drop.
        "players with 1500 points in each of the last 2 seasons",
        "players with 1500 points in both 2024-25 and 2025-26",
        "players with 1500 points in multiple seasons",
        "players with 1000 points in their first 60 games",
        "players with 1000 points before the all star break",
        "players in games with 250 total points",
        "players with 1500 points or 600 rebounds",
    ],
)
def test_wording_a_total_list_cannot_honour_stays_off_it(query):
    try:
        parsed = parse_query(query)
    except ValueError:
        return
    assert "min_total" not in parsed["route_kwargs"]


@pytest.mark.parametrize(
    ("query", "words"),
    [
        ("players with 1000 points at home", "at home"),
        ("players with 1000 points on the road", "on the road"),
        ("players with 800 points in wins", "in wins"),
        ("players with 300 points against the Celtics", "against the Boston Celtics"),
        ("players with 500 points in March", "from 2026-03-01 to 2026-03-31"),
    ],
)
def test_headline_names_the_filters_applied(query, words):
    assert words in execute_natural_query(query).metadata["answer_phrase"]


def test_strict_floor_and_team_in_a_season_headlines():
    phrase = execute_natural_query("players with over 1500 points").metadata["answer_phrase"]
    assert "more than 1,500 points" in phrase
    phrase = execute_natural_query(
        "how many Lakers players have 1000 points in a season since 2024"
    ).metadata["answer_phrase"]
    assert phrase.startswith("3 Los Angeles Lakers players have")


@pytest.mark.parametrize(
    "query",
    [
        "players with 1000 or more points",
        "players with 1000 points or more",
        "every player with 1500 points",
        "list every player with 1500 points this season",
    ],
)
def test_plain_threshold_wording_is_a_total_list(query):
    assert parse_query(query)["route_kwargs"].get("min_total") in (1000.0, 1500.0)


def test_a_total_in_several_seasons_refuses_rather_than_count_games():
    result = execute_natural_query("how many players have scored 1500 points in multiple seasons")
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"
