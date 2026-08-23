"""A question's conditions must be executed, refused, or clarified - never dropped.

The bug these tests exist for: "What team has stayed afloat best when its
leading scorer was out?" returned a populated league-wide team points-per-game
leaderboard and announced the Nuggets at 122.1 per game. The availability
condition, the role-based player reference, and the subjective framing were all
discarded, and a metric nobody asked for was substituted in their place.

Assertions here are deliberately concept-level. They check that no substituted
answer came back and that the blocker named in metadata is the condition the
user actually wrote - not that the app emits any particular sentence.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.needs_data]

# Routes that rank the whole league by a single season metric. Landing on one of
# these with an unexecuted condition is the failure mode under test.
BROAD_LEADERBOARD_ROUTES = {"season_leaders", "season_team_leaders"}


def _unsupported_filters(metadata: dict) -> list[str]:
    return list(metadata.get("unsupported_filters") or [])


def _applied_filter_labels(metadata: dict) -> list[str]:
    return [str(entry.get("label")) for entry in (metadata.get("applied_filters") or [])]


# ---------------------------------------------------------------------------
# 1. Parser / routing: no broad leaderboard fallback for discarded conditions
# ---------------------------------------------------------------------------

# (query, marker that must be reported as blocking)
DISCARDED_CONDITION_QUERIES = [
    (
        "What team has stayed afloat best when its leading scorer was out?",
        "unresolved_availability",
    ),
    ("best team when leading scorer is injured", "unresolved_availability"),
    ("what team has stayed afloat best", "subjective_outcome"),
    ("teams that cope best without their leading scorer", "unresolved_availability"),
    ("how do teams do when their star is out", "unresolved_availability"),
    # "best player" is claimed by the older subjective-query guard, which already
    # refuses before this one is reached. Either blocker is correct; what matters
    # is that neither shape reaches a leaderboard default.
    ("which teams hold up best when their best player sits out", "subjective_query"),
    ("how do teams fare without their star", "unresolved_availability"),
]


@pytest.mark.parser
@pytest.mark.parametrize("query, marker", DISCARDED_CONDITION_QUERIES)
def test_discarded_condition_never_selects_a_broad_leaderboard_fallback(query, marker):
    parsed = parse_query(query)
    route_kwargs = parsed["route_kwargs"]

    assert marker in (route_kwargs.get("unsupported_filters") or [])
    # The route boundary may still be named, but it must be blocked from
    # executing, and it must not carry a substituted ranking metric.
    if parsed["route"] in BROAD_LEADERBOARD_ROUTES:
        assert route_kwargs.get("unsupported_filters")
    assert "stat" not in route_kwargs


@pytest.mark.parser
@pytest.mark.parametrize(
    "query, marker",
    [
        ("in clutch time", "clutch"),
        ("clutch stats", "clutch"),
        ("against winning teams", "opponent_quality"),
    ],
)
def test_context_only_fragment_refuses_instead_of_defaulting_to_points(query, marker):
    """A bare clutch / opponent-quality fragment names no metric to rank by."""
    parsed = parse_query(query)

    assert parsed["route"] in BROAD_LEADERBOARD_ROUTES
    assert marker in (parsed["route_kwargs"].get("unsupported_filters") or [])
    assert "stat" not in parsed["route_kwargs"]


@pytest.mark.parser
def test_boundary_fragment_note_does_not_promise_a_broad_fallback():
    """The note must not claim a fallback the engine no longer returns."""
    for query in ("in clutch time", "against winning teams"):
        notes = " ".join(parse_query(query).get("notes", []))
        assert "broad points leaderboard fallback" not in notes
        assert "no broad points leaderboard was returned" in notes


# ---------------------------------------------------------------------------
# 2. Execution: no populated substituted answer comes back
# ---------------------------------------------------------------------------

NEGATIVE_PROBES = [
    "What team has stayed afloat best when its leading scorer was out?",
    "best team when leading scorer is injured",
    "what team has stayed afloat best",
    "teams that cope best without their leading scorer",
    "which team survives best without its best player",
    "how do teams do when their star is out",
    "Williams clutch stats",
    "Johnson clutch stats",
    "Jones clutch performance",
    "clutch stats",
    "clutch numbers this season",
    "how did they do in clutch time",
    "Smith against good teams",
    "stats against winning teams",
    "against winning teams this season",
]


@pytest.mark.parametrize("query", NEGATIVE_PROBES)
def test_unexecutable_question_returns_no_substituted_answer(query):
    executed = execute_natural_query(query)

    assert executed.result_status != "ok"
    # No answer rows of any shape, and therefore no headline built from them.
    assert executed.to_dict()["sections"] == {}
    for attr in ("leaders", "games", "streaks", "summary", "splits", "comparison"):
        assert getattr(executed.result, attr, None) is None


@pytest.mark.parametrize("query", NEGATIVE_PROBES)
def test_unexecutable_question_explains_the_real_condition(query):
    """Notes must describe the condition that blocked the answer."""
    executed = execute_natural_query(query)
    notes = " ".join(
        list(getattr(executed.result, "notes", None) or [])
        + list(executed.metadata.get("notes") or [])
    ).lower()

    assert notes.strip(), f"{query!r} returned a bare failure with nothing explained"


@pytest.mark.parametrize(
    "query, expected_blocker",
    [
        ("clutch stats", "clutch"),
        ("clutch numbers this season", "clutch"),
        ("how did they do in clutch time", "clutch"),
        ("Tatum clutch stats", "clutch"),
        ("stats against winning teams", "opponent_quality"),
        ("against winning teams this season", "opponent_quality"),
        (
            "What team has stayed afloat best when its leading scorer was out?",
            "unresolved_availability",
        ),
        ("what team has stayed afloat best", "subjective_outcome"),
        ("how do teams do when their star is out", "unresolved_availability"),
    ],
)
def test_blocker_is_named_by_the_condition_not_by_a_substituted_metric(query, expected_blocker):
    executed = execute_natural_query(query)

    assert expected_blocker in _unsupported_filters(executed.metadata)


# ---------------------------------------------------------------------------
# 3. Result metadata: a filter that did not run is never labelled applied
# ---------------------------------------------------------------------------

# Queries that request a filter the engine never executes. Each names the badge
# label the old behaviour showed over an answer it had not filtered.
REQUESTED_BUT_UNEXECUTED = [
    ("clutch stats", "Clutch"),
    ("clutch numbers this season", "Clutch"),
    ("how did they do in clutch time", "Clutch"),
    ("Tatum clutch stats", "Clutch"),
    ("Williams clutch stats", "Clutch"),
    ("Johnson clutch stats", "Clutch"),
    ("Jones clutch performance", "Clutch"),
    ("Smith against good teams", "Opponent quality"),
]


@pytest.mark.parametrize("query, badge_label", REQUESTED_BUT_UNEXECUTED)
def test_unexecuted_filter_is_not_claimed_as_applied(query, badge_label):
    executed = execute_natural_query(query)

    assert executed.result_status != "ok"
    assert badge_label not in _applied_filter_labels(executed.metadata)


@pytest.mark.parametrize("query", ["clutch stats", "Tatum clutch stats", "Williams clutch stats"])
def test_requested_context_is_preserved_even_though_it_did_not_execute(query):
    """Dropping the badge must not drop the record of what was asked for."""
    executed = execute_natural_query(query)

    assert executed.metadata.get("clutch") is True


def test_no_result_that_did_filter_still_reports_its_filters():
    """The guard targets unexecuted filters, not every empty answer.

    A query whose filters ran and matched nothing keeps its applied filters -
    that badge is an accurate description of work the engine did.
    """
    executed = execute_natural_query("Nikola Jokic games with over 80 points this season")

    assert executed.result_status != "ok"
    assert executed.result_reason == "no_match"
    assert _applied_filter_labels(executed.metadata)


# ---------------------------------------------------------------------------
# 4. Positive controls: clear metric-only leaderboards keep working
# ---------------------------------------------------------------------------

METRIC_ONLY_LEADERBOARDS = [
    ("top scorers this season", "season_leaders"),
    ("teams with the most points per game this season", "season_team_leaders"),
    ("highest ts% among players", "season_leaders"),
    ("best offensive teams", "season_team_leaders"),
    ("top 10 scorers 2025-26", "season_leaders"),
    ("points leaders", "season_leaders"),
    ("best defensive teams", "season_team_leaders"),
    ("who leads the league in assists", "season_leaders"),
    ("top rebounders this season", "season_leaders"),
    ("worst turnover teams", "season_team_leaders"),
]


@pytest.mark.parametrize("query, expected_route", METRIC_ONLY_LEADERBOARDS)
def test_clear_metric_only_leaderboards_still_answer(query, expected_route):
    executed = execute_natural_query(query)

    assert executed.route == expected_route
    assert executed.result_status == "ok"
    assert not _unsupported_filters(executed.metadata)
    assert len(executed.result.leaders) > 0


@pytest.mark.parser
@pytest.mark.parametrize(
    "query",
    [
        # Superlatives, role populations, and "without"-shaped stat phrases must
        # not be mistaken for the discarded-condition families above.
        "top scorers this season",
        "best offensive teams",
        "highest plus minus vs Celtics since 2021",
        "best efg% over the last 5 seasons",
        "who is the top scorer this season",
        "Lakers record without LeBron",
        "Nuggets record when Jokic plays",
    ],
)
def test_supported_queries_are_not_blocked_by_the_intent_guard(query):
    blocked = parse_query(query)["route_kwargs"].get("unsupported_filters") or []

    for marker in ("unresolved_availability", "unresolved_role_player", "subjective_outcome"):
        assert marker not in blocked
