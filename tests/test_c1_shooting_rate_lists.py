"""Shooting rates written as a list or an abbreviation.

- "shoot 80% from the line and 40% from three" kept only the first rate.
- "with ts 60%", "with efg 55%" and "40% from 3s" were ignored and answered
  with every game.

Expected values are counted with pandas from the fixture.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _execute(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]


def _record(query: str) -> tuple[int, int]:
    summary = _execute(query)["summary"][0]
    return summary["wins"], summary["losses"]


def _count(query: str) -> int:
    return _execute(f"how many {query}")["count"][0]["count"]


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when they shoot 80% from the line and 40% from three", (1, 0)),
        ("Lakers record when they shoot 50% from the field and 40% from three", (38, 8)),
        ("Lakers record when they shoot 40% from 3s", (39, 10)),
        ("Lakers record when they shoot 50% and allow under 110", (42, 3)),
    ],
)
def test_team_rate_lists(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    ("query", "count"),
    [
        ("LeBron James games shooting 50% on threes and 90% from the line", 8),
        ("LeBron James games with ts 60%", 48),
        ("LeBron James games with efg 55%", 52),
    ],
)
def test_player_rate_lists_and_abbreviations(query, count):
    assert _count(query) == count


def test_joined_rate_needs_its_own_area():
    from nbatools.commands._parse_helpers import _extract_shooting_percentage_conditions

    # "and 15 threes" is a count, not a second rate.
    found = _extract_shooting_percentage_conditions(
        "lakers record when they shoot 50% and 15 threes"
    )
    assert [c["stat"] for c in found] == ["fg_pct"]


@pytest.mark.parametrize(
    ("query", "count"),
    [
        # A joined count stays beside the rate.
        ("LeBron James games with ft 80% and 5 fta", 6),
        ("LeBron James games with fg 50% and 5 threes", 13),
        ("LeBron James games with ts 60% and 10 rebounds", 12),
        ("LeBron James games with ft 80% and 25 points", 4),
        ("LeBron James games shooting 50% and 5 threes", 13),
    ],
)
def test_rate_and_joined_count(query, count):
    assert _count(query) == count


def test_team_rate_and_joined_count():
    assert _record("Lakers record with fg 50% and 15 threes") == (17, 2)


def test_another_clauses_count_is_not_joined_to_the_rate():
    assert _record("Lakers record when they shoot 50% and opponents score 110 and 15 threes") == (
        1,
        4,
    )
    assert _count("LeBron James games shooting 50% when opponents score 110 and 15 threes") == 5


def test_team_clause_keeps_its_joined_count():
    # "when the Lakers score 120 and 30 assists": the team's assists.
    assert _count("LeBron James games when the Lakers score 120 and 30 assists") == 2
    assert _count("LeBron James games shooting 50% when the Lakers score 120 and 30 assists") == 1
