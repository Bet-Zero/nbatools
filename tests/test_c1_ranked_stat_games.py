"""C1: "top 3 assist games with 20 points" ranks the player's games.

The number was read as an assist bar ("3 assists and 20 points"), which gave a
league board of players; "top 3 rebounding games with 20 points" found
nothing, and "best 3 ..." ignored the 3. They read as "top 3 games by assists
with 20 points". Team lists ranked "by <stat>" dropped the condition or ranked
by the bound's stat. Expected values come from the fixture's game rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw")


def _rows(query: str) -> list[dict]:
    return execute_natural_query(query).result.to_dict()["sections"]["finder"]


def _lebron() -> pd.DataFrame:
    games = pd.read_csv(RAW / "player_game_stats/2025-26_regular_season.csv")
    return games[games["player_name"] == "LeBron James"]


@pytest.mark.parametrize(
    ("query", "rank", "keep"),
    [
        ("LeBron top 3 assist games with 20 points", "ast", lambda g: g["pts"] >= 20),
        ("top 3 assist games for LeBron with 20 points", "ast", lambda g: g["pts"] >= 20),
        ("LeBron best 3 assist games with 20 points", "ast", lambda g: g["pts"] >= 20),
        ("LeBron top 3 rebounding games with 20 points", "reb", lambda g: g["pts"] >= 20),
        ("LeBron top 3 assist games in 20 point games", "ast", lambda g: g["pts"] >= 20),
        (
            "LeBron top 3 assist games with 20 points or 10 rebounds",
            "ast",
            lambda g: (g["pts"] >= 20) | (g["reb"] >= 10),
        ),
    ],
)
def test_player_ranked_stat_games_with_a_condition(query, rank, keep):
    games = _lebron()
    games = games[keep(games)]
    rows = _rows(query)
    assert [row[rank] for row in rows] == games[rank].nlargest(3).tolist()
    assert {row["game_id"] for row in rows} <= set(games["game_id"])


@pytest.mark.parametrize(
    ("query", "rank", "keep"),
    [
        # The team list dropped the condition, or ranked by the bound's stat.
        ("Celtics top 3 scoring games with 15 threes", "pts", lambda g: g["fg3m"] >= 15),
        ("Celtics top 3 games by points with 15 threes", "pts", lambda g: g["fg3m"] >= 15),
        ("Celtics top 3 games by threes with 120 points", "fg3m", lambda g: g["pts"] >= 120),
    ],
)
def test_team_ranked_stat_games_with_a_condition(query, rank, keep):
    games = pd.read_csv(RAW / "team_game_stats/2025-26_regular_season.csv")
    games = games[games["team_abbr"] == "BOS"]
    games = games[keep(games)]
    rows = _rows(query)
    assert [row[rank] for row in rows] == games[rank].nlargest(3).tolist()
    assert {row["game_id"] for row in rows} <= set(games["game_id"])


def test_league_top_scoring_games_keep_their_board():
    result = execute_natural_query("top 5 scoring games this season")
    assert result.route == "top_player_games"


def _player(name: str, season_file: str = "2025-26_regular_season.csv") -> pd.DataFrame:
    games = pd.read_csv(RAW / "player_game_stats" / season_file)
    return games[games["player_name"] == name]


@pytest.mark.parametrize(
    ("query", "name", "rank", "keep"),
    [
        # Two conditions keep the reading they had (the rewrite stays off).
        (
            "LeBron top 3 scoring games with 2 steals and 2 blocks",
            "LeBron James",
            "pts",
            lambda g: (g["stl"] >= 2) & (g["blk"] >= 2),
        ),
        (
            "Jokic top 3 rebounding games with 20 points and 10 assists",
            "Nikola Jokić",
            "reb",
            lambda g: (g["pts"] >= 20) & (g["ast"] >= 10),
        ),
        # "biggest 3" keeps its 3.
        (
            "LeBron biggest 3 assist games with 20 points",
            "LeBron James",
            "ast",
            lambda g: g["pts"] >= 20,
        ),
        # A scope before the condition.
        (
            "LeBron top 3 assist games at home with 20 points",
            "LeBron James",
            "ast",
            lambda g: (g["pts"] >= 20) & (g["is_home"] == 1),
        ),
        # The OR form ranks by threes.
        (
            "LeBron top 3 three point games with 30 points or 10 assists",
            "LeBron James",
            "fg3m",
            lambda g: (g["pts"] >= 30) | (g["ast"] >= 10),
        ),
    ],
)
def test_ranked_player_lists_after_review(query, name, rank, keep):
    games = _player(name)
    games = games[keep(games)]
    rows = _rows(query)
    assert [row[rank] for row in rows] == games[rank].nlargest(3).tolist()
    assert {row["game_id"] for row in rows} <= set(games["game_id"])


def test_team_scope_before_the_condition():
    games = pd.read_csv(RAW / "team_game_stats/2025-26_regular_season.csv")
    games = games[
        (games["team_abbr"] == "BOS")
        & (games["opponent_team_abbr"] == "NYK")
        & (games["fg3m"] >= 15)
    ]
    rows = _rows("Celtics top 3 scoring games vs the Knicks with 15 threes")
    assert [row["pts"] for row in rows] == games["pts"].nlargest(3).tolist()


@pytest.mark.parametrize(
    "query",
    [
        # The opponent's bound is not the team's own stat: still refused.
        "Celtics top 3 scoring games with 120 points allowed",
        "Lakers highest scoring games with 50 rebounds allowed",
        "Lakers top 3 rebounding games with 120 points allowed",
    ],
)
def test_team_lists_with_an_opponent_bound_refuse(query):
    assert execute_natural_query(query).result_status == "no_result"


SPAN = ("2023-24", "2024-25", "2025-26")


def _span_rows(kind: str) -> pd.DataFrame:
    return pd.concat([pd.read_csv(RAW / kind / f"{s}_regular_season.csv") for s in SPAN])


def test_player_ranked_list_over_a_span_keeps_the_condition():
    # The span sent it through the summary route, which held no bound.
    games = _span_rows("player_game_stats")
    games = games[(games["player_name"] == "LeBron James") & (games["pts"] >= 20)]
    rows = _rows("LeBron top 3 assist games with 20 points from 2023-24 to 2025-26")
    assert [row["ast"] for row in rows] == games["ast"].nlargest(3).tolist()
    assert {row["game_id"] for row in rows} <= set(games["game_id"])


@pytest.mark.parametrize(
    ("query", "keep"),
    [
        # A span sent the team's list to its summary (no games).
        ("Lakers top 3 scoring games from 2023-24 to 2025-26", lambda g: g["pts"] > -1),
        (
            "Lakers top 3 scoring games with 15 threes from 2023-24 to 2025-26",
            lambda g: g["fg3m"] >= 15,
        ),
    ],
)
def test_team_ranked_list_over_a_span(query, keep):
    games = _span_rows("team_game_stats")
    games = games[games["team_abbr"] == "LAL"]
    games = games[keep(games)]
    rows = _rows(query)
    assert [row["pts"] for row in rows] == games["pts"].nlargest(3).tolist()
    assert {row["game_id"] for row in rows} <= set(games["game_id"])


def test_opponent_clause_with_is_not_the_condition():
    # "against teams with a winning record" is the opponent bar, not a bound.
    games = pd.read_csv(RAW / "player_game_stats/2025-26_regular_season.csv")
    teams = pd.read_csv(RAW / "team_game_stats/2025-26_regular_season.csv")
    records = teams.groupby("team_abbr")["wl"].value_counts().unstack(fill_value=0)
    winning = set(records[records["W"] > records["L"]].index)
    lebron = games[
        (games["player_name"] == "LeBron James") & games["opponent_team_abbr"].isin(winning)
    ]
    rows = _rows("LeBron top 3 scoring games against teams with a winning record")
    assert [row["pts"] for row in rows] == lebron["pts"].nlargest(3).tolist()


def test_opponent_bar_before_the_condition():
    games = pd.read_csv(RAW / "player_game_stats/2025-26_regular_season.csv")
    teams = pd.read_csv(RAW / "team_game_stats/2025-26_regular_season.csv")
    records = teams.groupby("team_abbr")["wl"].value_counts().unstack(fill_value=0)
    over = set(records[records["W"] > records["L"]].index)
    lebron = games[
        (games["player_name"] == "LeBron James")
        & games["opponent_team_abbr"].isin(over)
        & (games["pts"] >= 20)
    ]
    for query in (
        "LeBron top 3 assist games against teams over .500 with 20 points",
        "LeBron top 3 assist games against teams with a winning record with 20 points",
    ):
        rows = _rows(query)
        assert [row["ast"] for row in rows] == lebron["ast"].nlargest(3).tolist()
        assert {row["game_id"] for row in rows} <= set(lebron["game_id"])


@pytest.mark.parametrize(
    ("query", "rank"),
    [
        ("Lakers top 3 three point games since 2024", "fg3m"),
        ("Lakers top 3 passing games since 2024", "ast"),
    ],
)
def test_team_span_list_ranks_by_the_named_stat(query, rank):
    games = pd.concat(
        [pd.read_csv(RAW / "team_game_stats" / f"{s}_regular_season.csv") for s in SPAN[1:]]
    )
    games = games[games["team_abbr"] == "LAL"]
    rows = _rows(query)
    assert [row[rank] for row in rows] == games[rank].nlargest(3).tolist()


@pytest.mark.parametrize(
    "query",
    [
        # No stat named, a split, or "summary": the team summary stays.
        "Lakers best games since 2024",
        "Lakers games by month since 2024",
        "Lakers top 3 games by margin since 2024",
        "Lakers highest scoring games since 2024 summary",
        "Lakers stats since 2024",
        # The opponent's stat is not the team's own points.
        "Lakers top 3 games by points allowed since 2024",
        "Lakers top 3 games by opponent points since 2024",
        "Lakers highest scoring games allowed since 2024",
    ],
)
def test_team_span_summaries_stay(query):
    assert execute_natural_query(query).route == "game_summary"


def test_team_span_list_by_point_differential():
    games = pd.concat(
        [pd.read_csv(RAW / "team_game_stats" / f"{s}_regular_season.csv") for s in SPAN[1:]]
    )
    games = games[games["team_abbr"] == "LAL"]
    rows = _rows("Lakers top 3 games by point differential since 2024")
    assert [row["plus_minus"] for row in rows] == games["plus_minus"].nlargest(3).tolist()
