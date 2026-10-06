"""Player clauses inside a team-record sample.

- "Lakers record when LeBron plays and scores 30" checked 30 points against
  the team's points and answered with the whole record.
- "when Luka sits" was not read as absence at all.
- "in games LeBron plays 35 minutes and Luka plays 35 minutes" dropped Luka.
- "and the Lakers play at home" after a minutes bound counted as a second
  player and refused.
- "below 3 turnovers" was read as a floor, and "... but loses" was ignored.

Expected values are counted from the fixture.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _execute(query: str):
    from nbatools.query_service import execute_natural_query

    return execute_natural_query(query)


def _record(query: str) -> tuple[int, int, int]:
    result = _execute(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    summary = result.result.to_dict()["sections"]["summary"][0]
    return summary["wins"], summary["losses"], summary["games"]


def _rows(query: str) -> list[dict]:
    result = _execute(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]["finder"]


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when LeBron James plays and scores at least 30 points", (10, 1, 11)),
        ("Lakers record when LeBron James plays and has 10 assists", (6, 0, 6)),
        (
            "Lakers record when LeBron James plays at least 35 minutes and the Lakers play at home",
            (2, 0, 2),
        ),
        ("Lakers record when LeBron James plays at least 35 minutes but loses", (0, 1, 1)),
        ("Lakers record when LeBron James scores 30 but they lose", (0, 1, 1)),
        ("Lakers record in games with not under 120 points", (18, 1, 19)),
    ],
)
def test_player_clause_is_applied(query, record):
    assert _record(query) == record


def test_plays_and_scores_matches_scores():
    assert _record("Lakers record when LeBron James plays and scores at least 30 points") == (
        _record("Lakers record when LeBron James scores at least 30 points")
    )


@pytest.mark.parametrize(
    "query",
    [
        # Luka played every fixture game, so his absence leaves no games.
        "Lakers record when Luka Doncic sits",
        "Lakers record when Luka Doncic rests",
    ],
)
def test_sits_is_absence(query):
    result = _execute(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "no_match"


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record when LeBron James plays and Luka Doncic sits",
        "Lakers record in games LeBron James plays at least 35 minutes and Luka Doncic plays "
        "at least 35 minutes",
        # A second player the resolver can't name still isn't dropped.
        "Lakers record when LeBron James plays 35 minutes and Davis sits",
        "Lakers record when LeBron James plays and scores 30 points and Davis sits",
        "Lakers record when LeBron James plays and scores 30 points while Davis rests",
        "Lakers record when LeBron James plays and scores 30 points while Davis is out",
        "Lakers record when Davis sits",
        # The first player's own stat can't be checked on team rows.
        "Lakers record when LeBron James plays and scores 30 points and Davis plays",
        "Lakers record when LeBron James plays and has 10 assists and Anthony Davis plays",
        "Lakers record when LeBron James plays and scores 30 points and the starters play 30 "
        "minutes",
    ],
)
def test_second_player_clause_refuses(query):
    result = _execute(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"


def test_below_is_a_ceiling():
    assert _rows("LeBron James games with below 3 turnovers") == _rows(
        "LeBron James games with at most 2 turnovers"
    )
    assert _rows("LeBron James games with 30 points and below 3 turnovers") == _rows(
        "LeBron James games with 30 points and at most 2 turnovers"
    )


def test_team_sitting_is_not_an_absence():
    # "they sit atop the standings" names no player; the record is unfiltered.
    assert _record("Lakers record when they sit atop the standings") == (47, 13, 60)


@pytest.mark.parametrize(
    ("query", "record"),
    [
        (
            "Lakers record when LeBron James plays and grabs 10 rebounds and the defense plays "
            "well",
            (11, 2, 13),
        ),
        ("Lakers record when LeBron James plays and scores 30 points and LA plays", (10, 1, 11)),
        (
            "Lakers record when LeBron James plays and scores 30 points and the Lakers play at home",
            (4, 1, 5),
        ),
        # A team stat beside presence still filters team rows.
        ("Lakers record with LeBron James in games with 120 points", (18, 1, 19)),
    ],
)
def test_team_subjects_are_not_second_players(query, record):
    assert _record(query) == record
