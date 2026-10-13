"""C1: groups ranked by rating, and a team's best wins and single best game.

"vs top 5 offenses", "bottom 10 defenses" and "elite defenses" returned every
game. "Lakers best wins" listed wins by date, "best game" listed every game,
"best 3 point games" read points >= 3, "top 5 games with 120 points" became a
player board with no rows, and "teams that shoot 50% per game" read the
game-level rate. Expected values come from the fixture's rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")
SEASON = "2025-26_regular_season.csv"


def _team_games() -> pd.DataFrame:
    return pd.read_csv(RAW / "team_game_stats" / SEASON)


def _lakers() -> pd.DataFrame:
    games = _team_games()
    return games[games["team_abbr"] == "LAL"]


def _ratings() -> pd.DataFrame:
    advanced = pd.read_csv(RAW / "team_season_advanced" / SEASON)
    names = _team_games().drop_duplicates("team_id").set_index("team_id")["team_abbr"]
    return advanced.assign(team_abbr=advanced["team_id"].map(names))


def _group(column: str, count: int, best: bool) -> list[str]:
    # Best first: the lowest defensive rating, the highest offensive.
    ascending = (column == "def_rating") == best
    return _ratings().sort_values(column, ascending=ascending)["team_abbr"].head(count).tolist()


def _record(query: str) -> tuple[int, int, int]:
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    row = result.result.to_dict()["sections"]["summary"][0]
    return row["games"], row["wins"], row["losses"]


def _rows(query: str) -> list[dict]:
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    return result.result.to_dict()["sections"]["finder"]


@pytest.mark.parametrize(
    ("query", "column", "count", "best"),
    [
        ("Lakers record vs top 2 offenses", "off_rating", 2, True),
        ("Lakers record vs bottom 2 defenses", "def_rating", 2, False),
        ("Lakers record vs elite defenses", "def_rating", 5, True),
        ("Lakers record vs worst 3 offenses", "off_rating", 3, False),
        ("Lakers record vs top 10 offenses", "off_rating", 10, True),
    ],
)
def test_team_record_vs_a_rating_group(query, column, count, best):
    games = _lakers()
    games = games[games["opponent_team_abbr"].isin(_group(column, count, best))]
    assert _record(query) == (
        len(games),
        int((games["wl"] == "W").sum()),
        int((games["wl"] == "L").sum()),
    )


def test_stretch_board_vs_a_rating_group():
    players = pd.read_csv(RAW / "player_game_stats" / SEASON)
    worst = _group("def_rating", 2, False)
    luka = players[
        (players["player_name"] == "Luka Dončić") & players["opponent_team_abbr"].isin(worst)
    ].sort_values("game_date")
    rows = execute_natural_query(
        "best 5 game scoring stretch against the bottom 2 defenses in 2025-26"
    ).result.to_dict()["sections"]["leaderboard"]
    assert rows[0]["player_name"] == "Luka Dončić"
    assert rows[0]["stretch_value"] == pytest.approx(luka["pts"].rolling(5).mean().max())


def test_season_rate_descriptions_refuse():
    # The opponents' season rate is not loaded; the game rate is not it.
    for query in (
        "Lakers record vs teams that shoot 50% per game",
        "Lakers record vs teams that shot 50% on average",
    ):
        assert execute_natural_query(query).result_status == "no_result"
    assert _record("Lakers record vs teams that shoot 50%")[0] == 49


@pytest.mark.parametrize(
    ("query", "keep", "count", "ascending"),
    [
        ("Lakers best wins", lambda g: g["wl"] == "W", 25, False),
        ("Lakers top 5 wins", lambda g: g["wl"] == "W", 5, False),
        ("Lakers best win", lambda g: g["wl"] == "W", 1, False),
        ("Lakers best game", lambda g: g["plus_minus"] > -999, 1, False),
        ("Lakers worst game", lambda g: g["plus_minus"] > -999, 1, True),
        ("Lakers top 5 games with 120 points", lambda g: g["pts"] >= 120, 5, False),
        ("Lakers top 5 games with 15 threes", lambda g: g["fg3m"] >= 15, 5, False),
        (
            "Lakers best wins vs Celtics",
            lambda g: (g["wl"] == "W") & (g["opponent_team_abbr"] == "BOS"),
            25,
            False,
        ),
    ],
)
def test_team_games_by_margin(query, keep, count, ascending):
    games = _lakers()
    games = games[keep(games)]
    expected = games["plus_minus"].sort_values(ascending=ascending).head(count).tolist()
    assert [row["plus_minus"] for row in _rows(query)] == expected


@pytest.mark.parametrize(
    "query",
    ["Lakers best 3 point games", "Lakers best three point games", "Lakers best 3-point games"],
)
def test_team_three_point_games_rank_by_threes(query):
    assert [row["fg3m"] for row in _rows(query)] == _lakers()["fg3m"].nlargest(25).tolist()


def test_player_three_point_games_rank_by_threes():
    players = pd.read_csv(RAW / "player_game_stats" / SEASON)
    lebron = players[players["player_name"] == "LeBron James"]
    rows = _rows("LeBron top three point games")
    assert [row["fg3m"] for row in rows] == lebron["fg3m"].nlargest(len(rows)).tolist()


@pytest.mark.parametrize(
    ("query", "route"),
    [
        # Not a game ranking.
        ("Lakers best win percentage", "team_record"),
        ("Lakers best 5 game stretch", "team_stretch_leaderboard"),
        ("Lakers players with the most 30 point games", "player_occurrence_leaders"),
    ],
)
def test_other_readings_stay(query, route):
    assert execute_natural_query(query).route == route
