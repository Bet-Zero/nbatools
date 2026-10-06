"""C2: "most playoff wins by a player" ranks players by games won.

Fixture: three regular seasons, 2023-24 to 2025-26, plus the 2025-26 playoffs.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query]


@pytest.mark.parametrize(
    ("query", "season_type", "wins", "extra"),
    [
        ("most playoff wins by a player", "Playoffs", True, {}),
        ("which player has the most playoff wins", "Playoffs", True, {}),
        ("players with the most wins", "Regular Season", True, {}),
        ("players with the most losses this season", "Regular Season", False, {}),
        ("players with the most road wins", "Regular Season", True, {"away_only": True}),
        (
            "most wins in a single season by a player",
            "Regular Season",
            True,
            {"per_season": True, "start_season": "1996-97"},
        ),
        (
            "most playoff wins by a player in the 2020s",
            "Playoffs",
            True,
            {"start_season": "2020-21"},
        ),
    ],
)
def test_player_wins_rank_players(query, season_type, wins, extra):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "season_leaders"
    assert (kwargs["stat"], kwargs["season_type"]) == ("games_played", season_type)
    assert (kwargs["wins_only"], kwargs["losses_only"]) == (wins, not wins)
    for key, value in extra.items():
        assert kwargs[key] == value


@pytest.mark.parametrize(
    "query", ["most wins", "teams with the most wins", "Lakers most wins in a season"]
)
def test_team_wins_stay_team_boards(query):
    assert parse_query(query)["route"] != "season_leaders"


@pytest.mark.fixture_data
def test_player_playoff_wins_answer():
    result = execute_natural_query("most playoff wins by a player")
    assert result.result_status == "ok"
    rows = result.result.to_dict()["sections"]["leaderboard"]
    # Lakers and Nuggets players only; no one can exceed the series' games.
    assert rows and all(0 < row["games_played"] <= 7 for row in rows)


@pytest.mark.parametrize(
    "query",
    [
        "teams with the most wins when their best players rest",
        "most wins by a team with no all-star players",
    ],
)
def test_team_subject_with_players_word_stays_team_board(query):
    assert parse_query(query)["route"] == "team_record_leaderboard"


@pytest.mark.parametrize(
    "query",
    [
        "players with the most wins when facing elimination in the 2010s",
        "players with the most wins in game 7s in the 2010s",
        "players with the most playoff wins when facing elimination in the 2010s",
    ],
)
def test_playoff_situation_decades_are_not_shifted(query):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs["start_season"], kwargs["end_season"]) == ("2010-11", "2019-20")


def test_rookie_wins_keep_the_rookie_filter():
    kwargs = parse_query("players with the most wins as a rookie")["route_kwargs"]
    assert kwargs["rookies_only"] is True


@pytest.mark.fixture_data
def test_player_wins_show_the_count_in_pretty_output():
    from nbatools.commands.format_output import format_pretty_from_result

    query = "most playoff wins by a player"
    text = format_pretty_from_result(execute_natural_query(query).result, query)
    assert "games_played" in text


@pytest.mark.parametrize(
    ("query", "start", "end"),
    [
        ("most points in the finals in the 2010s", "2010-11", "2019-20"),
        ("most points in the conference finals in the 2010s", "2010-11", "2019-20"),
        ("most rebounds in the finals in the 2000s", "2000-01", "2009-10"),
        ("most points in game 7s in the 2010s", "2010-11", "2019-20"),
        ("most playoff points in the 2010s", "2010-11", "2019-20"),
        ("players with the most wins in the finals in the 2010s", "2010-11", "2019-20"),
    ],
)
def test_playoff_decades_start_at_the_decades_first_season(query, start, end):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs["start_season"], kwargs["end_season"]) == (start, end)


def test_wins_against_rookies_do_not_filter_to_rookies():
    kwargs = parse_query("players with the most wins against rookies")["route_kwargs"]
    assert not kwargs.get("rookies_only")
