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
