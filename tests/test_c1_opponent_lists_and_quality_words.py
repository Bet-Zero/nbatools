"""Opponent lists, quality words and "top N games" against a group.

- "Lakers record vs Celtics, Knicks and Heat" answered Boston's record, and
  "vs Celtics and Knicks" refused (it had kept Boston only); "vs Celtics or
  Knicks" refused as a boolean OR; "Knicks record vs Heat and Celtics" made
  Boston the team; streaks kept the first opponent only.
- "vs contending / elite / great / strong / weak / poor opponents" returned
  every game.
- "LeBron James top 5 games vs good opponents" dropped "top 5" and gave a
  summary; "top 5 games vs Celtics" listed the last 5.

Expected values are counted with pandas from the fixture (2025-26 unless a
streak spans the default three seasons).
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
    ("query", "record"),
    [
        ("Lakers record vs Celtics, Knicks and Heat", (36, 23, 13)),
        ("Lakers record vs the Celtics, the Knicks, and the Heat", (36, 23, 13)),
        ("Lakers record vs Celtics and Knicks", (24, 11, 13)),
        ("Lakers record vs Celtics or Knicks", (24, 11, 13)),
        ("Lakers record vs Celtics, Knicks and Heat at home", (18, 13, 5)),
        ("Lakers record vs Celtics and Knicks when they score 120", (8, 7, 1)),
        ("Celtics record vs Lakers, Warriors and Nuggets", (36, 30, 6)),
        ("Knicks record vs Heat and Celtics", (24, 17, 7)),
        ("LeBron James record vs Celtics, Knicks", (24, 11, 13)),
    ],
)
def test_opponent_list_records(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    ("query", "count"),
    [
        ("Lakers games vs Celtics or Knicks", 24),
        ("Lakers games vs Celtics, Knicks", 24),
        ("LeBron James games vs Celtics and Knicks", 24),
        ("LeBron James 30 point games vs Celtics, Knicks and Heat", 8),
    ],
)
def test_opponent_list_games(query, count):
    assert len(_execute(query)["finder"]) == count


@pytest.mark.parametrize(
    ("query", "length"),
    [
        ("Lakers longest winning streak vs Celtics, Knicks and Heat", 9),
        ("Lakers longest winning streak vs Celtics and Knicks", 6),
        ("LeBron James longest streak of 30 point games vs Celtics and Knicks", 2),
        ("LeBron James longest streak of 20 point games vs Celtics, Knicks and Heat", 10),
    ],
)
def test_opponent_list_streaks(query, length):
    assert _execute(query)["streak"][0]["streak_length"] == length


def test_clause_after_the_list_still_refuses():
    from nbatools.query_service import execute_natural_query

    query = "Lakers record vs Celtics and the Knicks score 110"
    assert execute_natural_query(query).result_status == "no_result"


@pytest.mark.parametrize(
    ("query", "term"),
    [
        ("Lakers record vs contending opponents", "contenders"),
        ("Lakers record vs contending teams", "contenders"),
        ("Lakers record vs elite teams", "top teams"),
        ("Lakers record vs great opponents", "top teams"),
        ("Lakers record vs strong teams", "good teams"),
        ("Lakers record vs weak teams", "bad teams"),
        ("Lakers record vs poor opponents", "bad teams"),
    ],
)
def test_quality_words(query, term):
    from nbatools.commands.natural_query import parse_query

    assert parse_query(query)["route_kwargs"]["opponent_quality"]["surface_term"] == term


@pytest.mark.parametrize(
    ("query", "record"),
    [
        # BOS and NYK are the winning teams; the conference top six is all six.
        ("Lakers record vs strong teams", (24, 11, 13)),
        ("Lakers record vs weak teams", (36, 36, 0)),
        ("Lakers record vs contending opponents", (60, 47, 13)),
    ],
)
def test_quality_word_records(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    ("query", "points"),
    [
        ("LeBron James top 5 games vs good opponents", [35, 33, 32, 31, 30]),
        ("LeBron James top 5 games vs Celtics", [35, 33, 31, 27, 26]),
    ],
)
def test_top_n_games_rank_by_points(query, points):
    rows = _execute(query)["finder"]
    assert [row["pts"] for row in rows] == points
