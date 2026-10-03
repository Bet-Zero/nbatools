"""B1 operations: condition-count rankings, game lists, qualified rates, games played.

"most 30 point 10 rebound games" used to refuse, "10+ assists and 0 turnovers"
counted every 10-assist game (zero read as a lower bound), "minimum 100
attempts" was a blocked phrase and "most games played" matched no route. Each
expected value here comes straight from the fixture's game CSVs with pandas,
never from the engine.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.commands._occurrence_route_utils import (
    extract_compound_occurrence_event,
    extract_occurrence_event,
)
from nbatools.commands._parse_helpers import extract_min_attempts
from nbatools.query_service import execute_natural_query

pytestmark = pytest.mark.query

GAMES = Path("qa/fixtures/query_engine_sample/data/raw/player_game_stats")
SEASON = "2025-26"


def _games(*seasons: str, season_type: str = "regular_season") -> pd.DataFrame:
    return pd.concat(pd.read_csv(GAMES / f"{season}_{season_type}.csv") for season in seasons)


def _sections(query: str) -> dict:
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]


def _event_counts(frame: pd.DataFrame, mask: pd.Series) -> pd.Series:
    return frame.assign(hit=mask.astype(int)).groupby("player_name")["hit"].sum()


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "most 30 point 10 rebound games",
            [{"stat": "pts", "min_value": 30.0}, {"stat": "reb", "min_value": 10.0}],
        ),
        (
            "most 30-point, 10-rebound games",
            [{"stat": "pts", "min_value": 30.0}, {"stat": "reb", "min_value": 10.0}],
        ),
        (
            "most 25 point 10 rebound 5 assist games",
            [
                {"stat": "pts", "min_value": 25.0},
                {"stat": "reb", "min_value": 10.0},
                {"stat": "ast", "min_value": 5.0},
            ],
        ),
        (
            "most 30/10 games",
            [{"stat": "pts", "min_value": 30.0}, {"stat": "reb", "min_value": 10.0}],
        ),
        (
            "most 10 assist 0 turnover games",
            [
                {"stat": "ast", "min_value": 10.0},
                {"stat": "tov", "min_value": None, "max_value": 0.0},
            ],
        ),
        (
            "games with 10+ assists and 0 turnovers",
            [
                {"stat": "ast", "min_value": 10.0},
                {"stat": "tov", "min_value": None, "max_value": 0.0},
            ],
        ),
        (
            "games with 10+ assists and no turnovers",
            [
                {"stat": "ast", "min_value": 10.0},
                {"stat": "tov", "min_value": None, "max_value": 0.0},
            ],
        ),
    ],
)
def test_compound_game_conditions_parse(text, expected):
    assert extract_compound_occurrence_event(text) == expected


def test_zero_is_an_exact_bound_and_zero_plus_is_not():
    assert extract_occurrence_event("most 0 turnover games") == {
        "stat": "tov",
        "min_value": None,
        "max_value": 0.0,
    }
    assert extract_occurrence_event("most 10 assist games") == {"stat": "ast", "min_value": 10.0}


@pytest.mark.parametrize(
    ("text", "value", "per_game", "attempt_stat"),
    [
        ("best three point percentage minimum 100 attempts", 100.0, False, None),
        ("best 3pt% min 100 3pa", 100.0, False, "fg3a"),
        ("best ft% 200 attempts minimum", 200.0, False, None),
        ("best fg% with at least 300 attempts", 300.0, False, None),
        ("best 3 point percentage with 5+ attempts per game", 5.0, True, None),
        ("best 3pt% min 6 three point attempts per game", 6.0, True, "fg3a"),
    ],
)
def test_attempt_minimum_parses(text, value, per_game, attempt_stat):
    parsed = extract_min_attempts(text)
    assert parsed is not None
    assert (parsed["value"], parsed["per_game"], parsed["attempt_stat"]) == (
        value,
        per_game,
        attempt_stat,
    )


def test_attempt_ranking_is_not_a_qualifier():
    assert extract_min_attempts("most three point attempts") is None


# ---------------------------------------------------------------------------
# Condition-count rankings
# ---------------------------------------------------------------------------


@pytest.mark.fixture_data
@pytest.mark.parametrize(
    ("query", "column", "mask"),
    [
        (
            "most 30 point 10 rebound games",
            "games_pts_30+_reb_10+",
            lambda g: (g["pts"] >= 30) & (g["reb"] >= 10),
        ),
        (
            "most 30/10 games this season",
            "games_pts_30+_reb_10+",
            lambda g: (g["pts"] >= 30) & (g["reb"] >= 10),
        ),
        (
            "who has the most 20 point 10 assist games",
            "games_pts_20+_ast_10+",
            lambda g: (g["pts"] >= 20) & (g["ast"] >= 10),
        ),
        (
            "most games with 10+ assists and 0 turnovers",
            "games_ast_10+_tov_0",
            lambda g: (g["ast"] >= 10) & (g["tov"] == 0),
        ),
        (
            "most 10 assist 0 turnover games",
            "games_ast_10+_tov_0",
            lambda g: (g["ast"] >= 10) & (g["tov"] == 0),
        ),
        ("most 0 turnover games", "games_tov_0", lambda g: g["tov"] == 0),
    ],
)
def test_condition_count_leaderboard_matches_raw_games(query, column, mask):
    games = _games(SEASON)
    counts = _event_counts(games, mask(games))

    rows = _sections(query)["leaderboard"]
    assert rows
    for row in rows:
        assert row[column] == counts[row["player_name"]], row
    assert rows[0][column] == counts.max()
    assert [row[column] for row in rows] == sorted((row[column] for row in rows), reverse=True)


@pytest.mark.fixture_data
def test_zero_turnover_condition_does_not_count_every_assist_game():
    games = _games(SEASON)
    with_zero = int(((games["ast"] >= 10) & (games["tov"] == 0)).sum())
    any_tov = int((games["ast"] >= 10).sum())
    assert with_zero < any_tov  # the fixture discriminates the two readings

    (count_row,) = _sections("how many games with 10+ assists and 0 turnovers this season")["count"]
    assert count_row["count"] == with_zero


@pytest.mark.fixture_data
def test_three_condition_ranking_across_seasons():
    games = _games("2024-25", SEASON)
    counts = _event_counts(games, (games["pts"] >= 25) & (games["reb"] >= 10) & (games["ast"] >= 5))
    rows = _sections("most 25 point 10 rebound 5 assist games since 2024")["leaderboard"]
    leader = rows[0]
    assert leader["games_pts_25+_reb_10+_ast_5+"] == counts.max()
    assert leader["player_name"] == counts.idxmax()


@pytest.mark.fixture_data
def test_single_player_condition_count():
    games = _games(SEASON)
    jokic = games[games["player_name"] == "Nikola Jokić"]
    expected = int(((jokic["pts"] >= 30) & (jokic["reb"] >= 10)).sum())
    (row,) = _sections("how many 30 point 10 rebound games does Jokic have this season")["count"]
    assert row["count"] == expected


# ---------------------------------------------------------------------------
# League-wide game lists and counts
# ---------------------------------------------------------------------------


@pytest.mark.fixture_data
@pytest.mark.parametrize(
    ("query", "mask"),
    [
        ("games with 10+ assists and 0 turnovers", lambda g: (g["ast"] >= 10) & (g["tov"] == 0)),
        ("show me 30 point 10 rebound games", lambda g: (g["pts"] >= 30) & (g["reb"] >= 10)),
        ("games with 40+ points this season", lambda g: g["pts"] >= 40),
    ],
)
def test_league_game_list_matches_raw_games(query, mask):
    games = _games(SEASON)
    expected = games[mask(games)]
    rows = _sections(query)["finder"]
    assert len(rows) == min(len(expected), 25)
    expected_keys = set(zip(expected["game_id"].astype(int), expected["player_id"]))
    assert {(int(r["game_id"]), r["player_id"]) for r in rows} <= expected_keys
    dates = [str(r["game_date"]) for r in rows]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.fixture_data
@pytest.mark.parametrize(
    ("query", "mask"),
    [
        (
            "How often has a player had 10+ assists and 0 turnovers this season?",
            lambda g: (g["ast"] >= 10) & (g["tov"] == 0),
        ),
        (
            "how many 30 point 10 rebound games this season",
            lambda g: (g["pts"] >= 30) & (g["reb"] >= 10),
        ),
        ("how many 40 point games this season", lambda g: g["pts"] >= 40),
    ],
)
def test_league_game_count_matches_raw_games(query, mask):
    games = _games(SEASON)
    (row,) = _sections(query)["count"]
    assert row["count"] == int(mask(games).sum())


# ---------------------------------------------------------------------------
# Qualified shooting-rate leaders
# ---------------------------------------------------------------------------


def _rate_board(
    made: str, attempted: str, minimum: float, *, per_game: bool = False
) -> pd.DataFrame:
    games = _games(SEASON)
    totals = games.groupby("player_name").agg(
        made=(made, "sum"), attempted=(attempted, "sum"), gp=("game_id", "nunique")
    )
    volume = totals["attempted"] / totals["gp"] if per_game else totals["attempted"]
    qualified = totals[volume >= minimum].copy()
    qualified["pct"] = qualified["made"] / qualified["attempted"]
    return qualified.sort_values(["pct", "gp"], ascending=[False, False])


@pytest.mark.fixture_data
@pytest.mark.parametrize(
    ("query", "column", "made", "attempted", "minimum", "per_game"),
    [
        ("best three point percentage minimum 300 attempts", "fg3_pct", "fg3m", "fg3a", 300, False),
        ("best 3pt% min 320 3pa this season", "fg3_pct", "fg3m", "fg3a", 320, False),
        ("best free throw percentage minimum 150 attempts", "ft_pct", "ftm", "fta", 150, False),
        ("best fg% with at least 900 attempts", "fg_pct", "fgm", "fga", 900, False),
        ("best 3 point percentage with 5+ attempts per game", "fg3_pct", "fg3m", "fg3a", 5, True),
    ],
)
def test_qualified_rate_leaders_match_raw_totals(query, column, made, attempted, minimum, per_game):
    expected = _rate_board(made, attempted, minimum, per_game=per_game).head(10)
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    rows = result.result.to_dict()["sections"]["leaderboard"]

    assert [r["player_name"] for r in rows] == list(expected.index)
    for row, (_, exp) in zip(rows, expected.iterrows()):
        assert row[column] == pytest.approx(exp["pct"])
    assert any("qualified: at least" in caveat for caveat in result.result.caveats)


@pytest.mark.fixture_data
def test_attempt_minimum_changes_who_qualifies():
    # Discriminating check: the stated minimum, not the default 100-attempt
    # floor, decides the board.
    default_board = _rate_board("fg3m", "fg3a", 100)
    strict_board = _rate_board("fg3m", "fg3a", 300)
    assert list(default_board.index[:10]) != list(strict_board.index[:10])


@pytest.mark.fixture_data
@pytest.mark.parametrize(
    "query",
    ["most points minimum 100 attempts", "team best 3 point percentage minimum 100 attempts"],
)
def test_attempt_minimum_outside_player_rates_still_refuses(query):
    result = execute_natural_query(query)
    assert result.result_status != "ok"


# ---------------------------------------------------------------------------
# Games played
# ---------------------------------------------------------------------------


@pytest.mark.fixture_data
@pytest.mark.parametrize(
    ("query", "seasons", "season_type"),
    [
        ("most games played", (SEASON,), "regular_season"),
        ("who has played the most games this season", (SEASON,), "regular_season"),
        ("most games played since 2024", ("2024-25", SEASON), "regular_season"),
        ("most playoff games played", (SEASON,), "playoffs"),
    ],
)
def test_games_played_leaders_match_raw_games(query, seasons, season_type):
    games = _games(*seasons, season_type=season_type)
    played = games.groupby("player_name")["game_id"].nunique()
    expected = played.reset_index().sort_values(["game_id", "player_name"], ascending=[False, True])
    rows = _sections(query)["leaderboard"]
    assert [r["player_name"] for r in rows] == list(expected["player_name"].head(10))
    assert [r["games_played"] for r in rows] == list(expected["game_id"].head(10))


@pytest.mark.fixture_data
def test_games_played_minimum_is_still_a_qualifier():
    result = execute_natural_query("best fg% minimum 50 games played")
    assert result.result_status == "ok"
    assert result.route == "season_leaders"
    rows = result.result.to_dict()["sections"]["leaderboard"]
    assert "fg_pct" in rows[0]


@pytest.mark.fixture_data
def test_team_games_played_ranking_has_one_column_and_name_ties():
    teams = pd.read_csv(
        Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")
        / f"{SEASON}_regular_season.csv"
    )
    played = teams.groupby("team_name")["game_id"].nunique().reset_index()
    expected = played.sort_values(["game_id", "team_name"], ascending=[False, True])
    rows = _sections("which team played the most games")["leaderboard"]
    assert [r["team_name"] for r in rows] == list(expected["team_name"].head(10))
    assert [r["games_played"] for r in rows] == list(expected["game_id"].head(10))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("at most 1 turnover", {"stat": "tov", "max_value": 1.0}),
        ("no more than 2 turnovers", {"stat": "tov", "max_value": 2.0}),
        ("2 turnovers or fewer", {"stat": "tov", "max_value": 2.0}),
        ("fewer than 2 turnovers", {"stat": "tov", "max_value": 2 - 0.0001}),
        ("under 2 turnovers", {"stat": "tov", "max_value": 2 - 0.0001}),
    ],
)
def test_upper_bound_wording_is_not_a_lower_bound(text, expected):
    from nbatools.commands._occurrence_route_utils import _parse_single_threshold

    assert _parse_single_threshold(text) == expected


@pytest.mark.fixture_data
@pytest.mark.parametrize(
    ("query", "column", "mask"),
    [
        (
            "most games with 20+ points and at most 1 turnover",
            "games_pts_20+_tov_1_or_fewer",
            lambda g: (g["pts"] >= 20) & (g["tov"] <= 1),
        ),
        (
            "most games with 10+ rebounds and fewer than 2 turnovers",
            "games_reb_10+_tov_under_2",
            lambda g: (g["reb"] >= 10) & (g["tov"] < 2),
        ),
    ],
)
def test_upper_bound_condition_leaders_match_raw_rows(query, column, mask):
    games = _games(SEASON)
    counts = _event_counts(games, mask(games))
    rows = _sections(query)["leaderboard"]
    assert [r[column] for r in rows] == sorted(counts.values, reverse=True)[: len(rows)]
    for row in rows:
        assert counts[row["player_name"]] == row[column], row


@pytest.mark.fixture_data
def test_at_most_count_is_a_league_count_not_a_ranking():
    games = _games(SEASON)
    expected = int(((games["pts"] >= 20) & (games["tov"] <= 1)).sum())
    (row,) = _sections("how many games with 20+ points and at most 1 turnover this season")["count"]
    assert row["count"] == expected
