"""Positive authorization for the subject-less broad defaults.

A broad default answers a question the user did not fully ask: with no player
and no team to anchor on, ``top scorers this season`` becomes a league-wide
points leaderboard. That is a good default when the leaderboard really is the
question. It is a wrong answer when the question said something the leaderboard
cannot say - ``best team while down two starters`` is not answered by ranking
every team's points per game.

The previous attempt asked detectors whether the query looked unanswerable and
let a *negative* answer authorize the default::

    if no unsupported condition was detected:
        return the leaderboard

That is fail-open by construction. Every phrase the detectors did not happen to
spell - ``at less than full strength``, ``missing half its rotation``, ``when
the rotation is thin`` - produced no detection, and no detection was read as
permission. Moving the detections into a dataclass did not change the direction
of the inference.

This module inverts it. The default is not "allowed unless blocked"; it is
"refused unless proven". Proof is span coverage: every content-bearing word in
the query must be *claimed* by a component the league-wide leaderboard actually
implements -

    ranking intent, sort direction, population, requested metric,
    time/season window, a supported qualifier, or benign grammar

- and anything left over is meaningful residual the leaderboard would silently
drop. Residual refuses.

The safety property follows from the direction of the claim, not from the size
of any word list. A claimer only claims text when the corresponding parse slot
actually resolved, so an unrecognized phrase produces *no claim*, which leaves
residual, which refuses. Vocabulary gaps here cost coverage of legitimate
questions. They cannot manufacture permission, which is what a blacklist gap
did.

:mod:`nbatools.commands._condition_semantics` still runs, and its
:class:`RequestedCondition` records still sharpen the refusal copy and the
blocker id. They are additive evidence about *why* a query is unanswerable.
Their absence proves nothing and authorizes nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from nbatools.commands._condition_semantics import (
    RequestedCondition,
    blocker_ids,
    unconsumed_conditions,
)
from nbatools.commands._constants import STAT_ALIASES
from nbatools.commands._leaderboard_utils import (
    LEADERBOARD_STAT_ALIASES,
    TEAM_LEADERBOARD_STAT_ALIASES,
)
from nbatools.commands.entity_resolution import TEAM_ALIASES

# ---------------------------------------------------------------------------
# Components a league-wide leaderboard can actually represent
# ---------------------------------------------------------------------------

RANKING_INTENT = "ranking_intent"
SORT_DIRECTION = "sort_direction"
POPULATION = "population"
METRIC = "metric"
TIME_WINDOW = "time_window"
QUALIFIER = "qualifier"
GRAMMAR = "grammar"

#: Every component that may account for query content. Anything a claimer here
#: does not cover is residual, and residual refuses.
AUTHORIZED_COMPONENTS = (
    RANKING_INTENT,
    SORT_DIRECTION,
    POPULATION,
    METRIC,
    TIME_WINDOW,
    QUALIFIER,
    GRAMMAR,
)

# Why authorization failed. Stable ids - the frontend and the QA corpus key off
# them, and they are reported in metadata so a refusal can be explained.
RESIDUAL_CONTENT = "residual_query_content"
UNCONSUMED_CONDITION = "unconsumed_condition"


@dataclass(frozen=True)
class _Span:
    start: int
    end: int
    component: str
    surface: str


@dataclass(frozen=True)
class BroadDefaultAuthorization:
    """Whether a league-wide leaderboard may answer this question, and why.

    ``authorized`` is true only when every content-bearing span of the query is
    accounted for by :data:`AUTHORIZED_COMPONENTS`. It is never true merely
    because no negative detector matched.
    """

    authorized: bool
    #: component -> the surfaces it accounted for, in query order.
    accounted: dict[str, list[str]] = field(default_factory=dict)
    #: Content-bearing words no component could account for.
    residual: list[str] = field(default_factory=list)
    #: The metric the leaderboard would rank by, when one is anchored.
    metric: str | None = None
    #: The words the metric was read from, when it is anchored to the request.
    metric_anchor: str | None = None
    #: Metric aliases found only inside an unresolved condition. Recorded, never
    #: promoted: "scorer" in "when its leading scorer was out" is part of the
    #: condition, not a request to rank the league by scoring.
    nested_metric_evidence: tuple[str, ...] = ()
    #: Stable reason id when ``authorized`` is false.
    reason: str | None = None
    #: Normalized conditions the leaderboard cannot express, when any.
    unconsumed: tuple[RequestedCondition, ...] = ()

    @property
    def blocker_ids(self) -> list[str]:
        """``unsupported_filters`` markers explaining the refusal."""
        if self.authorized:
            return []
        if self.unconsumed:
            return blocker_ids(list(self.unconsumed))
        return [self.reason or RESIDUAL_CONTENT]

    def to_dict(self) -> dict[str, Any]:
        return {
            "authorized": self.authorized,
            "reason": self.reason,
            "accounted": {k: list(v) for k, v in self.accounted.items()},
            "residual": list(self.residual),
            "metric": self.metric,
            "metric_anchor": self.metric_anchor,
            "nested_metric_evidence": list(self.nested_metric_evidence),
            "unconsumed_conditions": [c.to_dict() for c in self.unconsumed],
        }


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------

# Content-bearing tokens. Keeps "%", "+", ".", "-" and "/" inside a token so
# "ts%", "30+", ".500", "2023-24" and "w/l" stay whole.
_TOKEN = re.compile(r"[a-z0-9][a-z0-9'%+./-]*")

# Closed-class words with no basketball meaning. Deliberately excludes anything
# that could carry a condition: "without", "missing", "minus", "out", "sans",
# "despite", "while", "when", "down" and "short" are all absent, so a query
# built from them cannot be filled in by grammar.
_GRAMMAR_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "in",
        "on",
        "at",
        "for",
        "to",
        "and",
        "or",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "am",
        "has",
        "have",
        "had",
        "do",
        "does",
        "did",
        "this",
        "that",
        "these",
        "those",
        "there",
        "it",
        "its",
        "they",
        "them",
        "their",
        "he",
        "she",
        "his",
        "her",
        "him",
        "we",
        "our",
        "you",
        "your",
        "i",
        "my",
        "me",
        "s",
        "per",
        "by",
        "with",
        "from",
        "as",
        "than",
        "so",
        "just",
        "really",
        "actually",
        "please",
        "currently",
        "ever",
        "still",
        "any",
        "each",
        "every",
        "some",
        "all",
        "both",
        "up",
        "into",
        "about",
        "been",
        "having",
        "getting",
        "among",
        "amongst",
        "total",
        "overall",
        "combined",
    }
)


def _tokens(text: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group(0)) for m in _TOKEN.finditer(text)]


def _claim(patterns: tuple[str, ...], text: str, component: str) -> list[_Span]:
    spans: list[_Span] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            surface = match.group(0).strip()
            if surface:
                spans.append(_Span(match.start(), match.end(), component, surface))
    return spans


# ---------------------------------------------------------------------------
# Component vocabularies
#
# These are *whitelists of the supported*, which is the safe direction: a gap
# withholds authorization instead of granting it.
# ---------------------------------------------------------------------------

# 1. Ranking intent - the leaderboard's own interrogative grammar.
_RANKING_PATTERNS = (
    # Longest alternative first: Python's alternation is leftmost-first, so
    # "who" listed before "who's" would claim only three of the five characters
    # and leave the token itself uncovered.
    r"\b(?:who's|whos|who|which|whose|what)\b",
    r"\b(?:leaders?|leads?|leading|led|rank(?:s|ed|ing|ings)?|standings)\b",
    r"\b(?:number\s+one|no\.?\s*1)\b",
    r"\b(?:show|list|give|tell|find|display)\b",
    r"\b(?:averages?|averaged|averaging|scores?|scored|scoring|shoots?|shot|shooting"
    r"|rebounds?|rebounded|rebounding|played|plays?|makes?|made|making|gets?|got"
    r"|puts?\s+up|posts?|posted|puts?|dishes|dished|grabs?|grabbed)\b",
)

# 2. Sort direction.
_SORT_PATTERNS = (
    r"\b(?:top|best|worst|highest|lowest|most|fewest|least|greatest|biggest|bottom|elite)\b",
)

# 3. Population being ranked.
_POPULATION_PATTERNS = (
    r"\b(?:players?|teams?|nba|league|league-?wide)\b",
    # The unit a leaderboard counts over. "games" carries no condition on its
    # own - "30 point games" is already a metric alias, and a phrase like
    # "missing half its rotation" is not rescued by it.
    r"\bgames?\b",
)

# 4. Time / season / window. Each group is gated on the parse slot it explains,
#    so wording the parser did not actually resolve stays residual.
_SEASON_PATTERNS = (
    r"\b(?:this|current|the\s+current)\s+(?:season|year|yr|campaign)\b",
    r"\b(?:last|past|previous)\s+(?:season|year)\b",
    r"\b(?:over|in|during|across|for)?\s*(?:the\s+)?(?:last|past|previous)\s+"
    r"(?:\d+|two|three|four|five|six|seven|eight|nine|ten)\s+(?:seasons?|years?)\b",
    r"\b\d{4}\s*-\s*\d{2,4}\b",
    r"\b(?:in|for|during|from)\s+\d{4}\b",
    r"\bsince\s+\d{4}\b",
    r"\bso\s+far\b",
    r"\bthis\s+season\b",
    r"\ball[-\s]?time\b",
    r"\bcareer\b",
    r"\bever\b",
    r"\bright\s+now\b",
    r"\bthis\s+far\b",
    r"\bto\s+date\b",
    # The bare scope noun, as in "season leaders in assists for 2023-24". It
    # names the window the parser already resolved and carries nothing else.
    r"\b(?:seasons?|years?)\b",
)
_SEASON_TYPE_PATTERNS = (
    r"\bregular\s+season\b",
    r"\bplayoffs?\b",
    r"\bpostseason\b",
    r"\bpreseason\b",
    r"\bplay-?in\b",
)
_LAST_N_PATTERNS = (
    r"\b(?:over|in|during|across)?\s*(?:the\s+)?(?:his|her|their|its)?\s*"
    r"(?:last|past|previous|recent)\s+\d+\s*(?:games?)?\b",
    r"\b(?:last|past|previous|recent)\s+"
    r"(?:two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty)\s*(?:games?)?\b",
    r"\b(?:recently|lately|right\s+now|of\s+late)\b",
    r"\brecent\s+form\b",
)
_DATE_PATTERNS = (
    # The trailing \b on the day keeps "january 2024" from being read as
    # "january 20" plus a stranded "24"; the day group then declines and the
    # year group claims the whole token.
    r"\b(?:january|february|march|april|may|june|july|august|september|october"
    r"|november|december)\b(?:\s+\d{1,2}(?:st|nd|rd|th)?\b)?(?:,?\s*\d{4}\b)?",
    r"\b(?:jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec)\.?\s+\d{1,2}\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b(?:since|before|after|through|until|from)\b",
    r"\b(?:last\s+night|yesterday|today|tonight|this\s+week|this\s+month)\b",
    r"\b(?:over|in|during|across)?\s*(?:the\s+)?(?:last|past)\s+"
    r"(?:month|week|fortnight|\d+\s+(?:weeks?|days?|months?))\b",
    r"\ball[-\s]?star\s+break\b",
    r"\brecently\b",
    r"\blately\b",
)

# 5. Qualifiers the leaderboard routes execute, keyed to the slot that proves
#    the parser resolved them.
_OPPONENT_QUALITY_PATTERNS = (
    r"\b(?:against|vs\.?|versus)\s+(?:the\s+)?(?:top|bottom)[-\s]?\d*\s*"
    r"(?:defenses?|defences?|offenses?|teams?|opponents?)?\b",
    r"\b(?:against|vs\.?|versus)\s+(?:good|great|elite|bad|weak|poor|winning|losing"
    r"|playoff|contending|quality|tough)\s+(?:teams?|defenses?|offenses?|opponents?)?\b",
    r"\b(?:against|vs\.?|versus)\s+(?:contenders?|playoff\s+teams?|winning\s+teams?)\b",
    r"\bteams?\s+(?:over|above|under|below)\s*\.?\d+\b",
    r"\b(?:top|bottom)[-\s]?\d+\s+(?:defenses?|offenses?|teams?)\b",
    r"\bcontenders?\b",
    # The slot is resolved, so the comparison preposition itself is accounted
    # for; without this "vs teams over .500" leaves "vs" behind as residual.
    r"\b(?:against|vs\.?|versus)\b",
)
_CLUTCH_PATTERNS = (r"\bclutch\b", r"\bcrunch[-\s]?time\b")
_PERIOD_PATTERNS = (
    r"\b(?:1st|2nd|3rd|4th|first|second|third|fourth)\s+(?:quarter|qtr|period)\b",
    r"\bq[1-4]\b",
    r"\b(?:1st|2nd|first|second)\s+half\b",
)
_HOME_AWAY_PATTERNS = (
    r"\bat\s+home\b",
    r"\bhome\s+games?\b",
    r"\bon\s+the\s+road\b",
    r"\broad\s+games?\b",
    r"\baway\s+(?:games?|from\s+home)\b",
)
_OUTCOME_PATTERNS = (
    r"\bin\s+(?:wins|losses|victories|defeats)\b",
    r"\bwhen\s+(?:winning|losing)\b",
)
# Longest alternative first: "bigs?" listed before "big men" would claim only
# "big" and strand "men" as residual.
_POSITION_PATTERNS = (
    r"\b(?:point\s+guards?|shooting\s+guards?|small\s+forwards?|power\s+forwards?"
    r"|big\s+m[ae]n|wing\s+players?|guards?|forwards?|centers?|wings?|bigs?)\b",
)
_MIN_GAMES_PATTERNS = (
    r"\b(?:at\s+least|minimum(?:\s+of)?|min\.?)\s+\d+\s+games?\b",
    r"\bwith\s+\d+\+?\s+games?\b",
)
_TOP_N_PATTERNS = (r"\btop\s+\d+\b", r"\bbottom\s+\d+\b", r"\b\d+\s+best\b", r"\bfirst\s+\d+\b")
_THRESHOLD_PATTERNS = (
    r"\b\d+\+",
    r"\b(?:at\s+least|over|more\s+than|above|under|less\s+than|below|fewer\s+than)\s+\d+\b",
    r"\b\d+\s+or\s+(?:more|fewer|less)\b",
    r"\bwith\s+\d+\b",
)
_ROLE_PATTERNS = (r"\b(?:starters?|starting\s+lineup|bench|reserves?|off\s+the\s+bench)\b",)
_SPECIAL_EVENT_PATTERNS = (
    r"\b(?:christmas|xmas|opening\s+night|nba\s+finals|finals|all[-\s]?star\s+game"
    r"|mlk\s+day|martin\s+luther\s+king)\b",
)
_BACK_TO_BACK_PATTERNS = (r"\bback[-\s]?to[-\s]?back\b", r"\bb2b\b")
_REST_PATTERNS = (
    r"\b(?:on|with|after)\s+(?:no|zero|one|two|three|four|five|\d+)\s*(?:days?\s+)?rest\b",
    r"\brest\s+(?:advantage|disadvantage)\b",
)
_ONE_POSSESSION_PATTERNS = (
    r"\bone[-\s]?possession(?:\s+games?)?\b",
    r"\bwithin\s+one\s+possession\b",
)
_NATIONAL_TV_PATTERNS = (
    r"\bnational(?:ly)?\s*(?:tv|televised)\b",
    r"\bon\s+(?:tnt|espn|abc|nbc)\b",
)
# The named opponent itself, drawn from the same alias table the resolver used.
# Claimed only when ``opponent`` actually resolved, so a team word the parser did
# not read as an opponent still counts as residual.
_TEAM_NAME_GROUP = "|".join(
    re.escape(alias) for alias in sorted(TEAM_ALIASES, key=len, reverse=True)
)
_OPPONENT_PATTERNS = (
    rf"(?<!\w)(?:{_TEAM_NAME_GROUP})(?!\w)",
    r"\b(?:against|vs\.?|versus)\b",
)

#: qualifier slot -> (parse keys that must be set, patterns it may then claim).
_QUALIFIER_CLAIMS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("opponent_quality", ("opponent_quality",), _OPPONENT_QUALITY_PATTERNS),
    ("clutch", ("clutch",), _CLUTCH_PATTERNS),
    ("period", ("quarter", "half"), _PERIOD_PATTERNS),
    ("location", ("home_only", "away_only"), _HOME_AWAY_PATTERNS),
    ("outcome", ("wins_only", "losses_only"), _OUTCOME_PATTERNS),
    ("position_filter", ("position_filter",), _POSITION_PATTERNS),
    ("min_games", ("min_games",), _MIN_GAMES_PATTERNS),
    ("limit", ("top_n",), _TOP_N_PATTERNS),
    ("threshold", ("min_value", "max_value"), _THRESHOLD_PATTERNS),
    ("role", ("role",), _ROLE_PATTERNS),
    ("special_event", ("special_event",), _SPECIAL_EVENT_PATTERNS),
    ("back_to_back", ("back_to_back",), _BACK_TO_BACK_PATTERNS),
    ("rest_days", ("rest_days",), _REST_PATTERNS),
    ("one_possession", ("one_possession",), _ONE_POSSESSION_PATTERNS),
    ("nationally_televised", ("nationally_televised",), _NATIONAL_TV_PATTERNS),
    ("opponent", ("opponent",), _OPPONENT_PATTERNS),
)


def _slot_set(parsed: dict, keys: tuple[str, ...]) -> bool:
    """True when the parser actually resolved one of *keys*.

    ``is not None`` rather than truthiness: ``rest_days=0`` ("on no rest") is a
    real request, and reading it as absent would let its wording fall through to
    residual and refuse a query the route can answer.
    """
    for key in keys:
        value = parsed.get(key)
        if value is None:
            continue
        if value is False:
            continue
        return True
    return False


# ---------------------------------------------------------------------------
# Metric anchoring
# ---------------------------------------------------------------------------


# The season-type qualifier is captured separately upstream, and
# ``_detect_leaderboard_stat`` strips it before matching so "best playoff
# offense" still reads as "best offense". Allowing the same optional gap
# between alias words keeps the span contiguous instead of leaving "offense"
# stranded as residual.
_ALIAS_GAP = r"\s+(?:(?:playoffs?|postseason)\s+)?"


def _alias_pattern(phrase: str) -> str:
    return rf"(?<!\w){_ALIAS_GAP.join(re.escape(word) for word in phrase.split())}(?!\w)"


def _metric_spans(text: str, aliases: dict[str, str]) -> list[tuple[int, int, str, str]]:
    """Every ``(start, end, stat, surface)`` a metric alias covers in *text*.

    Longest alias first so ``points per game`` claims the whole phrase rather
    than leaving ``per game`` behind as residual.
    """
    found: list[tuple[int, int, str, str]] = []
    for phrase in sorted(aliases, key=len, reverse=True):
        for match in re.finditer(_alias_pattern(phrase), text):
            found.append((match.start(), match.end(), aliases[phrase], match.group(0)))
    return found


def _metric_alias_table(team_scope: bool) -> dict[str, str]:
    """Metric vocabulary a leaderboard default can rank by, in route precedence.

    A team leaderboard reads ``detect_team_leaderboard_stat(q) or stat``, so the
    plain stat vocabulary is genuinely reachable there too: ``Which teams score
    the most points this season?`` resolves through ``STAT_ALIASES``. Coverage
    has to see the same tables the route does, or wording the route understands
    would be scored as residual and refused.
    """
    if team_scope:
        return {**STAT_ALIASES, **LEADERBOARD_STAT_ALIASES, **TEAM_LEADERBOARD_STAT_ALIASES}
    return {**STAT_ALIASES, **LEADERBOARD_STAT_ALIASES}


def _condition_spans(text: str, conditions: list[RequestedCondition]) -> list[tuple[int, int]]:
    """Character ranges the requested conditions occupy in *text*.

    A metric read from inside one of these is not a metric the user asked to
    rank by. ``when its leading scorer was out`` contains the word ``scorer``,
    which the alias table maps to ``pts`` - but the request there is about the
    scorer being *absent*, not about a league scoring leaderboard.
    """
    spans: list[tuple[int, int]] = []
    for condition in conditions:
        surface = (condition.surface or "").strip()
        if not surface:
            continue
        for match in re.finditer(re.escape(surface), text):
            spans.append((match.start(), match.end()))
    return spans


def _inside_any(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(r_start <= start and end <= r_end for r_start, r_end in ranges)


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def authorize_broad_default(
    parsed: dict,
    *,
    route: str,
    team_scope: bool,
) -> BroadDefaultAuthorization:
    """Decide whether *route* may answer this question as a broad default.

    Returns an authorization that is true only when every content-bearing span
    of the query is accounted for by a component the leaderboard implements.
    The absence of a negative detection is never sufficient.
    """
    text = parsed.get("normalized_query") or ""
    conditions = list(parsed.get("requested_conditions") or [])
    unconsumed = tuple(unconsumed_conditions(conditions, route))

    aliases = _metric_alias_table(team_scope)
    condition_ranges = _condition_spans(text, conditions)

    # -- metric anchoring ------------------------------------------------
    # Only a metric span outside every unresolved condition may become the
    # leaderboard's requested metric.
    anchored: list[tuple[int, int, str, str]] = []
    nested_only: list[tuple[int, int, str, str]] = []
    for span in _metric_spans(text, aliases):
        if _inside_any(span[0], span[1], condition_ranges):
            nested_only.append(span)
        else:
            anchored.append(span)

    metric = None
    metric_anchor = None
    if anchored:
        # Prefer the longest anchored alias: it is the most specific reading.
        best = max(anchored, key=lambda s: s[1] - s[0])
        metric, metric_anchor = best[2], best[3]

    # -- span claims -----------------------------------------------------
    spans: list[_Span] = []
    spans += _claim(_RANKING_PATTERNS, text, RANKING_INTENT)
    spans += _claim(_SORT_PATTERNS, text, SORT_DIRECTION)
    spans += _claim(_POPULATION_PATTERNS, text, POPULATION)

    for start, end, _stat, surface in anchored:
        spans.append(_Span(start, end, METRIC, surface))

    if _slot_set(parsed, ("season", "start_season", "end_season", "explicit_relative_season")):
        spans += _claim(_SEASON_PATTERNS, text, TIME_WINDOW)
    spans += _claim(_SEASON_TYPE_PATTERNS[:1], text, TIME_WINDOW)
    if str(parsed.get("season_type") or "").lower() != "regular season":
        spans += _claim(_SEASON_TYPE_PATTERNS[1:], text, TIME_WINDOW)
    if _slot_set(parsed, ("last_n",)):
        spans += _claim(_LAST_N_PATTERNS, text, TIME_WINDOW)
    if _slot_set(parsed, ("start_date", "end_date")):
        spans += _claim(_DATE_PATTERNS, text, TIME_WINDOW)

    for _slot, keys, patterns in _QUALIFIER_CLAIMS:
        if _slot_set(parsed, keys):
            spans += _claim(patterns, text, QUALIFIER)

    # -- residual --------------------------------------------------------
    accounted: dict[str, list[str]] = {}
    for span in spans:
        surfaces = accounted.setdefault(span.component, [])
        if span.surface not in surfaces:
            surfaces.append(span.surface)

    claimed = [(span.start, span.end) for span in spans]
    residual: list[str] = []
    for start, end, token in _tokens(text):
        if token in _GRAMMAR_WORDS:
            accounted.setdefault(GRAMMAR, [])
            if token not in accounted[GRAMMAR]:
                accounted[GRAMMAR].append(token)
            continue
        if _inside_any(start, end, claimed):
            continue
        residual.append(token)

    # -- decision --------------------------------------------------------
    # Ordered so the most specific explanation wins: a normalized condition
    # explains the refusal better than the raw words it is made of. A metric
    # that only appeared inside a condition needs no reason of its own - it was
    # never promoted, so its words are still sitting in ``residual``.
    if unconsumed:
        reason: str | None = UNCONSUMED_CONDITION
    elif residual:
        reason = RESIDUAL_CONTENT
    else:
        reason = None

    return BroadDefaultAuthorization(
        authorized=reason is None,
        accounted=accounted,
        residual=residual,
        metric=metric,
        metric_anchor=metric_anchor,
        nested_metric_evidence=tuple(dict.fromkeys(span[3] for span in nested_only)),
        reason=reason,
        unconsumed=unconsumed,
    )
