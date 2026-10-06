"""Adjective game lists with a second condition.

"LeBron 30 point games with 10 assists" refused, and "Lakers record in 120
point games with 15+ threes" read "with 120 points" as a teammate. The
adjective form now reads as the condition list "games with 30 points and 10
assists". Expected values are counted from the fixture.
"""

from __future__ import annotations

import pytest

from nbatools.commands._parse_helpers import canonicalize_sample_phrases

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("lebron 30 point games with 10 assists", "lebron games with 30 points and 10 assists"),
        ("lakers 120 point games with 15+ threes", "lakers games with 120 points and 15+ threes"),
        (
            "lebron 30 point games with at least 8 assists",
            "lebron games with 30 points and at least 8 assists",
        ),
        (
            "lebron 30 point games where he had 10 rebounds",
            "lebron games with 30 points and 10 rebounds",
        ),
        # A teammate stays a teammate.
        ("lebron 30 point games with anthony davis", "lebron 30 point games with anthony davis"),
    ],
)
def test_adjective_games_with_rewrite(text, expected):
    assert canonicalize_sample_phrases(text) == expected


@pytest.mark.parametrize(
    ("query", "rows"),
    [
        ("LeBron 30 point games with 10 assists", 2),
        ("LeBron 30 point games with at least 8 assists", 6),
        ("LeBron 30 point games where he had 10 rebounds", 2),
        ("Lakers 120 point games with 15+ threes", 7),
    ],
)
def test_adjective_games_with_rows(query, rows):
    assert len(_run(query).result.to_dict()["sections"]["finder"]) == rows


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Lakers record in 120 point games with 15+ threes", (7, 7, 0)),
        ("Lakers record in games with 120 points and 15 threes", (7, 7, 0)),
        ("Lakers record with 120 points", (19, 18, 1)),
    ],
)
def test_record_with_a_count_is_a_condition(query, expected):
    row = _run(query).result.to_dict()["sections"]["summary"][0]
    assert (row["games"], row["wins"], row["losses"]) == expected


def test_or_alternative_keeps_first_condition():
    # 30+ points and (10+ assists or 10+ rebounds), not (30 and 10 ast) or 10 reb.
    rows = _run("LeBron 30 point games with 10 assists or 10 rebounds").result.to_dict()
    finder = rows["sections"]["finder"]
    assert len(finder) == 4
    assert all(row["pts"] >= 30 for row in finder)


@pytest.mark.parametrize(
    "query",
    [
        # Counts that are not box-score stats still refuse instead of
        # returning the unfiltered record.
        "Lakers record in games with 1 day of rest",
        "Lakers record in games with 2 overtimes",
        "Lakers record in games with 6 players in double figures",
        "Lakers record in games with 2 players scoring 30",
        "Lakers record with at least 3 days rest",
        "Lakers record with 23",
        # A player named after the stat bound cannot be combined yet.
        "Lakers record in games with 15 threes and LeBron",
        "Lakers record in games with 120 points with LeBron",
        "Lakers record when LeBron scores 30 in games with 120 points",
        # A stat noun the threshold reader does not read.
        "Lakers record in games with 15 3-pointers",
        # "or" before a season is not a stat alternative.
        "LeBron 30 point games with 10 assists in 2023-24 or 2024-25",
        # A clause after the bound that nothing reads.
        "Lakers record in games with 120 points and 2 players scoring 30",
        "Lakers record in games with 30 assists and 2 days rest",
        "Lakers record in games with 120 points when Davis sits",
        "Lakers record in games with 10 rebounds from Davis",
        "Lakers record in games with 120 points while allowing 130",
        "Lakers record in games with 120 points, 2 days rest",
        "Lakers record in games with 120 points in games where Davis sits",
        "Lakers record in games with 120 points before the all-star break",
        "Lakers record in games with 120 points in close games",
        "Lakers record in games with 120 points after a loss",
    ],
)
def test_non_stat_counts_still_refuse(query):
    from nbatools.query_service import execute_natural_query

    assert execute_natural_query(query).result_status != "ok"


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record in games with 10 or more turnovers", (45, 11)),
        ("Lakers record in games with 120 points or more", (18, 1)),
        ("Lakers record in games with 120 points vs the Celtics", (3, 1)),
        ("Lakers record in games with 120 points on the road", (5, 1)),
        ("Lakers record in games with 120 points against teams over .500", (7, 1)),
        ("Lakers record in games with 120 points after the all-star break", (10, 1)),
        ("Lakers record in games with 120 points in December", (2, 0)),
    ],
)
def test_team_record_stat_count_with_scope(query, record):
    summary = _run(query).result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == record
