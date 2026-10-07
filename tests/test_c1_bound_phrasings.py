"""Bound and order wording the readers missed.

- "10 assists at most" / "10 assists max" read as a 10-assist floor, and
  "30 minutes or under" refused as a boolean "or".
- "no-more-than" and "never more than" read as floors.
- "Lakers record when held to 100 points" counted games with 100 or more.
- "vs below .500 teams" was ignored and answered with every game.
- "Lakers lowest scoring games" listed the highest-scoring games first.

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


def _rows(query: str) -> list[dict]:
    return _execute(query)["finder"]


def _record(query: str) -> tuple[int, int]:
    summary = _execute(query)["summary"][0]
    return summary["wins"], summary["losses"]


@pytest.mark.parametrize(
    ("phrasing", "canonical"),
    [
        (
            "LeBron James games with 10 assists at most",
            "LeBron James games with 10 assists or fewer",
        ),
        ("LeBron James games with 10 assists max", "LeBron James games with 10 assists or fewer"),
        (
            "LeBron James games with 30 minutes or under",
            "LeBron James games with 30 minutes or fewer",
        ),
        (
            "Lakers games with no-more-than 10 turnovers",
            "Lakers games with no more than 10 turnovers",
        ),
        (
            "LeBron James games with never more than 2 turnovers",
            "LeBron James games with no more than 2 turnovers",
        ),
    ],
)
def test_ceiling_wording_matches_its_canonical_form(phrasing, canonical):
    assert _rows(phrasing) == _rows(canonical)


def test_ceiling_counts():
    assert max(row["ast"] for row in _rows("LeBron James games with 10 assists at most")) == 10
    assert max(row["minutes"] for row in _rows("LeBron James games with 30 minutes or under")) < 30
    assert len(_rows("Lakers games with no-more-than 10 turnovers")) == 7
    assert len(_rows("LeBron James games with never more than 2 turnovers")) == 22


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when held to 100 points", (6, 8)),
        ("Lakers record when held to 100", (6, 8)),
        ("Lakers record vs below .500 teams", (36, 0)),
        ("Lakers record vs above .500 teams", (11, 13)),
    ],
)
def test_team_record_samples(query, record):
    assert _record(query) == record


def test_team_lowest_scoring_games_run_lowest_first():
    assert [row["pts"] for row in _rows("Lakers lowest scoring games")][:6] == [
        81,
        83,
        84,
        86,
        89,
        90,
    ]
    assert [row["tov"] for row in _rows("Lakers games with the fewest turnovers")][:4] == [
        5,
        5,
        7,
        9,
    ]
    assert [row["pts"] for row in _rows("Lakers highest scoring games")][:2] == [153, 141]


def test_or_under_before_a_number_is_still_boolean():
    from nbatools.commands._constants import contains_boolean_or

    assert contains_boolean_or("LeBron games with 30 points or under 5 turnovers")
    assert not contains_boolean_or("LeBron games with 30 minutes or under")


@pytest.mark.parametrize(
    ("query", "record"),
    [
        # A bare number before "or under / lower / below" is a ceiling too.
        ("Lakers record when they score 100 or under", (6, 8)),
        ("Lakers record when they score 100 or lower", (6, 8)),
        ("Lakers record when scoring 100 or below", (6, 8)),
        ("Lakers record when they allow 100 or under", (41, 2)),
        ("Lakers record when opponents score 100 or under", (41, 2)),
        ("LeBron James record when he scores 20 or under", (12, 6)),
    ],
)
def test_bare_number_ceiling(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    "query",
    [
        # ".500 or below" includes .500, which no reader handles yet.
        "Lakers record against teams at .500 or below",
        "Lakers record vs teams .500 or below",
    ],
)
def test_500_or_below_still_refuses(query):
    from nbatools.query_service import execute_natural_query

    assert execute_natural_query(query).result_status == "no_result"


def test_held_to_reads_only_the_subjects_points():
    from nbatools.commands._parse_helpers import canonicalize_bound_phrases

    assert "or fewer" in canonicalize_bound_phrases("lakers record when held to 100")
    for text in (
        "lakers record when held to 40% shooting",
        "lakers games when held to 40 percent shooting",
        "lakers record when opponents were held to 100",
        "lakers record when the celtics were held to 100",
    ):
        assert canonicalize_bound_phrases(text) == text
