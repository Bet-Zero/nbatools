"""C1: clause subjects after "vs", game-clock wording and other players' stats.

- "Lakers record vs Celtics when they shoot 50%" answered Boston's record:
  "when" was read as part of the opponent name.
- "with 5 minutes left" / "in the final 2 minutes" read as minutes played.
- "LeBron James games when Davis scores 30" read LeBron's own points.

Expected values are counted with pandas from the fixture.
"""

from __future__ import annotations

import pytest

from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


def _record(query: str) -> tuple[int, int, str]:
    result = execute_natural_query(query)
    assert result.result_status == "ok", (query, result.result_reason)
    summary = result.result.to_dict()["sections"]["summary"][0]
    return summary["wins"], summary["losses"], summary.get("team_abbr", "")


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record vs Celtics when they shoot 50%",
        "Lakers record vs Celtics when the Lakers shoot 50%",
    ],
)
def test_clause_after_vs_keeps_the_first_team(query):
    wins, losses, _ = _record(query)
    assert (wins, losses) == (4, 7)


def test_unsplit_record_is_unchanged():
    wins, losses, _ = _record("Lakers record when they shoot 50%")
    assert (wins, losses) == (45, 11)


@pytest.mark.parametrize(
    "query",
    [
        "Lakers record vs Celtics when the Celtics shoot 50%",
        "LeBron James stats with 5 minutes left",
        "Lakers record in the final 2 minutes",
        "LeBron James games when Anthony Davis scores 30",
        "LeBron James games when Davis scores 30",
        "LeBron James games when Davis has 10 rebounds",
    ],
)
def test_unread_clauses_refuse(query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"


@pytest.mark.parametrize(
    ("query", "count"),
    [
        ("LeBron James games when he scores 30", 11),
        ("LeBron James games when LeBron scores 30", 11),
        ("LeBron James games with 30 minutes", 20),
    ],
)
def test_own_clauses_still_answer(query, count):
    result = execute_natural_query(query)
    assert result.result_status == "ok"
    assert len(result.result.to_dict()["sections"]["finder"]) == count


def test_la_is_his_team_when_he_plays_for_one():
    # Same 19 games as "when the Lakers score 120"; it read his own points.
    query = "LeBron James games when LA scores 120"
    result = execute_natural_query(query)
    assert result.result_status == "ok"
    assert len(result.result.to_dict()["sections"]["finder"]) == 19


@pytest.mark.parametrize(
    ("query", "record"),
    [
        # "was" is also the Wizards' abbreviation: not the first team.
        ("What was the Lakers record when the Lakers shoot 50%", (45, 11)),
        ("What was the Lakers record vs Celtics when the Lakers shoot 50%", (4, 7)),
    ],
)
def test_question_words_are_not_teams(query, record):
    wins, losses, _ = _record(query)
    assert (wins, losses) == record


@pytest.mark.parametrize(
    "query",
    [
        "LeBron James games when Bronny James scores 10",
        "Anthony Davis games when Anthony Edwards scores 30",
    ],
)
def test_shared_name_other_player_refuses(query):
    assert execute_natural_query(query).result_status == "no_result"


@pytest.mark.parametrize("name", ["LeBron James", "King James", "James"])
def test_his_own_names_still_answer(name):
    result = execute_natural_query(f"LeBron James games when {name} scores 30")
    assert len(result.result.to_dict()["sections"]["finder"]) == 11


@pytest.mark.parametrize(
    "query",
    [
        # The opponent's rate beside an abbreviated subject is not read.
        "BOS record vs Lakers when the Lakers shoot 50%",
        "LAL record vs Celtics when the Celtics shoot 50%",
    ],
)
def test_abbreviated_subject_keeps_opponent_clause_refused(query):
    result = execute_natural_query(query)
    assert result.result_status == "no_result"
    assert result.result_reason == "filter_not_supported"


def test_abbreviated_subjects_answer_their_own_clause():
    assert _record("LAL record vs BOS when the Lakers shoot 50%")[:2] == (4, 7)
    assert _record("BOS record vs Lakers when they shoot 50%")[:2] == (8, 3)


@pytest.mark.parametrize(
    "query",
    [
        "LeBron James games vs Celtics when the Celtics score 120",
        "LeBron James record vs Celtics when the Celtics score 120",
        "LeBron James games vs Boston when Boston scores 120",
        "LeBron James games vs Celtics when Boston scores 120",
    ],
)
def test_player_vs_team_when_that_team_scores(query):
    # The clause's team is his opponent, not his team.
    wins, losses, _ = _record(query)
    assert (wins, losses) == (1, 3)
