"""C2: "won it all", comparisons by playoff round, and single-game lists over spans.

"how many times have the Spurs won it all" answered regular-season wins, "who
won the title last year" counted every season, "Lakers vs Celtics in the
Finals" compared whole postseasons, and "most points in a game since 2000"
ranked only the current season.

Fixture: the 2025-26 Lakers-Nuggets first round (games 541-546) and three
regular seasons, 2023-24 to 2025-26.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands._seasons import previous_season
from nbatools.commands.natural_query import parse_query
from nbatools.commands.top_player_games import build_result as top_player_games
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _ok(query: str):
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.result.notes)
    return result


@pytest.mark.parametrize(
    ("query", "route", "team"),
    [
        ("how many times have the Spurs won it all", "playoff_history", "SAS"),
        ("Lakers won it all how many times", "playoff_history", "LAL"),
        ("who won it all in 2016", "playoff_appearances", None),
        ("which team won it all the most since 2000", "playoff_appearances", None),
    ],
)
def test_won_it_all_is_the_title(query, route, team):
    parsed = parse_query(query)
    assert parsed["route"] == route
    assert parsed["route_kwargs"].get("team") == team
    if route == "playoff_appearances":
        assert parsed["route_kwargs"]["titles"] is True


def test_won_it_all_for_a_player_counts_rings():
    parsed = parse_query("how many times has LeBron won it all")
    assert parsed["route"] == "playoff_appearances"
    assert parsed["route_kwargs"]["player"] == "LeBron James"
    assert parsed["route_kwargs"]["titles"] is True


@pytest.mark.parametrize(
    ("query", "relative"),
    [
        ("who won the title last year", "last"),
        ("who won it all last year", "last"),
        ("who won the title this year", "this"),
        ("LeBron rings this year", "this"),
    ],
)
def test_title_year_is_one_season(query, relative):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["start_season"] is None
    if relative == "last":
        assert kwargs["season"] == previous_season("Playoffs")
    else:
        assert kwargs["season"] is not None


@pytest.mark.parametrize(
    ("query", "route", "situation"),
    [
        ("Lakers vs Celtics in the Finals", "team_compare", "round_04"),
        ("LeBron vs Curry in the Finals", "player_compare", "round_04"),
        ("LeBron vs Curry in the 2016 Finals", "player_compare", "round_04"),
        ("LeBron vs Jokic in elimination games", "player_compare", "elimination"),
        ("Lakers vs Nuggets in game 4s", "team_compare", "game_4"),
    ],
)
def test_comparisons_take_the_round_or_situation(query, route, situation):
    parsed = parse_query(query)
    assert parsed["route"] == route
    assert parsed["route_kwargs"]["series_situation"] == situation


def test_finals_comparison_without_a_year_covers_every_season():
    kwargs = parse_query("Lakers vs Celtics in the Finals")["route_kwargs"]
    assert (kwargs["start_season"], kwargs["season"]) == ("1996-97", None)


@pytest.mark.fixture_data
def test_team_comparison_in_game_4s_uses_only_game_4():
    result = _ok("Lakers vs Nuggets in game 4s").result.to_dict()
    rows = {row["team_name"]: row for row in result["sections"]["summary"]}
    assert (rows["LAL"]["games"], rows["LAL"]["wins"]) == (1, 0)
    assert (rows["DEN"]["games"], rows["DEN"]["wins"]) == (1, 1)
    assert any("game 4s" in caveat for caveat in result["caveats"])


@pytest.mark.fixture_data
def test_player_comparison_in_elimination_games():
    # Only the Nuggets faced elimination (games 4 and 5).
    result = _ok("LeBron vs Jokic in elimination games").result.to_dict()
    rows = {row["player_name"]: row for row in result["sections"]["summary"]}
    assert rows["LeBron James"]["games"] == 0
    assert rows["Nikola Jokić"]["games"] == 2


@pytest.mark.parametrize(
    ("query", "start", "situation"),
    [
        ("most points in a game since 2000", "2000-01", None),
        ("highest scoring games since 2015", "2015-16", None),
        ("most points in a game ever", "1996-97", None),
        ("most points in a playoff game since 2000", "2000-01", None),
        ("most points in a game 7", "1996-97", "game_7"),
        ("most points in a finals game", "1996-97", "round_04"),
        ("highest scoring games in the finals", "1996-97", "round_04"),
        ("most rebounds in a single conference finals game", "1996-97", "round_03"),
        ("top team scoring games since 2010", "2010-11", None),
    ],
)
def test_single_game_lists_keep_their_span(query, start, situation):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] in {"top_player_games", "top_team_games"}
    assert (kwargs["season"], kwargs["start_season"]) == (None, start)
    assert kwargs.get("series_situation") == situation


def test_single_game_list_in_a_named_finals():
    kwargs = parse_query("most points in a game in the 2016 finals")["route_kwargs"]
    assert (kwargs["season"], kwargs["series_situation"]) == ("2015-16", "round_04")


@pytest.mark.fixture_data
def test_single_game_list_ranks_every_season_in_the_span():
    frames = [
        pd.read_csv(RAW / "player_game_stats" / f"{season}_regular_season.csv")
        for season in ("2023-24", "2024-25", "2025-26")
    ]
    best = pd.concat(frames)["pts"].max()
    result = _ok("most points in a game since 2023").result.to_dict()
    leaders = result["sections"]["leaderboard"]
    assert leaders[0]["pts"] == best
    assert {row["season"] for row in leaders} <= {"2023-24", "2024-25", "2025-26"}
    assert any("2023-24 to 2025-26" in caveat for caveat in result["caveats"])


@pytest.mark.fixture_data
def test_single_game_list_in_a_round():
    raw = pd.read_csv(RAW / "player_game_stats" / "2025-26_playoffs.csv")
    result = _ok("most points in a first round game this season").result.to_dict()
    assert result["sections"]["leaderboard"][0]["pts"] == raw["pts"].max()
    assert any("First Round" in caveat for caveat in result["caveats"])


@pytest.mark.fixture_data
def test_team_single_game_list_in_closeout_games():
    result = _ok("highest scoring team games in closeout games this season").result.to_dict()
    games = {int(row["game_id"]) for row in result["sections"]["leaderboard"]}
    assert games == {544, 545}


@pytest.mark.fixture_data
def test_structured_top_games_take_a_span():
    result = top_player_games(
        season=None, start_season="2023-24", end_season="2025-26", stat="ast", limit=3
    )
    assert len(result.leaders) == 3
    assert set(result.leaders["season"]) <= {"2023-24", "2024-25", "2025-26"}


def test_team_round_record_keeps_this_season():
    kwargs = parse_query("Lakers record in the first round this season")["route_kwargs"]
    assert (kwargs["season"], kwargs["start_season"]) == ("2025-26", None)
    assert kwargs["playoff_round"] == "01"


def test_team_round_record_keeps_last_year():
    kwargs = parse_query("Lakers record in the first round last year")["route_kwargs"]
    assert (kwargs["season"], kwargs["start_season"]) == (previous_season("Playoffs"), None)


@pytest.mark.parametrize(
    "query",
    [
        "most points in a game ever this postseason",
        "Jokic most points in a game ever this postseason",
        "has Jokic ever had a triple double this postseason",
        "most points ever in the current playoffs",
        "most points in a game ever this season",
    ],
)
def test_ever_keeps_a_named_season(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs.get("start_season") is None
    assert kwargs["season"] == "2025-26"


def test_won_it_all_with_a_comeback_is_not_a_title_list():
    with pytest.raises(ValueError):
        parse_query("biggest series comeback by a team that won it all")
