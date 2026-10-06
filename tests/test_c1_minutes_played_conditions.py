"""A minutes bound on "record when PLAYER plays ...".

"Lakers record when LeBron plays at least 35 minutes" answered with the team's
whole record: "when PLAYER plays" was read as whole-game presence and the
minutes bound was dropped. The ceiling form gave no games at all. The bound is
now a condition on that player's minutes, exactly as "when LeBron has at least
35 minutes" already was. Expected values are counted from the fixture.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _summary(query: str) -> dict:
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]["summary"][0]


def _record(query: str) -> tuple[int, int, int]:
    summary = _summary(query)
    return summary["wins"], summary["losses"], summary["games"]


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when LeBron James plays at least 35 minutes", (6, 1, 7)),
        ("Lakers record when LeBron James plays 35+ minutes", (6, 1, 7)),
        ("Lakers record when LeBron James plays 35 minutes", (6, 1, 7)),
        ("Lakers record when LeBron James plays at least 30 minutes", (15, 5, 20)),
        ("Lakers record when LeBron James plays under 30 minutes", (32, 8, 40)),
        ("Lakers record when LeBron James plays 30 minutes or less", (32, 8, 40)),
        ("Lakers record when LeBron James plays at most 25 minutes", (19, 2, 21)),
    ],
)
def test_minutes_bound_is_applied(query, record):
    assert _record(query) == record


def test_floor_and_ceiling_partition_the_games_he_played():
    # 30+ minutes and under 30 split the games he played, with nothing lost
    # and nothing double counted.
    played = _record("Lakers record when LeBron James plays")
    floor = _record("Lakers record when LeBron James plays at least 30 minutes")
    ceiling = _record("Lakers record when LeBron James plays under 30 minutes")
    assert tuple(a + b for a, b in zip(floor, ceiling)) == played


def test_plays_matches_the_has_phrasing():
    assert _record("Lakers record when LeBron James plays at least 35 minutes") == _record(
        "Lakers record when LeBron James has at least 35 minutes"
    )


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record when LeBron James plays",
        "Lakers record when LeBron James plays this season",
        "Lakers record when LeBron James played",
    ],
)
def test_bare_presence_still_reads_as_presence(query):
    # No bound stated: every game he played, not a minutes condition.
    assert _record(query) == (47, 13, 60)
