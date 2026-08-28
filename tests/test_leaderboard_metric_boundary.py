"""A league-wide ranking must name the stat it ranks by.

The bug: `best NBA teams this season` returned a team points-per-game
leaderboard, and so did `best team while depleted`, `teams that cope best` and
`NBA leaders this season`. None of those questions named a metric. The route
needed one, took points, and presented the result as the answer.

These tests pin the replacement policy: the metric comes from the query or the
question is refused, the aggregation the user asked for is the one that runs,
and wording outside the stat-shaped grammar is refused rather than dropped.

The negative matrix is deliberately one row per *semantic category*, not a list
of synonyms. Understanding narrative language is not a Phase 1 goal; the only
requirement is that it cannot be silently discarded on the way to a different
answer.
"""

from __future__ import annotations

import pytest

from nbatools.commands._leaderboard_eligibility import (
    NO_REQUESTED_METRIC,
    UNCLEAR_REQUEST,
    UNSUPPORTED_AGGREGATION,
    assess_leaderboard_request,
)
from nbatools.commands.natural_query import _build_parse_state, parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.needs_data]

#: Routes that rank the whole league by one season metric.
BROAD_LEADERBOARD_ROUTES = {"season_leaders", "season_team_leaders"}


def _blockers(metadata: dict) -> list[str]:
    return list(metadata.get("unsupported_filters") or [])


def _no_substituted_answer(executed) -> None:
    """No populated result and no headline about a metric nobody asked for."""
    assert executed.result_status != "ok"
    assert executed.to_dict()["sections"] == {}
    for attr in ("leaders", "games", "streaks", "summary", "splits", "comparison"):
        assert getattr(executed.result, attr, None) is None


# ---------------------------------------------------------------------------
# 1. Approved shorthands still answer
# ---------------------------------------------------------------------------

# Every one of these worked at the pinned base and must keep working. They are
# the shorthands this PR preserves; it introduces none of its own.
APPROVED_SHORTHANDS = [
    ("top scorers this season", "season_leaders", "pts"),
    ("most rebounds this season", "season_leaders", "reb"),
    ("assists leaders this season", "season_leaders", "ast"),
    ("best 3P% this season", "season_leaders", "fg3_pct"),
    ("most threes made this season", "season_leaders", "fg3m"),
    ("best offensive teams", "season_team_leaders", "off_rating"),
    ("best defensive teams", "season_team_leaders", "def_rating"),
    ("teams with the most points per game", "season_team_leaders", "pts"),
    ("points leaders", "season_leaders", "pts"),
    ("rebound leaders", "season_leaders", "reb"),
]


@pytest.mark.parametrize("query, expected_route, expected_metric", APPROVED_SHORTHANDS)
def test_approved_shorthand_still_answers(query, expected_route, expected_metric):
    executed = execute_natural_query(query)

    assert executed.route == expected_route
    assert executed.result_status == "ok"
    assert not _blockers(executed.metadata)
    assert executed.metadata.get("stat") == expected_metric
    assert len(executed.result.leaders) > 0


@pytest.mark.parser
def test_best_team_record_keeps_its_own_route():
    """`best team record` is answered by the record leaderboard, not this gate."""
    parsed = parse_query("best team record")

    assert parsed["route"] == "team_record_leaderboard"
    assert not (parsed["route_kwargs"].get("unsupported_filters") or [])


# ---------------------------------------------------------------------------
# 2. A ranking with no metric is refused
# ---------------------------------------------------------------------------

# One row per semantic category, not per phrase.
METRICLESS_RANKINGS = [
    ("bare_superlative_team", "best NBA teams this season"),
    ("bare_league_leaders", "NBA leaders this season"),
    ("vague_verb", "teams that play best this season"),
    ("overall_scope", "best teams overall"),
    ("availability_narrative", "best team while depleted"),
    ("survival_narrative", "what team stayed afloat best"),
    ("coping_narrative", "teams that cope best"),
    ("population_only", "best teams with players"),
]


@pytest.mark.parser
@pytest.mark.parametrize(
    "category, query", METRICLESS_RANKINGS, ids=[r[0] for r in METRICLESS_RANKINGS]
)
def test_metricless_ranking_refuses_with_a_stable_blocker(category, query):
    parsed = parse_query(query)
    route_kwargs = parsed["route_kwargs"]

    assert NO_REQUESTED_METRIC in (route_kwargs.get("unsupported_filters") or []), category
    # No invented ranking metric reaches the blocked route.
    assert "stat" not in route_kwargs, category
    assert parsed["route"] in BROAD_LEADERBOARD_ROUTES, category


@pytest.mark.parametrize(
    "category, query", METRICLESS_RANKINGS, ids=[r[0] for r in METRICLESS_RANKINGS]
)
def test_metricless_ranking_returns_no_substituted_leaderboard(category, query):
    _no_substituted_answer(execute_natural_query(query))


@pytest.mark.parser
@pytest.mark.parametrize(
    "query",
    [
        # The inferences this policy forbids, stated as the queries that would
        # have produced them.
        "best NBA teams this season",
        "NBA leaders this season",
        "top players overall",
        "best teams overall",
        "teams that play best this season",
    ],
)
def test_no_query_silently_becomes_a_points_ranking(query):
    """None of these may resolve to `pts` merely because a route needed one."""
    eligibility = assess_leaderboard_request(_build_parse_state(query))

    assert eligibility.metric is None, f"{query!r} inferred metric {eligibility.metric!r}"
    assert not eligibility.authorized


# ---------------------------------------------------------------------------
# 3. Aggregation words are content, not grammar
# ---------------------------------------------------------------------------

# League leaderboards rank per-game figures. A season-total request is a
# different question, and answering it with a per-game board is wrong rather
# than approximate.
TOTAL_AGGREGATION_REQUESTS = [
    ("total_prefix", "total points leaders this season"),
    ("total_noun", "players with the most total rebounds"),
    ("total_suffix", "most points total this season"),
    ("combined", "combined scoring leaders"),
    ("cumulative", "cumulative points leaders this season"),
]

PER_GAME_REQUESTS = [
    ("points per game leaders this season", "pts"),
    ("average points leaders this season", "pts"),
    ("teams with the most points per game", "pts"),
]


@pytest.mark.parser
@pytest.mark.parametrize(
    "category, query",
    TOTAL_AGGREGATION_REQUESTS,
    ids=[r[0] for r in TOTAL_AGGREGATION_REQUESTS],
)
def test_total_aggregation_refuses_instead_of_returning_per_game(category, query):
    parsed = parse_query(query)

    assert UNSUPPORTED_AGGREGATION in (parsed["route_kwargs"].get("unsupported_filters") or []), (
        category
    )
    assert "stat" not in parsed["route_kwargs"], category


@pytest.mark.parametrize(
    "category, query",
    TOTAL_AGGREGATION_REQUESTS,
    ids=[r[0] for r in TOTAL_AGGREGATION_REQUESTS],
)
def test_total_aggregation_returns_no_per_game_leaderboard(category, query):
    _no_substituted_answer(execute_natural_query(query))


@pytest.mark.parametrize("query, expected_metric", PER_GAME_REQUESTS)
def test_per_game_aggregation_is_what_the_leaderboard_computes(query, expected_metric):
    executed = execute_natural_query(query)

    assert executed.result_status == "ok"
    assert executed.metadata.get("stat") == expected_metric
    assert any("per_game" in str(c) for c in executed.result.leaders.columns)


@pytest.mark.parser
def test_aggregation_words_are_not_treated_as_grammar():
    """`total` must survive as content; grammar words are dropped by design."""
    eligibility = assess_leaderboard_request(_build_parse_state("total points leaders"))

    assert eligibility.reason == UNSUPPORTED_AGGREGATION
    assert eligibility.metric == "pts"


# ---------------------------------------------------------------------------
# 4. Three-point policy
# ---------------------------------------------------------------------------

EXPLICIT_THREE_POINT = [
    ("three pointers made leaders", "fg3m"),
    ("most threes made", "fg3m"),
    ("three point percentage leaders", "fg3_pct"),
    ("best 3P%", "fg3_pct"),
]

AMBIGUOUS_THREE_POINT = [
    "NBA three point leaders",
    "top three point shooters",
    # Explicit about percentage, but the current metric vocabulary does not
    # resolve this construction. Refusing is correct until it does; mapping it
    # to points would be the original defect. Recorded as a focused follow-up.
    "top three-point shooters by percentage",
]


@pytest.mark.parametrize("query, expected_metric", EXPLICIT_THREE_POINT)
def test_explicit_three_point_forms_keep_their_metric(query, expected_metric):
    executed = execute_natural_query(query)

    assert executed.result_status == "ok"
    assert executed.metadata.get("stat") == expected_metric


@pytest.mark.parser
@pytest.mark.parametrize("query", AMBIGUOUS_THREE_POINT)
def test_ambiguous_three_point_forms_never_become_points(query):
    parsed = parse_query(query)

    assert parsed["route_kwargs"].get("unsupported_filters"), query
    assert parsed["route_kwargs"].get("stat") != "pts"
    assert "stat" not in parsed["route_kwargs"]


@pytest.mark.parametrize("query", AMBIGUOUS_THREE_POINT)
def test_ambiguous_three_point_forms_return_no_points_leaderboard(query):
    _no_substituted_answer(execute_natural_query(query))


# ---------------------------------------------------------------------------
# 5. Narrative wording is refused, not interpreted
# ---------------------------------------------------------------------------

# Safety probes only. The product is not expected to understand any of these;
# the requirement is that none of them is discarded on the way to an answer.
# Deliberately one per category, and deliberately not a vocabulary to absorb.
NARRATIVE_PROBES = [
    ("roster_strength", "best offensive teams at less than full strength"),
    ("foul_trouble", "best offensive teams once their center fouled out"),
    ("game_state", "top scorers when the defense collapses"),
    ("officiating", "top scorers when the whistle disappears"),
    ("roster_churn", "best defensive teams amid roster churn"),
]


@pytest.mark.parser
@pytest.mark.parametrize("category, query", NARRATIVE_PROBES, ids=[r[0] for r in NARRATIVE_PROBES])
def test_narrative_wording_is_refused_not_dropped(category, query):
    """The metric is anchored here; the narrative clause is what refuses.

    Each of these names a real metric, so rule 1 passes and rule 2 has to do the
    work. That is the case a metric check alone would let through.
    """
    eligibility = assess_leaderboard_request(_build_parse_state(query))

    assert eligibility.metric is not None, f"{category}: precondition lost"
    assert eligibility.reason == UNCLEAR_REQUEST, category
    assert eligibility.residual, f"{category}: refused with nothing to point at"


@pytest.mark.parametrize("category, query", NARRATIVE_PROBES, ids=[r[0] for r in NARRATIVE_PROBES])
def test_narrative_wording_returns_no_substituted_leaderboard(category, query):
    _no_substituted_answer(execute_natural_query(query))


# ---------------------------------------------------------------------------
# 6. Concrete with/without-player questions are untouched
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    ["Lakers record without LeBron", "Nuggets record when Jokic plays"],
)
def test_named_player_availability_still_answers(query):
    executed = execute_natural_query(query)

    assert executed.route == "team_record"
    assert executed.result_status == "ok"
    assert not _blockers(executed.metadata)


def test_named_player_availability_keeps_its_route_even_with_no_matching_games():
    """`Lakers record without Anthony Davis` finds no games in this generation.

    That is the pinned base's answer too, and it is an honest one: the route and
    the availability filter are both intact. What matters here is that this PR
    did not turn it into a refusal or a substituted leaderboard.
    """
    executed = execute_natural_query("Lakers record without Anthony Davis")

    assert executed.route == "team_record"
    assert not _blockers(executed.metadata)


def test_role_based_availability_refuses_safely():
    """`their leading scorer` names no player, and this PR does not resolve one.

    Role-to-player resolution is future feature work. What must not happen is a
    scoring leaderboard standing in for a record question.
    """
    executed = execute_natural_query("Lakers record without their leading scorer")

    _no_substituted_answer(executed)
    assert executed.route in BROAD_LEADERBOARD_ROUTES or executed.route == "team_record"


# ---------------------------------------------------------------------------
# 7. Eligibility is positive, not merely unblocked
# ---------------------------------------------------------------------------


@pytest.mark.parser
@pytest.mark.parametrize("query, _route, _metric", APPROVED_SHORTHANDS)
def test_supported_rankings_are_authorized_by_full_accounting(query, _route, _metric):
    """Authorized because every word is accounted for, not because nothing matched."""
    eligibility = assess_leaderboard_request(_build_parse_state(query))

    assert eligibility.authorized, f"{query!r} unaccounted words: {eligibility.residual}"
    assert eligibility.metric is not None
    assert not eligibility.residual


@pytest.mark.parser
@pytest.mark.parametrize(
    "query",
    [
        "so who are the top scorers this season",
        "please show me the points leaders",
        "which players have the most rebounds this year",
        "top scorers at home this season",
        "top scorers among guards this season",
        "who leads the league in assists",
    ],
)
def test_grammatical_variation_keeps_eligibility(query):
    eligibility = assess_leaderboard_request(_build_parse_state(query))

    assert eligibility.authorized, f"{query!r} unaccounted words: {eligibility.residual}"
