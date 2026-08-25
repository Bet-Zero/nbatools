"""Normalized parse state for the meaningful conditions a question asks for.

The first attempt at intent preservation asked three regexes whether a query
looked unanswerable, and let the answer decide whether a broad default could
fire. That made the regexes the safety boundary, so every paraphrase they did
not happen to spell escaped: ``best team when leading scorer is suspended`` and
``teams that do best shorthanded`` still came back as a league points-per-game
leaderboard.

The boundary here is parse state instead. Detectors normalize surface language
into :class:`RequestedCondition` records, and routing decides using the records.
A detector that misses a phrase now loses coverage of one concept; it can no
longer silently authorize a broad default, because the default asks the ledger
"is every condition accounted for?" rather than asking a regex "did you match?".

Vocabulary lives in the frozensets below and the grammar is composed from them,
so extending a concept is a data change. Adding a *new* concept means adding a
detector and declaring which routes can represent it - not adding another
special case to the router.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Condition kinds
# ---------------------------------------------------------------------------

#: A player being absent, unavailable, or unable to play.
PLAYER_AVAILABILITY = "player_availability"
#: A player referred to by the role they fill rather than by name.
ROLE_REFERENCE = "role_reference"
#: A judgement about performance with no metric defined for it.
SUBJECTIVE_OUTCOME = "subjective_outcome"

#: Marker id reported in ``unsupported_filters`` for each kind.
CONDITION_BLOCKER_IDS = {
    PLAYER_AVAILABILITY: "unresolved_availability",
    ROLE_REFERENCE: "unresolved_role_player",
    SUBJECTIVE_OUTCOME: "subjective_outcome",
}


@dataclass(frozen=True)
class RequestedCondition:
    """One meaningful condition the user asked for.

    Carries enough to answer, at any later point in routing or execution:
    what was requested, did it resolve, and to what.
    """

    kind: str
    #: The words the user actually wrote, for explaining the refusal back.
    surface: str
    #: What the condition resolved to, when anything did.
    binding: str | None = None

    @property
    def is_bound(self) -> bool:
        return self.binding is not None

    @property
    def blocker_id(self) -> str:
        return CONDITION_BLOCKER_IDS.get(self.kind, self.kind)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "kind": self.kind,
            "surface": self.surface,
            "binding": self.binding,
            "status": "bound" if self.is_bound else "unresolved",
        }


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

# Words that describe a player (or a team's players) being unavailable. These
# are states, not verbs: they appear as "is injured", "while depleted",
# "when shorthanded".
_ABSENCE_STATES = (
    "injured",
    "injuries",
    "injury",
    "hurt",
    "suspended",
    "suspension",
    "sidelined",
    "unavailable",
    "inactive",
    "absent",
    "absence",
    "shorthanded",
    "short-handed",
    "short handed",
    "undermanned",
    "depleted",
    "banged up",
    "load managed",
    "load management",
    "in street clothes",
    "ruled out",
)

# Verb phrases for not playing. Written as alternatives rather than one
# hand-tuned pattern so a new phrasing is one more tuple entry.
_ABSENCE_VERB_PHRASES = (
    r"do(?:es)?\s+n[o']?t\s+play",
    r"did\s+n[o']?t\s+play",
    r"(?:can|could|will|would)\s*n[o']?t\s+play",
    r"(?:is|are|was|were|been|being|get|gets|got|go|goes|went)\s+(?:out|down|hurt)",
    r"miss(?:es|ed|ing)?\s+(?:time|games?|action|the\s+game)",
    r"(?:sits?|sat|sitting)\s+out",
    r"out\s+(?:with|due|for\s+the|of\s+the\s+(?:lineup|game))",
    r"rul(?:ed|ing)\s+out",
    r"held\s+out",
)

# Prepositions that introduce who is missing.
_ABSENCE_PREPOSITIONS = ("without", r"w/o", "minus", "lacking", "sans", "missing", "short of")

# Nouns naming a player by the role they fill.
_ROLE_NOUNS = (
    "scorer",
    "player",
    "star",
    "starter",
    "guy",
    "man",
    "option",
    "weapon",
    "producer",
    "contributor",
)

# Qualifiers that pick out which role holder is meant.
_ROLE_QUALIFIERS = (
    "leading",
    "lead",
    "top",
    "best",
    "number\\s+one",
    r"no\.?\s*1",
    "franchise",
    "go-to",
    "go\\s+to",
    "primary",
    "main",
)

# Determiners that make a role phrase point at one specific unidentified player
# belonging to some other entity. The definite article is deliberately absent:
# "the top scorer this season" is the league-wide ranking itself, which the
# leaderboard routes answer, while "its top scorer" is a dangling reference.
_POSSESSIVE_DETERMINERS = ("its", "their", "his", "her", "the team's", "each team's")

# Verbs describing how well someone coped, with no metric defined for any of
# them. Plain superlatives ("best offensive teams") are not in this family -
# those name a metric and stay supported.
_SUBJECTIVE_OUTCOME_PHRASES = (
    r"(?:stay|stays|stayed|staying|keep|keeps|keeping|kept|remain|remains|remained)\s+afloat",
    r"(?:stay|stays|stayed|staying|remain|remains|remained)\s+competitive",
    r"cope[sd]?|coping",
    r"surviv\w+",
    r"(?:hold|holds|holding)\s+up|held\s+up",
    r"(?:hang|hangs|hanging)\s+on|hung\s+on",
    r"(?:get|gets|getting)\s+by|got\s+by",
    r"(?:weather|weathers|weathered)\s+(?:the|it)",
    r"withstand\w*|withstood",
    r"fares?|fared|faring",
    r"manag(?:e|es|ed|ing)\s+(?:best|without|well)",
    r"(?:tread|treads|treading)\s+water",
)


def _alternation(terms: tuple[str, ...]) -> str:
    return "|".join(terms)


_ROLE_NOUN_GROUP = rf"(?:{_alternation(_ROLE_NOUNS)})s?"
_ROLE_QUALIFIER_GROUP = rf"(?:{_alternation(_ROLE_QUALIFIERS)})"

# 1. Availability. Three independent grammars, any of which means the question
#    depends on somebody not playing.
_AVAILABILITY_PATTERNS = (
    # "is injured", "while depleted", "when shorthanded"
    re.compile(rf"\b(?:{_alternation(tuple(re.escape(t) for t in _ABSENCE_STATES))})\b"),
    # "does not play", "sits out", "misses time"
    re.compile(rf"\b(?:{_alternation(_ABSENCE_VERB_PHRASES)})"),
    # "without their leading scorer", "missing starters", "with no stars"
    re.compile(
        rf"\b(?:{_alternation(_ABSENCE_PREPOSITIONS)})"
        rf"\s+(?:(?:{_ROLE_QUALIFIER_GROUP}|any|all|its|their|his|her|the)\s+)*"
        rf"{_ROLE_NOUN_GROUP}\b"
    ),
    re.compile(rf"\bwith\s+no\s+(?:{_ROLE_QUALIFIER_GROUP}\s+)?{_ROLE_NOUN_GROUP}\b"),
    # "without its leading scorer" where the noun is a name-shaped placeholder
    re.compile(
        rf"\b(?:{_alternation(_ABSENCE_PREPOSITIONS)})\s+(?:its|their|his|her)\b",
    ),
)

# 2. Role reference. A possessive determiner pointing at one unidentified
#    player, or the inherently subjective "best player".
_ROLE_REFERENCE_PATTERNS = (
    re.compile(
        rf"\b(?:{_alternation(_POSSESSIVE_DETERMINERS)})"
        rf"\s+(?:{_ROLE_QUALIFIER_GROUP}\s+)?{_ROLE_NOUN_GROUP}\b"
    ),
    re.compile(r"\bbest\s+players?\b"),
)

# 3. Subjective outcome.
_SUBJECTIVE_OUTCOME_PATTERN = re.compile(rf"\b(?:{_alternation(_SUBJECTIVE_OUTCOME_PHRASES)})\b")


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def _first_match(patterns: tuple[re.Pattern[str], ...], text: str) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(0).strip()
    return None


def detect_requested_conditions(
    text: str,
    *,
    with_player: str | None = None,
    without_player: str | None = None,
) -> list[RequestedCondition]:
    """Normalize *text* into the meaningful conditions it asks for.

    ``with_player`` / ``without_player`` are the parser's availability bindings.
    A detected availability concept is recorded either way - the record is what
    later phases reason about - but it carries the binding when one exists, so
    "Lakers record without LeBron" is a *bound* availability condition while
    "teams that cope best without their leading scorer" is an unresolved one.
    """
    conditions: list[RequestedCondition] = []

    availability_surface = _first_match(_AVAILABILITY_PATTERNS, text)
    binding = without_player or with_player
    if availability_surface or binding:
        conditions.append(
            RequestedCondition(
                kind=PLAYER_AVAILABILITY,
                surface=availability_surface or (binding or ""),
                binding=binding,
            )
        )

    role_surface = _first_match(_ROLE_REFERENCE_PATTERNS, text)
    if role_surface:
        conditions.append(RequestedCondition(kind=ROLE_REFERENCE, surface=role_surface))

    subjective = _SUBJECTIVE_OUTCOME_PATTERN.search(text)
    if subjective:
        conditions.append(
            RequestedCondition(kind=SUBJECTIVE_OUTCOME, surface=subjective.group(0).strip())
        )

    return conditions


# ---------------------------------------------------------------------------
# Route capability
# ---------------------------------------------------------------------------

# What each route can actually represent *and execute*. A kind absent from a
# route's set means that route has no way to express the condition, so letting
# it answer would delete the condition from the question.
#
# Deliberately narrow: only team_record executes whole-game availability, and
# only for a resolved player. Everything else - including every leaderboard
# route a broad default can pick - represents none of these kinds.
ROUTE_CONDITION_SUPPORT: dict[str, frozenset[str]] = {
    "team_record": frozenset({PLAYER_AVAILABILITY}),
}

#: Routes a broad default may select. They rank the league by one metric and can
#: represent none of the condition kinds above.
BROAD_DEFAULT_ROUTES = frozenset({"season_leaders", "season_team_leaders"})


def unconsumed_conditions(
    conditions: list[RequestedCondition],
    route: str | None,
) -> list[RequestedCondition]:
    """Conditions *route* can neither represent nor execute.

    A condition is consumed when the route supports its kind *and* the condition
    actually bound to something. An unbound condition is never consumed: a route
    that filters by "games without LeBron" still cannot filter by "games without
    whoever their leading scorer is".
    """
    supported = ROUTE_CONDITION_SUPPORT.get(route or "", frozenset())
    return [
        condition
        for condition in conditions
        if condition.kind not in supported or not condition.is_bound
    ]


def blocker_ids(conditions: list[RequestedCondition]) -> list[str]:
    """Stable ``unsupported_filters`` markers for *conditions*, order preserved."""
    ids: list[str] = []
    for condition in conditions:
        marker = condition.blocker_id
        if marker not in ids:
            ids.append(marker)
    return ids
