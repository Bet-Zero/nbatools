"""C2 stats by playoff round: "LeBron stats in the Finals", "most points in the first round".

Player and leaderboard questions naming a round refused (player_playoff_round)
or dropped the round. The round now filters the games as a series situation,
every playoff season since 1996-97 unless a span is named. Team round records
keep their own playoff routes.

Fixture: the 2025-26 Lakers-Nuggets first round (game ids 541-546, Lakers 5-1).
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.commands.playoff_history import series_situation_label
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


@pytest.mark.parametrize(
    ("query", "route", "situation"),
    [
        ("LeBron stats in the Finals", "player_game_summary", "round_04"),
        ("Jokic first-round averages", "player_game_summary", "round_01"),
        ("LeBron finals game 7 stats", "player_game_summary", "game_7@04"),
        ("LeBron Finals stats", "player_game_summary", "round_04"),
        ("LeBron Finals averages", "player_game_summary", "round_04"),
        ("Jokic stats in the conference finals", "player_game_summary", "round_03"),
        ("Jokic game 7 stats in the second round", "player_game_summary", "game_7@02"),
        ("Lakers record in game 7s in the Finals", "team_record", "game_7@04"),
        ("who scored the most points in the first round", "season_leaders", "round_01"),
    ],
)
def test_round_filters_games_every_playoff_season(query, route, situation):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == route
    assert kwargs["series_situation"] == situation
    assert (kwargs["start_season"], kwargs["end_season"]) == ("1996-97", "2025-26")
    assert not kwargs.get("unsupported_filters")


@pytest.mark.parametrize(
    ("query", "season", "start"),
    [
        ("LeBron stats in the 2016 Finals", "2015-16", None),
        ("most rebounds in the first round this season", "2025-26", None),
        ("most rebounds in the first round last season", "2024-25", None),
        ("LeBron stats in the Finals last season", "2024-25", None),
        ("who scored the most points in the Finals since 2000", None, "2000-01"),
    ],
)
def test_named_span_is_kept(query, season, start):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["series_situation"].endswith(("_04", "_01"))
    assert (kwargs["season"], kwargs["start_season"]) == (season, start)


def test_round_leaders_default_to_totals():
    kwargs = parse_query("who scored the most points in the Finals since 2000")["route_kwargs"]
    assert kwargs["stat"] == "pts_total"


@pytest.mark.parametrize(
    ("query", "route"),
    [
        ("Lakers record in the Finals", "playoff_history"),
        ("Lakers first round record", "playoff_history"),
        ("Lakers vs Celtics Finals history", "playoff_matchup_history"),
    ],
)
def test_team_round_records_keep_their_routes(query, route):
    parsed = parse_query(query)
    assert parsed["route"] == route
    assert not parsed["route_kwargs"].get("series_situation")


def test_labels_name_the_round():
    assert series_situation_label("round_04") == "Finals games"
    assert series_situation_label("game_7@04") == "game 7s in the Finals"


def test_player_round_stats_use_only_that_rounds_games():
    result = execute_natural_query("LeBron stats in the first round this season")
    assert result.result_status == "ok", result.result_reason
    sections = result.result.to_dict()["sections"]
    summary = sections["summary"][0]
    assert (summary["games"], summary["wins"], summary["losses"]) == (6, 5, 1)
    assert sorted(int(g) for g in {row["game_id"] for row in sections["game_log"]}) == list(
        range(541, 547)
    )


def test_round_the_player_never_reached_is_no_match():
    result = execute_natural_query("LeBron Finals stats")
    assert result.result_status == "no_result"


def test_team_record_in_a_rounds_game_number():
    result = execute_natural_query("Lakers record in game 6s in the first round")
    summary = result.result.to_dict()["sections"]["summary"][0]
    assert (summary["games"], summary["wins"], summary["losses"]) == (1, 1, 0)


def test_round_leaderboard_totals_that_rounds_games():
    result = execute_natural_query("most rebounds in the first round this season")
    assert result.result_status == "ok", result.result_reason
    top = result.result.to_dict()["sections"]["leaderboard"][0]
    assert (top["player_name"], top["games_played"], top["reb_total"]) == ("Nikola Jokić", 6, 79)


@pytest.mark.parametrize(
    "query",
    [
        # Exclusions, several rounds, a conference half, awards, draft picks,
        # teams that reached a round, trips, single games and relative seasons
        # the parser misses: never answer only one round's games.
        "Jokic playoff stats excluding the first round",
        "Jokic stats outside the finals",
        "Jokic non-finals playoff stats",
        "Jokic stats before the finals",
        "Jokic stats in the first round and second round",
        "Jokic stats in the finals and conference finals",
        "LeBron western conference finals stats",
        "most points in the western conference finals",
        "Jokic stats in the west finals",
        "Jokic stats in the east semis",
        "most points in a finals game",
        "highest scoring finals game",
        "LeBron finals mvp",
        "LeBron stats against finals teams",
        "how many finals has LeBron been to",
        "LeBron stats as a first round pick",
        "LeBron stats in the most recent finals",
        "LeBron finals stats two years ago",
        "LeBron best finals game",
        # Round words framed as anything but "in the <round>" / "<round> stats".
        "Jokic stats in the first and second round",
        "Jokic stats beyond the first round",
        "LeBron stats in every round but the finals",
        "LeBron playoff stats apart from the finals",
        "LeBron stats leading up to the finals",
        "LeBron stats through the conference finals",
        "LeBron stats in his first finals",
        "LeBron stats in the 2016 and 2018 finals",
        "LeBron stats in the 2016 finals and 2018 finals",
        "Jokic first round series wins",
        "Jokic stats in first round exits",
        "LeBron first round series record",
        "number of finals LeBron played in",
        "LeBron vs Jokic in the finals",
        # The round dates a clause, not the games asked about.
        "LeBron stats in years he lost in the finals",
        "LeBron playoff stats in years he was in the finals",
        "LeBron stats in runs that ended in the finals",
        "Jokic playoff stats when he lost in the first round",
        "LeBron stats in the playoffs aside from games in the finals",
        "LeBron stats since he played in the finals",
        "LeBron stats since the 2016 finals",
    ],
)
def test_round_words_that_are_not_a_round_filter_never_filter(query):
    parsed = parse_query(query)
    situation = (parsed.get("route_kwargs") or {}).get("series_situation")
    assert not (situation and ("round_" in situation or "@" in situation))


def test_finals_game_number_still_filters():
    kwargs = parse_query("LeBron finals game 7 stats")["route_kwargs"]
    assert kwargs["series_situation"] == "game_7@04"


@pytest.mark.parametrize(
    ("query", "situation"),
    [
        ("most points in game 1 of the finals", "game_1@04"),
        ("most points in game 7s of the conference finals", "game_7@03"),
        ("most points in elimination games in the finals", "elimination@04"),
        ("LeBron stats in game 6 of the finals", "game_6@04"),
        ("Lakers record in game 1 of the finals", "game_1@04"),
        ("Jokic stats in the conference semifinals", "round_02"),
    ],
)
def test_situation_within_a_round_keeps_both(query, situation):
    assert parse_query(query)["route_kwargs"]["series_situation"] == situation


def test_leaderboard_never_drops_a_round_it_did_not_apply():
    # "years he lost in the finals" is not a round filter, so a board must not
    # answer it over every round either.
    parsed = parse_query("most points in years he lost in the finals")
    assert parsed["route_kwargs"].get("unsupported_filters")
