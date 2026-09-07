"""Compound event and filter routing integrity.

A stat-shaped question can carry four separable things at once, and a route that
reads only one of them answers a different question confidently:

===================  ====================================================
ranking key          what the results are ordered by
event conditions     what makes one game count toward the answer
filters              the scope: seasons, dates, teammate availability
residual             wording nothing above accounted for
===================  ====================================================

``teams with most games scoring 120+ and making 15+ threes since 2020`` means
*rank teams by how many games matched*, where a game matches when the team
scored 120 and made 15 threes, inside a since-2020 window. Its ranking key is a
count. Neither ``120`` nor ``15`` is the key - they are conditions - and the
last threshold the detectors happened to see is not a ranking metric. Reading it
as one produced a league three-pointers leaderboard that answered nobody's
question.

**The invariant this module enforces.** Before a compound or event-shaped
request is executed, every meaningful component of it must be *accounted for*,
which means exactly one of:

1. the chosen route actually executes it;
2. it defines that route's semantics (an occurrence route's ranking key *is*
   its event conditions);
3. it is named as unsupported in a refusal that returns no answer.

"The parser recognized it" is not on that list. A recognized component that
reached no route is the defect, not the evidence against it.

Deliberately narrow. This is not universal residual-clause protection for every
fixed-metric route - that is a separate project - and it interprets no vague
language. An unreadable request refuses; it never acquires a meaning here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Blocker id
# ---------------------------------------------------------------------------

#: A compound/event-shaped request the selected route cannot execute in full.
#: One id, not a taxonomy: what specifically could not run travels in the
#: refusal metadata (``requested_event_conditions``, ``requested_stat``,
#: ``unsupported_availability``) rather than in a family of ids. Backend and
#: test vocabulary only - never product copy.
COMPOUND_EVENT_UNEXECUTABLE = "compound_event_request_unexecutable"

#: Blockers raised here run no ranking and no finder, so a result carrying one
#: must publish no executed stat - the same guarantee the metric boundary makes.
COMPOUND_EVENT_BOUNDARY_FILTERS = frozenset({COMPOUND_EVENT_UNEXECUTABLE})


def is_compound_event_refusal(route_kwargs: dict | None) -> bool:
    """True when this route was blocked by the compound-event boundary."""
    if not isinstance(route_kwargs, dict):
        return False
    filters = route_kwargs.get("unsupported_filters") or []
    if isinstance(filters, str):
        filters = [filters]
    return any(f in COMPOUND_EVENT_BOUNDARY_FILTERS for f in filters)


# ---------------------------------------------------------------------------
# Route ranking keys
# ---------------------------------------------------------------------------

#: Routes whose ranking key is a count of matching games. The route supplies the
#: key; the query supplies the conditions being counted.
OCCURRENCE_COUNT_ROUTES = frozenset({"player_occurrence_leaders", "team_occurrence_leaders"})

#: Season-aggregate leaderboards. Their unit of execution is a whole season, so
#: a *game-level* condition cannot be executed on them at all: a "15+ threes"
#: game condition became a filter on the season average, which is a different
#: question with a plausible-looking answer.
SEASON_AGGREGATE_ROUTES = frozenset({"season_leaders", "season_team_leaders"})

#: Raw single-game rankings. One row is one game, so a game-level condition is
#: expressible, but the ranking key is still a single-game box-score metric.
SINGLE_GAME_RANKING_ROUTES = frozenset({"top_player_games", "top_team_games"})

#: Game-level finders. One row is one game.
GAME_FINDER_ROUTES = frozenset({"game_finder", "player_game_finder"})

#: Every route this boundary governs. Fixed-metric record, playoff, stretch,
#: lineup and decade routes are deliberately absent: whether they drop an extra
#: clause is a separate project.
GOVERNED_ROUTES = (
    OCCURRENCE_COUNT_ROUTES
    | SEASON_AGGREGATE_ROUTES
    | SINGLE_GAME_RANKING_ROUTES
    | GAME_FINDER_ROUTES
)

#: A season column that *is* an occurrence count: its name encodes the very
#: event condition being counted, so "30-point games" and ``games_30p`` are the
#: same statement rather than two competing metrics.
_OCCURRENCE_COUNT_COLUMN = re.compile(r"^games_(\d+)(p|r|a|s|b)$")

_COUNT_COLUMN_STAT = {"p": "pts", "r": "reb", "a": "ast", "s": "stl", "b": "blk"}


def occurrence_count_column_condition(stat: str | None) -> dict[str, Any] | None:
    """The event condition a ``games_30p``-style column already encodes."""
    if not isinstance(stat, str):
        return None
    match = _OCCURRENCE_COUNT_COLUMN.match(stat)
    if not match:
        return None
    mapped = _COUNT_COLUMN_STAT.get(match.group(2))
    if mapped is None:
        return None
    return {"stat": mapped, "min_value": float(match.group(1)), "max_value": None}


# ---------------------------------------------------------------------------
# Event conditions
# ---------------------------------------------------------------------------


def _normalize_condition(condition: Any) -> dict[str, Any] | None:
    """One condition as a comparable dict, or ``None`` if it is not one.

    ``special_event`` conditions (triple-double, double-double) carry no
    threshold and are compared by name.
    """
    if not isinstance(condition, dict):
        return None
    if condition.get("special_event"):
        return {"special_event": condition["special_event"]}
    stat = condition.get("stat")
    if not stat:
        return None
    min_value = condition.get("min_value")
    max_value = condition.get("max_value")
    if min_value is None and max_value is None:
        return None
    return {
        "stat": stat,
        "min_value": float(min_value) if min_value is not None else None,
        "max_value": float(max_value) if max_value is not None else None,
    }


def _dedupe(conditions: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    seen: list[dict[str, Any]] = []
    for condition in conditions:
        if condition not in seen:
            seen.append(condition)
    return tuple(seen)


#: How far an executed bound may sit from the stated one and still be the same
#: condition. "over 25 points" is stated as 25 and executed as 25.0001, because
#: a strict inequality is expressed by nudging the bound - that epsilon *is* the
#: correct executed form, not a changed threshold. One point of slack keeps the
#: two readings equal while still catching a genuinely different number.
_BOUND_TOLERANCE = 1.0


def _same_bound(declared: float | None, executed: float | None) -> bool:
    """Whether one side of a condition survived into execution unchanged."""
    if declared is None:
        return True
    if executed is None:
        return False
    return abs(float(executed) - float(declared)) <= _BOUND_TOLERANCE


def condition_is_executed(
    declared: dict[str, Any],
    executed: tuple[dict[str, Any], ...],
) -> bool:
    """Whether *declared* is applied by one of the *executed* conditions.

    Matched on stat, direction and value rather than dict equality: a strict
    inequality reaches execution as a nudged bound, and comparing those exactly
    reported ordinary working finder queries as having lost a threshold.
    """
    if declared.get("special_event"):
        return any(
            candidate.get("special_event") == declared["special_event"] for candidate in executed
        )
    for candidate in executed:
        if candidate.get("stat") != declared.get("stat"):
            continue
        if not _same_bound(declared.get("min_value"), candidate.get("min_value")):
            continue
        if not _same_bound(declared.get("max_value"), candidate.get("max_value")):
            continue
        return True
    return False


def declared_event_conditions(parsed: dict) -> tuple[dict[str, Any], ...]:
    """Every *game-level* condition the question states, in query order.

    Only the occurrence extractors' output counts. ``threshold_conditions`` is
    deliberately excluded: it is a season-aggregate threshold ("players
    averaging 25+ points"), a different and correctly executed thing. Conflating
    the two would refuse ordinary working leaderboards.
    """
    declared: list[dict[str, Any]] = []
    for condition in parsed.get("compound_occurrence_conditions") or []:
        normalized = _normalize_condition(condition)
        if normalized is not None:
            declared.append(normalized)
    single = _normalize_condition(parsed.get("occurrence_event"))
    if single is not None:
        declared.append(single)
    return _dedupe(declared)


def executed_event_conditions(route: str | None, route_kwargs: dict) -> tuple[dict[str, Any], ...]:
    """Every game-level condition the chosen route will actually apply."""
    executed: list[dict[str, Any]] = []

    if route in OCCURRENCE_COUNT_ROUTES:
        for condition in route_kwargs.get("conditions") or []:
            normalized = _normalize_condition(condition)
            if normalized is not None:
                executed.append(normalized)
        if route_kwargs.get("special_event"):
            executed.append({"special_event": route_kwargs["special_event"]})
        single = _normalize_condition(
            {
                "stat": route_kwargs.get("stat"),
                "min_value": route_kwargs.get("min_value"),
                "max_value": route_kwargs.get("max_value"),
            }
        )
        if single is not None:
            executed.append(single)
        return _dedupe(executed)

    if route in GAME_FINDER_ROUTES | SINGLE_GAME_RANKING_ROUTES:
        for condition in route_kwargs.get("conditions") or []:
            normalized = _normalize_condition(condition)
            if normalized is not None:
                executed.append(normalized)
        if route_kwargs.get("special_event"):
            executed.append({"special_event": route_kwargs["special_event"]})
        single = _normalize_condition(
            {
                "stat": route_kwargs.get("stat"),
                "min_value": route_kwargs.get("min_value"),
                "max_value": route_kwargs.get("max_value"),
            }
        )
        if single is not None:
            executed.append(single)
        return _dedupe(executed)

    if route in SEASON_AGGREGATE_ROUTES:
        # A season leaderboard executes no game-level condition. The single
        # exception is an occurrence-count column, whose definition *is* one
        # condition: ranking `games_30p` genuinely counts 30-point games.
        encoded = occurrence_count_column_condition(route_kwargs.get("stat"))
        return (encoded,) if encoded else ()

    return ()


# ---------------------------------------------------------------------------
# Named metrics
# ---------------------------------------------------------------------------


def named_metrics(parsed: dict) -> tuple[str, ...]:
    """Every metric the question's wording names, in query order.

    Longest alias first with overlapping spans skipped, so "most efficient" is
    one metric rather than a stray "efficient" inside something else. Unlike the
    metric boundary's own scan this keeps metrics that sit next to a number:
    that exclusion exists to stop "30 point games" reading as a points request,
    and here the count column is recognized directly instead - which leaves
    "most efficient 30-point games" with the metric the boundary's scan drops.
    """
    from nbatools.commands._constants import STAT_ALIASES
    from nbatools.commands._leaderboard_utils import (
        LEADERBOARD_STAT_ALIASES,
        TEAM_LEADERBOARD_STAT_ALIASES,
    )

    text = parsed.get("normalized_query") or ""
    aliases: dict[str, str] = {**STAT_ALIASES, **LEADERBOARD_STAT_ALIASES}
    if parsed.get("team_leaderboard_intent") or "team" in text:
        aliases = {**aliases, **TEAM_LEADERBOARD_STAT_ALIASES}

    claimed: list[tuple[int, int]] = []
    found: list[tuple[int, str]] = []
    for phrase in sorted(aliases, key=len, reverse=True):
        if phrase.split()[0] not in text:
            continue
        for match in re.finditer(rf"(?<!\w){re.escape(phrase)}(?!\w)", text):
            start, end = match.span()
            if any(start < c_end and c_start < end for c_start, c_end in claimed):
                continue
            claimed.append((start, end))
            found.append((start, aliases[phrase]))
    ordered: list[str] = []
    for _, stat in sorted(found):
        if stat not in ordered:
            ordered.append(stat)
    return tuple(ordered)


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

#: Availability *status* wording with no execution-backed data behind it. NBA
#: Tools carries no injury feed, so "while the player was injured" states a real
#: condition the product cannot apply. Recognizing the words is not interpreting
#: them: nothing here decides what counts as injured, and nothing infers it from
#: missed games. It exists so the clause is refused instead of dropped.
_UNSUPPORTED_AVAILABILITY_STATUS = (
    (r"\b(?:injured|injury|injuries|hurt)\b", "injury status"),
    (r"\b(?:load\s+management|rest(?:ing|ed)?\s+(?:game|games|night))\b", "rest status"),
    (r"\bhealthy\b", "health status"),
)


def unsupported_availability_status(parsed: dict) -> str | None:
    """The availability *status* this question conditions on, if unsupported.

    Returns a short label ("injury status") or ``None``. Says nothing about what
    the status means - only that the question asked to filter on one and the
    product has no data that could.
    """
    text = parsed.get("normalized_query") or ""
    for pattern, label in _UNSUPPORTED_AVAILABILITY_STATUS:
        if re.search(pattern, text):
            return label
    return None


# ---------------------------------------------------------------------------
# The decision
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompoundEventAuthorization:
    """Whether a compound/event route may execute, and what it would have lost.

    Carries no executed stat. Nothing ran, so what the question asked for
    travels in the ``requested_*`` fields instead - the same contract the metric
    boundary's refusals follow.
    """

    authorized: bool
    reason: str | None = None
    #: Every game-level condition the question stated, whole or not at all.
    requested_event_conditions: tuple[dict[str, Any], ...] = ()
    #: A ranking metric the question named that the chosen route cannot rank by.
    requested_stat: str | None = None
    #: The ranking this route would have produced instead, in plain words.
    unsupported_scope: str | None = None
    #: The availability condition the route cannot apply.
    unsupported_availability: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "authorized": self.authorized,
            "reason": self.reason,
            "requested_event_conditions": [dict(c) for c in self.requested_event_conditions],
            "requested_stat": self.requested_stat,
            "unsupported_scope": self.unsupported_scope,
            "unsupported_availability": dict(self.unsupported_availability),
        }


_AUTHORIZED = CompoundEventAuthorization(authorized=True)


def is_compound_event_request(parsed: dict, route: str | None, route_kwargs: dict) -> bool:
    """True when this request is the compound/event shape this boundary governs.

    A request qualifies when it states a game-level event condition, in either
    the query's own wording or the occurrence-count column a route resolved from
    it. Everything else is out of scope by design.
    """
    if route is not None and route not in GOVERNED_ROUTES:
        return False
    if declared_event_conditions(parsed):
        return True
    return occurrence_count_column_condition(route_kwargs.get("stat")) is not None


def authorize_compound_event_route(
    parsed: dict,
    route: str | None,
    route_kwargs: dict,
) -> CompoundEventAuthorization:
    """Whether *route* accounts for every meaningful part of a compound request.

    Checked in the order that gives the sharpest reason:

    1. every stated event condition is executed;
    2. no condition metric was promoted into the ranking-key slot;
    3. no named ranking metric was discarded;
    4. an availability condition is executed or refused.
    """
    if is_compound_event_refusal(route_kwargs):
        # Already refused on this boundary upstream; re-deciding would only
        # append the same note twice.
        return _AUTHORIZED
    if not is_compound_event_request(parsed, route, route_kwargs):
        return _AUTHORIZED

    declared = declared_event_conditions(parsed)
    executed = executed_event_conditions(route, route_kwargs)
    # Gathered up front so whichever check fires still carries every part of the
    # request the route would have dropped. A refusal that names one lost
    # component and quietly loses a second is the same defect one level down.
    availability = unexecuted_availability(parsed, route)
    scope = _ranking_description(route, route_kwargs)

    def refuse(*, requested_stat: str | None = None) -> CompoundEventAuthorization:
        return CompoundEventAuthorization(
            authorized=False,
            reason=COMPOUND_EVENT_UNEXECUTABLE,
            requested_event_conditions=declared,
            requested_stat=requested_stat,
            unsupported_scope=scope,
            unsupported_availability=availability,
        )

    # 1. A condition the route never received is a piece of the question that
    #    silently stopped existing.
    if any(not condition_is_executed(condition, executed) for condition in declared):
        return refuse()

    # 2. On a count route the ranking key is the count. A condition metric
    #    sitting in the ranking-stat slot alongside a conditions list means the
    #    route is about to order by a threshold rather than count matches.
    if route in OCCURRENCE_COUNT_ROUTES and route_kwargs.get("conditions"):
        if route_kwargs.get("stat"):
            return refuse(requested_stat=route_kwargs.get("stat"))

    # 3. A metric named outside every condition is a ranking key the question
    #    asked for. If the route ranks by something else, answering means
    #    dropping it.
    # Both sides count. A metric the question stated is accounted for, and so is
    # one the route actually filters on - a grouped boolean ("(A and B) or C")
    # executes a third condition the compound extractor never listed, and
    # reading only the stated side reported that third metric as discarded.
    accounted = {condition.get("stat") for condition in declared}
    accounted |= {condition.get("stat") for condition in executed}
    ranking_stat = route_kwargs.get("stat")
    if ranking_stat:
        accounted.add(ranking_stat)
        encoded = occurrence_count_column_condition(ranking_stat)
        if encoded:
            accounted.add(encoded["stat"])
    for metric in named_metrics(parsed):
        if metric in accounted:
            continue
        if occurrence_count_column_condition(metric):
            # A count column names the same event the conditions already state.
            continue
        return refuse(requested_stat=metric)

    # 4. An availability condition this route cannot apply.
    if availability:
        return refuse()

    return _AUTHORIZED


def unexecuted_availability(parsed: dict, route: str | None) -> dict[str, Any]:
    """The availability condition this route will not apply, if there is one.

    Whole-game teammate presence/absence is execution-backed on a small set of
    routes; availability *status* is backed nowhere, because the product holds
    no injury data.
    """
    from nbatools.commands.natural_query import (
        _WITH_PLAYER_SUPPORTED_ROUTES,
        _WITHOUT_PLAYER_SUPPORTED_ROUTES,
    )

    unexecuted: dict[str, Any] = {}
    if parsed.get("with_player") and route not in _WITH_PLAYER_SUPPORTED_ROUTES:
        unexecuted["with_player"] = parsed["with_player"]
    if parsed.get("without_player") and route not in _WITHOUT_PLAYER_SUPPORTED_ROUTES:
        unexecuted["without_player"] = parsed["without_player"]
    status = unsupported_availability_status(parsed)
    if status:
        unexecuted["condition"] = status
    return unexecuted


def ranking_key(route: str | None, route_kwargs: dict) -> str | None:
    """What the chosen route orders its rows by, as a stable machine label.

    Published so a consumer can tell "ranked by how many games matched" from
    "ranked by threes made" without inferring it from a stat field that, on a
    compound occurrence route, names a *condition* rather than the key.
    """
    if route in OCCURRENCE_COUNT_ROUTES:
        return "occurrence_count"
    if route in SEASON_AGGREGATE_ROUTES:
        if occurrence_count_column_condition(route_kwargs.get("stat")):
            return "occurrence_count"
        return "season_aggregate" if route_kwargs.get("stat") else None
    if route in SINGLE_GAME_RANKING_ROUTES:
        return "single_game"
    return None


def publishes_condition_metric_as_stat(route: str | None, route_kwargs: dict) -> bool:
    """True when this route's ``stat`` kwarg would name a condition, not the key.

    A compound occurrence route ranks by a count of matching games. Any stat
    reported alongside it is one of the conditions being counted, and reporting
    it as the answer's metric is the promotion this boundary exists to stop.
    """
    return bool(route in OCCURRENCE_COUNT_ROUTES and route_kwargs.get("conditions"))


def _ranking_description(route: str | None, route_kwargs: dict) -> str:
    """What this route would have ranked by, in the reader's words."""
    if route in OCCURRENCE_COUNT_ROUTES:
        return "a count of matching games"
    if route in SEASON_AGGREGATE_ROUTES:
        if occurrence_count_column_condition(route_kwargs.get("stat")):
            return "a count of matching games"
        return "a season leaderboard"
    if route in SINGLE_GAME_RANKING_ROUTES:
        return "a single-game ranking"
    if route in GAME_FINDER_ROUTES:
        return "a game list"
    return "this ranking"


# ---------------------------------------------------------------------------
# Compound requests that matched no route
# ---------------------------------------------------------------------------


def unrouted_compound_event_reason(parsed: dict) -> str | None:
    """Why a compound event request that matched no route cannot be answered.

    ``players with 25 points and 10 rebounds`` states two real conditions and
    then says nothing about what to do with them - count the games, average the
    season, list them. It used to surface as an unrouted error whose metadata
    still carried a stat, which reads as a partial answer to a question nothing
    executed.

    Answering it means choosing an aggregation the question never stated, so it
    refuses with both conditions intact instead. Deliberately narrow: it
    classifies the request and never works out what the user meant.
    """
    if len(declared_event_conditions(parsed)) < 2:
        return None
    return COMPOUND_EVENT_UNEXECUTABLE
