"""Ratings groups, season-described opponents and a team's best games.

- "vs top 10 defenses" / "offenses" raised an error when the ratings table
  names teams by id only.
- "vs teams that score 115 points per game" read the team's own points, and
  "vs teams who average 115 points" became a player list; both describe the
  opponents' season, which is not loaded, and refuse.
- "vs teams that are winning" was dropped.
- "Lakers top 5 games", "best games" and "worst games" listed games by date;
  they rank by final margin.

Expected values are counted with pandas from the fixture (2025-26).
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _execute(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]


def _record(query: str) -> tuple[int, int, int]:
    summary = _execute(query)["summary"][0]
    return summary["games"], summary["wins"], summary["losses"]


@pytest.mark.parametrize(
    ("metric", "expected"),
    [
        # Lowest defensive rating: NYK 91.9, BOS 92.5; highest offensive:
        # LAL 110.2, BOS 102.2.
        ("def_rating_rank", ["BOS", "NYK"]),
        ("off_rating_rank", ["BOS", "LAL"]),
    ],
)
def test_ratings_groups_name_teams_by_id(metric, expected):
    from nbatools.commands.data_utils import resolve_opponent_quality_teams

    quality = {"definition": {"metric": metric, "operator": "top_n", "value": 2}}
    assert resolve_opponent_quality_teams(quality, ["2025-26"], "Regular Season") == expected


@pytest.mark.parametrize(
    ("query", "record"),
    [
        # Every fixture team is in the top 10.
        ("Lakers record vs top 10 defenses", (60, 47, 13)),
        ("Celtics record vs top 10 offenses", (60, 43, 17)),
        ("Lakers record vs teams that are winning", (24, 11, 13)),
        ("Lakers record vs teams that are losing", (36, 36, 0)),
    ],
)
def test_records(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record vs teams that score 115 points per game",
        "Lakers record vs teams that score 115 ppg",
        "Lakers record vs teams who average 115 points",
    ],
)
def test_season_descriptions_refuse(query):
    from nbatools.query_service import execute_natural_query

    assert execute_natural_query(query).result_status == "no_result"


@pytest.mark.parametrize(
    ("query", "margins"),
    [
        ("Lakers top 5 games", [79, 76, 68, 65, 59]),
        ("Lakers top 5 games by margin", [79, 76, 68, 65, 59]),
        ("Lakers best games in March", [9, -2, -26]),
        ("Lakers top 3 games vs Celtics", [79, 20, 9]),
    ],
)
def test_team_best_games_rank_by_margin(query, margins):
    assert [row["plus_minus"] for row in _execute(query)["finder"]] == margins


def test_team_worst_games_rank_lowest_first():
    rows = _execute("Lakers worst games")["finder"]
    assert [row["plus_minus"] for row in rows[:5]] == [-52, -38, -36, -36, -26]


@pytest.mark.parametrize(
    ("query", "stat"),
    [
        # A named ranking stat still wins.
        ("Lakers top 5 scoring games", "pts"),
        ("Lakers top 5 games by assists", "ast"),
        ("Lakers biggest wins", "win_margin"),
        ("LeBron James top 5 games", "pts"),
    ],
)
def test_named_ranking_stats_stay(query, stat):
    from nbatools.commands.natural_query import parse_query

    assert parse_query(query)["route_kwargs"]["stat"] == stat
