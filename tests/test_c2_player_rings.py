"""C2 player rings: "how many rings does LeBron have", "who has the most rings".

Ring questions refused as championship counts. A ring is a title won while
playing at least one playoff game for the team that won the Finals that season.

Fixture: the 2025-26 Lakers-Nuggets series (Lakers 4-1). It is a first-round
series in the fixture, so these tests relabel it as the Finals.
"""

from __future__ import annotations

import pandas as pd
import pytest

import nbatools.commands.playoff_history as playoff_history
from nbatools.commands.data_utils import load_player_games_for_seasons
from nbatools.commands.natural_query import parse_query
from nbatools.commands.structured_results import LeaderboardResult
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


@pytest.fixture
def finals(monkeypatch):
    load = playoff_history._load_playoff_games
    monkeypatch.setattr(
        playoff_history,
        "_load_playoff_games",
        lambda seasons: load(seasons).assign(playoff_round_code="04"),
    )


@pytest.mark.parametrize(
    ("query", "player"),
    [
        ("how many rings does lebron have", "LeBron James"),
        ("LeBron championships", "LeBron James"),
        ("how many titles has Jokic won", "Nikola Jokić"),
        ("Stephen Curry rings", "Stephen Curry"),
    ],
)
def test_player_ring_questions_route_to_player_titles(query, player):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "playoff_appearances"
    assert kwargs["player"] == player
    assert kwargs["titles"] is True
    assert kwargs["player_titles"] is False
    assert (kwargs["start_season"], kwargs["season"]) == ("1996-97", None)
    assert not parsed.get("count_intent")


@pytest.mark.parametrize(
    ("query", "start"),
    [
        ("who has the most rings", "1996-97"),
        ("players with the most rings since 1996", "1996-97"),
        ("which player has the most titles", "1996-97"),
        ("most rings since 2010", "2010-11"),
    ],
)
def test_ring_boards_rank_players(query, start):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "playoff_appearances"
    assert (kwargs["player"], kwargs["player_titles"]) == (None, True)
    assert kwargs["start_season"] == start


@pytest.mark.parametrize(
    ("query", "start", "end"),
    [
        ("how many rings does LeBron have over the last 5 seasons", "2021-22", "2025-26"),
        ("players with the most rings over the last 20 years", "2006-07", "2025-26"),
        ("LeBron rings between 2012 and 2016", "2011-12", "2015-16"),
        ("how many rings does LeBron have over his career", "1996-97", "2025-26"),
        ("most titles by a player since 2000", "2000-01", "2025-26"),
        ("LeBron's rings", "1996-97", "2025-26"),
        ("King James rings", "1996-97", "2025-26"),
    ],
)
def test_span_wording_still_answers(query, start, end):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "playoff_appearances"
    assert (kwargs["start_season"], kwargs["end_season"]) == (start, end)


def test_named_span_is_kept():
    kwargs = parse_query("LeBron titles since 2015")["route_kwargs"]
    assert kwargs["start_season"] == "2015-16"


@pytest.mark.parametrize(
    "query",
    [
        "LeBron rings with the Heat",
        "LeBron scoring titles",
        "LeBron conference titles",
        "players with the most rings with Shaq",
        "LeBron back to back titles",
        # Qualifiers a ring count cannot honour refuse, never answer the total.
        "how many rings does LeBron have vs the Warriors",
        "LeBron rings against the Celtics",
        "LeBron rings at home",
        "LeBron rings on the road",
        "LeBron rings when he scores 30",
        "Kobe vs Jordan rings",
        "how many rings does Kobe have compared to Shaq",
        "LeBron rings over Jordan",
        "Kobe and Shaq rings",
        "LeBron rings as a Laker",
        "most rings among active players",
        "who has the most rings as a bench player",
        "most rings in a row",
        "most consecutive rings",
        "most rings by a center",
        "most rings by a player under 25",
        "LeBron rings at age 27",
        "LeBron rings in his 30s",
        "LeBron rings in his first 10 seasons",
        "LeBron rings in his last 3 seasons",
        "LeBron rings in the East",
        "LeBron rings not counting the bubble",
        "who has the most rings over the past decade",
    ],
)
def test_other_title_questions_stay_refused(query):
    parsed = parse_query(query)
    assert parsed["route"] is None


@pytest.mark.parametrize(
    ("query", "route"),
    [
        ("which team has won the most titles", "playoff_appearances"),
        ("Lakers titles", "playoff_history"),
    ],
)
def test_team_title_questions_keep_their_routes(query, route):
    parsed = parse_query(query)
    assert parsed["route"] == route
    assert not parsed["route_kwargs"].get("player_titles")


def test_lebron_ring_counts_the_lakers_title(finals):
    result = execute_natural_query("how many rings does lebron have")
    assert result.result_status == "ok", result.result_reason
    assert isinstance(result.result, LeaderboardResult)
    row = result.result.leaders.iloc[0]
    assert (row["player_name"], row["titles"]) == ("LeBron James", 1)
    assert (row["title_seasons"], row["title_teams"]) == ("2025-26", "LAL")
    assert result.metadata["answer_phrase"] == (
        "LeBron James won 1 title from 1996-97 to 2025-26 (2025-26; LAL)."
    )


def test_player_on_the_finals_loser_has_no_ring(finals):
    result = execute_natural_query("how many titles has Jokic won")
    row = result.result.leaders.iloc[0]
    assert (row["player_name"], row["titles"]) == ("Nikola Jokić", 0)
    assert result.metadata["answer_phrase"] == (
        "Nikola Jokić won no titles from 1996-97 to 2025-26."
    )


def test_ring_board_lists_every_champion_who_played(finals):
    result = execute_natural_query("who has the most rings")
    board = result.result.leaders
    games = load_player_games_for_seasons(["2025-26"], "Playoffs")
    lakers = set(games.loc[games["team_abbr"] == "LAL", "player_name"])
    assert set(board["player_name"]) == lakers
    assert set(board["titles"]) == {1}
    assert "tied for the most titles" in result.metadata["answer_phrase"]


def test_board_limit_never_cuts_a_tie(finals):
    result = playoff_history.build_playoff_appearances_result(
        season="2025-26", titles=True, player_titles=True, limit=2
    )
    assert len(result.leaders) > 2
    assert list(result.leaders["rank"]) == list(range(1, len(result.leaders) + 1))


def test_unfinished_finals_awards_no_ring(monkeypatch):
    load = playoff_history._load_playoff_games

    def three_games(seasons):
        games = load(seasons).assign(playoff_round_code="04")
        return games[games["game_id"].astype(int) <= 543]

    monkeypatch.setattr(playoff_history, "_load_playoff_games", three_games)
    result = playoff_history.build_playoff_appearances_result(
        season="2025-26", titles=True, player_titles=True
    )
    assert result.result_status != "ok" or result.leaders.empty


def test_no_finals_in_span_is_no_result():
    result = execute_natural_query("how many rings does lebron have")
    assert result.result_status == "no_result"


def test_unknown_player_is_no_match():
    result = playoff_history.build_playoff_appearances_result(
        player="Nobody Atall", titles=True, season="2025-26"
    )
    assert result.result_reason == "no_match"


def test_repeated_finals_rows_do_not_crown_a_champion(monkeypatch):
    load = playoff_history._load_playoff_games

    def doubled(seasons):
        games = load(seasons).assign(playoff_round_code="04")
        games = games[games["game_id"].astype(int) <= 543]
        return pd.concat([games, games], ignore_index=True)

    monkeypatch.setattr(playoff_history, "_load_playoff_games", doubled)
    assert playoff_history._champions(doubled(["2025-26"])).empty


def test_finals_rows_with_padded_ids_are_one_game(monkeypatch):
    load = playoff_history._load_playoff_games

    def mixed(seasons):
        games = load(seasons).assign(playoff_round_code="04")
        games = games[games["game_id"].astype(int) <= 543]
        padded = games.assign(game_id=games["game_id"].astype(int).map(lambda g: f"{g:010d}"))
        return pd.concat([games, padded], ignore_index=True)

    assert playoff_history._champions(mixed(["2025-26"])).empty
