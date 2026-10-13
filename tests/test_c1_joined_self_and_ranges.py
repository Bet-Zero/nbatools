"""Joined clauses that name the team itself, and opponent ranges.

- "Lakers record when the Lakers score 120 and the Celtics score 110" answered
  as the Celtics (the first clause named the Lakers, so the joined Celtics
  clause was never read).
- "... and LA makes 15 threes" dropped the threes; a Celtics record "when LA
  scores 110" read the Celtics' own points.
- "when they score between 110 and 120 and make 15 threes" dropped the threes.
- "opponents had 40 to 50 rebounds" and "allowing 10-15 threes" read the
  Lakers' own stat.
- "when opposition scores 120" refused on the name check.

Expected values are counted with pandas from the fixture.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _record(query: str) -> tuple[int, int]:
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    summary = result.result.to_dict()["sections"]["summary"][0]
    return summary["wins"], summary["losses"]


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when the Lakers score 120 and the Celtics score 110", (2, 1)),
        ("Lakers record when LA scores 120 and the Celtics score 110", (2, 1)),
        ("Lakers record when the Lakers score 120 and make 15 threes", (7, 0)),
        ("Lakers record when they score 120 and LA makes 15 threes", (7, 0)),
        ("Lakers record when they score 120 and L.A. makes 15 threes", (7, 0)),
        ("Lakers record when they score between 110 and 120 and make 15 threes", (7, 0)),
        ("Lakers record when they score 110 or fewer and make 15 threes", (7, 2)),
        ("Lakers record when they shoot 50% and make 15 threes", (17, 2)),
        ("Lakers record when opponents had 40 to 50 rebounds", (8, 4)),
        ("Lakers record when allowing 10-15 threes", (20, 5)),
        ("Lakers record when allowing 10 to 15 threes", (20, 5)),
        ("Lakers record when they allow 20-30 assists", (28, 4)),
        ("Lakers record when opposition scores 120", (2, 5)),
    ],
)
def test_records(query, record):
    assert _record(query) == record


def test_the_teams_own_name_reads_as_they():
    from nbatools.commands.natural_query import parse_query

    kwargs = parse_query("Lakers games when the Lakers score 120 and the Celtics score 110")[
        "route_kwargs"
    ]
    assert kwargs["team"] == "LAL"
    stats = {(c["stat"], c["min_value"]) for c in kwargs.get("conditions") or []}
    assert ("opponent_pts", 110.0) in stats


@pytest.mark.parametrize(
    "query",
    [
        # LA is the Lakers or the Clippers; not read for another team.
        "Celtics record when they score 120 and LA scores 110",
        "best record when LA scores 120",
    ],
)
def test_la_for_another_team_refuses(query):
    from nbatools.query_service import execute_natural_query

    assert execute_natural_query(query).result_status == "no_result"
