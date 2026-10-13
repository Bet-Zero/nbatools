"""Shooting written as "N% shooting", rest minutes, two-player subjects.

- "LeBron 50% shooting games", "games on 50% shooting" and "30 point games
  shooting 50%" ignored or refused the rate.
- "with 5 minutes rest" was read as 5+ minutes played.
- "when the Lakers' opponents score 110" checked the Lakers' own points.
- "Lakers vs Celtics when the Celtics score 110" bounded both teams' points.
- "LeBron and Luka games with 30 points" answered with LeBron alone.
- "LeBron stats in close games" listed the games instead of the summary.

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


def _conditions(query: str) -> set[tuple]:
    from nbatools.commands.natural_query import parse_query

    kwargs = parse_query(query)["route_kwargs"]
    found = {(c["stat"], c["min_value"], c["max_value"]) for c in kwargs.get("conditions") or []}
    if kwargs.get("stat"):
        found.add((kwargs["stat"], kwargs.get("min_value"), kwargs.get("max_value")))
    return found


@pytest.mark.parametrize(
    "query",
    ["LeBron James 50% shooting games", "LeBron James games on 50% shooting"],
)
def test_percent_shooting_is_a_floor(query):
    assert ("fg_pct", 0.5, None) in _conditions(query)
    assert all(row["fg_pct"] >= 0.5 for row in _execute(query)["finder"])


@pytest.mark.parametrize(
    ("query", "count"),
    [
        ("LeBron James 30 point games shooting 50%", 11),
        ("LeBron James 30 point games on 50% shooting", 11),
        ("LeBron James 30 point games shooting over 60%", 8),
    ],
)
def test_adjective_games_with_a_rate(query, count):
    rows = _execute(query)["finder"]
    assert len(rows) == count
    assert all(row["pts"] >= 30 for row in rows)


@pytest.mark.parametrize(
    ("query", "stat", "value"),
    [
        # The area or kind after (or before) "shooting" names the rate.
        ("LeBron James games on 50% shooting from three", "fg3_pct", 0.5),
        ("LeBron James games on 40% three point shooting", "fg3_pct", 0.4),
        ("LeBron James games on 80% free throw shooting", "ft_pct", 0.8),
        ("LeBron James games on 80% shooting from the line", "ft_pct", 0.8),
    ],
)
def test_percent_shooting_names_its_rate(query, stat, value):
    assert (stat, value, None) in _conditions(query)
    assert ("fg_pct", value, None) not in _conditions(query)


def test_rate_after_a_bound_word_is_not_a_floor():
    # Read by the opponent and "held to" readers, not as the team's floor.
    assert ("fg_pct", 0.4, None) not in _conditions(
        "Lakers games when they held opponents to 40% shooting"
    )


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when the Lakers' opponents score 110", (3, 9)),
        ("LeBron James stats in close games", (4, 3)),
        ("LeBron James stats in blowouts", (35, 7)),
        ("LeBron James stats in games with 30 points", (10, 1)),
        ("Lakers stats in close games", (4, 3)),
    ],
)
def test_records(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    "query",
    [
        "LeBron James games with 5 minutes rest",
        "Lakers record with 5 minutes rest",
        "Lakers vs Celtics when the Celtics score 110",
        "Lakers vs Celtics when the Knicks score 110",
        "LeBron and Luka games with 30 points",
        "LeBron James and Luka Doncic 30 point games",
        "LeBron and Luka record",
        # A team's or the opponent's rate, not read here.
        "LeBron James games when the Lakers have 50% shooting",
        "Lakers record when they allow 45% shooting",
        "Lakers games when they allow 45% shooting",
    ],
)
def test_refuses(query):
    from nbatools.query_service import execute_natural_query

    assert execute_natural_query(query).result_status == "no_result"


def test_compare_with_their_own_clause_still_answers():
    from nbatools.commands.natural_query import parse_query
    from nbatools.query_service import execute_natural_query

    query = "compare the Lakers and Celtics when they score 120"
    assert parse_query(query)["route"] == "team_compare"
    assert execute_natural_query(query).result_status == "ok"
