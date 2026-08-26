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

from nbatools.commands._broad_default_authorization import (
    RANKING_INTENT,
    SORT_DIRECTION,
)
from nbatools.commands._condition_semantics import detect_requested_conditions
from nbatools.commands._constants import normalize_text
from nbatools.commands.natural_query import (
    _broad_default_authorization,
    _build_parse_state,
    parse_query,
)
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

# A semantic variant matrix, not a list of the phrases the detectors were
# written against. Each row names the dimension it varies, so a detector that
# only learned one spelling of a concept fails here rather than in production.
#
# (dimension, query, marker that must be reported as blocking)
DISCARDED_CONDITION_MATRIX = [
    # -- absence verbs ----------------------------------------------------
    (
        "absence_verb_negated",
        "best team when leading scorer does not play",
        "unresolved_availability",
    ),
    ("absence_verb_past", "best team when leading scorer did not play", "unresolved_availability"),
    (
        "absence_verb_modal",
        "which team wins most when their star cannot play",
        "unresolved_availability",
    ),
    (
        "absence_verb_sit",
        "which teams win most when their best player sits out",
        "unresolved_availability",
    ),
    (
        "absence_verb_miss",
        "best team when its leading scorer misses games",
        "unresolved_availability",
    ),
    # -- absence states ---------------------------------------------------
    (
        "absence_state_injured",
        "best team when leading scorer is injured",
        "unresolved_availability",
    ),
    (
        "absence_state_suspended",
        "best team when leading scorer is suspended",
        "unresolved_availability",
    ),
    ("absence_state_sidelined", "best team when its star is sidelined", "unresolved_availability"),
    (
        "absence_state_inactive",
        "which team wins most with its best player inactive",
        "unresolved_availability",
    ),
    # -- squad-level absence ---------------------------------------------
    ("shorthanded", "teams that do best shorthanded", "unresolved_availability"),
    ("depleted", "best team while depleted", "unresolved_availability"),
    ("depleted_plural", "teams that win most when depleted", "unresolved_availability"),
    ("undermanned", "which teams win most undermanned", "unresolved_availability"),
    ("missing_starters", "which team plays best when missing starters", "unresolved_availability"),
    # -- absence prepositions --------------------------------------------
    ("without_plural_role", "teams that perform best without stars", "unresolved_availability"),
    ("with_no_role", "best team with no stars", "unresolved_availability"),
    (
        "without_possessive_role",
        "teams that cope best without their leading scorer",
        "unresolved_availability",
    ),
    ("without_singular_role", "best record without its best player", "unresolved_availability"),
    # -- subjective outcomes ---------------------------------------------
    ("subjective_afloat", "what team has stayed afloat best", "subjective_outcome"),
    ("subjective_hold_up", "which teams hold up best", "subjective_outcome"),
    ("subjective_fare", "how do teams fare", "subjective_outcome"),
    ("subjective_tread_water", "which teams tread water best", "subjective_outcome"),
    # -- combined ---------------------------------------------------------
    (
        "combined_all_three",
        "What team has stayed afloat best when its leading scorer was out?",
        "unresolved_availability",
    ),
    ("combined_role_absence", "how do teams do when their star is out", "unresolved_availability"),
]


@pytest.mark.parser
@pytest.mark.parametrize(
    "dimension, query, marker",
    DISCARDED_CONDITION_MATRIX,
    ids=[row[0] for row in DISCARDED_CONDITION_MATRIX],
)
def test_semantic_condition_is_represented_in_parse_state(dimension, query, marker):
    """Every variant must normalize into the condition ledger during parsing."""
    conditions = detect_requested_conditions(normalize_text(query))

    assert conditions, f"{dimension}: no condition recorded for {query!r}"
    assert all(condition.surface for condition in conditions)


@pytest.mark.parser
@pytest.mark.parametrize(
    "dimension, query, marker",
    DISCARDED_CONDITION_MATRIX,
    ids=[row[0] for row in DISCARDED_CONDITION_MATRIX],
)
def test_broad_default_cannot_fire_with_an_unconsumed_condition(dimension, query, marker):
    parsed = parse_query(query)
    route_kwargs = parsed["route_kwargs"]
    blockers = route_kwargs.get("unsupported_filters") or []

    assert blockers, f"{dimension}: refused with no stable blocker"
    # "best player" is claimed by the older subjective-query guard, which
    # refuses earlier than this one. Either blocker is a correct refusal; what
    # must never happen is the question reaching a broad default.
    assert marker in blockers or "subjective_query" in blockers, dimension
    # No substituted ranking metric may be handed to the blocked route.
    assert "stat" not in route_kwargs
    assert parsed["route"] in BROAD_LEADERBOARD_ROUTES or parsed["route"] is None


@pytest.mark.parametrize(
    "dimension, query, marker",
    DISCARDED_CONDITION_MATRIX,
    ids=[row[0] for row in DISCARDED_CONDITION_MATRIX],
)
def test_semantic_variant_returns_no_substituted_answer(dimension, query, marker):
    executed = execute_natural_query(query)

    assert executed.result_status != "ok", dimension
    assert executed.to_dict()["sections"] == {}
    for attr in ("leaders", "games", "streaks", "summary", "splits", "comparison"):
        assert getattr(executed.result, attr, None) is None


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
        # A named player whose clutch request was understood but has no trusted
        # coverage is a different blocker from an uninterpretable clutch fragment.
        ("Tatum clutch stats", "clutch_coverage"),
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


# ---------------------------------------------------------------------------
# 5. Fail-closed authorization: refusal must not depend on a detector matching
# ---------------------------------------------------------------------------

# The point of these rows is that none of their wording appears in
# _condition_semantics: not in _ABSENCE_STATES, not in _ABSENCE_PREPOSITIONS,
# not in _ROLE_NOUNS, not in _SUBJECTIVE_OUTCOME_PHRASES. If refusal still
# depended on a detector matching, every one of them would come back as a
# populated league leaderboard, which is what the previous candidate did.
#
# They are also deliberately not a synonym list to be absorbed: adding these
# exact phrases to a vocabulary would leave the next paraphrase broken, so the
# fix has to be the authorization direction, not the words.
OUT_OF_VOCABULARY_RESIDUALS = [
    ("bench_strength", "best team while down two starters"),
    ("roster_strength", "best team at less than full strength"),
    ("rotation_depth", "which team won most while missing half its rotation"),
    ("roster_completeness", "best team playing without a full roster"),
    ("defensive_collapse", "top scorers when the defense collapses"),
    ("foul_trouble", "best offensive teams once their center fouled out"),
    ("travel_context", "best team in the middle of a road trip from hell"),
    ("officiating", "who scores most when the whistle disappears"),
    ("lineup_quality", "which team performed best amid roster churn"),
    ("offensive_stall", "best scorers on nights the offense stalls"),
]


@pytest.mark.parser
@pytest.mark.parametrize(
    "dimension, query",
    OUT_OF_VOCABULARY_RESIDUALS,
    ids=[row[0] for row in OUT_OF_VOCABULARY_RESIDUALS],
)
def test_no_condition_detector_matches_these_at_all(dimension, query):
    """Guard the premise: these must stay outside the condition vocabularies.

    If a later change teaches the detectors one of these phrasings, this test
    fails and the row has to be replaced. Otherwise the refusal test below would
    silently start proving the old, fail-open thing again.
    """
    assert not detect_requested_conditions(normalize_text(query)), (
        f"{dimension}: {query!r} is now inside the condition vocabulary, so it no "
        "longer tests fail-closed authorization"
    )


@pytest.mark.parser
@pytest.mark.parametrize(
    "dimension, query",
    OUT_OF_VOCABULARY_RESIDUALS,
    ids=[row[0] for row in OUT_OF_VOCABULARY_RESIDUALS],
)
def test_unrecognized_content_withholds_broad_default_authorization(dimension, query):
    parsed = parse_query(query)
    route_kwargs = parsed["route_kwargs"]

    assert route_kwargs.get("unsupported_filters"), f"{dimension}: refused with no blocker"
    # No invented ranking metric handed to the blocked route.
    assert "stat" not in route_kwargs, dimension


@pytest.mark.parametrize(
    "dimension, query",
    OUT_OF_VOCABULARY_RESIDUALS,
    ids=[row[0] for row in OUT_OF_VOCABULARY_RESIDUALS],
)
def test_unrecognized_content_returns_no_substituted_leaderboard(dimension, query):
    executed = execute_natural_query(query)

    assert executed.result_status != "ok", dimension
    assert executed.to_dict()["sections"] == {}
    for attr in ("leaders", "games", "streaks", "summary", "splits", "comparison"):
        assert getattr(executed.result, attr, None) is None, dimension


@pytest.mark.parser
@pytest.mark.parametrize(
    "dimension, query",
    OUT_OF_VOCABULARY_RESIDUALS,
    ids=[row[0] for row in OUT_OF_VOCABULARY_RESIDUALS],
)
def test_refusal_carries_enough_metadata_to_explain_itself(dimension, query):
    authorization = _broad_default_authorization(_build_parse_state(query))

    assert not authorization.authorized, dimension
    assert authorization.reason, dimension
    assert authorization.residual, f"{dimension}: refused with nothing to point at"


# ---------------------------------------------------------------------------
# 6. Positive authorization: valid leaderboards are *proven*, not just unblocked
# ---------------------------------------------------------------------------


@pytest.mark.parser
@pytest.mark.parametrize("query, expected_route", METRIC_ONLY_LEADERBOARDS)
def test_valid_leaderboards_are_authorized_by_full_accounting(query, expected_route):
    """Every content-bearing word is claimed by a component the route implements.

    This is the assertion the previous candidate could not make. It passed by
    finding nothing wrong; this one requires the query to be positively
    accounted for, so a leaderboard that answers by accident fails here.
    """
    parsed = _build_parse_state(query)
    authorization = _broad_default_authorization(parsed)

    assert authorization.authorized, (
        f"{query!r} lost authorization; unaccounted words: {authorization.residual}"
    )
    assert not authorization.residual
    assert authorization.accounted, "authorized with nothing accounted for"
    # Something has to carry the ranking itself, not only grammar.
    assert {RANKING_INTENT, SORT_DIRECTION} & set(authorization.accounted), query


@pytest.mark.parser
@pytest.mark.parametrize(
    "query",
    [
        # Filler, politeness and grammatical variation around the same request.
        "so who are the top scorers this season",
        "please show me the points leaders",
        "which players have the most rebounds this year",
        "what team has the best net rating right now",
        "who's been the best scorer over the last 10 games",
        "top scorers among guards this season",
        "most points vs the lakers since 2018",
        "best efg% over the last 5 seasons",
    ],
)
def test_grammatical_variation_keeps_authorization(query):
    authorization = _broad_default_authorization(_build_parse_state(query))

    assert authorization.authorized, (
        f"{query!r} lost authorization; unaccounted words: {authorization.residual}"
    )


# ---------------------------------------------------------------------------
# 7. Metric anchoring: a metric inside a condition is not the requested metric
# ---------------------------------------------------------------------------


@pytest.mark.parser
def test_metric_nested_in_a_condition_is_not_promoted():
    """ "scorer" inside "when its leading scorer was out" is not a scoring request."""
    authorization = _broad_default_authorization(
        _build_parse_state("best team when its leading scorer was out")
    )

    assert not authorization.authorized
    assert authorization.metric is None, "a condition's noun became the ranking metric"
    assert authorization.metric_anchor is None
    # The evidence is recorded, so the decision can be explained - just not used.
    assert "scorer" in authorization.nested_metric_evidence


@pytest.mark.parser
def test_metric_outside_any_condition_anchors_normally():
    authorization = _broad_default_authorization(_build_parse_state("top scorers this season"))

    assert authorization.authorized
    assert authorization.metric == "pts"
    assert authorization.metric_anchor == "scorers"
    assert not authorization.nested_metric_evidence
