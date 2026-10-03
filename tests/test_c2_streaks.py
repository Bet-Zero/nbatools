"""C2 streaks: league streak rankings, current streaks, any game condition.

"longest 30 point streak this season" and "longest winning streak this season"
matched no route, "Lakers current winning streak" listed games, "Curry longest
streak of games with 5+ threes" and "Jokic consecutive games with 10+ rebounds"
fell to the game finder, "current" returned the longest streak rather than the
live one, and "this season" was replaced by a three-season window. Expected
values here are counted from the fixture's game CSVs with a plain loop, never
from the engine.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")
SEASON = "2025-26"


def _games(kind: str, *seasons: str) -> pd.DataFrame:
    frame = pd.concat(
        pd.read_csv(RAW / kind / f"{season}_regular_season.csv", dtype={"game_id": str})
        for season in seasons
    )
    return frame.sort_values(["game_date", "game_id"])


def _runs(flags: list[bool]) -> tuple[int, int]:
    """(longest run, run still going at the last game), counted by hand."""
    longest = current = 0
    for ok in flags:
        current = current + 1 if ok else 0
        longest = max(longest, current)
    return longest, current


def _per_entity(frame: pd.DataFrame, key: str, flag) -> dict:
    return {
        name: _runs([bool(flag(row)) for _, row in games.iterrows()])
        for name, games in frame.groupby(key)
    }


def _streaks(query: str) -> tuple[list[dict], dict]:
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]["streak"], result.metadata


def test_league_player_streak_ranking_matches_raw_rows():
    runs = _per_entity(_games("player_game_stats", SEASON), "player_name", lambda r: r.pts >= 20)
    expected = sorted((longest for longest, _ in runs.values()), reverse=True)[:10]

    rows, metadata = _streaks("who has the longest 20 point streak this season")
    assert metadata["route"] == "player_streak_finder"
    assert [row["streak_length"] for row in rows] == expected
    for row in rows:
        assert runs[row["player_name"]][0] == row["streak_length"], row
    assert {row["start_date"][:4] for row in rows} <= {"2025", "2026"}


@pytest.mark.parametrize(
    "query", ["longest 30 point streak this season", "longest winning streak this season"]
)
def test_this_season_is_not_widened_to_three_seasons(query):
    opening_night = _games("team_game_stats", SEASON)["game_date"].min()
    rows, _ = _streaks(query)
    assert all(row["start_date"] >= opening_night for row in rows)


def test_compound_condition_streak_for_a_player():
    games = _games("player_game_stats", SEASON)
    jokic = games[games["player_name"] == "Nikola Jokić"]
    longest, _ = _runs(list((jokic["pts"] >= 20) & (jokic["reb"] >= 10)))

    rows, metadata = _streaks(f"Jokic longest streak of 20 point 10 rebound games in {SEASON}")
    assert metadata["route"] == "player_streak_finder"
    assert rows[0]["streak_length"] == longest
    assert rows[0]["condition"] == "pts>=20 and reb>=10"


@pytest.mark.parametrize(
    ("query", "name", "flag"),
    [
        (
            f"Curry longest streak of games with 5+ threes in {SEASON}",
            "Stephen Curry",
            lambda g: g["fg3m"] >= 5,
        ),
        (
            f"Jokic consecutive games with 10+ rebounds in {SEASON}",
            "Nikola Jokić",
            lambda g: g["reb"] >= 10,
        ),
        (
            f"Jokic consecutive double doubles in {SEASON}",
            "Nikola Jokić",
            lambda g: (g[["pts", "reb", "ast", "stl", "blk"]] >= 10).sum(axis=1) >= 2,
        ),
    ],
)
def test_player_streak_wording_reaches_the_streak_finder(query, name, flag):
    games = _games("player_game_stats", SEASON)
    player = games[games["player_name"] == name]
    longest, _ = _runs(list(flag(player)))

    rows, metadata = _streaks(query)
    assert metadata["route"] == "player_streak_finder"
    assert rows[0]["streak_length"] == longest


def test_current_player_streak_is_the_live_one():
    games = _games("player_game_stats", SEASON)
    jokic = games[games["player_name"] == "Nikola Jokić"]
    longest, current = _runs(list(jokic["pts"] >= 20))
    assert current != longest  # the fixture separates the two answers

    rows, _ = _streaks(f"Jokic current streak of 20 point games in {SEASON}")
    assert [row["streak_length"] for row in rows] == [current]
    assert rows[0]["is_active"] == int(current > 0)
    assert rows[0]["end_date"] == jokic["game_date"].iloc[-1]


def test_no_live_streak_is_a_zero_streak_not_no_answer():
    games = _games("player_game_stats", SEASON)
    jokic = games[games["player_name"] == "Nikola Jokić"]
    _, current = _runs(list(jokic["pts"] >= 30))
    assert current == 0  # his latest fixture game was under 30

    result = execute_natural_query(f"Jokic current streak of 30 point games in {SEASON}")
    rows = result.result.to_dict()["sections"]["streak"]
    assert [(row["streak_length"], row["is_active"]) for row in rows] == [(0, 0)]
    assert rows[0]["end_date"] == jokic["game_date"].iloc[-1]
    assert any("no active streak" in c for c in result.result.caveats)


@pytest.mark.parametrize(
    ("query", "outcome"),
    [
        (f"longest winning streak in {SEASON}", "W"),
        (f"longest losing streak in {SEASON}", "L"),
    ],
)
def test_league_team_outcome_streaks_match_raw_rows(query, outcome):
    runs = _per_entity(_games("team_game_stats", SEASON), "team_name", lambda r: r.wl == outcome)
    rows, metadata = _streaks(query)
    assert metadata["route"] == "team_streak_finder"
    assert [row["streak_length"] for row in rows] == sorted(
        (longest for longest, _ in runs.values()), reverse=True
    )
    for row in rows:
        assert runs[row["team_name"]][0] == row["streak_length"], row


def test_current_team_streaks():
    teams = _games("team_game_stats", SEASON)
    runs = _per_entity(teams, "team_name", lambda r: r.wl == "W")
    live = sorted((current for _, current in runs.values() if current), reverse=True)

    rows, _ = _streaks(f"which team has the longest current winning streak in {SEASON}")
    assert [row["streak_length"] for row in rows] == live
    assert all(row["is_active"] == 1 for row in rows)

    lakers = runs["Los Angeles Lakers"][1]
    result = execute_natural_query(f"Lakers current winning streak in {SEASON}")
    assert result.metadata["route"] == "team_streak_finder"
    rows = result.result.to_dict()["sections"]["streak"]
    assert [row["streak_length"] for row in rows] == [lakers]


def test_home_winning_streak_counts_home_games_only():
    teams = _games("team_game_stats", SEASON)
    home = teams[(teams["team_abbr"] == "BOS") & (teams["is_home"])]
    longest, _ = _runs(list(home["wl"] == "W"))

    result = execute_natural_query(f"Celtics winning streak at home in {SEASON}")
    assert "filtered to home games only" in result.result.caveats
    assert result.result.to_dict()["sections"]["streak"][0]["streak_length"] == longest


def test_unread_subject_does_not_become_a_league_ranking():
    result = execute_natural_query("Jokc longest 30 point streak")
    assert result.metadata.get("route") not in {"player_streak_finder", "team_streak_finder"}


def test_current_streak_with_a_length_reports_the_live_run():
    games = _games("player_game_stats", SEASON)
    jokic = games[games["player_name"] == "Nikola Jokić"]
    _, current = _runs(list(jokic["pts"] >= 20))
    assert 0 < current < 5

    result = execute_natural_query(f"Jokic current 5 straight games with 20 points in {SEASON}")
    rows = result.result.to_dict()["sections"]["streak"]
    assert [(row["streak_length"], row["is_active"]) for row in rows] == [(current, 1)]
    assert "the current streak is shorter than 5 games" in result.result.caveats


def test_league_streaks_respect_each_players_last_n_games():
    games = _games("player_game_stats", SEASON)
    last5 = games.groupby("player_name").tail(5)
    runs = _per_entity(last5, "player_name", lambda r: r.pts >= 20)

    rows, _ = _streaks("longest 20 point streak in the last 5 games this season")
    assert [row["streak_length"] for row in rows] == sorted(
        (longest for longest, _ in runs.values()), reverse=True
    )[:10]
    assert max(row["streak_length"] for row in rows) <= 5


@pytest.mark.parametrize(
    ("query", "flag", "label"),
    [
        (
            f"Jokic consecutive games with under 20 points in {SEASON}",
            lambda g: g["pts"] < 20,
            "pts<20",
        ),
        (
            f"Jokic consecutive games with at most 2 turnovers in {SEASON}",
            lambda g: g["tov"] <= 2,
            "tov<=2",
        ),
    ],
)
def test_upper_bound_streaks(query, flag, label):
    games = _games("player_game_stats", SEASON)
    jokic = games[games["player_name"] == "Nikola Jokić"]
    rows, _ = _streaks(query)
    assert rows[0]["streak_length"] == _runs(list(flag(jokic)))[0]
    assert rows[0]["condition"] == label


def test_team_stat_streak_ranking():
    teams = _games("team_game_stats", SEASON)
    runs = _per_entity(teams, "team_name", lambda r: r.pts >= 120)
    rows, metadata = _streaks(f"which team has the longest streak of 120 point games in {SEASON}")
    assert metadata["route"] == "team_streak_finder"
    assert [row["streak_length"] for row in rows] == sorted(
        (longest for longest, _ in runs.values() if longest), reverse=True
    )


def test_three_season_streak_window_stays_on_streak_routes():
    result = execute_natural_query("Jokic win streak")
    assert result.metadata["route"] != "player_streak_finder"
    (summary,) = result.result.to_dict()["sections"]["summary"]
    assert summary["season_start"] == summary["season_end"] == SEASON


@pytest.mark.parametrize(
    "query",
    [
        "who has a current 3 straight games with 20 points this season",
        "who is on a current 3 game 20 point streak this season",
    ],
)
def test_league_current_streaks_keep_the_stated_length(query):
    runs = _per_entity(_games("player_game_stats", SEASON), "player_name", lambda r: r.pts >= 20)
    expected = sorted((current for _, current in runs.values() if current >= 3), reverse=True)
    rows, _ = _streaks(query)
    assert [row["streak_length"] for row in rows] == expected


@pytest.mark.parametrize(
    "query",
    [
        "players with 3 straight 30 point games this season",
        "who had 3 consecutive 30 point games this season",
        "who has 3 straight games with 30 points this season",
    ],
)
def test_length_before_the_condition_is_the_streak_length(query):
    runs = _per_entity(_games("player_game_stats", SEASON), "player_name", lambda r: r.pts >= 30)
    expected = sorted((longest for longest, _ in runs.values() if longest >= 3), reverse=True)
    rows, _ = _streaks(query)
    assert [row["streak_length"] for row in rows] == expected[:10]
    assert all(row["condition"] == "pts>=30" for row in rows)


def test_team_game_count_in_a_winning_streak_is_its_length():
    runs = _per_entity(_games("team_game_stats", SEASON), "team_name", lambda r: r.wl == "W")
    expected = sorted((current for _, current in runs.values() if current >= 3), reverse=True)
    rows, _ = _streaks(f"which teams have a current 3 game winning streak in {SEASON}")
    assert [row["streak_length"] for row in rows] == expected
