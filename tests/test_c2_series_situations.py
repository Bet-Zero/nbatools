"""C2 playoff series situations: game 7s, elimination and closeout games, "up 3-1".

"Celtics record in game 7s" and "Warriors record when up 3-1" answered the
team's whole regular season, and "who has won the most game 7s" was unrouted.

Fixture: the 2025-26 Lakers-Nuggets series, Lakers W W W L W. Before game 4
the Lakers led 3-0, before game 5 3-1, so games 4 and 5 are Lakers closeout
games and Nuggets elimination games.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands._parse_helpers import detect_series_comeback, detect_series_situation
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW_PLAYERS = Path(
    "qa/fixtures/query_engine_sample/data/raw/player_game_stats/2025-26_playoffs.csv"
)
CLOSEOUT_GAMES = {544, 545}


def _ok(query: str):
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.result.notes)
    return result


def _summary(query: str) -> dict:
    return _ok(query).result.to_dict()["sections"]["summary"][0]


@pytest.mark.parametrize(
    ("text", "situation"),
    [
        ("Celtics record in game 7s", "game_7"),
        ("LeBron points in game sevens", "game_7"),
        ("Heat record in a game 6", "game_6"),
        ("Heat record in elimination games", "elimination"),
        ("Knicks record when facing elimination", "elimination"),
        ("Celtics in closeout games", "closeout"),
        ("Celtics in series clinching games", "closeout"),
        ("LeBron in winner take all games", "deciding"),
        ("Warriors record when up 3-1", "score_3_1"),
        ("Warriors record when leading 2-0", "score_2_0"),
        ("Lakers record when down 3-1", "score_1_3"),
        ("Celtics record when trailing 1-3 in the series", "score_1_3"),
        ("Knicks record when tied 2-2", "score_2_2"),
        ("Lakers record in game 7s last season", "game_7"),
        ("Lakers record in game 5s last postseason", "game_5"),
        ("LeBron points in game 7s past 3 seasons", "game_7"),
        ("LeBron stats in games 2 and 3", "game_2_3"),
        ("Lakers record in game 6 or game 7", "game_6_7"),
        ("LeBron games 1 through 5", "game_1_2_3_4_5"),
        ("Lakers record in game 1s 2025-26", "game_1"),
    ],
)
def test_series_situation_wording(text, situation):
    assert detect_series_situation(text) == situation


@pytest.mark.parametrize(
    "text",
    [
        "LeBron 30 point game 5 rebounds",
        "Jokic game 3 times",
        "Celtics last 10 games",
        "Celtics game 2 of a back to back",
        "Heat game 4 of the road trip",
        "Celtics record when up 2-0 in the season series",
        "Lakers up 10-2",
        "Knicks record when tied 2-1",
        "Celtics record",
        "Stephen Curry last 10 games 3 pointers",
        "Stephen Curry games 5 3 pointers",
        "Stephen Curry game 5 3 pointers",
        "Nikola Jokic games 6 offensive rebounds",
        "Nikola Jokic games 4 fouls",
        "Lakers game 1 of the last 5",
        "Lakers record when up 2-0 on the season",
        "Lakers record when tied 2-2 after the first quarter",
        "Lakers when up 3-1 in the fourth",
        "Lakers when trailing 0-3 in their last 3",
        "Jokic games 2 and 3 steals",
        "Curry games 5 or 6 threes",
        "Jokic last 5 games 2 or 3 blocks",
        "Curry games 3 to 5 made threes",
        "LeBron games 1-3 from three",
        "Lakers record in game 3 of road trips",
    ],
)
def test_not_a_series_situation(text):
    assert detect_series_situation(text) is None


@pytest.mark.parametrize(
    ("text", "comeback"),
    [
        ("teams that came back from 3-1 down", {"wins": 1, "losses": 3, "blown": False}),
        ("Cavs 3-1 comeback", {"wins": 1, "losses": 3, "blown": False}),
        ("came back from 0-2", {"wins": 0, "losses": 2, "blown": False}),
        ("Warriors blew a 3-1 lead", {"wins": 3, "losses": 1, "blown": True}),
        ("which teams have blown 3-1 leads", {"wins": 3, "losses": 1, "blown": True}),
    ],
)
def test_series_comeback_wording(text, comeback):
    assert detect_series_comeback(text) == comeback
    # A comeback is about the series, never a game filter.
    assert detect_series_situation(text) is None


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record in closeout games", (1, 1)),
        ("Nuggets record in elimination games", (1, 1)),
        ("Lakers record in game 4s", (0, 1)),
        ("Lakers record when up 3-1", (1, 0)),
        ("Nuggets record when down 3-1", (0, 1)),
        ("Nuggets record when trailing 1-3", (0, 1)),
        ("Lakers record when up 3-0", (0, 1)),
        ("Lakers record in elimination games in 2026", (0, 0)),
    ],
)
def test_team_record_in_series_situation(query, record):
    result = execute_natural_query(query)
    assert result.metadata["route"] == "team_record"
    if record == (0, 0):
        # The Lakers never faced elimination: an empty sample, not their season.
        assert result.result_status == "no_result"
        return
    assert result.result_status == "ok", result.result_reason
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == record
    assert any("playoff series situation" in c for c in result.result.caveats)


def test_series_situation_reads_playoffs_since_1996_unless_a_season_is_named():
    parsed = parse_query("Celtics record in game 7s")
    assert parsed["season_type"] == "Playoffs"
    assert (parsed["start_season"], parsed["season"]) == ("1996-97", None)
    assert "default: every playoff season since 1996-97" in parsed["notes"]
    assert parsed["route_kwargs"]["series_situation"] == "game_7"

    named = parse_query("Celtics record in game 7s in 2026")
    assert named["season"] == "2025-26"
    assert named["season_type"] == "Playoffs"
    assert not any("every playoff season" in note for note in named.get("notes", []))

    plain = parse_query("Celtics record")
    assert plain["season_type"] == "Regular Season"
    assert "series_situation" not in plain["route_kwargs"]


@pytest.mark.parametrize(
    ("query", "start"),
    [
        ("Lakers record in game 7s last 3 playoffs", "2023-24"),
        ("Lakers record in game 7s last 2 postseasons", "2024-25"),
        ("Lakers record in game 7s last 3 years", "2023-24"),
    ],
)
def test_last_n_playoffs_is_a_season_window_not_a_game_count(query, start):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["series_situation"] == "game_7"
    assert (kwargs["start_season"], kwargs["end_season"]) == (start, "2025-26")
    assert kwargs.get("last_n") is None


@pytest.mark.parametrize(
    "query",
    [
        "who has the most triple doubles in game 7s",
        "best road record in game 5s 2025-26",
        "best home team in game 7s",
    ],
)
def test_board_never_swaps_in_overall_records(query):
    # Home/road splits and stats the team board cannot read are not answered
    # with its overall record board.
    assert parse_query(query)["route"] != "playoff_round_record"
    assert execute_natural_query(query).result_status != "ok"


def test_player_summary_in_closeout_games_uses_those_games():
    rows = pd.read_csv(RAW_PLAYERS)
    lebron = rows[(rows["player_name"] == "LeBron James") & rows["game_id"].isin(CLOSEOUT_GAMES)]

    result = _ok("LeBron stats in closeout games")
    assert result.metadata["route"] == "player_game_summary"
    sections = result.result.to_dict()["sections"]
    assert {row["game_id"] for row in sections["game_log"]} == CLOSEOUT_GAMES
    assert sections["summary"][0]["games"] == len(lebron) == 2
    assert sections["summary"][0]["pts_avg"] == pytest.approx(lebron["pts"].mean())


def test_team_game_list_and_summary_in_closeout_games():
    games = _ok("list Lakers closeout games").result.to_dict()["sections"]["finder"]
    assert {row["game_id"] for row in games} == CLOSEOUT_GAMES

    summary = _ok("Lakers stats in closeout games").result.to_dict()["sections"]["summary"][0]
    assert (summary["games"], summary["wins"], summary["losses"]) == (2, 1, 1)


def test_player_total_leaderboard_in_elimination_games():
    rows = pd.read_csv(RAW_PLAYERS)
    nuggets = rows[(rows["team_abbr"] == "DEN") & rows["game_id"].isin(CLOSEOUT_GAMES)]
    totals = nuggets.groupby("player_name")["pts"].sum().sort_values(ascending=False)

    result = _ok("most total points in elimination games")
    assert result.metadata["route"] == "season_leaders"
    top = result.result.to_dict()["sections"]["leaderboard"][0]
    assert top["player_name"] == totals.index[0]
    assert top["pts_total"] == totals.iloc[0]
    assert top["games_played"] == 2


@pytest.mark.parametrize(
    ("query", "team", "stat"),
    [
        ("who has won the most elimination games", "DEN", ("wins", 1)),
        ("which team has played the most closeout games", "LAL", ("games_played", 2)),
        ("who has lost the most closeout games", "LAL", ("losses", 1)),
    ],
)
def test_team_board_in_series_situation(query, team, stat):
    result = _ok(query)
    assert result.metadata["route"] == "playoff_round_record"
    top = result.result.to_dict()["sections"]["leaderboard"][0]
    assert top["team_abbr"] == team
    assert top[stat[0]] == stat[1]


@pytest.mark.parametrize(
    "query",
    [
        "LeBron James came back from 3-1 down",
        "players who came back from 3-1 down",
        "LeBron James record after blowing a 3-1 lead",
        "Lakers vs Nuggets came back from 3-1",
    ],
)
def test_series_comeback_refuses_instead_of_answering_a_game_record(query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record when up 2-0 regular season",
        "Lakers record in game 1s 2025-26 regular season",
        "Lakers record in game 5s regular season",
        "which coach has the most game 7 wins",
    ],
)
def test_series_situation_the_data_cannot_answer_refuses(query):
    # The regular season has no series games and coaches are not in the data.
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"


def test_games_in_a_set_use_every_named_game():
    result = _ok("Lakers record in games 4 and 5")
    summary = result.result.to_dict()["sections"]["summary"][0]
    # Lakers lost game 4 and won game 5.
    assert (summary["wins"], summary["losses"]) == (1, 1)
    assert "playoff series situation: games 4 and 5" in result.result.caveats


def test_best_team_board_ranks_by_record():
    result = _ok("who is the best team in game 4s in 2026")
    assert result.metadata["route"] == "playoff_round_record"
    assert result.result.to_dict()["sections"]["leaderboard"][0]["team_abbr"] == "DEN"


def test_most_points_in_a_situation_is_a_total_and_rates_are_answered():
    rows = pd.read_csv(RAW_PLAYERS)
    picked = rows[rows["game_id"].isin(CLOSEOUT_GAMES)]
    totals = picked.groupby("player_name")["pts"].sum().sort_values(ascending=False)

    parsed = parse_query("who scored the most points in closeout games")
    assert parsed["route_kwargs"]["stat"] == "pts_total"
    assert "default: totals over those games; ask per game for averages" in parsed["notes"]
    assert parse_query("most points per game in closeout games")["route_kwargs"]["stat"] == "pts"

    top = _ok("who scored the most points in closeout games").result.to_dict()["sections"]
    assert top["leaderboard"][0]["pts_total"] == totals.iloc[0]

    # One season of closeout games is a small sample: a rate board still answers.
    rate = _ok("who has the best fg% in closeout games in 2026").result.to_dict()["sections"]
    assert rate["leaderboard"]
    assert _ok("most points per game in closeout games in 2026").result.to_dict()["sections"][
        "leaderboard"
    ]


@pytest.mark.parametrize(
    ("query", "route"),
    [
        ("Lakers home away splits in closeout games", "team_split_summary"),
        ("LeBron vs Jokic in elimination games", "player_compare"),
        ("Lakers vs Nuggets in game 4s", "team_compare"),
    ],
)
def test_route_without_series_situation_support_refuses(query, route):
    # These routes do not read the series situation yet: refuse, never ignore it.
    result = execute_natural_query(query)
    assert result.metadata["route"] == route
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"


@pytest.mark.parametrize(
    ("query", "start"),
    [
        ("Lakers record past 2 postseasons", "2024-25"),
        ("most points in the last 5 playoffs", "2021-22"),
        ("playoff scoring leaders last 3 playoffs", "2023-24"),
    ],
)
def test_last_n_postseasons_are_playoff_seasons(query, start):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["season_type"] == "Playoffs"
    assert (kwargs["start_season"], kwargs["end_season"]) == (start, "2025-26")
    assert kwargs.get("last_n") is None
    assert not kwargs.get("unsupported_filters")
