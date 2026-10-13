"""Shooting-rate wording and the opponent's rates and turnovers on records.

- "under 40% shooting", "at least 50% shooting" and "between 40 and 50
  percent" were dropped (or read as a 50-point floor) and answered with
  every game; "from the floor" and "beyond the arc" were dropped too.
- "at least 40% three point shooting" ranked the list by points.
- Records refused the opponent's shooting ("when opponents shoot 50%",
  "when the Celtics shoot 50%", "opponents shot between 40 and 50 percent").
- "when they force 15 turnovers" and "15 forced turnovers" read the team's
  own turnovers; "Lakers record with 15 opponent turnovers" refused as an
  unknown teammate, and "with 15 opponent turnovers" on a game list was
  dropped.

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
    return _execute(query)["finder"]


def _bounds(query: str) -> list[tuple]:
    from nbatools.commands.natural_query import parse_query

    kwargs = parse_query(query)["route_kwargs"]
    conditions = kwargs.get("conditions") or [kwargs]
    return [(c["stat"], c["min_value"], c["max_value"]) for c in conditions]


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record with at least 50% shooting", (45, 11)),
        ("Lakers record when they shoot between 40% and 50%", (2, 2)),
        ("Lakers record with between 30% and 40% three point shooting", (2, 4)),
    ],
)
def test_own_rate_records(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    ("query", "count"),
    [
        ("Lakers games shooting between 40 and 50 percent", 4),
        ("Lakers games shooting between 30 and 40 percent from three", 6),
        ("LeBron James games shooting between 40 and 50 percent", 9),
    ],
)
def test_own_rate_ranges(query, count):
    assert len(_rows(query)) == count


@pytest.mark.parametrize(
    ("query", "bound"),
    [
        ("Lakers games with under 40% shooting", ("fg_pct", None, 0.3999)),
        ("Lakers games with over 50% shooting", ("fg_pct", 0.5001, None)),
        ("LeBron James games with at least 50% shooting", ("fg_pct", 0.5, None)),
        ("Lakers games with at least 40% three point shooting", ("fg3_pct", 0.4, None)),
        ("Lakers games shooting 50% from the floor", ("fg_pct", 0.5, None)),
        ("Lakers games from the floor over 50%", ("fg_pct", 0.5001, None)),
        ("Lakers games shooting 40% beyond the arc", ("fg3_pct", 0.4, None)),
        ("Lakers record when opponents shoot 40% or less", ("opponent_fg_pct", None, 0.4)),
        (
            "Lakers record when opponents shoot under 40 percent",
            ("opponent_fg_pct", None, 0.3999),
        ),
    ],
)
def test_rate_bounds(query, bound):
    assert [pytest.approx(b) if isinstance(b, float) else b for b in bound] in [
        list(b) for b in _bounds(query)
    ]


def test_bound_word_rate_is_not_a_ranking():
    from nbatools.commands.natural_query import parse_query

    kwargs = parse_query("Lakers games with at least 40% three point shooting")["route_kwargs"]
    assert kwargs["stat"] == "fg3_pct"
    rows = _rows("Lakers games with at least 40% three point shooting")
    assert all(row["fg3m"] / row["fg3a"] >= 0.4 for row in rows)


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when opponents shoot 50%", (36, 13)),
        ("Lakers record when opponents shoot over 50%", (34, 12)),
        ("Lakers record when opponents shoot 50% or worse", (13, 1)),
        ("Lakers record when opponents shot between 40 and 50 percent", (13, 1)),
        ("Lakers record when opponents shoot 50 percent from three", (22, 8)),
        ("Lakers record when opponents shot under 40 percent from three", (16, 2)),
        ("Lakers record when opponents shoot over 50% and they score 110", (19, 2)),
        ("Lakers record when they shoot 50% and opponents shoot 50%", (35, 11)),
        # The named opponent's rate, in games against it.
        ("Lakers record when the Celtics shoot 50%", (3, 8)),
        ("Lakers record vs Celtics when the Celtics shoot 50%", (3, 8)),
        ("LAL record vs Celtics when the Celtics shoot 50%", (3, 8)),
        ("BOS record vs Lakers when the Lakers shoot 50%", (7, 4)),
        ("Lakers record when the Lakers shoot 50% and the Celtics shoot 40%", (4, 7)),
    ],
)
def test_opponent_rate_records(query, record):
    assert _record(query) == record


def test_opponent_rate_range_on_a_game_list():
    assert len(_rows("Lakers games when opponents shot between 40 and 50 percent")) == 14


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when they force 15 turnovers", (25, 4)),
        ("Lakers record when they force at least 15 turnovers", (25, 4)),
        ("Lakers record when they forced fewer than 10 turnovers", (6, 1)),
        ("Lakers record with 15 forced turnovers", (25, 4)),
        ("Lakers record with 15 opponent turnovers", (25, 4)),
        ("Lakers record with at least 15 opponent turnovers", (25, 4)),
    ],
)
def test_forced_turnover_records(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    "query",
    [
        "Lakers games forcing 15 turnovers",
        "Lakers games with 15 forced turnovers",
        "Lakers games with 15 opponent turnovers",
    ],
)
def test_forced_turnover_lists(query):
    assert _bounds(query) == [("opponent_tov", 15.0, None)]


@pytest.mark.parametrize(
    "query",
    [
        # A count joined onto the opponent's rate is not read yet.
        "Lakers games when opponents shoot 50% and make 15 threes",
        # "allow under 45% shooting" is the opponent's, in wording not read.
        "Lakers record when they allow under 45% shooting",
    ],
)
def test_unread_opponent_wording_refuses(query):
    from nbatools.query_service import execute_natural_query

    assert execute_natural_query(query).result_status == "no_result"


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record when they keep opponents under 55% shooting", (23, 2)),
        ("Lakers record when they hold opponents under 55% shooting", (23, 2)),
        ("Lakers record when they have at least 50% shooting", (45, 11)),
        # The joined clause is the team's own turnovers again.
        ("Lakers record when they force 15 turnovers and commit 15 turnovers", (13, 1)),
    ],
)
def test_clause_subjects_beside_rates_and_forced_turnovers(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    "query",
    [
        # Another side's rate read as the subject's own filtered the wrong team.
        "Lakers record against teams under 55% shooting",
        "Lakers record when they hold the Celtics under 55% shooting",
        "Lakers record when they allow between 40 and 50% shooting",
        "LeBron James games when the Lakers have at least 55% shooting",
        "LeBron James record when the team has at least 55% shooting",
        "LeBron James games when the Lakers have under 50% shooting",
        "LeBron James games when the Lakers have between 40 and 50% shooting",
        # Forcing by a player or another team is not the team's own forcing.
        "LeBron James games when he forced 3 turnovers",
        "Lakers record when LeBron forces 3 turnovers",
        "Celtics record when the Lakers force 15 turnovers",
        "Lakers record when the Celtics force 15 turnovers",
    ],
)
def test_other_sides_rates_and_forcing_refuse(query):
    from nbatools.query_service import execute_natural_query

    assert execute_natural_query(query).result_status == "no_result"


@pytest.mark.parametrize(
    ("query", "record"),
    [
        # "vs <team> on 50% shooting" is the subject's own rate in those games.
        ("Lakers record vs Celtics on 50% shooting", (4, 7)),
        ("Lakers record against the Celtics on 50% shooting", (4, 7)),
    ],
)
def test_own_rate_against_a_named_opponent(query, record):
    assert _record(query) == record


def test_player_rate_against_a_named_opponent():
    assert len(_rows("LeBron James games against Boston on 50% shooting")) == 11
