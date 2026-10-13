"""Wording the sample readers dropped and answered with the wrong sample.

- "LeBron games with Davis" / "without Davis": an unresolved teammate was
  dropped and every game came back.
- "Lakers record vs Celtics and Knicks" kept Boston only.
- "Lakers record when the Celtics' opponents score 110" answered Boston's
  record.
- "Lakers 120 point seasons" and "40% shooting seasons" listed games.
- "when the score was 120" was dropped.

Each now refuses until it is read.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _status(query: str) -> str:
    from nbatools.query_service import execute_natural_query

    return execute_natural_query(query).result_status


@pytest.mark.parametrize(
    "query",
    [
        "LeBron James games with Davis",
        "LeBron James games without Davis",
        "LeBron James games with Davis with 30 points",
        "Lakers record vs Celtics and Knicks",
        "Lakers record vs Celtics and Knicks when they score 120",
        "Lakers record when the Celtics' opponents score 110",
        "Lakers record when the Celtics opponents score 110",
        "Lakers 120 point seasons",
        "Lakers 40% shooting seasons",
        "Lakers seasons with 40% shooting",
        "Lakers record when the score was 120 and they had 30 assists",
    ],
)
def test_unread_samples_refuse(query):
    assert _status(query) == "no_result"


def _record(query: str) -> tuple[int, int]:
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.metadata)
    summary = result.result.to_dict()["sections"]["summary"][0]
    return summary["wins"], summary["losses"]


@pytest.mark.parametrize(
    ("query", "record"),
    [
        # The subject's own opponents, and an opponent clause after "vs".
        ("Lakers record when the Lakers' opponents score 110", (3, 9)),
        ("Lakers record vs Celtics when opponents made 15+ threes", (1, 4)),
        ("Lakers record vs Celtics and they score 120", (3, 1)),
    ],
)
def test_neighbouring_wording_still_answers(query, record):
    assert _record(query) == record


def test_stat_bounds_after_with_are_not_teammates():
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query("LeBron James games with 30 points")
    assert len(result.result.to_dict()["sections"]["finder"]) == 11
