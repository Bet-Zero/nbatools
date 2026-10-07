"""C2 playoff appearances: wording, players, last appearance, runs and droughts.

"how many times have the Lakers made the playoffs" counted playoff games,
"how many Finals appearances does LeBron have" refused (team-grain only), and
"Lakers last playoff appearance", "consecutive playoff appearances" and
"playoff drought" answered only the appearance count. Expected values are
taken from the fixture CSVs, never from the engine.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands.playoff_history import _appearance_runs
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _playoff_teams() -> set[str]:
    games = pd.read_csv(RAW / "team_game_stats" / "2025-26_playoffs.csv")
    return set(games["team_abbr"])


def _ok(query: str):
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    assert result.metadata["route"] == "playoff_appearances"
    return result


@pytest.mark.parametrize(
    "query",
    [
        "how many times have the Lakers made the playoffs since 2000",
        "how many times have the Lakers made the playoffs",
        "Lakers playoff appearances",
    ],
)
def test_made_the_playoffs_counts_seasons(query):
    assert "LAL" in _playoff_teams()
    result = _ok(query)
    row = result.result.to_dict()["sections"]["summary"][0]
    assert row["appearances"] == 1  # the fixture's one postseason
    assert result.metadata["query_class"] != "count"
    assert "reached the playoffs 1 time" in result.metadata["answer_phrase"]


@pytest.mark.parametrize(
    ("query", "phrase"),
    [
        ("did the Celtics make the playoffs this season", "did not reach the playoffs in 2025-26"),
        ("did the Nuggets make the playoffs this season", "reached the playoffs in 2025-26"),
        ("Lakers last playoff appearance", "last reached the playoffs in 2025-26"),
        ("when did the Lakers last make the playoffs", "last reached the playoffs in 2025-26"),
    ],
)
def test_single_season_and_last_appearance(query, phrase):
    assert {"DEN", "LAL"} <= _playoff_teams() and "BOS" not in _playoff_teams()
    assert phrase in _ok(query).metadata["answer_phrase"]


def test_drought_and_misses_count_regular_seasons_played():
    # Boston played all three fixture seasons and reached no fixture playoffs.
    seasons = {
        path.name[:7]
        for path in (RAW / "team_game_stats").glob("*_regular_season.csv")
        if (pd.read_csv(path)["team_abbr"] == "BOS").any()
    }
    result = _ok("how many times did the Celtics miss the playoffs since 2023")
    row = result.result.to_dict()["sections"]["summary"][0]
    assert row["missed"] == len(seasons) == 3
    assert row["seasons_since_last"] == 3
    drought = _ok("Celtics playoff drought").metadata["answer_phrase"]
    assert "missed the playoffs the last 3 seasons" in drought


def test_appearance_runs_by_hand():
    played = ["2010-11", "2011-12", "2012-13", "2013-14", "2014-15", "2015-16", "2016-17"]
    appeared = ["2010-11", "2012-13", "2013-14", "2014-15", "2016-17"]
    runs = _appearance_runs(appeared, played)
    assert runs["longest_streak"] == 3
    assert (runs["longest_streak_start"], runs["longest_streak_end"]) == ("2012-13", "2014-15")
    assert runs["current_streak"] == 1
    assert runs["missed"] == 2
    assert runs["longest_drought"] == 1
    assert runs["seasons_since_last"] == 0
    assert runs["last_appearance"] == "2016-17"


def test_player_appearances_count_seasons_with_a_game():
    games = pd.read_csv(RAW / "player_game_stats" / "2025-26_playoffs.csv")
    lebron = games[(games["player_name"] == "LeBron James") & (games["minutes"] > 0)]
    assert not lebron.empty

    result = _ok("how many times has LeBron made the playoffs")
    row = result.result.to_dict()["sections"]["leaderboard"][0]
    assert row["player_name"] == "LeBron James"
    assert row["appearances"] == lebron["season"].nunique()
    assert "LeBron James reached the playoffs in 1 season" in result.metadata["answer_phrase"]


def test_player_with_no_finals_answers_zero():
    result = _ok("how many finals appearances does LeBron have")
    row = result.result.to_dict()["sections"]["leaderboard"][0]
    assert row["appearances"] == 0
    assert "did not reach the Finals" in result.metadata["answer_phrase"]


def test_player_board_ranks_players():
    games = pd.read_csv(RAW / "player_game_stats" / "2025-26_playoffs.csv")
    players = games[games["minutes"] > 0]["player_id"].nunique()
    result = _ok("which player has the most playoff appearances")
    rows = result.result.to_dict()["sections"]["leaderboard"]
    # Every fixture playoff player has one season, so all tie for first.
    assert len(rows) == players
    assert {row["appearances"] for row in rows} == {1}


def test_consecutive_board_ranks_franchise_runs():
    result = _ok("most consecutive playoff appearances")
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert {row["team_abbr"] for row in rows} == _playoff_teams()
    assert {row["longest_streak"] for row in rows} == {1}


def _teams(season: str, kind: str) -> set[str]:
    return set(pd.read_csv(RAW / "team_game_stats" / f"{season}_{kind}.csv")["team_name"])


def test_which_teams_missed_the_playoffs_lists_the_teams_that_missed():
    missed = _teams("2025-26", "regular_season") - _teams("2025-26", "playoffs")
    result = _ok("which teams missed the playoffs")
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert {row["team_name"] for row in rows} == missed
    assert result.metadata["answer_phrase"].startswith(f"{len(missed)} teams missed the playoffs")


def test_which_teams_made_the_playoffs_lists_the_latest_postseason():
    result = _ok("which teams made the playoffs")
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert {row["team_name"] for row in rows} == _teams("2025-26", "playoffs")


def test_league_drought_ranks_droughts_not_runs():
    result = _ok("which team has the longest playoff drought")
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert "longest_drought" in rows[0]
    # Teams that never reached the fixture's one postseason tie at 3 seasons.
    missed = _teams("2025-26", "regular_season") - _teams("2025-26", "playoffs")
    assert {row["team_name"] for row in rows if row["longest_drought"] == 3} == missed
    assert "longest drought without reaching the playoffs" in result.metadata["answer_phrase"]


def test_tied_runs_name_every_team():
    phrase = _ok("most consecutive playoff appearances").metadata["answer_phrase"]
    assert "the Denver Nuggets and the Los Angeles Lakers share" in phrase.replace("The ", "the ")


def test_player_run_and_miss_questions_use_his_seasons():
    games = pd.concat(
        pd.read_csv(path) for path in (RAW / "player_game_stats").glob("*_regular_season.csv")
    )
    seasons = set(games[games["player_name"] == "LeBron James"]["season"])
    assert len(seasons) == 3
    missed = _ok("LeBron missed the playoffs").metadata["answer_phrase"]
    assert "LeBron James missed the playoffs in 2 of 3 seasons" in missed
    run = _ok("LeBron consecutive playoff appearances").metadata["answer_phrase"]
    assert "longest run" in run and "1 season in the playoffs (2025-26)" in run


def test_fewest_appearances_ranks_from_zero():
    missed = _teams("2025-26", "regular_season") - _teams("2025-26", "playoffs")
    result = _ok("fewest playoff appearances")
    rows = result.result.to_dict()["sections"]["leaderboard"]
    zeros = {row["team_name"] for row in rows if row["appearances"] == 0}
    assert zeros == missed
    assert [row["appearances"] for row in rows] == sorted(row["appearances"] for row in rows)
    assert "fewest times" in result.metadata["answer_phrase"]


def test_teams_that_missed_as_the_subject_is_a_question():
    missed = _teams("2025-26", "regular_season") - _teams("2025-26", "playoffs")
    rows = _ok("teams that missed the playoffs in 2025-26").result.to_dict()["sections"][
        "leaderboard"
    ]
    assert {row["team_name"] for row in rows} == missed


def test_against_teams_that_made_the_playoffs_stays_an_opponent_filter():
    result = execute_natural_query("Lakers record against teams that made the playoffs")
    assert result.metadata["route"] == "team_record"


def test_a_stated_top_n_never_cuts_a_tie_at_the_fewest():
    missed = _teams("2025-26", "regular_season") - _teams("2025-26", "playoffs")
    result = _ok("top 2 teams with the fewest playoff appearances")
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert {row["team_name"] for row in rows} == missed
    for name in missed:
        assert name in result.metadata["answer_phrase"]
