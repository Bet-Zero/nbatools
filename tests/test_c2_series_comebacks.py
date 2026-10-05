"""C2 series comebacks: "teams that came back from 3-1 down", "blew a 3-1 lead".

They refused. Each is now the list of series a team won after trailing by
that score (or lost after leading by it).

Fixture: the 2025-26 Lakers-Nuggets series, relabelled as the 2000-01 first
round (best of five) with the Lakers losing games 1 and 2 and winning 3-5, so
the Lakers came back from 2-0 down and the Nuggets blew a 2-0 lead.
"""

from __future__ import annotations

import pytest

import nbatools.commands.playoff_history as playoff_history
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


@pytest.fixture
def comeback(monkeypatch):
    load = playoff_history._load_playoff_games

    def series(seasons):
        games = load(["2025-26"])
        games = games[games["game_id"].astype(int) <= 545].copy()
        games["season"] = "2000-01"
        lakers_won = dict(zip(sorted(games["game_id"].unique()), [False, False, True, True, True]))
        on_lakers = games["team_abbr"].eq("LAL")
        games["wl"] = [
            "W" if lakers_won[game] == lakers else "L"
            for game, lakers in zip(games["game_id"], on_lakers)
        ]
        return games

    monkeypatch.setattr(playoff_history, "_load_playoff_games", series)


@pytest.mark.parametrize(
    ("query", "wins", "losses", "blown", "team"),
    [
        ("teams that came back from 3-1 down", 1, 3, False, None),
        ("3-1 comebacks", 1, 3, False, None),
        ("how many teams have come back from 3-0 down", 0, 3, False, None),
        ("which teams have blown a 3-1 lead", 3, 1, True, None),
        ("have the Celtics ever come back from 3-1", 1, 3, False, "BOS"),
        ("Warriors blew a 3-1 lead", 3, 1, True, "GSW"),
    ],
)
def test_comeback_questions_route_to_series_list(query, wins, losses, blown, team):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "playoff_series_comebacks"
    assert (kwargs["deficit_wins"], kwargs["deficit_losses"]) == (wins, losses)
    assert (kwargs["blown"], kwargs["team"]) == (blown, team)
    assert (kwargs["start_season"], kwargs["end_season"]) == ("1996-97", "2025-26")
    assert "default: every playoff season since 1996-97" in parsed["notes"]
    assert not parsed.get("count_intent")


@pytest.mark.parametrize(
    ("query", "season"),
    [
        ("teams that came back from 3-1 down this season", "2025-26"),
        ("teams that came back from 3-1 down last season", "2024-25"),
        ("teams that came back from 3-1 in the 2016 playoffs", "2015-16"),
        ("Warriors blew a 3-1 lead in 2016", "2015-16"),
    ],
)
def test_named_season_is_one_playoffs(query, season):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs["season"], kwargs["start_season"]) == (season, None)


def test_structured_call_without_a_span_covers_every_season(comeback):
    from nbatools.query_service import execute_structured_query

    result = execute_structured_query("playoff_series_comebacks", deficit_wins=0, deficit_losses=2)
    assert result.result_status == "ok", result.result_reason
    assert result.result.metadata["first_season"] == "1996-97"


def test_this_season_headline_names_the_season(monkeypatch):
    load = playoff_history._load_playoff_games

    def series(seasons):
        # The real 2025-26 first round is best of seven: Lakers lose 1-2, win 3-6.
        games = load(["2025-26"]).copy()
        results = [False, False, True, True, True, True]
        lakers_won = dict(zip(sorted(games["game_id"].unique()), results))
        on_lakers = games["team_abbr"].eq("LAL")
        games["wl"] = [
            "W" if lakers_won[game] == lakers else "L"
            for game, lakers in zip(games["game_id"], on_lakers)
        ]
        return games

    monkeypatch.setattr(playoff_history, "_load_playoff_games", series)
    result = execute_natural_query("teams that came back from 2-0 down this season")
    assert result.result_status == "ok", result.result_reason
    assert result.metadata["answer_phrase"].startswith(
        "Teams came back from 2-0 down in 1 series in 2025-26:"
    )


@pytest.mark.parametrize(
    ("query", "team", "playoff_round"),
    [
        ("Warriors 3-1 collapse", "GSW", None),
        ("Warriors collapsed from 3-1", "GSW", None),
        ("teams that came back from 3-1 down to win the series", None, None),
        ("teams that came back from 3-1 down and won the series", None, None),
        ("teams that came back from 3-1 down in nba history", None, None),
        ("teams that came back from a 3-0 hole", None, None),
        ("how often have teams come back from 3-1", None, None),
        ("teams that came back from 3-1 in the conference semifinals", None, "02"),
        ("Thunder blew a 3-1 lead in the western conference finals", "OKC", "03"),
    ],
)
def test_everyday_comeback_wording_answers(query, team, playoff_round):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "playoff_series_comebacks"
    assert (kwargs["team"], kwargs["playoff_round"]) == (team, playoff_round)


def test_round_span_and_opponent_are_kept():
    kwargs = parse_query("teams that came back from 3-1 down in the Finals")["route_kwargs"]
    assert kwargs["playoff_round"] == "04"
    kwargs = parse_query("teams that came back from 3-1 since 2010")["route_kwargs"]
    assert kwargs["start_season"] == "2010-11"
    kwargs = parse_query("Lakers came back from 3-1 against the Nuggets")["route_kwargs"]
    assert (kwargs["team"], kwargs["opponent"]) == ("LAL", "DEN")


@pytest.mark.parametrize(
    "query",
    [
        "LeBron James came back from 3-1 down",
        "players who came back from 3-1 down",
        "Lakers vs Nuggets came back from 3-1",
        "teams that came back from 3-1 down at home",
        "coaches who came back from 3-1",
        "teams that came back from 3-1 in the regular season",
        # A count, ranking or qualifier the series list cannot honour.
        "which team has the most 3-1 comebacks",
        "teams that came back from 3-1 down twice",
        "top 5 3-1 comebacks",
        "teams that came back from 2-0 down in game 7",
        "teams that came back from 2-0 down and won in 6",
        "teams that came back from 3-1 down with Jordan Poole",
        "teams that came back from 3-1 down in the 4th quarter",
        "teams that came back from 3-1 down in March",
        "western conference teams that came back from 3-1",
        "lower seeds that came back from 2-0",
        "last time a team came back from 3-1",
        "teams that came back from 3-1 down 2 times",
        "teams that came back from 3-1 down 3 times",
        "teams that came back from 3-1 down in 2",
        # Span words the parser does not resolve must not fall back to every season.
        "teams that came back from 3-1 through 2005",
        "teams that came back from 3-1 until 2010",
        "teams that came back from 3-1 to 2010",
        "Celtics came back from 3-1 from 2008",
        "teams that came back from 3-1 and won the championship",
        "teams that came back from 3-1 to win the finals",
        "teams that came back from 3-1 in the western conference finals",
    ],
)
def test_comeback_questions_the_list_cannot_answer_refuse(query):
    parsed = parse_query(query)
    assert parsed["route"] is None
    assert parsed["route_kwargs"]["unsupported_filters"] == ["series_comeback"]


def test_comeback_lists_the_series_won_after_trailing(comeback):
    result = execute_natural_query("teams that came back from 2-0 down in 2001")
    assert result.result_status == "ok", result.result_reason
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert len(rows) == 1
    row = rows[0]
    assert (row["team_abbr"], row["opponent_team_abbr"]) == ("LAL", "DEN")
    assert (row["trailed"], row["series"], row["result"]) == ("0-2", "3-2", "Won")
    assert result.metadata["answer_phrase"] == (
        "Teams came back from 2-0 down in 1 series in 2000-01: the 2000-01 Los Angeles "
        "Lakers (First Round vs the Denver Nuggets, won 3-2)."
    )


def test_blown_lead_lists_the_series_lost_after_leading(comeback):
    result = execute_natural_query("teams that blew a 2-0 lead in 2001")
    row = result.result.to_dict()["sections"]["leaderboard"][0]
    assert (row["team_abbr"], row["led"], row["series"], row["result"]) == (
        "DEN",
        "2-0",
        "2-3",
        "Lost",
    )


def test_named_team_headline_counts_its_comebacks(comeback):
    result = execute_natural_query("Lakers came back from 0-2 in 2001")
    assert result.metadata["answer_phrase"] == (
        "The Los Angeles Lakers came back from 2-0 down once in 2000-01: 2000-01 First "
        "Round vs the Denver Nuggets (won 3-2)."
    )


def test_team_that_never_did_it_is_no_match(comeback):
    result = execute_natural_query("have the Nuggets ever come back from 2-0 down in 2001")
    assert result.result_status == "no_result"
    assert result.result_reason == "no_match"
    assert (
        "The Denver Nuggets never came back from 2-0 down in a playoff series in 2000-01"
        in result.metadata["notes"]
    )


def test_no_match_note_names_the_round_and_opponent(comeback):
    result = execute_natural_query(
        "Lakers came back from 0-2 against the Nuggets in the Finals in 2001"
    )
    assert result.result_reason == "no_match"
    assert (
        "The Los Angeles Lakers never came back from 2-0 down in a playoff series against "
        "the Denver Nuggets in the Finals in 2000-01" in result.metadata["notes"]
    )


def test_score_the_series_never_reached_is_no_match(comeback):
    result = playoff_history.build_series_comebacks_result(
        deficit_wins=1, deficit_losses=3, season="2000-01"
    )
    assert result.result_reason == "no_match"


def test_unfinished_series_is_not_a_comeback(monkeypatch):
    load = playoff_history._load_playoff_games

    def cut(seasons):
        games = load(["2025-26"])
        games = games[games["game_id"].astype(int) <= 543].copy()
        games["season"] = "2000-01"
        on_lakers = games["team_abbr"].eq("LAL")
        lakers_won = dict(zip(sorted(games["game_id"].unique()), [False, False, True]))
        games["wl"] = [
            "W" if lakers_won[game] == lakers else "L"
            for game, lakers in zip(games["game_id"], on_lakers)
        ]
        return games

    monkeypatch.setattr(playoff_history, "_load_playoff_games", cut)
    result = playoff_history.build_series_comebacks_result(
        deficit_wins=0, deficit_losses=2, season="2000-01"
    )
    assert result.result_reason == "no_match"
