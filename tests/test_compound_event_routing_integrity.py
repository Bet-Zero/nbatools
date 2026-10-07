"""A compound question must be executed whole or refused whole.

The bug: a clear question that combines a ranking intent, one or more event
thresholds, a time window and sometimes an availability clause could lose part
of itself on the way to a route, and the answer that came back was confident and
was not the question asked.

At the pinned base:

- ``teams with most games scoring 120+ and making 15+ threes since 2020``
  returned a league three-pointers-per-game leaderboard. The 120-point condition
  was never read, "most games" stopped meaning a count, and the surviving
  threshold metric became the ranking key.
- ``most efficient 30-point games`` returned a count of 30-point games.
  "Efficient" - which this repo already reads as True Shooting % - was dropped
  without a word.
- ``players with 25 points and 10 rebounds`` came back as an unrouted error
  whose metadata still carried a rebounds stat (it now lists every player
  with a game meeting both).
- ``most 40-point games while the player was injured`` returned a Washington
  Wizards game list: "was" resolved to the Wizards and the injury clause was
  discarded.
- ``Lakers leading scorer while LeBron was out`` returned a LeBron James player
  summary - the wrong subject, and the absence dropped.

These tests pin the replacement policy. They assert route, status, reason, the
kwargs that actually execute, which sections are populated, and which requested
components survive into the refusal - not status alone. See
``docs/architecture/parser/compound_event_routing.md``.

Scope. Compound/event-shaped routing only: occurrence counts, game finders,
single-game rankings, and the season leaderboards a compound request can leak
onto. Fixed-metric record, playoff, stretch, lineup and decade routes are a
separate project, and no vague word acquires a meaning here.
"""

from __future__ import annotations

import pytest

from nbatools.commands._compound_event_authorization import (
    COMPOUND_EVENT_UNEXECUTABLE,
    authorize_compound_event_route,
    declared_event_conditions,
    executed_event_conditions,
    named_metrics,
    occurrence_count_column_condition,
    ranking_key,
    unsupported_availability_status,
)
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.needs_data]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _blockers(metadata: dict) -> list[str]:
    return list(metadata.get("unsupported_filters") or [])


def _no_answer_was_returned(executed) -> None:
    """Nothing ran: no populated section, no executed metric, no substitute."""
    assert executed.result_status != "ok"
    assert executed.to_dict()["sections"] == {}
    assert executed.metadata.get("stat") is None
    for attr in ("leaders", "games", "streaks", "summary", "splits", "comparison"):
        assert getattr(executed.result, attr, None) is None


def _condition(stat: str, minimum: float) -> dict:
    return {"stat": stat, "min_value": minimum, "max_value": None}


def _leaderboard_rows(executed) -> list[dict]:
    return list(executed.to_dict()["sections"]["leaderboard"])


# ---------------------------------------------------------------------------
# 1. The team compound occurrence question executes in full
# ---------------------------------------------------------------------------

TEAM_COMPOUND_QUERY = "teams with most games scoring 120+ and making 15+ threes since 2020"


def test_team_compound_occurrence_executes_every_component():
    parsed = parse_query(TEAM_COMPOUND_QUERY)

    assert parsed["route"] == "team_occurrence_leaders"
    kwargs = parsed["route_kwargs"]
    # Both thresholds reach execution, in query order.
    assert kwargs["conditions"] == [
        _condition("pts", 120.0),
        _condition("fg3m", 15.0),
    ]
    # The date scope survives.
    assert kwargs["start_season"] == "2020-21"
    assert kwargs["end_season"] is not None
    # The ranking key is the count, so no threshold metric may sit in the stat
    # slot. This is the exact promotion that produced the base's wrong answer.
    assert kwargs.get("stat") is None


def test_team_compound_occurrence_ranks_by_matching_game_count():
    executed = execute_natural_query(TEAM_COMPOUND_QUERY)

    assert executed.route == "team_occurrence_leaders"
    assert executed.result_status == "ok"
    assert not _blockers(executed.metadata)
    # Said outright rather than inferred from a stat field.
    assert executed.metadata.get("ranking_key") == "occurrence_count"
    # No condition metric is published as the answer's metric.
    assert executed.metadata.get("stat") is None

    rows = _leaderboard_rows(executed)
    assert rows
    # The count column names both conditions, so a row proves both ran.
    count_columns = [key for key in rows[0] if key.startswith("games_")]
    assert "games_pts_120+_fg3m_15+" in count_columns
    # Ranked by the count, descending.
    counts = [row["games_pts_120+_fg3m_15+"] for row in rows]
    assert counts == sorted(counts, reverse=True)
    # And not by either threshold metric.
    assert "fg3m_per_game" not in rows[0]


def test_team_compound_occurrence_date_scope_is_applied():
    executed = execute_natural_query(TEAM_COMPOUND_QUERY)

    rows = _leaderboard_rows(executed)
    assert rows[0]["seasons"].startswith("2020-21")


# ---------------------------------------------------------------------------
# 2. A ranking metric the route cannot order by is refused, not dropped
# ---------------------------------------------------------------------------

EFFICIENT_QUERY = "most efficient 30-point games"


def test_efficient_thirty_point_games_refuses_and_keeps_both_halves():
    executed = execute_natural_query(EFFICIENT_QUERY)

    assert COMPOUND_EVENT_UNEXECUTABLE in _blockers(executed.metadata)
    assert executed.result_reason == "filter_not_supported"
    _no_answer_was_returned(executed)

    # "Efficient" is not invented here - the repo's leaderboard vocabulary
    # already reads it as True Shooting %. What cannot happen is ranking
    # individual games by it, and the refusal says which metric it is about.
    assert executed.metadata.get("requested_stat") == "ts_pct"
    # The 30-point condition is preserved rather than answered.
    assert executed.metadata.get("requested_event_conditions") == [_condition("pts", 30.0)]


def test_efficient_thirty_point_games_is_not_reduced_to_a_count():
    executed = execute_natural_query(EFFICIENT_QUERY)

    # The base answered with a games_30p count leaderboard. That is one of the
    # four shapes this question must never become.
    assert executed.metadata.get("ranking_key") != "occurrence_count"
    assert executed.metadata.get("stat") not in {"pts", "games_30p", "ppg"}
    assert executed.to_dict()["sections"] == {}


def test_efficiency_alias_is_existing_repository_behavior():
    """The proof that "efficient" was not given a new meaning in this project."""
    executed = execute_natural_query("most efficient players")

    assert executed.result_status == "ok"
    assert executed.metadata.get("stat") == "ts_pct"


# ---------------------------------------------------------------------------
# 3. Two thresholds are both meaningful
# ---------------------------------------------------------------------------

TWO_THRESHOLD_QUERY = "players with 25 points and 10 rebounds"


def test_two_threshold_request_lists_players_meeting_both_thresholds():
    # Was a whole-question refusal (a one-condition answer was the silent
    # reduction). It now answers whole: every player with a game meeting both,
    # counted by the condition pair, never by one of them alone.
    executed = execute_natural_query(TWO_THRESHOLD_QUERY)

    assert executed.result_status == "ok"
    assert executed.route == "player_occurrence_leaders"
    assert COMPOUND_EVENT_UNEXECUTABLE not in _blockers(executed.metadata)
    rows = _leaderboard_rows(executed)
    assert rows and all(row["games_pts_25+_reb_10+"] >= 1 for row in rows)
    assert executed.metadata.get("stat") is None


def test_two_threshold_parse_reads_both_conditions():
    parsed = parse_query(TWO_THRESHOLD_QUERY)

    assert declared_event_conditions(parsed) == (
        _condition("pts", 25.0),
        _condition("reb", 10.0),
    )


# ---------------------------------------------------------------------------
# 4. An availability condition with no data behind it
# ---------------------------------------------------------------------------

INJURY_QUERY = "most 40-point games while the player was injured"


def test_injury_condition_refuses_and_keeps_the_event_intent():
    executed = execute_natural_query(INJURY_QUERY)

    assert COMPOUND_EVENT_UNEXECUTABLE in _blockers(executed.metadata)
    _no_answer_was_returned(executed)
    assert executed.metadata.get("requested_event_conditions") == [_condition("pts", 40.0)]
    # The clause is named as unsupported rather than dropped. Naming it is not
    # interpreting it: nothing here decides what counts as injured.
    assert executed.metadata.get("unsupported_availability") == {"condition": "injury status"}


def test_injury_condition_does_not_invent_a_team():
    """`was` is the Wizards abbreviation and the English copula."""
    executed = execute_natural_query(INJURY_QUERY)

    assert executed.metadata.get("team") is None
    assert executed.metadata.get("team_context") is None


def test_wizards_abbreviation_still_resolves_when_it_means_the_team():
    parsed = parse_query("was record this season")

    assert parsed["team"] == "WAS"


def test_injury_status_is_recognized_but_never_modelled():
    parsed = parse_query(INJURY_QUERY)

    assert unsupported_availability_status(parsed) == "injury status"
    # No proxy: nothing in the parse turns "injured" into missed games, a rest
    # flag, or any other stand-in.
    assert parsed.get("without_player") is None
    assert parsed.get("with_player") is None


# ---------------------------------------------------------------------------
# 5. A team ranking with a teammate absence the route cannot apply
# ---------------------------------------------------------------------------

TEAM_SCORER_QUERY = "Lakers leading scorer while LeBron was out"


def test_team_scorer_with_absence_refuses():
    executed = execute_natural_query(TEAM_SCORER_QUERY)

    assert executed.result_status != "ok"
    assert executed.result_reason == "filter_not_supported"
    _no_answer_was_returned(executed)


def test_team_scorer_with_absence_keeps_the_lakers_as_the_subject():
    executed = execute_natural_query(TEAM_SCORER_QUERY)

    # The base switched the subject to LeBron and returned his player summary.
    assert executed.metadata.get("team") == "LAL"
    assert executed.metadata.get("player") is None
    assert executed.route != "player_game_summary"


def test_team_scorer_absence_survives_into_the_refusal():
    executed = execute_natural_query(TEAM_SCORER_QUERY)

    assert "without_player" in _blockers(executed.metadata)
    assert executed.metadata.get("unsupported_availability") == {"without_player": "LeBron James"}
    # Cleared from the applied slot, because nothing applied it.
    assert executed.metadata.get("without_player") is None


def test_while_states_the_same_absence_as_when():
    """The clause was readable all along in one wording and not the other."""
    assert parse_query("Lakers record while LeBron was out")["without_player"] == "LeBron James"
    assert parse_query("Lakers record when LeBron was out")["without_player"] == "LeBron James"


# ---------------------------------------------------------------------------
# 6. Elliptical compound metric requests
# ---------------------------------------------------------------------------

ELLIPTICAL_QUERIES = [
    "field goals made and attempted leaders",
    "best offense and defense this season",
]


@pytest.mark.parametrize("query", ELLIPTICAL_QUERIES)
def test_elliptical_compound_metric_requests_refuse_without_choosing_a_half(query):
    executed = execute_natural_query(query)

    assert executed.result_status != "ok"
    _no_answer_was_returned(executed)
    # Neither half is executed, and neither is published as the metric that ran.
    assert executed.metadata.get("stat") is None


# ---------------------------------------------------------------------------
# 7. Positive controls - clear supported shapes keep working
# ---------------------------------------------------------------------------

#: (query, route, published stat). Every one answered correctly at the pinned
#: base and must keep answering identically.
POSITIVE_CONTROLS = [
    ("points leaders", "season_leaders", "pts"),
    ("rebounds leaders", "season_leaders", "reb"),
    ("most points in a game", "top_player_games", "pts"),
    ("most 30 point games", "season_leaders", "pts"),
    ("teams with most 120 point games", "team_occurrence_leaders", "pts"),
    ("team points leaders", "season_team_leaders", "pts"),
    ("points leaders 2023-24", "season_leaders", "pts"),
]


@pytest.mark.parametrize("query, route, stat", POSITIVE_CONTROLS)
def test_supported_shapes_still_answer(query, route, stat):
    executed = execute_natural_query(query)

    assert executed.route == route
    assert executed.result_status == "ok"
    assert not _blockers(executed.metadata)
    assert executed.metadata.get("stat") == stat
    assert executed.to_dict()["sections"]


AVAILABILITY_CONTROLS = [
    ("Lakers record without LeBron", "without_player", "LeBron James"),
    ("Warriors record with Stephen Curry", "with_player", "Stephen Curry"),
]


@pytest.mark.parametrize("query, field, value", AVAILABILITY_CONTROLS)
def test_execution_backed_availability_still_answers(query, field, value):
    executed = execute_natural_query(query)

    assert executed.route == "team_record"
    assert executed.result_status == "ok"
    assert not _blockers(executed.metadata)
    assert executed.metadata.get(field) == value


def test_single_threshold_player_occurrence_still_answers():
    executed = execute_natural_query("most 30 point games")

    assert executed.result_status == "ok"
    rows = _leaderboard_rows(executed)
    assert rows and "games_30p" in rows[0]


def test_existing_compound_occurrence_phrasing_still_answers():
    """The already-supported wording of the same question as section 1."""
    executed = execute_natural_query(
        "teams with most games with 120+ points and 15+ threes since 2020"
    )

    assert executed.route == "team_occurrence_leaders"
    assert executed.result_status == "ok"
    assert executed.metadata.get("ranking_key") == "occurrence_count"


# Three shapes an over-strict authorization check refused on the first pass.
# The differential against the pinned base caught every one, and each is a
# perfectly ordinary question that must keep answering.

SPECIAL_EVENT_CONTROLS = [
    "How often has Nikola Jokic recorded a triple-double this season?",
    "how many LeBron triple doubles",
]


@pytest.mark.parametrize("query", SPECIAL_EVENT_CONTROLS)
def test_special_event_finder_queries_still_answer(query):
    """A triple-double is an event condition the finder executes as one.

    It arrives as ``special_event`` rather than in a conditions list, so a check
    that only read the list saw a condition nobody executed and refused.
    """
    executed = execute_natural_query(query)

    assert executed.result_status == "ok"
    assert not _blockers(executed.metadata)
    assert executed.to_dict()["sections"]


STRICT_INEQUALITY_CONTROLS = [
    "Jokic over 25 points and over 10 rebounds",
    "Jokic over 30 points and over 10 rebounds and over 10 assists",
]


@pytest.mark.parametrize("query", STRICT_INEQUALITY_CONTROLS)
def test_strict_inequality_thresholds_still_answer(query):
    """ "over 25 points" is stated as 25 and executed as 25.0001.

    That epsilon is how a strict inequality is expressed, not a changed
    threshold, so conditions are matched on stat, direction and value within a
    tolerance rather than by exact equality.
    """
    executed = execute_natural_query(query)

    assert executed.result_status == "ok"
    assert not _blockers(executed.metadata)
    assert executed.to_dict()["sections"]


GROUPED_BOOLEAN_CONTROLS = [
    "Jokic (over 25 points and over 10 rebounds) or over 15 assists",
    "Celtics (over 120 points and over 15 threes) or under 10 turnovers",
]


@pytest.mark.parametrize("query", GROUPED_BOOLEAN_CONTROLS)
def test_grouped_boolean_queries_still_answer(query):
    """A grouped boolean executes a condition the compound extractor never lists.

    Reading only the stated side reported that third metric as a discarded
    ranking metric. A metric the route actually filters on is accounted for.
    """
    executed = execute_natural_query(query)

    assert executed.result_status == "ok"
    assert not _blockers(executed.metadata)
    assert executed.to_dict()["sections"]


def test_a_condition_the_route_never_receives_is_still_caught():
    """The tolerance must not swallow a genuinely absent or changed threshold."""
    parsed = parse_query("Jokic over 25 points and over 10 rebounds")
    kwargs = dict(parsed["route_kwargs"])

    # Threshold deleted.
    kwargs["conditions"] = [c for c in kwargs["conditions"] if c["stat"] != "reb"]
    assert not authorize_compound_event_route(parsed, "player_game_finder", kwargs).authorized

    # Threshold changed beyond the strict-inequality epsilon.
    changed = dict(parsed["route_kwargs"])
    changed["conditions"] = [
        {**c, "min_value": 40.0} if c["stat"] == "reb" else c for c in changed["conditions"]
    ]
    assert not authorize_compound_event_route(parsed, "player_game_finder", changed).authorized


def test_phase_1a_multiple_metric_refusal_is_untouched():
    executed = execute_natural_query("points and rebounds leaders")

    assert _blockers(executed.metadata) == ["leaderboard_multiple_metrics_unsupported"]
    assert executed.metadata.get("requested_metrics") == ["pts", "reb"]
    _no_answer_was_returned(executed)


# ---------------------------------------------------------------------------
# 8. The invariant itself - ranking key is not an event condition
# ---------------------------------------------------------------------------


def test_occurrence_count_column_is_read_as_the_condition_it_encodes():
    assert occurrence_count_column_condition("games_30p") == _condition("pts", 30.0)
    assert occurrence_count_column_condition("games_10r") == _condition("reb", 10.0)
    assert occurrence_count_column_condition("pts") is None
    assert occurrence_count_column_condition(None) is None


def test_ranking_key_names_what_the_route_orders_by():
    assert ranking_key("team_occurrence_leaders", {"conditions": [_condition("pts", 120.0)]}) == (
        "occurrence_count"
    )
    assert ranking_key("season_leaders", {"stat": "games_30p"}) == "occurrence_count"
    assert ranking_key("season_leaders", {"stat": "pts"}) == "season_aggregate"
    assert ranking_key("top_player_games", {"stat": "pts"}) == "single_game"


def test_season_aggregate_route_executes_no_game_level_condition():
    """The heart of the base defect, stated directly.

    A season leaderboard's unit of execution is a season, so a "15+ threes"
    *game* condition cannot run there. Applying it to the season average is a
    different question with a plausible answer.
    """
    assert executed_event_conditions("season_team_leaders", {"stat": "fg3m", "min_value": 15}) == ()
    # Except an occurrence-count column, whose definition is a condition.
    assert executed_event_conditions("season_leaders", {"stat": "games_30p"}) == (
        _condition("pts", 30.0),
    )


def test_a_named_metric_outside_every_condition_is_a_ranking_request():
    parsed = parse_query(EFFICIENT_QUERY)

    # The metric boundary's own scan drops "efficient" because a number follows
    # it; this scan is what recovers the discarded ranking metric.
    assert "ts_pct" in named_metrics(parsed)


# ---------------------------------------------------------------------------
# 9. Mutation coverage - each of these is a way to lose part of the question
# ---------------------------------------------------------------------------


def test_dropping_one_of_two_conditions_is_refused():
    """Mutation: the route receives only one of the two stated thresholds."""
    parsed = parse_query(TEAM_COMPOUND_QUERY)
    mutated = dict(parsed["route_kwargs"])
    mutated["conditions"] = [_condition("fg3m", 15.0)]

    decision = authorize_compound_event_route(parsed, "team_occurrence_leaders", mutated)

    assert not decision.authorized
    assert decision.reason == COMPOUND_EVENT_UNEXECUTABLE
    # The refusal still carries both, not the surviving one.
    assert decision.requested_event_conditions == (
        _condition("pts", 120.0),
        _condition("fg3m", 15.0),
    )


def test_swapping_the_occurrence_route_for_a_season_leaderboard_is_refused():
    """Mutation: the exact substitution the base made."""
    parsed = parse_query(TEAM_COMPOUND_QUERY)

    decision = authorize_compound_event_route(
        parsed, "season_team_leaders", {"stat": "fg3m", "min_value": 15.0}
    )

    assert not decision.authorized
    assert decision.reason == COMPOUND_EVENT_UNEXECUTABLE


def test_promoting_a_condition_metric_into_the_ranking_slot_is_refused():
    """Mutation: the last threshold metric becomes the ranking key."""
    parsed = parse_query(TEAM_COMPOUND_QUERY)
    mutated = dict(parsed["route_kwargs"])
    mutated["stat"] = "fg3m"

    decision = authorize_compound_event_route(parsed, "team_occurrence_leaders", mutated)

    assert not decision.authorized
    assert decision.requested_stat == "fg3m"


def test_discarding_the_date_scope_is_visible_in_the_executed_kwargs():
    """Mutation: the since-2020 window never reaches the route."""
    parsed = parse_query(TEAM_COMPOUND_QUERY)

    assert parsed["route_kwargs"]["start_season"] == "2020-21"


def test_removing_the_absence_clause_from_authorization_is_refused():
    """Mutation: the route is allowed to answer with the absence dropped.

    The parse is taken before the router clears the unapplied absence, because
    that clearing is downstream of the decision under test - authorization has
    to see the clause the question stated.
    """
    parsed = dict(parse_query("most 40 point games while LeBron was out"))
    parsed["without_player"] = "LeBron James"

    decision = authorize_compound_event_route(
        parsed, "player_occurrence_leaders", {"stat": "pts", "min_value": 40.0}
    )

    assert not decision.authorized
    assert decision.unsupported_availability == {"without_player": "LeBron James"}
    # The event condition survives the refusal alongside the absence.
    assert decision.requested_event_conditions == (_condition("pts", 40.0),)


def test_occurrence_leaderboard_with_an_absence_refuses_end_to_end():
    executed = execute_natural_query("most 40 point games while LeBron was out")

    assert executed.result_status != "ok"
    _no_answer_was_returned(executed)
    assert executed.metadata.get("unsupported_availability") == {"without_player": "LeBron James"}
    assert executed.metadata.get("requested_event_conditions") == [_condition("pts", 40.0)]


def test_authorization_rejection_admits_no_fallback_route():
    """Every refused priority query returns an empty result, not a smaller one."""
    for query in (EFFICIENT_QUERY, TWO_THRESHOLD_QUERY, INJURY_QUERY, TEAM_SCORER_QUERY):
        executed = execute_natural_query(query)
        assert executed.to_dict()["sections"] == {}, query
        assert executed.metadata.get("stat") is None, query
        assert not executed.metadata.get("applied_filters"), query


def test_every_compound_refusal_carries_human_wording():
    """Blocker ids are backend vocabulary; a refusal must also say why in words.

    The repository's existing contract is that the execution layer appends one
    id-bearing note for *every* blocker, and the frontend suppresses that entry
    for boundary ids while rendering its own copy. What this pins is the half
    that has to be true here: a human-worded reason exists and does not name the
    id. The suppression half is pinned in the frontend suite, which keeps
    ``LEADERBOARD_BOUNDARY_IDS`` in sync with this module.
    """
    for query in (EFFICIENT_QUERY, TWO_THRESHOLD_QUERY, INJURY_QUERY):
        notes = execute_natural_query(query).metadata.get("notes") or []
        human = [
            note
            for note in notes
            if note.startswith("unsupported_boundary:") and COMPOUND_EVENT_UNEXECUTABLE not in note
        ]
        assert human, query
