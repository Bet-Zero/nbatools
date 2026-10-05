"""Points-allowed floors, made-threes thresholds, and repeat-game player counts.

"Lakers record when they allow 110 or more points" filters the opponent's
score (it filtered the Lakers' own), "5 made threes" is a 5+ threes threshold
(it was ignored), and "how many players scored 30 in at least 5 games" counts
players with five such games (it counted players with one). Expected values
are counted from the fixture.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _run(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result


def _count(result) -> int:
    return result.result.to_dict()["sections"]["count"][0]["count"]


@pytest.mark.parametrize(
    ("query", "games", "wins", "losses"),
    [
        ("Lakers record when they allow 110 or more points", 12, 3, 9),
        ("Lakers record when giving up 120 or more", 7, 2, 5),
        ("Lakers record when opponents score at least 120 points", 7, 2, 5),
        ("Lakers record when allowing over 119 points", 7, 2, 5),
        # The team's own points are unchanged.
        ("Lakers record when scoring 120 or more", 19, 18, 1),
    ],
)
def test_points_allowed_floors(query, games, wins, losses):
    result = _run(query)
    assert result.route == "team_record"
    row = result.result.to_dict()["sections"]["summary"][0]
    assert (row["games"], row["wins"], row["losses"]) == (games, wins, losses)


def test_points_allowed_floor_count():
    assert _count(_run("how many games did the Lakers give up 120+ points")) == 7


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("how many games did LeBron have 5 made threes", 14),
        ("how many games did LeBron have 3+ made threes", 22),
        ("how many games did LeBron have 30 points and 5 made threes", 3),
    ],
)
def test_made_threes_thresholds(query, expected):
    assert _count(_run(query)) == expected


@pytest.mark.parametrize(
    ("query", "expected", "phrase"),
    [
        (
            "how many players scored 10 points or fewer in at least 20 games",
            16,
            "16 players have had 20+ games with at most 10 points",
        ),
        (
            "how many players scored 30+ in at least 5 games",
            9,
            "9 players have had 5+ games with 30+ points",
        ),
        (
            "how many players had 30 points and 10 rebounds in at least 2 games",
            7,
            "7 players have had 2+ games with 30+ points and 10+ rebounds",
        ),
        (
            "how many players had a triple double at least 3 times",
            6,
            "6 players have had 3+ triple-doubles",
        ),
        (
            "how many players have had a 40 point game",
            2,
            "2 players have had a game with 40+ points",
        ),
    ],
)
def test_repeat_game_player_counts(query, expected, phrase):
    result = _run(query)
    assert _count(result) == expected
    assert result.metadata["count_phrase"].startswith(phrase)


@pytest.mark.parametrize(
    ("query", "phrase"),
    [
        (
            "how many games did the Lakers give up 120+ points",
            "The Los Angeles Lakers have allowed 120+ points 7 times",
        ),
        (
            "how many games did the Lakers allow over 119 points",
            "The Los Angeles Lakers have allowed more than 119 points 7 times",
        ),
        (
            "how many games did the Lakers allow 100 or fewer points",
            "The Los Angeles Lakers have held opponents to 100 or fewer points 43 times",
        ),
        (
            "how many games did the Lakers hold opponents under 100",
            "The Los Angeles Lakers have held opponents under 100 points 42 times",
        ),
    ],
)
def test_points_allowed_headlines(query, phrase):
    assert _run(query).metadata["count_phrase"].startswith(phrase)


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record when they allow 15 or more threes",
        "Lakers record when they allow 45 or more rebounds",
        "Lakers record when giving up 15+ threes",
        "Lakers record when allowing 10 or fewer turnovers",
    ],
)
def test_other_stats_after_allow_are_not_points_allowed(query):
    from nbatools.commands.natural_query import parse_query

    kwargs = parse_query(query)["route_kwargs"]
    stats = {kwargs.get("stat")} | {c.get("stat") for c in kwargs.get("conditions") or []}
    assert "opponent_pts" not in stats


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("how many players scored 30 points at least 10 times", 8),
        ("how many players scored 30 points at least 5 times", 9),
        ("how many players had 10 rebounds at least 20 times", 6),
    ],
)
def test_at_least_n_times_after_a_stat(query, expected):
    assert _count(_run(query)) == expected
