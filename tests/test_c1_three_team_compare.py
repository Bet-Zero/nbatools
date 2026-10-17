"""C1: three teams compared side by side.

"Lakers vs Celtics vs Knicks" compared Boston and New York only, and
"compare Lakers, Celtics and Knicks" listed Boston's games. Expected values
come from the fixture's rows.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]

RAW = Path("qa/fixtures/query_engine_sample/data/raw/team_game_stats")


def _games(*seasons: str) -> pd.DataFrame:
    return pd.concat(pd.read_csv(RAW / f"{s}_regular_season.csv") for s in seasons)


def _expected(games: pd.DataFrame, last: int | None = None) -> list[tuple]:
    rows = []
    for abbr in ("LAL", "BOS", "NYK"):
        team = games[games["team_abbr"] == abbr].sort_values("game_date")
        if last:
            team = team.tail(last)
        rows.append((abbr, len(team), int((team["wl"] == "W").sum()), round(team["pts"].mean(), 3)))
    return rows


def _summary(query: str) -> list[tuple]:
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    assert result.route == "team_compare"
    return [
        (row["team_name"], row["games"], row["wins"], round(row["pts_avg"], 3))
        for row in result.result.to_dict()["sections"]["summary"]
    ]


@pytest.mark.parametrize(
    "query",
    [
        "Lakers vs Celtics vs Knicks",
        "compare Lakers, Celtics and Knicks this season",
        "compare the Lakers, the Celtics, and the Knicks",
        "compare Lakers and Celtics and Knicks",
    ],
)
def test_three_teams_this_season(query):
    assert _summary(query) == _expected(_games("2025-26"))


def test_three_teams_over_a_span():
    expected = _expected(_games("2024-25", "2025-26"))
    assert _summary("compare Lakers, Celtics and Knicks since 2024-25") == expected


def test_three_teams_at_home_and_last_10():
    games = _games("2025-26")
    assert _summary("Lakers vs Celtics vs Knicks at home") == _expected(
        games[games["is_home"] == 1]
    )
    assert _summary("Lakers vs Celtics vs Knicks last 10 games") == _expected(games, last=10)


def test_comparison_table_has_three_columns():
    result = execute_natural_query("Lakers vs Celtics vs Knicks")
    row = result.result.to_dict()["sections"]["comparison"][0]
    assert set(row) == {"metric", "LAL", "BOS", "NYK"}


def test_a_condition_beside_three_teams_refuses():
    result = execute_natural_query("Lakers vs Celtics vs Knicks when LeBron scores 30")
    assert result.result_status == "no_result"


def test_two_teams_keep_their_comparison():
    assert len(_summary("Lakers vs Celtics")) == 2


@pytest.mark.parametrize(
    ("query", "season", "month"),
    [
        ("Lakers vs Celtics vs Knicks in March", "2025-26", "2026-03"),
        ("Lakers vs Celtics vs Knicks in March 2024", "2023-24", "2024-03"),
        ("Lakers vs Celtics vs Knicks points per game", "2025-26", None),
    ],
)
def test_three_teams_keep_month_and_explicit_scoring_scope(query, season, month):
    """All three independently scoped team rows, not a two-team fallback."""
    games = _games(season)
    if month is not None:
        games = games[games["game_date"].astype(str).str.startswith(month)]
    expected = _expected(games)
    assert all(row[1] > 0 for row in expected)
    assert _summary(query) == expected


@pytest.mark.parametrize(
    "query",
    [
        "Lakers vs Celtics vs Knicks longest win streak",
        "Lakers vs Celtics vs Knicks head to head",
        "Lakers vs Celtics vs Knicks in wins",
        "Lakers vs Celtics vs Knicks when LeBron scores 30",
    ],
)
def test_three_teams_refuse_unread_conditions_instead_of_dropping_a_team(query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result", (query, result.route, result.result_reason)


def test_three_team_best_stretch_preserves_existing_specialized_route():
    result = execute_natural_query("Lakers vs Celtics vs Knicks best 5 game stretch")
    assert result.result_status == "ok"
    assert result.result.to_dict()["sections"]["leaderboard"]
