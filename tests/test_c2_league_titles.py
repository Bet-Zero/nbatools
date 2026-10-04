"""C2 league title leaderboard: "which team has won the most titles since 2000".

A title is a Finals series won. The parse tests need no data; the table and
headline tests build Finals game rows by hand and count them independently.
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands import playoff_history
from nbatools.commands.natural_query import parse_query
from nbatools.commands.structured_results import LeaderboardResult
from nbatools.query_service import _add_titles_leaderboard_answer_metadata

pytestmark = pytest.mark.engine

TEAMS = {
    "GSW": (1610612744, "Golden State Warriors"),
    "CLE": (1610612739, "Cleveland Cavaliers"),
    "SAS": (1610612759, "San Antonio Spurs"),
    "MIA": (1610612748, "Miami Heat"),
}


def _finals(season: str, winner: str, loser: str, loser_wins: int) -> list[dict]:
    """Both teams' rows for a best-of-7 Finals the winner takes 4-loser_wins."""
    results = ["L"] * loser_wins + ["W"] * 4
    rows = []
    year = int(season[:4]) + 1
    for i, wl in enumerate(results):
        date = f"{year}-06-{i + 1:02d}"
        for team, opp, mark in ((winner, loser, wl), (loser, winner, "L" if wl == "W" else "W")):
            rows.append(
                {
                    "season": season,
                    "team_abbr": team,
                    "team_name": TEAMS[team][1],
                    "opponent_team_id": TEAMS[opp][0],
                    "opponent_team_name": TEAMS[opp][1],
                    "opponent_team_abbr": opp,
                    "playoff_round_code": "04",
                    "wl": mark,
                    "game_date": date,
                }
            )
    return rows


def _board(rows: list[dict], seasons: list[str]) -> LeaderboardResult:
    result = playoff_history._titles_leaderboard(pd.DataFrame(rows), seasons, limit=30, caveats=[])
    assert isinstance(result, LeaderboardResult)
    return result


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("query", "season", "start", "limit"),
    [
        ("which team has won the most titles since 1997", None, "1997-98", 30),
        ("top 3 teams with the most titles", None, "1996-97", 3),
        ("which team has the most championships", None, "1996-97", 30),
        ("nba champions since 2010", None, "2010-11", 30),
        ("title winners since 2015", None, "2015-16", 30),
        ("who won the title in 2016", "2015-16", None, 30),
        ("who was the champion in 2016", "2015-16", None, 30),
        ("the 2016 champions", "2015-16", None, 30),
    ],
)
def test_league_title_questions_route_to_titles_leaderboard(query, season, start, limit):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "playoff_appearances"
    assert kwargs["titles"] is True
    assert kwargs["playoff_round"] == "04"
    assert kwargs["season"] == season
    assert kwargs["start_season"] == start
    assert kwargs["limit"] == limit


@pytest.mark.parametrize(
    "query",
    [
        "who has the most rings",
        "who won the most titles",
        "which player has the most titles",
        "which team has the most titles with kobe",
        "conference champions since 2010",
        "eastern conference champions",
        "which team has the most division titles",
    ],
)
def test_player_and_non_league_titles_still_refuse(query):
    parsed = parse_query(query)
    assert parsed.get("route") is None
    assert "championship_count" in parsed["route_kwargs"]["unsupported_filters"]


def test_named_team_champions_wording_counts_that_teams_titles():
    parsed = parse_query("were the lakers champions in 2010")
    assert parsed["route"] == "playoff_history"
    assert parsed["route_kwargs"]["team"] == "LAL"
    assert parsed["route_kwargs"]["season"] == "2009-10"


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------


def test_titles_leaderboard_counts_finals_series_won():
    rows = (
        _finals("2015-16", "CLE", "GSW", 3)
        + _finals("2016-17", "GSW", "CLE", 1)
        + _finals("2017-18", "GSW", "CLE", 0)
    )
    board = _board(rows, ["2015-16", "2016-17", "2017-18"]).leaders
    assert list(board["team_abbr"]) == ["GSW", "CLE"]
    assert list(board["titles"]) == [2, 1]
    assert list(board["finals_appearances"]) == [3, 3]
    assert board["title_seasons"].iloc[0] == "2016-17, 2017-18"
    assert board["seasons"].iloc[0] == "2015-16 to 2017-18"
    assert "finals_opponent" not in board


def test_titles_leaderboard_drops_finals_losers_without_a_title():
    rows = _finals("2012-13", "MIA", "SAS", 3) + _finals("2013-14", "SAS", "MIA", 1)
    rows += _finals("2016-17", "GSW", "CLE", 1)
    board = _board(rows, ["2012-13", "2013-14", "2016-17"]).leaders
    assert "CLE" not in set(board["team_abbr"])
    # Ties on titles: fewer Finals trips first, then the name.
    assert list(board["team_abbr"]) == ["GSW", "MIA", "SAS"]


def test_unfinished_finals_is_not_a_title():
    rows = _finals("2015-16", "CLE", "GSW", 3)[:6]  # 3-0 so far
    result = playoff_history._titles_leaderboard(
        pd.DataFrame(rows), ["2015-16"], limit=30, caveats=[]
    )
    assert result.result_status == "no_result"


# ---------------------------------------------------------------------------
# Headline
# ---------------------------------------------------------------------------


def _phrase(result: LeaderboardResult, **metadata) -> str:
    meta = {"route": "playoff_appearances", **metadata}
    _add_titles_leaderboard_answer_metadata(meta, result)
    return meta["answer_phrase"]


def test_headline_names_the_leader_with_title_seasons():
    rows = (
        _finals("2015-16", "CLE", "GSW", 3)
        + _finals("2016-17", "GSW", "CLE", 1)
        + _finals("2017-18", "GSW", "CLE", 0)
    )
    result = _board(rows, ["2015-16", "2016-17", "2017-18"])
    assert _phrase(result, start_season="2015-16", end_season="2017-18") == (
        "The Golden State Warriors won the most titles from 2015-16 to 2017-18: "
        "2 titles (2016-17, 2017-18)."
    )


def test_headline_lists_every_team_tied_for_most():
    rows = _finals("2012-13", "MIA", "SAS", 3) + _finals("2013-14", "SAS", "MIA", 1)
    result = _board(rows, ["2012-13", "2013-14"])
    assert _phrase(result, start_season="2012-13", end_season="2013-14") == (
        "The Miami Heat and the San Antonio Spurs tied for the most titles "
        "from 2012-13 to 2013-14, with 1 title each."
    )


def test_single_season_headline_names_the_finals_opponent():
    result = _board(_finals("2015-16", "CLE", "GSW", 3), ["2015-16"])
    assert _phrase(result, season="2015-16") == (
        "The Cleveland Cavaliers won the 2015-16 title, beating the "
        "Golden State Warriors 4-3 in the Finals."
    )


def test_headline_never_counts_from_before_the_data():
    rows = _finals("2016-17", "GSW", "CLE", 1)
    result = _board(rows, ["1990-91", "2016-17"])
    phrase = _phrase(result, start_season="1990-91", end_season="2016-17")
    assert "from 1996-97 (where the data starts) to 2016-17" in phrase
