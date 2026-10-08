"""C1: teams by season win total.

"how many teams have 40 wins" and "how many teams won 40 games last season"
did not route; "teams with 40 wins" listed a top 10 with no headline. The
count is the board's team seasons (every season since 1996-97 unless one is
named), listed with a headline. Expected values come from the fixture's team
rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")
SEASONS = ("2023-24", "2024-25", "2025-26")


def _season_wins(seasons=SEASONS) -> pd.DataFrame:
    frames = []
    for season in seasons:
        games = pd.read_csv(RAW / f"{season}_regular_season.csv")
        wins = games.groupby("team_abbr")["wl"].apply(lambda s: int((s == "W").sum()))
        frames.append(wins.rename("wins").reset_index().assign(season=season))
    return pd.concat(frames)


def _count(query: str) -> int:
    return execute_natural_query(query).result.to_dict()["sections"]["count"][0]["count"]


@pytest.mark.parametrize(
    ("query", "seasons", "keep"),
    [
        # Present tense is this season, as "how many teams have a winning record" is.
        ("how many teams have 40 wins", ("2025-26",), lambda w: w >= 40),
        ("how many teams have 40 wins this season", ("2025-26",), lambda w: w >= 40),
        ("how many teams have won 40 games", SEASONS, lambda w: w >= 40),
        ("how many teams won 40 games", SEASONS, lambda w: w >= 40),
        (
            "how many teams won 40 games in the last 2 seasons",
            ("2024-25", "2025-26"),
            lambda w: w >= 40,
        ),
        ("how many teams won 40 games last season", ("2024-25",), lambda w: w >= 40),
        ("how many teams had 40 wins in 2023-24", ("2023-24",), lambda w: w >= 40),
        ("how many teams finished with fewer than 20 wins", SEASONS, lambda w: w < 20),
        (
            "how many teams had between 40 and 45 wins since 2024",
            ("2024-25", "2025-26"),
            lambda w: (w >= 40) & (w <= 45),
        ),
    ],
)
def test_win_total_counts(query, seasons, keep):
    wins = _season_wins(seasons)
    assert _count(query) == int(keep(wins["wins"]).sum())


def test_win_total_list_is_every_team_season():
    # It was a top 10 (the bound was a filter, the row count a default).
    wins = _season_wins()
    result = execute_natural_query("teams with 40 wins")
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert len(rows) == int((wins["wins"] >= 40).sum())
    assert result.metadata["answer_phrase"].startswith(
        f"{int((wins['wins'] >= 40).sum())} team seasons have 40+ wins"
    )


def test_single_season_headline_names_teams():
    phrase = execute_natural_query("how many teams won 40 games last season").metadata[
        "count_phrase"
    ]
    assert phrase.startswith("3 teams have 40+ wins in the 2024-25 regular season")


@pytest.mark.parametrize(
    "query",
    ["how many teams have 40 wins at home", "how many teams have 40 wins and a losing record"],
)
def test_win_total_with_other_conditions_refuses(query):
    assert execute_natural_query(query).result_status == "no_result"


@pytest.mark.parametrize(
    "query",
    ["how many teams won 5 games in a row", "how many teams won 10 games in a row this season"],
)
def test_streak_counts_stay_on_the_streak_board(query):
    assert execute_natural_query(query).route == "team_streak_finder"


@pytest.mark.parametrize(
    "query", ["how many different teams won 40 games", "how many different teams have had 40 wins"]
)
def test_different_teams_count_franchises(query):
    wins = _season_wins()
    assert _count(query) == wins[wins["wins"] >= 40]["team_abbr"].nunique()


def test_two_named_seasons_refuse():
    # "in 2024-25 and 2025-26" was read as 2024-25 alone.
    result = execute_natural_query("how many teams won 40 games in 2024-25 and 2025-26")
    assert result.result_status == "no_result"


def test_span_headline_names_the_season_of_a_single_row():
    result = execute_natural_query("teams with at least 45 wins since 2024")
    assert "in 2025-26 (47-13)" in result.metadata["answer_phrase"]


@pytest.mark.parametrize(
    ("query", "keep"),
    [
        # Present tense is this season whatever the bound's wording.
        ("how many teams have at least 40 wins", lambda w: w >= 40),
        ("how many teams have 40+ wins", lambda w: w >= 40),
        ("how many teams have 45 or more wins", lambda w: w >= 45),
        ("how many teams have at most 20 wins", lambda w: w <= 20),
        ("how many teams have 40 wins this year", lambda w: w >= 40),
    ],
)
def test_present_tense_bounds_are_this_season(query, keep):
    wins = _season_wins(("2025-26",))
    assert _count(query) == int(keep(wins["wins"]).sum())


def test_a_40_win_season_is_any_season():
    wins = _season_wins()
    assert _count("how many teams have a 40 win season") == int((wins["wins"] >= 40).sum())


def test_over_the_last_seasons():
    wins = _season_wins(("2024-25", "2025-26"))
    assert _count("how many teams won 40 games over the last 2 seasons") == int(
        (wins["wins"] >= 40).sum()
    )


def test_list_with_two_named_seasons_refuses():
    result = execute_natural_query("teams with 40 wins in 2024-25 and 2025-26")
    assert result.result_status == "no_result"
