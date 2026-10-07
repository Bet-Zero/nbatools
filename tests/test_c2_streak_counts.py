"""C2 streak counts and remaining streak wording.

"how many 10 game winning streaks do the Celtics have" answered 60 (games, not
streaks), "Lakers winning streaks of 5 or more games" listed games, "how many
times did the Lakers win 5 straight" counted every win, "Curry most
consecutive games with a three" gave a season summary, "Celtics longest streak
holding opponents under 100" listed games, and "since 2024" on a streak was
replaced by the three-season default. Expected values are counted from the
fixture's game CSVs with a plain loop, never from the engine.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")
SEASON = "2025-26"
DEFAULT_WINDOW = ("2023-24", "2024-25", "2025-26")


def _games(kind: str, *seasons: str) -> pd.DataFrame:
    frame = pd.concat(
        pd.read_csv(RAW / kind / f"{season}_regular_season.csv", dtype={"game_id": str})
        for season in seasons
    )
    return frame.sort_values(["game_date", "game_id"])


def _run_lengths(flags) -> list[int]:
    """Every maximal run of True, counted by hand."""
    runs, current = [], 0
    for ok in flags:
        if ok:
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return runs


def _team(abbr: str, *seasons: str) -> pd.DataFrame:
    games = _games("team_game_stats", *seasons)
    return games[games["team_abbr"] == abbr]


def _player(name: str, *seasons: str) -> pd.DataFrame:
    games = _games("player_game_stats", *seasons)
    return games[games["player_name"] == name]


def _count(query: str) -> tuple[int, dict, list[dict]]:
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    payload = result.result.to_dict()
    return payload["sections"]["count"][0]["count"], result.metadata, payload["sections"]


@pytest.mark.parametrize(
    ("query", "abbr", "outcome", "length", "seasons"),
    [
        ("how many 10 game winning streaks do the Celtics have", "BOS", "W", 10, DEFAULT_WINDOW),
        ("how many times did the Lakers win 5 straight", "LAL", "W", 5, DEFAULT_WINDOW),
        ("how many times have the Celtics lost 3 in a row", "BOS", "L", 3, DEFAULT_WINDOW),
        (
            "how many times did the Lakers win 5 straight games this season",
            "LAL",
            "W",
            5,
            (SEASON,),
        ),
        (
            "how many 5+ game losing streaks did the Lakers have since 2024",
            "LAL",
            "L",
            5,
            ("2024-25", "2025-26"),
        ),
    ],
)
def test_team_streak_counts_match_raw_runs(query, abbr, outcome, length, seasons):
    runs = _run_lengths(_team(abbr, *seasons)["wl"] == outcome)
    expected = sum(run >= length for run in runs)

    count, metadata, sections = _count(query)
    assert metadata["route"] == "team_streak_finder"
    assert metadata["query_class"] == "count"
    assert count == expected
    # Each counted streak is listed, longest first.
    rows = sections.get("streak", [])
    assert sorted((row["streak_length"] for row in rows), reverse=True) == sorted(
        (run for run in runs if run >= length), reverse=True
    )
    noun = "winning" if outcome == "W" else "losing"
    assert f"{noun} streak" in metadata["count_phrase"]
    assert f"{length}+ games" in metadata["count_phrase"]


def test_the_streak_count_is_not_cut_at_the_list_limit():
    runs = _run_lengths(_player("LeBron James", *DEFAULT_WINDOW)["pts"] >= 20)
    expected = sum(run >= 2 for run in runs)
    assert expected > 0

    count, _, _ = _count("how many times has LeBron had 2 straight 20 point games")
    assert count == expected


@pytest.mark.parametrize(
    ("query", "name", "flag", "length"),
    [
        (
            "how many times has LeBron had 3 straight 20 point games since 2024",
            "LeBron James",
            lambda g: g["pts"] >= 20,
            3,
        ),
        (
            "how many times has Curry had 5 straight games with a three",
            "Stephen Curry",
            lambda g: g["fg3m"] >= 1,
            5,
        ),
        (
            "how many times has Jokic had 3 straight triple doubles",
            "Nikola Jokić",
            lambda g: (g[["pts", "reb", "ast", "stl", "blk"]] >= 10).sum(axis=1) >= 3,
            3,
        ),
    ],
)
def test_player_streak_counts_match_raw_runs(query, name, flag, length):
    seasons = ("2024-25", "2025-26") if "since 2024" in query else DEFAULT_WINDOW
    games = _player(name, *seasons)
    runs = _run_lengths(flag(games))

    count, metadata, _ = _count(query)
    assert metadata["route"] == "player_streak_finder"
    assert count == sum(run >= length for run in runs)
    assert f"{length}+ straight games" in metadata["count_phrase"]


def test_league_streak_count_is_players_with_a_run_that_long():
    games = _games("player_game_stats", SEASON)
    expected = sum(
        max(_run_lengths(player["pts"] >= 20), default=0) >= 5
        for _, player in games.groupby("player_id")
    )
    count, metadata, _ = _count("how many players have had 5 straight 20 point games this season")
    assert metadata["route"] == "player_streak_finder"
    assert count == expected
    assert metadata["count_phrase"].startswith(f"{expected} players have had a streak of 5+")


def test_league_team_streak_count():
    games = _games("team_game_stats", SEASON)
    expected = sum(
        max(_run_lengths(team["wl"] == "W"), default=0) >= 10
        for _, team in games.groupby("team_id")
    )
    count, _, _ = _count("how many teams have had a 10 game winning streak this season")
    assert count == expected


def test_a_longest_streak_question_is_not_a_count():
    result = execute_natural_query("how many games was the Lakers longest winning streak")
    assert result.metadata["route"] == "team_streak_finder"
    assert result.metadata["query_class"] != "count"
    rows = result.result.to_dict()["sections"]["streak"]
    assert rows[0]["streak_length"] == max(_run_lengths(_team("LAL", *DEFAULT_WINDOW)["wl"] == "W"))


@pytest.mark.parametrize(
    "query",
    ["Lakers winning streaks of 5 or more games", "Lakers winning streaks of at least 5 games"],
)
def test_streaks_of_n_or_more_list_every_run(query):
    runs = _run_lengths(_team("LAL", *DEFAULT_WINDOW)["wl"] == "W")
    result = execute_natural_query(query)
    assert result.metadata["route"] == "team_streak_finder"
    rows = result.result.to_dict()["sections"]["streak"]
    assert sorted((row["streak_length"] for row in rows), reverse=True) == sorted(
        (run for run in runs if run >= 5), reverse=True
    )


@pytest.mark.parametrize(
    "query",
    [
        "Curry most consecutive games with a three",
        "Curry longest streak of games with a three",
        "Curry consecutive games with a 3 pointer",
    ],
)
def test_made_three_streak_wording(query):
    expected = max(_run_lengths(_player("Stephen Curry", *DEFAULT_WINDOW)["fg3m"] >= 1))
    result = execute_natural_query(query)
    assert result.metadata["route"] == "player_streak_finder"
    rows = result.result.to_dict()["sections"]["streak"]
    assert rows[0]["condition"] == "made_three"
    assert rows[0]["streak_length"] == expected


def test_a_count_of_three_is_not_a_made_three():
    result = execute_natural_query("Curry consecutive games with 3 threes")
    rows = result.result.to_dict()["sections"]["streak"]
    assert rows[0]["condition"] == "fg3m>=3"


def test_opponent_points_streak_without_the_word_points():
    teams = _games("team_game_stats", *DEFAULT_WINDOW)
    allowed = teams.merge(
        teams[["game_id", "team_abbr", "pts"]].rename(
            columns={"team_abbr": "opp_abbr", "pts": "opp_pts"}
        ),
        on="game_id",
    )
    allowed = allowed[(allowed["team_abbr"] == "BOS") & (allowed["opp_abbr"] != "BOS")]
    expected = max(_run_lengths(allowed["opp_pts"] < 100))

    result = execute_natural_query("Celtics longest streak holding opponents under 100")
    assert result.metadata["route"] == "team_streak_finder"
    rows = result.result.to_dict()["sections"]["streak"]
    assert rows[0]["condition"] == "opponent_pts<100"
    assert rows[0]["streak_length"] == expected


@pytest.mark.parametrize(
    ("query", "start"),
    [
        ("Lakers longest winning streak since 2024", "2024-25"),
        ("LeBron longest streak of 20 point games in the last 2 seasons", "2024-25"),
    ],
)
def test_a_stated_span_replaces_the_three_season_default(query, start):
    result = execute_natural_query(query)
    assert result.metadata.get("start_season") == start
    assert not any("three-season window" in note for note in result.metadata.get("notes") or [])
