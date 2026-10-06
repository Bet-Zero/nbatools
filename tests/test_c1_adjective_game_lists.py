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
        # Opponents and players after the bound must resolve.
        "Lakers record in games with 120 points against division rivals",
        "Lakers record in games with 120 points if anyone plays",
        # A non-stat count after filler is not rewritten into a bound.
        "LeBron 30 point games for the Lakers with 2 teammates scoring 20",
        "Lakers 120 point games this season with 2 players scoring 30",
        "LeBron 30 point games this season with 3 days rest",
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
        ("Lakers record in games with 120 points against the Golden State Warriors", (3, 0)),
        ("Lakers record in games with 120 points vs the Celtics at home", (2, 0)),
    ],
)
def test_team_record_stat_count_with_scope(query, record):
    summary = _run(query).result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == record


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "how many 30 point games did lebron have with 5+ threes",
            "how many games did lebron have with 30 points and 5+ threes",
        ),
        (
            "lebron 30 point games this season with 5 threes",
            "lebron games this season with 30 points and 5 threes",
        ),
        # A teammate between keeps the adjective form.
        (
            "lebron 30 point games with anthony davis with 5 threes",
            "lebron 30 point games with anthony davis with 5 threes",
        ),
    ],
)
def test_separated_adjective_rewrite(text, expected):
    assert canonicalize_sample_phrases(text) == expected


def test_separated_adjective_count():
    result = _run("how many 30 point games did LeBron have with 5+ threes")
    assert result.result.to_dict()["sections"]["count"][0]["count"] == 3


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record in games with 120 points vs good teams", (7, 1)),
        ("Lakers record in games with 120 points against losing teams", (11, 0)),
    ],
)
def test_stat_bound_with_opponent_quality(query, record):
    summary = _run(query).result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == record


@pytest.mark.parametrize(
    ("query", "top"),
    [
        # A bare count is a bound, not the whole season.
        ("which team has the best record with 15 threes", ("LAL", 18, 2)),
        # Teams with a handful of games in the sample are left out.
        ("best record when scoring 120+", ("LAL", 18, 1)),
    ],
)
def test_record_leaderboard_stat_sample(query, top):
    rows = _run(query).result.to_dict()["sections"]["leaderboard"]
    assert (rows[0]["team_abbr"], rows[0]["wins"], rows[0]["losses"]) == top
    if "120" in query:
        assert all(row["wins"] + row["losses"] >= 4 for row in rows)


@pytest.mark.parametrize(
    ("query", "record"),
    [
        # Glossary opponent-quality terms are read scope after a stat bound.
        # Every fixture team ranks in its conference top 10.
        ("Lakers record in games with 120 points vs playoff teams", (18, 1)),
        ("Lakers record in games with 120 points against teams that made the playoffs", (18, 1)),
        ("Lakers record in games with 120 points vs good teams at home", (5, 0)),
    ],
)
def test_stat_bound_with_glossary_opponents(query, record):
    summary = _run(query).result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"]) == record


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record vs non-playoff teams",
        "LeBron games vs non-playoff teams",
        "Lakers record in games with 120 points vs non-playoff teams",
        # Multi-season and streak routes take the season-token path.
        "Lakers record vs non-playoff teams since 2023",
        "LeBron longest 20 point streak vs non-playoff teams",
        "Lakers longest winning streak vs non-playoff teams",
    ],
)
def test_empty_opponent_quality_set_is_no_match(query):
    # No fixture team missed the playoffs: the answer is no games, never the
    # unfiltered record.
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "no_match"
