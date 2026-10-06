"""Team and opponent totals on a player's games.

"LeBron games when the Lakers score 120" checked 120 against LeBron's own
points, so nothing matched. "when opponents score 120" did the same on every
route, and an opponent bound on a player route refused. The team's and the
opponent's box score now come from the team rows of the player's games.
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
        ("LeBron James games when the Lakers score 120", (18, 1, 19)),
        ("LeBron James games with 30 points when the Lakers score 120", (5, 0, 5)),
        ("LeBron James 30 point games when the Lakers score 120 or more", (5, 0, 5)),
        ("Lakers record when LeBron James scores 30 points and they score 120", (5, 0, 5)),
        (
            "Lakers record when LeBron James plays and scores 30 points and the Lakers score 120",
            (5, 0, 5),
        ),
        (
            "Lakers record when LeBron James plays and has 10 assists and the team has 30 assists",
            (2, 0, 2),
        ),
        ("Lakers record when LeBron James scores 30 points and the team has 30 assists", (1, 0, 1)),
        ("LeBron James games with 5 threes when the Lakers make 15 threes", (8, 1, 9)),
        ("LeBron James games when the Lakers score 120 and opponents score under 110", (15, 0, 15)),
        (
            "Lakers record when LeBron James scores 30 points and opponents score at least 120",
            (1, 1, 2),
        ),
    ],
)
def test_team_and_opponent_totals_on_player_games(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    ("query", "count"),
    [
        ("LeBron James games when opponents score 120", 7),
        ("LeBron James 30 point games when the opponent scored 120", 2),
        ("LeBron James games with 30 points when opponents score 120", 2),
        ("LeBron James games with 20 points when opponents make 15 threes", 19),
        ("LeBron James games with 30 points and the Lakers score under 110", 3),
    ],
)
def test_player_game_list_with_context_bound(query, count):
    assert len(_rows(query)) == count


def test_own_bound_is_kept_beside_a_team_bound():
    result = _execute(
        "LeBron James games with 30 points and 10 assists when opponents make 15 threes"
    )
    assert result.result_status == "no_result"
    assert result.result_reason == "no_match"


@pytest.mark.parametrize(
    ("query", "record"),
    [
        # The opponent's score, not the team's own points.
        ("Lakers record when opponents score 120", (2, 5, 7)),
        ("Lakers record when the other team scored 120 points", (2, 5, 7)),
        ("Lakers record when opponents score below 100", (40, 2, 42)),
        ("Lakers record when opponents make 15 threes", (17, 7, 24)),
        ("Lakers record when opponents score 15 threes", (17, 7, 24)),
    ],
)
def test_opponent_scoring_on_team_records(query, record):
    summary = _execute(query).result.to_dict()["sections"]["summary"][0]
    assert (summary["wins"], summary["losses"], summary["games"]) == record


def test_plain_player_bounds_unchanged():
    assert _record("Lakers record when LeBron James scores 30 points") == (10, 1, 11)
    assert len(_rows("LeBron James games with 30 points and 10 assists")) == 2


@pytest.mark.parametrize(
    ("query", "count"),
    [
        # A team after "vs" / "for" / "with" is a filter; "scoring" is the player's.
        ("LeBron James games vs Boston scoring 30 points", 3),
        ("LeBron James vs Boston scores 30 points", 3),
        ("LeBron James games for the Lakers scoring 30 points", 11),
        ("LeBron James games with the Lakers scoring 30", 11),
        # "the other team" is only the opponent.
        ("LeBron James games when the other team scored 120 points", 7),
        ("how many games did LeBron James play when the Lakers scored 110 or fewer", 32),
    ],
)
def test_team_word_that_is_not_a_clause_subject(query, count):
    assert len(_rows(query)) == count


def test_ranking_keeps_the_players_stat():
    rows = _rows("LeBron James highest scoring games when the Lakers score 120")
    points = [row["pts"] for row in rows]
    assert points == sorted(points, reverse=True)
    assert points[:3] == [36, 35, 33]
