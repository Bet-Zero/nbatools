"""True/effective shooting wording, route-read ceilings and described opponents.

- "60% true shooting", "65% ts" and "55% efg" were dropped or ranked the list
  by the rate; a team record with "true shooting" became a team-leader board
  (any "%" counted as a ranking word).
- "with 10 or fewer opponent turnovers" refused although the bound was read.
- "vs teams that shoot 50%" and "vs teams that score 120" read the team's
  own stat; they now read the opponent's line in those games.
- "vs teams that won 50 games" counted wins, "vs teams that allow 120" read
  the opponent's points, and "vs poor shooting teams" and "when the score is
  tied" were dropped; they now refuse.
- "vs teams that have a winning record" was dropped.
- "LeBron James best 5 game stretch vs Celtics and Knicks" read the Knicks as
  his team.

Expected values are counted with pandas from the fixture (2025-26).
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def _execute(query: str):
    from nbatools.query_service import execute_natural_query

    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason, result.metadata)
    return result.result.to_dict()["sections"]


def _record(query: str) -> tuple[int, int, int]:
    summary = _execute(query)["summary"][0]
    return summary["games"], summary["wins"], summary["losses"]


@pytest.mark.parametrize(
    ("query", "record"),
    [
        ("Lakers record with 60% true shooting", (46, 39, 7)),
        ("Lakers record with at least 60% true shooting", (46, 39, 7)),
        ("Lakers record with between 55% and 65% true shooting", (33, 22, 11)),
        ("Lakers record with 55% efg", (56, 45, 11)),
        ("Lakers record with 10 or fewer opponent turnovers", (11, 9, 2)),
        ("Lakers record when opponents commit 10 or fewer turnovers", (11, 9, 2)),
        ("Lakers record vs teams that have a winning record", (24, 11, 13)),
        ("Lakers record vs teams that had losing records", (36, 36, 0)),
        # The opponent's line in those games, like "when opponents score 120".
        ("Lakers record vs teams that score 120 points", (7, 2, 5)),
        ("Lakers record vs teams that shoot 50%", (49, 36, 13)),
        ("Lakers record against opponents who made 15 threes", (24, 17, 7)),
    ],
)
def test_records(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    ("query", "bound"),
    [
        ("LeBron James games with 60% true shooting", ("ts_pct", 0.6, None)),
        ("LeBron James games with 65% ts", ("ts_pct", 0.65, None)),
        ("Lakers games with 60% true shooting", ("ts_pct", 0.6, None)),
        (
            "Lakers record with under 50% effective field goal shooting",
            ("efg_pct", None, 0.4999),
        ),
    ],
)
def test_rate_word_bounds(query, bound):
    from nbatools.commands.natural_query import parse_query

    kwargs = parse_query(query)["route_kwargs"]
    stat, low, high = bound
    assert kwargs["stat"] == stat
    assert (kwargs["min_value"], kwargs["max_value"]) == (
        pytest.approx(low) if low is not None else None,
        pytest.approx(high) if high is not None else None,
    )


def test_game_list_reads_the_opponent_ceiling():
    rows = _execute("Lakers games with 10 or fewer opponent turnovers")["finder"]
    assert len(rows) == 11


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record vs teams that allow 120 points",
        "Lakers record against teams that won 50 games",
        "Lakers record vs poor shooting teams",
        "Lakers record vs good defensive teams",
        "Lakers record vs high scoring teams",
        "Lakers record when the score is tied",
    ],
)
def test_unread_descriptions_refuse(query):
    from nbatools.query_service import execute_natural_query

    assert execute_natural_query(query).result_status == "no_result"


@pytest.mark.parametrize(
    ("query", "record"),
    [
        # Described by the standings, which are read.
        ("Lakers record vs teams that are over .500", (24, 11, 13)),
        ("Lakers record vs teams with a winning record", (24, 11, 13)),
    ],
)
def test_standings_descriptions_still_answer(query, record):
    assert _record(query) == record


@pytest.mark.parametrize(
    ("query", "value"),
    [
        # Game score over his best 5 straight games against the listed teams.
        ("LeBron James best 5 game stretch vs Celtics and Knicks", 27.74),
        ("LeBron James best 5 game stretch vs Celtics", 25.5),
    ],
)
def test_player_stretch_vs_a_list(query, value):
    row = _execute(query)["leaderboard"][0]
    assert row["player_name"] == "LeBron James"
    assert row["stretch_value"] == pytest.approx(value)


def test_ranked_games_against_teams_that_scored():
    # Read as the opponent's points (it used to refuse); his 30-point games
    # against a 120-point opponent, ranked by rebounds.
    rows = _execute(
        "LeBron James most rebounds in a game with 30 points against teams that scored 120 points"
    )["finder"]
    assert [row["reb"] for row in rows] == [9, 5]
