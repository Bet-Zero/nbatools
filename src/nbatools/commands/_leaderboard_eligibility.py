"""When a league-wide leaderboard is allowed to answer.

The bug: `best NBA teams this season` returned a team points-per-game
leaderboard. So did `best team while depleted`, `teams that cope best`, and
`NBA leaders this season`. None of them named a metric. The route needed one,
so it used points.

That fallback is the defect. A ranking question with no metric in it is not a
points question - it is a question the product cannot answer yet, and the
honest reply is to ask which stat.

Two rules, applied before the default may fire:

1. **The metric must be anchored.** It comes from the query, either from a stat
   the parser resolved or from an already-approved leaderboard shorthand
   (`top scorers`, `best offensive teams`). Nothing is inferred: `best team`,
   `NBA leaders`, `top players` and `play best` name no metric, and there is no
   default to fall back on.

2. **The rest of the question must be stat-shaped.** Every content-bearing word
   has to belong to the approved grammar - ranking wording, the population being
   ranked, the metric, a time window, or a qualifier the route actually
   executes. Anything left over is content the leaderboard would drop, so the
   request is refused instead.

Rule 2 is deliberately not a vocabulary of narrative phrases. `stayed afloat`,
`while depleted` and `once their center fouled out` are refused because nothing
in the approved grammar accounts for them, not because they were listed. A word
this module has never seen produces no claim, which leaves residual, which
refuses - so a gap here costs coverage of a real question and cannot invent
permission. That direction is the whole point; listing phrases to reject is the
shape that failed.

Scope: this decides *eligibility*. Once a request is eligible, the route's
existing behavior is unchanged, including its documented `stat_fallback`
substitutions for metrics a particular window cannot compute.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from nbatools.commands._leaderboard_utils import (
    detect_player_leaderboard_stat,
    detect_team_leaderboard_stat,
)
from nbatools.commands.entity_resolution import TEAM_ALIASES

# Stable ids reported in ``unsupported_filters``. Each one needs different
# guidance from the user, so they stay distinct.

#: A ranking was requested and no metric was named.
NO_REQUESTED_METRIC = "leaderboard_metric_required"
#: A total/combined/cumulative ranking was requested; leaderboards are per-game.
UNSUPPORTED_AGGREGATION = "leaderboard_aggregation_unsupported"
#: Part of the question is outside the stat-shaped grammar.
UNCLEAR_REQUEST = "leaderboard_request_unclear"


@dataclass(frozen=True)
class LeaderboardEligibility:
    """Whether a league-wide leaderboard may answer, the metric, and why not."""

    authorized: bool
    metric: str | None = None
    reason: str | None = None
    #: Content-bearing words nothing in the approved grammar accounted for.
    residual: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "authorized": self.authorized,
            "metric": self.metric,
            "reason": self.reason,
            "residual": list(self.residual),
        }


# ---------------------------------------------------------------------------
# 1. Metric anchoring
# ---------------------------------------------------------------------------


def anchored_leaderboard_metric(parsed: dict) -> str | None:
    """The metric this ranking question named, or ``None`` if it named none.

    Mirrors the route's own resolution order exactly, minus its ``or "pts"``
    tail. Keeping the order identical is what guarantees every question that
    resolves a metric today still resolves the same one.
    """
    q = parsed.get("normalized_query") or ""
    stat = parsed.get("stat")
    if parsed.get("team_leaderboard_intent"):
        return detect_team_leaderboard_stat(q) or stat
    if "team" in q or "teams" in q:
        return stat
    return detect_player_leaderboard_stat(q) or stat


# ---------------------------------------------------------------------------
# 2. Aggregation
# ---------------------------------------------------------------------------

# Leaderboards rank per-game rates. "total points leaders" asks for something
# else, and answering it with a per-game board is a wrong answer, not a near
# one. These words are content, never grammar.
_TOTAL_AGGREGATION = re.compile(r"\b(?:total|totals|combined|cumulative|aggregate)\b")


def _leaderboard_column(metric: str, *, team_scope: bool) -> str | None:
    """The column a leaderboard would rank *metric* by, if it supports it."""
    if team_scope:
        from nbatools.commands.season_team_leaders import ALLOWED_STATS as TEAM_STATS

        return TEAM_STATS.get(metric.lower())
    from nbatools.commands.season_leaders import ALLOWED_STATS as PLAYER_STATS

    return PLAYER_STATS.get(metric.lower())


def _aggregation_supported(text: str, metric: str, *, team_scope: bool) -> bool:
    """Whether the aggregation the question asked for is the one that would run.

    Only totals are checked. Per-game and rate wording describe what the
    leaderboard already computes, so they need no separate support.
    """
    if not _TOTAL_AGGREGATION.search(text):
        return True
    column = _leaderboard_column(metric, team_scope=team_scope)
    if column is None:
        return True  # unknown metric; the route will refuse it on its own terms
    # A season total is only available where the leaderboard already ranks one.
    return column.endswith("_total")


# ---------------------------------------------------------------------------
# 3. Stat-shaped grammar
# ---------------------------------------------------------------------------

# Content tokens. Keeps "%", "+", "." and "-" inside a token so "ts%", "30+",
# ".500" and "2023-24" stay whole.
_TOKEN = re.compile(r"[a-z0-9][a-z0-9'%+./-]*")

# Closed-class words only. Nothing here may carry meaning a leaderboard would
# have to act on: "without", "missing", "while", "when", "despite", "out" and
# every aggregation word are deliberately absent.
_GRAMMAR_WORDS = frozenset(
    """
    a an the of in on at for to and or is are was were be been am has have had
    do does did this that these those there it its they them their he she his
    her him we our you your i my me s per by with from as than so just really
    actually please currently still any each every some all both up into about
    among amongst show list give tell find me
    """.split()
)

# Ranking wording. A ranking question is allowed to say it is a ranking
# question: interrogatives, superlatives, "leaders", and the ordinary verbs
# used to phrase one.
_RANKING = (
    r"\b(?:who's|whos|who|which|whose|what)\b",
    r"\b(?:top|best|worst|highest|lowest|most|fewest|least|greatest|bottom)\b",
    r"\b(?:leaders?|leads?|leading|led|rank(?:s|ed|ing|ings)?|standings)\b",
    r"\b(?:averages?|averaged|averaging|scores?|scored|scoring|shoots?|shot|shooting"
    r"|rebounds?|rebounded|rebounding|played|plays?|makes?|made|making|gets?|got"
    r"|posts?|posted|grabs?|grabbed|dishes|dished)\b",
)

# The population being ranked.
_POPULATION = (r"\b(?:players?|teams?|nba|league|league-?wide|games?)\b",)

# Time and qualifier wording, each gated on the parse slot that proves the
# parser actually resolved it. Wording the parser did not read stays residual.
_SEASON = (
    r"\b(?:this|current|the\s+current)\s+(?:season|year|yr|campaign)\b",
    r"\b(?:last|past|previous)\s+(?:season|year)\b",
    r"\b(?:over|in|during|across|for)?\s*(?:the\s+)?(?:last|past|previous)\s+"
    r"(?:\d+|two|three|four|five|six|seven|eight|nine|ten)\s+(?:seasons?|years?)\b",
    r"\b\d{4}\s*-\s*\d{2,4}\b",
    r"\b(?:in|for|during|from)\s+\d{4}\b",
    r"\bsince\s+\d{4}\b",
    r"\b(?:so\s+far|right\s+now|to\s+date|all[-\s]?time|career|ever)\b",
    r"\b(?:seasons?|years?)\b",
)
_SEASON_TYPE = (r"\b(?:playoffs?|postseason|preseason|play-?in)\b",)
_LAST_N = (
    r"\b(?:over|in|during|across)?\s*(?:the\s+)?(?:his|her|their|its)?\s*"
    r"(?:last|past|previous|recent)\s+\d+\s*(?:games?)?\b",
    r"\b(?:last|past|previous|recent)\s+"
    r"(?:two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty)\s*(?:games?)?\b",
    r"\b(?:recently|lately|right\s+now|of\s+late)\b",
    r"\brecent\s+form\b",
)
_DATES = (
    # The trailing \b on the day stops "january 2024" reading as "january 20"
    # plus a stranded "24".
    r"\b(?:january|february|march|april|may|june|july|august|september|october"
    r"|november|december)\b(?:\s+\d{1,2}(?:st|nd|rd|th)?\b)?(?:,?\s*\d{4}\b)?",
    r"\b(?:jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec)\.?\s+\d{1,2}\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b(?:since|before|after|through|until|from)\b",
    r"\b(?:last\s+night|yesterday|today|tonight|this\s+week|this\s+month)\b",
    r"\b(?:over|in|during|across)?\s*(?:the\s+)?(?:last|past)\s+"
    r"(?:month|week|fortnight|\d+\s+(?:weeks?|days?|months?))\b",
    r"\ball[-\s]?star\s+break\b",
    r"\b(?:recently|lately)\b",
)
_OPPONENT_QUALITY = (
    r"\b(?:against|vs\.?|versus)\b",
    r"\b(?:top|bottom)[-\s]?\d+\s+(?:defenses?|offenses?|teams?)\b",
    r"\b(?:defenses?|offenses?|opponents?|contenders?)\b",
    r"\b(?:good|great|elite|bad|weak|poor|winning|losing|playoff|contending)\s+teams?\b",
    r"\bteams?\s+(?:over|above|under|below)\s*\.?\d+\b",
)
_OPPONENT = (r"\b(?:against|vs\.?|versus)\b",)
_CLUTCH = (r"\bclutch\b", r"\bcrunch[-\s]?time\b")
_PERIOD = (
    r"\b(?:1st|2nd|3rd|4th|first|second|third|fourth)\s+(?:quarter|qtr|period)\b",
    r"\bq[1-4]\b",
    r"\b(?:1st|2nd|first|second)\s+half\b",
)
_LOCATION = (
    r"\bat\s+home\b",
    r"\bhome\s+games?\b",
    r"\bon\s+the\s+road\b",
    r"\broad\s+games?\b",
    r"\baway\s+(?:games?|from\s+home)\b",
)
_OUTCOME = (r"\bin\s+(?:wins|losses|victories|defeats)\b",)
_POSITION = (
    # Longest first: "bigs?" before "big men" would strand "men".
    r"\b(?:point\s+guards?|shooting\s+guards?|small\s+forwards?|power\s+forwards?"
    r"|big\s+m[ae]n|wing\s+players?|guards?|forwards?|centers?|wings?|bigs?)\b",
)
_ROLE = (r"\b(?:starters?|starting\s+lineup|bench|reserves?|off\s+the\s+bench)\b",)
_MIN_GAMES = (
    r"\b(?:at\s+least|minimum(?:\s+of)?|min\.?)\s+\d+\s+games?\b",
    r"\bwith\s+\d+\+?\s+games?\b",
)
_TOP_N = (r"\btop\s+\d+\b", r"\bbottom\s+\d+\b", r"\b\d+\s+best\b", r"\bfirst\s+\d+\b")
_THRESHOLD = (
    r"\b\d+\+",
    r"\b(?:at\s+least|over|more\s+than|above|under|less\s+than|below|fewer\s+than)\s+\d+\b",
    r"\b\d+\s+or\s+(?:more|fewer|less)\b",
)

# A named team, drawn from the same alias table the resolver used. Claimed only
# when the parser actually resolved that team - as the ranking's own subject
# ("Lakers leading scorer") or as its opponent ("most points vs the Lakers").
# A team word the parser did not read as either is still residual.
_TEAM_NAME = ("|".join(re.escape(alias) for alias in sorted(TEAM_ALIASES, key=len, reverse=True)),)
_SUBJECT = (rf"(?<!\w)(?:{_TEAM_NAME[0]})(?!\w)",)

#: (parse keys that must be resolved, wording they then account for).
_SLOT_CLAIMS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("season", "start_season", "end_season", "explicit_relative_season"), _SEASON),
    (("last_n",), _LAST_N),
    (("start_date", "end_date"), _DATES),
    (("opponent_quality",), _OPPONENT_QUALITY),
    (("opponent",), _OPPONENT + _SUBJECT),
    (("clutch",), _CLUTCH),
    (("quarter", "half"), _PERIOD),
    (("home_only", "away_only"), _LOCATION),
    (("wins_only", "losses_only"), _OUTCOME),
    (("position_filter",), _POSITION),
    (("role",), _ROLE),
    (("min_games",), _MIN_GAMES),
    (("top_n",), _TOP_N),
    (("min_value", "max_value"), _THRESHOLD),
    (("team",), _SUBJECT),
)


def _slot_resolved(parsed: dict, keys: tuple[str, ...]) -> bool:
    """True when the parser actually resolved one of *keys*.

    ``is not None`` rather than truthiness, so a meaningful ``0`` counts.
    """
    return any(parsed.get(key) not in (None, False) for key in keys)


def _claimed_ranges(text: str, parsed: dict, metric: str | None) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []

    def claim(patterns: tuple[str, ...]) -> None:
        for pattern in patterns:
            ranges.extend(m.span() for m in re.finditer(pattern, text) if m.group(0).strip())

    claim(_RANKING)
    claim(_POPULATION)
    if metric:
        claim(tuple(_metric_patterns(text, parsed)))
    for keys, patterns in _SLOT_CLAIMS:
        if _slot_resolved(parsed, keys):
            claim(patterns)
    # The season-type qualifier is captured separately upstream.
    if str(parsed.get("season_type") or "").lower() != "regular season":
        claim(_SEASON_TYPE)
    claim((r"\bregular\s+season\b",))
    return ranges


def _metric_patterns(text: str, parsed: dict) -> list[str]:
    """Wording the resolved metric was read from.

    Built from the same alias tables the detectors used, so the words that
    produced the metric are the words it accounts for.
    """
    from nbatools.commands._constants import STAT_ALIASES
    from nbatools.commands._leaderboard_utils import (
        LEADERBOARD_STAT_ALIASES,
        TEAM_LEADERBOARD_STAT_ALIASES,
    )

    aliases: dict[str, str] = {**STAT_ALIASES, **LEADERBOARD_STAT_ALIASES}
    if parsed.get("team_leaderboard_intent") or "team" in text:
        aliases = {**aliases, **TEAM_LEADERBOARD_STAT_ALIASES}
    # The season-type qualifier sits inside phrases like "best playoff offense";
    # allow it between alias words so the span stays contiguous.
    gap = r"\s+(?:(?:playoffs?|postseason)\s+)?"
    return [
        rf"(?<!\w){gap.join(re.escape(word) for word in phrase.split())}(?!\w)"
        for phrase in sorted(aliases, key=len, reverse=True)
        if phrase.split()[0] in text
    ]


def _residual_tokens(text: str, ranges: list[tuple[int, int]]) -> list[str]:
    residual: list[str] = []
    for match in _TOKEN.finditer(text):
        token = match.group(0)
        if token in _GRAMMAR_WORDS:
            continue
        if any(start <= match.start() and match.end() <= end for start, end in ranges):
            continue
        residual.append(token)
    return residual


# ---------------------------------------------------------------------------
# The decision
# ---------------------------------------------------------------------------


def assess_leaderboard_request(
    parsed: dict, *, metric: str | None = None
) -> LeaderboardEligibility:
    """Whether a ranking route may answer this question.

    Refuses unless the metric is anchored in the query *and* the rest of the
    question is stat-shaped. Never authorizes by failing to find a problem.

    ``metric`` lets a route that resolved its own anchor pass it in - the
    team-scoped leader route reads ``team_leader_stat`` rather than the
    league-wide tables, and the second rule applies to it just the same.
    """
    text = parsed.get("normalized_query") or ""
    metric = metric or anchored_leaderboard_metric(parsed)

    if metric is None:
        return LeaderboardEligibility(authorized=False, reason=NO_REQUESTED_METRIC)

    team_scope = bool(parsed.get("team_leaderboard_intent")) or "team" in text
    if not _aggregation_supported(text, metric, team_scope=team_scope):
        return LeaderboardEligibility(
            authorized=False, metric=metric, reason=UNSUPPORTED_AGGREGATION
        )

    residual = _residual_tokens(text, _claimed_ranges(text, parsed, metric))
    if residual:
        return LeaderboardEligibility(
            authorized=False,
            metric=metric,
            reason=UNCLEAR_REQUEST,
            residual=tuple(dict.fromkeys(residual)),
        )

    return LeaderboardEligibility(authorized=True, metric=metric)
