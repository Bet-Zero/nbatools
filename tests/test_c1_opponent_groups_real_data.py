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


def test_celtics_playoff_record_vs_atlantic_2024_25():
    path = "raw/team_game_stats/2024-25_playoffs.csv"
    if not data_exists(path):
        pytest.skip("2024-25 playoffs not served")
    games = data_read_csv(path, dtype={"game_id": str})
    atlantic = {
        team_id
        for team_id, (_, division) in historical_alignment("2024-25").items()
        if division == "Atlantic"
    }
    celtics = games[(games["team_abbr"] == "BOS") & games["opponent_team_id"].isin(atlantic)]

    result = _run("Celtics playoff record vs Atlantic Division 2024-25")
    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert summary["games"] == len(celtics)
    assert summary["wins"] == int((celtics["wl"] == "W").sum())


def test_lakers_vs_warriors_last_10_are_their_ten_latest_meetings():
    frames = [_team_games(season) for season in SEASONS[-6:]]
    games = pd.concat(frames)
    meetings = games[(games["team_abbr"] == "LAL") & (games["opponent_team_abbr"] == "GSW")]
    meetings = meetings.sort_values(["game_date", "game_id"], ascending=False).head(10)

    result = _run("Lakers vs Warriors last 10 games")
    lakers, warriors = result.result.to_dict()["sections"]["summary"]
    assert lakers["games"] == warriors["games"] == 10
    assert lakers["wins"] == int((meetings["wl"] == "W").sum())
    assert warriors["wins"] == 10 - lakers["wins"]


def test_pair_last_10_vs_a_third_team():
    games = pd.concat([_team_games(season) for season in SEASONS[-8:]])
    result = _run("Lakers and Warriors last 10 games vs the Celtics")
    lakers, warriors = result.result.to_dict()["sections"]["summary"]
    for side, abbr in ((lakers, "LAL"), (warriors, "GSW")):
        rows = games[(games["team_abbr"] == abbr) & (games["opponent_team_abbr"] == "BOS")]
        rows = rows.sort_values(["game_date", "game_id"], ascending=False).head(10)
        assert side["games"] == 10
        assert side["wins"] == int((rows["wl"] == "W").sum())


def test_division_and_winning_teams_both_apply():
    games = _team_games("2024-25")
    records = games.groupby("team_id")["wl"].apply(lambda wl: (wl == "W").mean())
    winning = set(records[records >= 0.5].index)
    atlantic = {
        team_id
        for team_id, (_, division) in historical_alignment("2024-25").items()
        if division == "Atlantic"
    }
    celtics = games[
        (games["team_abbr"] == "BOS") & games["opponent_team_id"].isin(atlantic & winning)
    ]

    result = _run("Celtics record vs Atlantic Division winning teams 2024-25")
    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert summary["games"] == len(celtics)
    assert summary["wins"] == int((celtics["wl"] == "W").sum())


def test_pair_series_history_matches_the_adjacent_playoff_history():
    expected = _run("Lakers Nuggets playoff history")
    result = _run("Lakers and Nuggets series history")
    assert result.route == "playoff_matchup_history"
    assert result.result.to_dict()["sections"] == expected.result.to_dict()["sections"]


def test_player_pair_against_a_team():
    season = SEASONS[-1]
    rows = data_read_csv(f"raw/player_game_stats/{season}_regular_season.csv")
    result = _run(f"LeBron vs Curry against the Celtics {season}")
    lebron, curry = result.result.to_dict()["sections"]["summary"]
    for side, name in ((lebron, "LeBron James"), (curry, "Stephen Curry")):
        games = rows[(rows["player_name"] == name) & (rows["opponent_team_abbr"] == "BOS")]
        assert side["games"] == len(games)


def test_pair_leading_scorers_rank_both_rosters():
    season = SEASONS[-1]
    result = _run(f"Lakers and Celtics leading scorers {season}")
    teams = {row["team_abbr"] for row in result.result.to_dict()["sections"]["leaderboard"]}
    assert teams == {"LAL", "BOS"}


@pytest.mark.parametrize("season", ["2007-08", "2023-24"])
def test_celtics_win_streak_vs_the_west(season):
    games = _team_games(season)
    west = {
        team_id
        for team_id, (conference, _) in historical_alignment(season).items()
        if conference == "West"
    }
    games = games[(games["team_abbr"] == "BOS") & games["opponent_team_id"].isin(west)]
    games = games.sort_values(["game_date", "game_id"])
    best = run = 0
    for outcome in games["wl"]:
        run = run + 1 if outcome == "W" else 0
        best = max(best, run)

    result = _run(f"Celtics longest winning streak vs the West in {season}")
    assert result.route == "team_streak_finder"
    assert result.result.to_dict()["sections"]["streak"][0]["streak_length"] == best


def test_league_win_streaks_vs_the_east_2023_24():
    season = "2023-24"
    games = _team_games(season)
    east = {
        team_id
        for team_id, (conference, _) in historical_alignment(season).items()
        if conference == "East"
    }
    games = games[games["opponent_team_id"].isin(east)].sort_values(["game_date", "game_id"])
    longest = {}
    for team, rows in games.groupby("team_abbr"):
        best = run = 0
        for outcome in rows["wl"]:
            run = run + 1 if outcome == "W" else 0
            best = max(best, run)
        longest[team] = best

    result = _run(f"longest winning streak vs the East in {season}")
    assert result.route == "team_streak_finder"
    rows = result.result.to_dict()["sections"]["streak"]
    assert rows[0]["streak_length"] == max(longest.values())


def test_team_120_point_games_vs_the_west_2023_24():
    season = "2023-24"
    games = _team_games(season)
    west = {
        team_id
        for team_id, (conference, _) in historical_alignment(season).items()
        if conference == "West"
    }
    games = games[games["opponent_team_id"].isin(west)]
    counts = games[pd.to_numeric(games["pts"]) >= 120].groupby("team_abbr").size()

    result = _run(f"which team has the most 120 point games vs the West in {season}")
    assert result.route == "team_occurrence_leaders"
    board = result.result.to_dict()["sections"]["leaderboard"]
    assert board[0]["games_pts_120+"] == int(counts.max())


def test_league_win_streak_vs_the_west_is_not_a_player_named_west():
    result = _run("longest winning streak vs the West in 2023-24")
    assert result.route == "team_streak_finder"


def test_distinct_40_point_scorers_vs_the_warriors_2023_24():
    season = "2023-24"
    rows = data_read_csv(
        f"raw/player_game_stats/{season}_regular_season.csv", dtype={"game_id": str}
    )
    rows = rows[(rows["opponent_team_abbr"] == "GSW") & (pd.to_numeric(rows["pts"]) >= 40)]

    result = _run(f"how many players scored 40 vs the Warriors in {season}")
    assert result.route == "player_occurrence_leaders"
    count = result.result.to_dict()["sections"]["count"][0]["count"]
    assert count == rows["player_id"].nunique()


def test_distinct_30_and_10_players_2023_24():
    season = "2023-24"
    rows = data_read_csv(
        f"raw/player_game_stats/{season}_regular_season.csv", dtype={"game_id": str}
    )
    rows = rows[(pd.to_numeric(rows["pts"]) >= 30) & (pd.to_numeric(rows["reb"]) >= 10)]

    result = _run(f"how many players had 30 points and 10 rebounds in {season}")
    assert result.route == "player_occurrence_leaders"
    assert result.result.to_dict()["sections"]["count"][0]["count"] == rows["player_id"].nunique()


def test_distinct_comma_list_and_bench_counts():
    season = "2023-24"
    rows = data_read_csv(
        f"raw/player_game_stats/{season}_regular_season.csv", dtype={"game_id": str}
    )
    stats = rows[["pts", "reb", "ast"]].apply(pd.to_numeric)
    listed = rows[(stats["pts"] >= 25) & (stats["reb"] >= 5) & (stats["ast"] >= 5)]
    result = _run(f"how many players had 25 points, 5 rebounds, 5 assists in {season}")
    assert result.result.to_dict()["sections"]["count"][0]["count"] == listed["player_id"].nunique()

    # Starter roles are served only from 2024-25.
    season = "2024-25"
    rows = data_read_csv(
        f"raw/player_game_stats/{season}_regular_season.csv", dtype={"game_id": str}
    )
    stats = rows[["pts"]].apply(pd.to_numeric)
    roles = data_read_csv(
        f"raw/player_game_starter_roles/{season}_regular_season.csv", dtype={"game_id": str}
    )
    bench = roles[roles["starter_flag"].astype(str).str.lower().isin(["false", "0"])]
    scored = rows[stats["pts"] >= 30][["game_id", "player_id"]].astype(str)
    bench_keys = bench[["game_id", "player_id"]].astype(str)
    expected = scored.merge(bench_keys, on=["game_id", "player_id"])["player_id"].nunique()
    result = _run(f"how many players scored 30 off the bench in {season}")
    assert result.result.to_dict()["sections"]["count"][0]["count"] == expected


def test_lakers_and_warriors_playoff_record_is_their_2023_series():
    # The Lakers beat the Warriors 4-2 in the 2023 West semifinals, their only
    # playoff meeting since 1996-97.
    result = _run("Lakers and Warriors playoff record")
    assert result.route == "playoff_matchup_history"
    lakers = result.result.to_dict()["sections"]["summary"][0]
    assert (lakers["team_name"], lakers["wins"], lakers["losses"]) == ("Los Angeles Lakers", 4, 2)
    assert result.metadata.get("season") is None
