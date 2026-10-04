"""Conference/division opponents against the real 1996-97+ game rows.

Companion to ``test_opponent_groups.py`` (fixture). The historical alignment
table is checked against the schedule itself: teams in different conferences
meet at most twice a season (three times with an NBA Cup final), so a pair
that met four or more times must share a conference, and since 2004-05
division rivals meet four times in a full 82-game season. Expected query
answers are counted from the raw rows with plain pandas.
"""

from __future__ import annotations

import pandas as pd
import pytest

from nbatools.commands._nba_alignment import historical_alignment
from nbatools.data_source import data_exists, data_read_csv

pytestmark = [pytest.mark.needs_data, pytest.mark.query]

SEASONS = [f"{year}-{str(year + 1)[-2:]}" for year in range(1996, 2026)]
SHORT_SEASONS = {"1998-99", "2011-12", "2019-20", "2020-21"}


def _team_games(season: str) -> pd.DataFrame:
    path = f"raw/team_game_stats/{season}_regular_season.csv"
    if not data_exists(path):
        pytest.skip(f"{season} not served")
    frame = data_read_csv(path, dtype={"game_id": str})
    frame["team_id"] = pd.to_numeric(frame["team_id"]).astype(int)
    frame["opponent_team_id"] = pd.to_numeric(frame["opponent_team_id"]).astype(int)
    return frame


@pytest.mark.parametrize("season", SEASONS)
def test_alignment_covers_every_team_and_matches_the_schedule(season):
    games = _team_games(season)
    alignment = historical_alignment(season)

    assert set(games["team_id"]) == set(alignment), season

    meetings = games.groupby(["team_id", "opponent_team_id"]).size()
    for (team, opponent), count in meetings.items():
        same_conference = alignment[team][0] == alignment[opponent][0]
        if count >= 4:
            assert same_conference, (season, team, opponent, count)
        if not same_conference:
            assert count <= 3, (season, team, opponent, count)

    if season >= "2004-05" and season not in SHORT_SEASONS:
        for (team, opponent), count in meetings.items():
            if alignment[team] == alignment[opponent]:
                assert count >= 4, (season, team, opponent, count)


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def test_lebron_career_vs_the_west_counts_each_season():
    expected = 0
    for season in SEASONS:
        path = f"raw/player_game_stats/{season}_regular_season.csv"
        if not data_exists(path):
            continue
        rows = data_read_csv(path, dtype={"game_id": str})
        rows = rows[rows["player_name"] == "LeBron James"]
        if rows.empty:
            continue
        west = {
            team_id
            for team_id, (conference, _) in historical_alignment(season).items()
            if conference == "West"
        }
        opponents = pd.to_numeric(rows["opponent_team_id"]).astype(int)
        expected += int(opponents.isin(west).sum())

    result = _run("LeBron James career stats vs Western conference teams")
    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert summary["games"] == expected


def test_lakers_record_vs_winning_teams_is_season_by_season():
    seasons = SEASONS[-5:]
    expected_games = expected_wins = 0
    for season in seasons:
        games = _team_games(season)
        records = games.groupby("team_id")["wl"].apply(lambda wl: (wl == "W").mean())
        winning = set(records[records >= 0.5].index)
        lakers = games[games["team_abbr"] == "LAL"]
        lakers = lakers[lakers["opponent_team_id"].isin(winning)]
        expected_games += len(lakers)
        expected_wins += int((lakers["wl"] == "W").sum())

    result = _run(f"Lakers record vs winning teams from {seasons[0]} to {seasons[-1]}")
    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert summary["games"] == expected_games
    assert summary["wins"] == expected_wins


def test_pacific_division_before_2004_has_seven_teams():
    games = _team_games("2000-01")
    pacific = {
        team_id
        for team_id, (_, division) in historical_alignment("2000-01").items()
        if division == "Pacific"
    }
    lakers = games[(games["team_abbr"] == "LAL") & games["opponent_team_id"].isin(pacific)]

    result = _run("Lakers record vs Pacific division teams 2000-01")
    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert summary["games"] == len(lakers)
    assert summary["wins"] == int((lakers["wl"] == "W").sum())
