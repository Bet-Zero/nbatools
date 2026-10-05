"""Final-margin filters: "won by 10+", "lost by 20 or more", "decided by 3 or fewer".

"Lakers games won by 10+ points" used to read as games where the Lakers scored
10 or more, and "decided by 3 or fewer" refused. The margin is the team's final
plus-minus; "won by" reads the winning margin, "lost by" the losing margin and
"decided by" / "within" either. Player rows use their team's margin, never their
own on-court plus-minus. Expected values are counted from the fixture.
"""

from __future__ import annotations

import pytest

from nbatools.commands._parse_helpers import (
    canonicalize_margin_phrases,
    extract_team_streak_request,
)

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def _summary(result) -> tuple[int, int, int]:
    row = result.result.to_dict()["sections"]["summary"][0]
    return row["games"], row["wins"], row["losses"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("lakers games won by 10+ points", "lakers games won at 10+ win margin"),
        ("lakers wins by 10 or more", "lakers wins at 10+ win margin"),
        ("lakers losses by at least 20 points", "lakers losses at 20+ loss margin"),
        ("lakers won by more than 15", "lakers won at 16+ win margin"),
        ("games decided by 3 points or less", "games at 3 or fewer game margin"),
        ("lakers lost by single digits", "lakers lost at 9 or fewer loss margin"),
        ("lakers won by 1", "lakers won at between 1 and 1 win margin"),
        ("lakers games within 5 points", "lakers games at 5 or fewer game margin"),
        ("lakers double-digit losses", "lakers losses at 10+ loss margin"),
        ("longest winning streak by 10+", "longest winning streak at 10+ win margin"),
        # Not margins: another stat, a percentage, a series, a team's own score.
        ("lakers won by 10 rebounds", "lakers won by 10 rebounds"),
        ("lakers record when winning by 30%", "lakers record when winning by 30%"),
        ("celtics won the series by 4 games", "celtics won the series by 4 games"),
        ("lakers streak of 120 point wins", "lakers streak of 120 point wins"),
        ("did the lakers win 5 straight", "did the lakers win 5 straight"),
        ("lebron 30 point wins", "lebron 30 point wins"),
        ("road team won by 20", "road team won by 20"),
    ],
)
def test_canonical_margin_phrases(text, expected):
    assert canonicalize_margin_phrases(text) == expected


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Lakers record in games won by 10 or more", (37, 37, 0)),
        ("Lakers record when winning by double digits", (37, 37, 0)),
        ("Lakers record when losing by 20+", (5, 0, 5)),
        ("Lakers record in games decided by 3 points or less", (4, 2, 2)),
        ("Lakers record in games within 5 points", (7, 4, 3)),
        ("Lakers record in games decided by 1", (2, 2, 0)),
        ("Lakers record in games won by 1", (2, 2, 0)),
        ("Lakers record in games lost by 2", (2, 0, 2)),
        ("Lakers record in games won by 5 or fewer", (4, 4, 0)),
        ("Lakers record in games lost by single digits", (5, 0, 5)),
        ("Lakers record in games won by 10+ while scoring 120+", (15, 15, 0)),
        # These used to refuse as unparsed upper bounds.
        ("Celtics record in games decided by 5 or less", (12, 7, 5)),
        ("Celtics record in games decided by 5 points or fewer", (12, 7, 5)),
        ("Celtics record when they win by 10 or fewer", (16, 16, 0)),
    ],
)
def test_team_record_margin(query, expected):
    result = _run(query)
    assert result.route == "team_record"
    assert _summary(result) == expected


@pytest.mark.parametrize(
    ("query", "count"),
    [
        ("Lakers games won by 10+ points", 37),
        ("Lakers losses by 20 or more points", 5),
        ("Lakers won by more than 15", 35),
        ("Lakers double-digit losses", 8),
    ],
)
def test_team_finder_margin(query, count):
    result = _run(query)
    assert result.route == "game_finder"
    rows = result.result.to_dict()["sections"]["finder"]
    assert len(rows) == min(count, 25)
    assert all(abs(row["plus_minus"]) >= 10 for row in rows)


def test_player_rows_use_the_team_margin():
    result = _run("LeBron summary in games won by 10+")
    assert result.route == "player_game_summary"
    assert _summary(result) == (37, 37, 0)
    rows = _run("LeBron 25+ point games in losses by 10 or more").result.to_dict()["sections"][
        "finder"
    ]
    assert len(rows) == 3


@pytest.mark.parametrize(
    ("query", "condition", "length"),
    [
        ("Lakers longest winning streak by 10+ points", ("win_margin", 10.0, None), 7),
        ("Lakers longest streak of wins by 20+", ("win_margin", 20.0, None), 5),
        # Own bounds on an outcome streak hold in every game of it.
        ("Lakers longest winning streak with 15+ threes", ("fg3m", 15.0, None), 3),
        ("Lakers longest streak of 120 point wins", ("pts", 120.0, None), 5),
    ],
)
def test_outcome_streak_bounds(query, condition, length):
    from nbatools.commands._parse_helpers import canonicalize_sample_phrases

    request = extract_team_streak_request(canonicalize_sample_phrases(query.lower()))
    assert request["special_condition"] == "wins"
    assert [(c["stat"], c["min_value"], c["max_value"]) for c in request["conditions"]] == [
        condition
    ]
    row = _run(query).result.to_dict()["sections"]["streak"][0]
    assert row["streak_length"] == length
