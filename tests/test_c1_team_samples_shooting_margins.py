"""Team samples: own stats beside an opponent bound, close games, shooting.

- "Lakers record when they make 15 threes and allow under 110" kept only
  the opponent's points (44-4).
- "close games" and "blowouts" were ignored and answered with every game.
- "when they shoot 50 percent", "shooting 50% or better" and "at most 40%"
  were ignored, and "shooting over 50% with 30 points" dropped the points.

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


def _rows(query: str) -> list[dict]:
    sections = _execute(query)
    return sections.get("finder") or sections.get("game_log") or []


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when they make 15 threes and allow under 110", (16, 1)),
        ("Lakers record when they make 15 threes and allow 110 or fewer", (16, 1)),
        ("Lakers record when they allow under 110 and make 15 threes", (16, 1)),
        ("Lakers record when they allow under 110 and score 120", (15, 0)),
        ("Lakers record when opponents score under 110 and the Lakers make 15 threes", (16, 1)),
    ],
)
def test_own_stat_beside_opponent_bound(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    ("query", "record"),
    [
        # Close: final margin of 5 or fewer. Blowout: 15 or more.
        ("Lakers record in close games", (4, 3)),
        ("LeBron James record in close games", (4, 3)),
        ("Lakers record in blowouts", (35, 7)),
        ("Lakers record in blowout wins", (35, 0)),
        ("Celtics record in close games vs the Lakers", (3, 1)),
    ],
)
def test_close_games_and_blowouts(query, record):
    assert _record(query) == record


def test_close_and_blowout_game_lists():
    assert len(_rows("Lakers close losses")) == 3
    assert len(_rows("Lakers blowout losses")) == 7


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when they shoot 50 percent", (45, 11)),
        ("Lakers record when shooting 50% or better", (45, 11)),
        ("Lakers record when shooting at most 40%", (0, 0)),
        ("Lakers record when they shoot 40% from three", (39, 10)),
        ("Lakers record when shooting at least 50% and making 15 threes", (17, 2)),
        ("Lakers record when shooting 50% with 15 threes", (17, 2)),
        ("Lakers record when they shoot 50% and score 120 points", (18, 1)),
    ],
)
def test_team_shooting_percent_wording(query, record):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    if record == (0, 0):
        assert result.result_status == "no_result"
        assert result.result_reason == "no_match"
        return
    assert _record(query) == record


@pytest.mark.parametrize(
    ("query", "count"),
    [
        ("LeBron James games shooting 50% with 30 points", 11),
        ("LeBron James games with 30 points shooting 50%", 11),
        ("LeBron James games shooting over 50% with 30 points", 11),
        ("LeBron James games with 30 points shooting over 50%", 11),
        ("LeBron James games shooting 50% and scoring 30 points", 11),
    ],
)
def test_player_shooting_with_points(query, count):
    rows = _rows(query)
    assert len(rows) == count
    assert all(row["pts"] >= 30 for row in rows)


def test_shot_count_is_not_a_percentage():
    rows = _rows("LeBron James games where he shot 60 percent")
    assert rows and all(row["fgm"] / row["fga"] >= 0.6 for row in rows)
    assert len(_rows("LeBron James games shooting at most 40%")) == 1
    # "or less" after a shooting rate is read now (it used to refuse).
    assert len(_rows("LeBron games shooting 40% or less")) == 1


@pytest.mark.parametrize(
    ("query", "record"),
    [
        # The clause after "and" keeps the opponent as its subject.
        ("Lakers record when opponents score 110 and make 15 threes", (1, 4)),
        ("Lakers record when opponents score under 110 and have 30 assists", (0, 1)),
        ("Lakers record when the Celtics score 110 and make 15 threes", (1, 2)),
    ],
)
def test_opponent_clause_stays_the_opponents(query, record):
    assert _record(query) == record


def _count(query: str) -> int:
    return _execute(f"how many {query}")["count"][0]["count"]


@pytest.mark.parametrize(
    ("query", "count"),
    [
        # The rate the wording names, not field goal percentage.
        ("LeBron James games shooting 80% from the line", 13),
        ("LeBron James games shooting 90% on free throws", 11),
        ("LeBron James games with free throw shooting 90% or better", 11),
        ("LeBron James games with true shooting 60% or better", 48),
        ("LeBron James games with effective shooting 55%", 52),
    ],
)
def test_shooting_percent_reads_the_named_rate(query, count):
    assert _count(query) == count


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record when they shoot 40% on threes",
        "Lakers record when they shoot 40% from deep",
        "Lakers record when they shoot 40% from beyond the arc",
        "Lakers record with 3-point shooting 40%",
    ],
)
def test_three_point_shooting_wording(query):
    assert _record(query) == (39, 10)


@pytest.mark.parametrize(
    ("query", "result"),
    [
        # The margin stays beside the shooting bound and the event.
        ("LeBron James games shooting 50% with 30 points in close games", 2),
        ("Lakers record when they shoot 50% in blowouts with 15 threes", (12, 2)),
    ],
)
def test_shooting_and_event_inside_a_margin(query, result):
    if isinstance(result, tuple):
        assert _record(query) == result
    else:
        assert len(_rows(query)) == result


@pytest.mark.parametrize(
    "query",
    [
        # A count joined onto the opponent's rate is not read yet; it must
        # not filter the team's own counts.
        "Lakers record when opponents shoot 50% and make 15 threes",
        "Lakers games when the opponent shoots 50% with 15 threes",
    ],
)
def test_opponent_bare_shooting_refuses(query):
    from nbatools.query_service import execute_natural_query

    assert execute_natural_query(query).result_status == "no_result"


def test_the_team_is_the_subject_not_the_opponent():
    assert _record("Lakers record when the team allows 110 and makes 15 threes") == (2, 1)
