"""C1: splits by opponent, opponent lists on splits and player stretches.

"Lakers record by opponent" and "LeBron averages by opponent" gave the whole
sample; "Lakers home and away record vs Celtics and Knicks" kept Boston only;
"LeBron best 10 game stretch vs Celtics, Knicks and Heat" read the Celtics as
a second player; "LeBron top 5 games with 30 points each season" ranked the
span. Expected values come from the fixture's rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")
SEASON = "2025-26_regular_season.csv"


def _team() -> pd.DataFrame:
    games = pd.read_csv(RAW / "team_game_stats" / SEASON)
    return games[games["team_abbr"] == "LAL"]


def _lebron(season_file: str = SEASON) -> pd.DataFrame:
    games = pd.read_csv(RAW / "player_game_stats" / season_file)
    return games[games["player_name"] == "LeBron James"]


def _splits(query: str) -> list[dict]:
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    return result.result.to_dict()["sections"]["split_comparison"]


def _by_opponent(games: pd.DataFrame) -> list[tuple]:
    return [
        (abbr, len(group), int((group["wl"] == "W").sum()), round(group["pts"].mean(), 3))
        for abbr, group in sorted(games.groupby("opponent_team_abbr"), key=lambda x: x[0])
    ]


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record by opponent",
        "Lakers split by opponent",
        "Lakers record against every opponent",
    ],
)
def test_team_record_by_opponent(query):
    rows = _splits(query)
    got = [(r["bucket"], r["games"], r["wins"], round(r["pts_avg"], 3)) for r in rows]
    assert got == _by_opponent(_team())


@pytest.mark.parametrize(
    "query",
    ["LeBron averages by opponent", "LeBron stats vs each team", "LeBron points per opponent"],
)
def test_player_averages_by_opponent(query):
    rows = _splits(query)
    got = [(r["bucket"], r["games"], r["wins"], round(r["pts_avg"], 3)) for r in rows]
    assert got == _by_opponent(_lebron())


def test_split_by_opponent_keeps_an_opponent_list():
    games = _team()
    games = games[games["opponent_team_abbr"].isin(["BOS", "NYK"])]
    rows = _splits("Lakers record by opponent vs Celtics and Knicks")
    got = [(r["bucket"], r["games"], r["wins"], round(r["pts_avg"], 3)) for r in rows]
    assert got == _by_opponent(games)


def test_home_away_split_keeps_an_opponent_list():
    games = _team()
    games = games[games["opponent_team_abbr"].isin(["BOS", "NYK"])]
    rows = {
        r["bucket"]: (r["games"], r["wins"])
        for r in _splits("Lakers home and away record vs Celtics and Knicks")
    }
    home = games[games["is_home"] == 1]
    away = games[games["is_home"] != 1]
    assert rows == {
        "home": (len(home), int((home["wl"] == "W").sum())),
        "away": (len(away), int((away["wl"] == "W").sum())),
    }


def test_ranking_by_an_opponent_stat_is_not_a_split():
    assert execute_natural_query("Lakers games by opponent points").route == "game_finder"


@pytest.mark.parametrize(
    "query",
    [
        "LeBron James best 10 game scoring stretch vs Celtics, Knicks and Heat",
        "LeBron James best 10 game scoring stretch vs Celtics, Knicks, and Heat",
    ],
)
def test_player_stretch_vs_a_three_team_list(query):
    games = _lebron()
    games = games[games["opponent_team_abbr"].isin(["BOS", "NYK", "MIA"])].sort_values("game_date")
    result = execute_natural_query(query)
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert rows[0]["stretch_value"] == pytest.approx(games["pts"].rolling(10).mean().max())


def test_team_stretch_vs_a_list_stops_before_the_subject():
    rows = execute_natural_query(
        "against the Celtics and Knicks, Lakers best 5 game stretch in 2025-26"
    ).result.to_dict()["sections"]["leaderboard"]
    assert {row["team_abbr"] for row in rows} == {"LAL"}


def test_counted_ranking_with_a_threshold_each_season():
    rows = execute_natural_query("LeBron top 2 games with 30 points each season").result.to_dict()[
        "sections"
    ]["finder"]
    expected = []
    for season in ("2025-26", "2024-25", "2023-24"):
        games = _lebron(f"{season}_regular_season.csv")
        expected += [(season, v) for v in games.loc[games["pts"] >= 30, "pts"].nlargest(2)]
    assert [(row["season"], row["pts"]) for row in rows] == expected
