"""Follow-ups to team and opponent totals on a player's games.

"when his team scores 120", "the opposing team scored 120", "LA scores 120",
"the Lakers allow 120" and "commit 20 turnovers" were not read as team or
opponent totals. A team named after "vs <opponent>" was skipped, and a team
total next to a player event ("in which the Lakers scored 120 and he had 10
assists") refused. "highest scoring games with 10 assists" ranked by assists
or refused. Expected values are counted from the fixture.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _execute(query: str):
    from nbatools.query_service import execute_natural_query

    return execute_natural_query(query)


def _sections(query: str) -> dict:
    result = _execute(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]


def _games(query: str) -> int:
    sections = _sections(query)
    if sections.get("summary") and "games" in sections["summary"][0]:
        return sections["summary"][0]["games"]
    return len(sections["finder"])


@pytest.mark.parametrize(
    ("query", "games"),
    [
        ("LeBron James games when his team scores 120", 19),
        ("LeBron James games when his Lakers score 120", 19),
        ("LeBron James games when the opposing team scored 120", 7),
        ("LeBron James games when the Lakers allow 120", 7),
        ("LeBron James games when the Lakers commit 20 turnovers", 10),
        ("LeBron James games in which the Lakers scored 120 and he had 10 assists", 1),
    ],
)
def test_team_and_opponent_clauses(query, games):
    assert _games(query) == games


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record when they allow 120",
        "Lakers record when they allow 120 points",
        "Lakers record when they gave up 120",
    ],
)
def test_allowed_points_are_the_opponents(query):
    summary = _sections(query)["summary"][0]
    assert (summary["wins"], summary["losses"]) == (2, 5)


def test_la_is_only_an_la_team():
    # Tatum's team is not from LA, so "LA" is not his team's total.
    result = _execute("Jayson Tatum games when LA scores 120")
    assert result.result_status == "no_result"
    assert _games("Jayson Tatum games vs the Lakers when LA scores 120") == 4


def test_player_without_games_finds_none():
    # Kawhi is not in the fixture: no games, not an error.
    for query in (
        "Kawhi Leonard games when they score 120",
        "Kawhi Leonard games when opponents score 120",
    ):
        result = _execute(query)
        assert result.result_status == "no_result", query
        assert result.result_reason == "no_match", query


@pytest.mark.parametrize(
    ("query", "points"),
    [
        ("LeBron James lowest scoring games with 10 assists", [14, 19, 21, 29, 30]),
        ("LeBron James lowest scoring games", [11, 14, 14, 16, 17]),
        ("LeBron James highest scoring games with at least 10 assists", [32, 30, 29, 21, 19]),
    ],
)
def test_ranking_direction(query, points):
    rows = _sections(query)["finder"]
    assert [row["pts"] for row in rows][:5] == points


def test_team_named_beside_an_opponent():
    rows = _sections("LeBron James top 3 scoring games vs Boston when the Lakers score 120")[
        "finder"
    ]
    assert [row["pts"] for row in rows] == [35, 33, 27]


@pytest.mark.parametrize(
    "query",
    [
        "LeBron James highest scoring games with 10 assists",
        "LeBron James highest scoring games with at least 10 assists",
        "LeBron James most points in games with 10 assists",
    ],
)
def test_ranking_stat_beside_a_condition(query):
    rows = _sections(query)["finder"]
    assert all(row["ast"] >= 10 for row in rows)
    assert [row["pts"] for row in rows][:5] == [32, 30, 29, 21, 19]


def test_ranking_with_condition_and_team_total():
    rows = _sections(
        "LeBron James highest scoring games with 10 assists when the Lakers score 120"
    )["finder"]
    assert [row["pts"] for row in rows] == [29]
