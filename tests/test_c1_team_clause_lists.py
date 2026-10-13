"""C1: team-route clause lists and points-allowed wording.

- "Lakers record when they score 120 and make 15 threes" kept only the points.
- "when they shoot 50% and the Celtics score 110" answered Boston's record.
- "when they hold opponents to under 100", "give up less than 100" and "the
  opposition scores 120" were dropped or read as the Lakers' own points.
- "opponents had between 40 and 50 rebounds" / "allowing between 10 and 15
  threes" read the Lakers' own stat.
- "Lakers record when Davis scores 30" (no Davis resolved) read the team's
  30 points: every game.

Expected values are counted with pandas from the fixture.
"""

from __future__ import annotations

import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


def _execute(query: str):
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    return result.result.to_dict()["sections"]


def _record(query: str) -> tuple[int, int]:
    summary = _execute(query)["summary"][0]
    return summary["wins"], summary["losses"]


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when they score 120 and make 15 threes", (7, 0)),
        ("Lakers record when they score 120 and they make 15 threes", (7, 0)),
        ("Lakers record when they make 15 threes and they score 120", (7, 0)),
        ("Lakers record when they score 120 and they have 30 assists", (2, 0)),
        ("Lakers record when they score 120", (18, 1)),
        ("Lakers record when they shoot 50% and the Celtics score 110", (2, 5)),
        ("Lakers record when they score 120 and the Celtics score 110", (2, 1)),
        ("Lakers record when they hold opponents to under 100", (40, 2)),
        ("Lakers record when holding opponents to under 100", (40, 2)),
        ("Lakers record when they give up less than 100 points", (40, 2)),
        ("Lakers record when the opposition scores 120", (2, 5)),
        ("Lakers record when another team scores 120", (2, 5)),
        ("Lakers record when opponents had between 40 and 50 rebounds", (8, 4)),
        ("Lakers record when allowing between 10 and 15 threes", (20, 5)),
        ("Lakers record when they had between 40 and 50 rebounds", (12, 3)),
    ],
)
def test_team_clause_records(query, record):
    assert _record(query) == record


def test_team_clause_lists_on_game_lists():
    assert len(_execute("Lakers games when they score 120 and they make 15 threes")["finder"]) == 7


def test_unknown_name_clause_refuses():
    result = execute_natural_query("Lakers record when Davis scores 30")
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"
