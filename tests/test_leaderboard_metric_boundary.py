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

import pathlib

import pytest

from nbatools.commands import natural_query as natural_query_module
from nbatools.commands._leaderboard_eligibility import (
    METRIC_SCOPE_UNSUPPORTED,
    MULTIPLE_METRICS,
    NO_REQUESTED_METRIC,
    UNCLEAR_REQUEST,
    UNSUPPORTED_AGGREGATION,
    assess_leaderboard_request,
    ranks_a_season_total,
    requested_leaderboard_metrics,
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


# ---------------------------------------------------------------------------
# 8. Subject-less context fragments never receive an invented metric
# ---------------------------------------------------------------------------

# A branch ahead of the eligibility gate used to hand `season_leaders` a literal
# stat="pts" so it had something to rank, for any clutch or opponent-quality
# fragment with no subject and no stat. That is the same metric invention the
# gate exists to stop, reached by a route that ran before it. The data happened
# to refuse afterwards, but the substituted metric was already created and
# reached result metadata.
CONTEXT_ONLY_FRAGMENTS = [
    ("clutch_bare", "clutch stats"),
    ("clutch_season", "clutch numbers this season"),
    ("clutch_prepositional", "in clutch time"),
    ("clutch_sentence", "how did they do in clutch time"),
    ("opponent_quality_bare", "stats against winning teams"),
    ("opponent_quality_season", "against winning teams this season"),
    ("opponent_quality_playoff", "stats against playoff teams"),
]


@pytest.mark.parser
def test_context_fragment_points_fallback_no_longer_exists():
    """The literal fallback is gone from the source, not merely unreachable.

    Scoped to the branch itself. Elsewhere in the router ``stat="pts"`` can be
    legitimate - ``top_player_games`` serves "top scorer on January 1", where
    the wording names scoring - so a file-wide ban would assert the wrong thing.
    """
    source = pathlib.Path(natural_query_module.__file__).read_text()

    assert "returning a broad points leaderboard fallback" not in source
    assert "boundary_fragment:" not in source

    marker = "and (opponent_quality or clutch)"
    assert marker in source, "the context-fragment branch moved; rescope this test"
    branch = source.split(marker, 1)[1].split("    elif ", 1)[0]
    assert '"stat"' not in branch, "the context-fragment branch is setting a metric again"


@pytest.mark.parser
@pytest.mark.parametrize(
    "category, query", CONTEXT_ONLY_FRAGMENTS, ids=[r[0] for r in CONTEXT_ONLY_FRAGMENTS]
)
def test_context_fragment_gets_no_invented_metric(category, query):
    route_kwargs = parse_query(query)["route_kwargs"]

    assert "stat" not in route_kwargs, category
    assert UNCLEAR_REQUEST in (route_kwargs.get("unsupported_filters") or []), category


@pytest.mark.parser
@pytest.mark.parametrize(
    "category, query", CONTEXT_ONLY_FRAGMENTS, ids=[r[0] for r in CONTEXT_ONLY_FRAGMENTS]
)
def test_context_fragment_carries_no_broad_points_fallback_note(category, query):
    notes = " ".join(parse_query(query).get("notes") or [])

    assert "broad points leaderboard fallback" not in notes, category
    assert "no substituted leaderboard was returned" in notes, category


@pytest.mark.parametrize(
    "category, query", CONTEXT_ONLY_FRAGMENTS, ids=[r[0] for r in CONTEXT_ONLY_FRAGMENTS]
)
def test_context_fragment_returns_no_points_result(category, query):
    executed = execute_natural_query(query)

    _no_substituted_answer(executed)
    # No points metadata for the frontend to build a headline out of.
    assert executed.metadata.get("stat") is None, category
    assert UNCLEAR_REQUEST in _blockers(executed.metadata), category


@pytest.mark.parametrize(
    "query",
    ["Williams clutch stats", "Smith against good teams"],
)
def test_ambiguous_entity_stays_ambiguous(query):
    """An unresolved name is an ambiguity, not a missing-metric refusal.

    These never reach the fragment branch - entity ambiguity resolves earlier -
    and turning them into a generic metric complaint would hide the real fix,
    which is naming the player.
    """
    executed = execute_natural_query(query)

    assert executed.result_reason == "ambiguous"
    assert not _blockers(executed.metadata)
    assert executed.metadata.get("stat") is None


@pytest.mark.parametrize(
    "query, expected_route",
    [
        ("Tatum against good teams", "player_game_summary"),
        ("Celtics record against playoff teams", "team_record"),
        ("Nuggets record vs winning teams", "team_record"),
    ],
)
def test_opponent_quality_with_a_subject_still_answers(query, expected_route):
    executed = execute_natural_query(query)

    assert executed.route == expected_route
    assert executed.result_status == "ok"
    assert not _blockers(executed.metadata)


@pytest.mark.parametrize(
    "query, expected_route",
    [("Tatum clutch stats", "player_game_summary"), ("Lakers clutch record", "team_record")],
)
def test_concrete_clutch_keeps_its_coverage_behavior(query, expected_route):
    """A clutch question with a subject is understood; its refusal is about data.

    This correction is only about subject-less fragments inventing a metric, so
    these must keep the route and the honest coverage refusal they already had.
    """
    executed = execute_natural_query(query)

    assert executed.route == expected_route
    assert executed.result_reason == "filter_not_supported"
    assert executed.metadata.get("stat") is None
    assert UNCLEAR_REQUEST not in _blockers(executed.metadata)


# ---------------------------------------------------------------------------
# 9. The metric boundary governs every ranking-producing route family
# ---------------------------------------------------------------------------

# Test-owned inventory. Each row is a route family that can return a ranked
# list, with a query that names a metric and one that does not. The point is to
# be independent of the router: a new specialized branch that forgets the guard
# fails here even though every other test still passes, because a metricless
# query for its family will come back populated.
#
# (family, metric-named query, metricless query)
RANKING_ROUTE_FAMILIES = [
    ("season_leaders", "points leaders this season", "top players this season"),
    ("season_team_leaders", "teams with the most points per game", "best teams overall"),
    ("rookie_leaderboard", "rookie scoring leaders this season", "rookie leaders this season"),
    ("sophomore_leaderboard", "sophomore assist leaders this season", "best sophomores"),
    ("starter_leaderboard", "starter points leaders this season", "starter leaders"),
    ("bench_leaderboard", "bench assist leaders this season", "bench leaders"),
    (
        "top_team_games",
        "highest scoring team games this season",
        "best team performances this season",
    ),
    ("top_player_games", "top scoring games this season", "top players this season"),
    ("team_scoped_leader", "Lakers leading scorer", "Lakers record without their leading scorer"),
]

#: Route families whose metric is fixed by the route itself rather than chosen
#: from the query, so "no metric named" is not a possible request for them.
FIXED_METRIC_RANKING_ROUTES = {
    # Ranks win percentage by definition; "best team record" names it.
    "team_record_leaderboard",
    # Ranks occurrences of a named event ("most 40 point games"), which the
    # event itself supplies.
    "player_occurrence_leaders",
}


@pytest.mark.parametrize(
    "family, with_metric, _without",
    RANKING_ROUTE_FAMILIES,
    ids=[r[0] for r in RANKING_ROUTE_FAMILIES],
)
def test_ranking_family_answers_when_a_metric_is_named(family, with_metric, _without):
    executed = execute_natural_query(with_metric)

    assert executed.result_status == "ok", f"{family}: {with_metric!r} stopped answering"
    assert executed.metadata.get("stat"), family


@pytest.mark.parametrize(
    "family, _with_metric, without",
    RANKING_ROUTE_FAMILIES,
    ids=[r[0] for r in RANKING_ROUTE_FAMILIES],
)
def test_ranking_family_refuses_when_no_metric_is_named(family, _with_metric, without):
    executed = execute_natural_query(without)

    _no_substituted_answer(executed)
    assert _blockers(executed.metadata), f"{family}: refused with no blocker"


@pytest.mark.parser
@pytest.mark.parametrize(
    "family, _with_metric, without",
    RANKING_ROUTE_FAMILIES,
    ids=[r[0] for r in RANKING_ROUTE_FAMILIES],
)
def test_ranking_family_never_invents_a_metric(family, _with_metric, without):
    """No ranking branch may hand its route a metric the query did not name."""
    route_kwargs = parse_query(without)["route_kwargs"]

    assert "stat" not in route_kwargs or route_kwargs["stat"] is None, family


@pytest.mark.parser
def test_no_unanchored_points_fallback_remains_in_the_router():
    """Every surviving ``pts`` literal is an approved shorthand, not a default.

    The router had thirteen `or "pts"` tails. What is left may only be the
    documented shorthands - `<player> season high`, `top scoring games` - which
    the branch conditions require the wording for.
    """
    source = pathlib.Path(natural_query_module.__file__).read_text()
    code = [line for line in source.splitlines() if not line.lstrip().startswith("#")]

    assert 'stat or detect_player_leaderboard_stat(q) or "pts"' not in source
    offenders = [line.strip() for line in code if 'or "pts"' in line]
    assert not offenders, f"an unanchored points fallback is back: {offenders}"


# ---------------------------------------------------------------------------
# 10. Several metrics at once
# ---------------------------------------------------------------------------

MULTI_METRIC_REQUESTS = [
    ("and_two", "points and rebounds leaders this season"),
    ("and_synonym", "scoring and assists leaders this season"),
    ("or_two", "top points or rebounds this season"),
    ("team_and", "teams with the most points and assists"),
    ("comma_three", "players leading in points, rebounds, and assists"),
    ("rate_and_count", "best shooting percentage and scoring leaders"),
]


@pytest.mark.parametrize(
    "category, query", MULTI_METRIC_REQUESTS, ids=[r[0] for r in MULTI_METRIC_REQUESTS]
)
def test_several_requested_metrics_refuse_instead_of_picking_one(category, query):
    """Ranking by whichever the detectors returned last deletes the rest."""
    executed = execute_natural_query(query)

    _no_substituted_answer(executed)
    assert MULTIPLE_METRICS in _blockers(executed.metadata), category


@pytest.mark.parser
@pytest.mark.parametrize(
    "category, query", MULTI_METRIC_REQUESTS, ids=[r[0] for r in MULTI_METRIC_REQUESTS]
)
def test_every_requested_metric_is_preserved_in_metadata(category, query):
    metrics = requested_leaderboard_metrics(_build_parse_state(query))

    assert len(metrics) > 1, f"{category}: precondition lost, only {metrics}"


@pytest.mark.parser
@pytest.mark.parametrize(
    "query, expected",
    [
        # One metric, spelled with words that also appear in other aliases.
        ("highest true shooting percentage this season", ("ts_pct",)),
        ("points per game leaders", ("pts",)),
        ("best field goal percentage among guards", ("fg_pct",)),
        # A position name contains "point"; that is not a points request.
        ("point guard assist leaders this season", ("ast",)),
        ("most assists while the starting point guard was out", ("ast",)),
    ],
)
def test_single_metric_questions_are_not_read_as_compound(query, expected):
    assert requested_leaderboard_metrics(_build_parse_state(query)) == expected


# ---------------------------------------------------------------------------
# 11. A metric the window cannot compute is not a reason to rank by another
# ---------------------------------------------------------------------------

UNSUPPORTED_SCOPE_REQUESTS = [
    ("team_rating_multi_season", "best offensive teams from 2022-23 to 2024-25"),
    ("team_net_rating_multi_season", "best net rating teams from 2022-23 to 2024-25"),
    ("team_pace_multi_season", "pace leaders from 2022-23 to 2024-25"),
    (
        "team_rating_opponent",
        "offensive rating leaders vs Lakers from 2022-23 to 2024-25",
    ),
]


@pytest.mark.parametrize(
    "category, query",
    UNSUPPORTED_SCOPE_REQUESTS,
    ids=[r[0] for r in UNSUPPORTED_SCOPE_REQUESTS],
)
def test_unavailable_metric_window_refuses_rather_than_becoming_points(category, query):
    """These returned points leaderboards with a `stat_fallback` note.

    Saying "using pts" in a note does not make the answer the one that was
    asked for.
    """
    executed = execute_natural_query(query)

    _no_substituted_answer(executed)
    assert METRIC_SCOPE_UNSUPPORTED in _blockers(executed.metadata), category
    assert executed.metadata.get("stat") != "pts", category


@pytest.mark.parser
def test_no_cross_metric_stat_fallback_remains():
    source = pathlib.Path(natural_query_module.__file__).read_text()

    assert "stat_fallback" not in source
    assert "using pts" not in source


@pytest.mark.parametrize(
    "query",
    [
        # The same metrics inside a window that can compute them.
        "best offensive teams",
        "best defensive teams",
    ],
)
def test_single_season_rating_requests_still_answer(query):
    executed = execute_natural_query(query)

    assert executed.result_status == "ok"
    assert not _blockers(executed.metadata)


# ---------------------------------------------------------------------------
# 12. Narrative clauses refuse on specialized branches too
# ---------------------------------------------------------------------------

# Safety probes. The product is not expected to understand any of these; the
# requirement is that a specialized branch cannot skip residual accounting just
# because it already resolved a metric and a population.
SPECIALIZED_NARRATIVE_PROBES = [
    ("league_wide", "most assists while the starting point guard was out"),
    ("rookie", "rookie scoring leaders while their best player was injured"),
    ("bench", "bench points leaders when the rotation was depleted"),
    ("team_games", "best team performances once their center fouled out"),
    ("sophomore", "top sophomore scorers amid roster churn"),
]


@pytest.mark.parametrize(
    "category, query",
    SPECIALIZED_NARRATIVE_PROBES,
    ids=[r[0] for r in SPECIALIZED_NARRATIVE_PROBES],
)
def test_specialized_route_refuses_a_narrative_clause(category, query):
    executed = execute_natural_query(query)

    _no_substituted_answer(executed)
    assert _blockers(executed.metadata), f"{category}: refused with no blocker"


# ---------------------------------------------------------------------------
# 13. Aggregation is metric-specific
# ---------------------------------------------------------------------------

# The leaderboards are not uniformly per-game. `pf` ranks `pf_total`, so "total
# personal fouls leaders" is exactly what runs; `pts` ranks `pts_per_game`, so
# "total points leaders" would be answered with a different figure entirely.
TOTAL_BACKED_METRICS = [
    ("personal fouls leaders", "pf"),
    ("total personal fouls leaders", "pf"),
    ("minutes leaders", "minutes"),
    ("total minutes leaders", "minutes"),
    ("total field goals made leaders", "fgm"),
    ("total free throws made leaders", "ftm"),
]

PER_GAME_BACKED_TOTAL_REQUESTS = [
    "total points leaders this season",
    "players with the most total rebounds",
    "most points total this season",
    "combined scoring leaders",
    "cumulative points leaders this season",
]

RATE_AND_PER_GAME_REQUESTS = [
    ("points per game leaders", "pts"),
    ("average points leaders", "pts"),
    ("rebounds per game leaders", "reb"),
    ("best 3P%", "fg3_pct"),
    ("usage rate leaders", "usg_pct"),
]


@pytest.mark.parametrize("query, expected_metric", TOTAL_BACKED_METRICS)
def test_total_backed_metrics_keep_their_total_support(query, expected_metric):
    """A blanket "leaderboards are per-game" rule refuses these wrongly."""
    executed = execute_natural_query(query)

    assert executed.result_status == "ok", f"{query!r} lost its total-backed answer"
    assert executed.metadata.get("stat") == expected_metric
    assert not _blockers(executed.metadata)


@pytest.mark.parser
@pytest.mark.parametrize("query, expected_metric", TOTAL_BACKED_METRICS)
def test_total_backed_metrics_rank_a_total_column(query, expected_metric):
    assert ranks_a_season_total(expected_metric, team_scope=False), (
        f"{expected_metric} is not total-backed; this row belongs in the per-game set"
    )


@pytest.mark.parametrize("query", PER_GAME_BACKED_TOTAL_REQUESTS)
def test_per_game_backed_metrics_refuse_total_wording(query):
    executed = execute_natural_query(query)

    _no_substituted_answer(executed)
    assert UNSUPPORTED_AGGREGATION in _blockers(executed.metadata)


@pytest.mark.parametrize("query, expected_metric", RATE_AND_PER_GAME_REQUESTS)
def test_per_game_and_rate_requests_answer(query, expected_metric):
    executed = execute_natural_query(query)

    assert executed.result_status == "ok"
    assert executed.metadata.get("stat") == expected_metric


# ---------------------------------------------------------------------------
# 14. Metricless player rankings get a typed clarification, not an error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    ["top players this season", "best players overall", "players that perform best"],
)
def test_metricless_player_ranking_is_typed_not_unrouted(query):
    """These came back as `error` / `unrouted`, which tells the user nothing."""
    executed = execute_natural_query(query)

    assert executed.result_status == "no_result"
    assert executed.result_reason == "filter_not_supported"
    assert NO_REQUESTED_METRIC in _blockers(executed.metadata)
    assert executed.metadata.get("stat") is None
    _no_substituted_answer(executed)


# ---------------------------------------------------------------------------
# 15. Subject-resolved team controls
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query, expected_route, expected_metric",
    [
        ("Lakers leading scorer", "season_leaders", "pts"),
        ("Nuggets top rebounder", "season_leaders", "reb"),
    ],
)
def test_team_scoped_leaders_still_answer(query, expected_route, expected_metric):
    executed = execute_natural_query(query)

    assert executed.route == expected_route
    assert executed.result_status == "ok"
    assert executed.metadata.get("stat") == expected_metric
