"""Team and opponent box-score conditions on a player's games.

"LeBron games when the Lakers score 120" and "Lakers record when LeBron
scores 30 and they score 120" name the team's total, not the player's. The
threshold reader returns a plain ``pts`` bound for both, so on a player route
the 120 was checked against LeBron's own points and no game matched. Here the
team-subject clauses are found and their bounds moved to ``team_<stat>`` (or
``opponent_<stat>`` when the subject is the opponent), which the player routes
read from the team rows of the same game.
"""

from __future__ import annotations

import re
from typing import Any

from nbatools.commands._condition_utils import PLAYER_GAME_CONTEXT_BASES
from nbatools.commands._constants import STAT_PATTERN
from nbatools.commands._parse_helpers import (
    _OPP_STAT_WORD,
    _opponent_stat_word,
    extract_opponent_points_allowed_conditions,
)
from nbatools.commands.entity_resolution import TEAM_ALIASES

_PLAYER_ROUTES = ("player_game_finder", "player_game_summary")

_SCORE_VERB = r"scor(?:e|es|ed)|puts?\s+up|put\s+up"
_TEAM_STAT_VERB = re.compile(
    rf"\s({_SCORE_VERB}|ha(?:d|s|ve)|ma(?:de|kes?)|hits?|grab(?:s|bed)?"
    r"|record(?:s|ed)?|reach(?:es|ed)?|(?:did|does|do)\s+not\s+reach|dish(?:es|ed)?|commit(?:s|ted)?)\s+"
)
_BOUND = re.compile(
    r"(?P<pre>at\s+least\s+|a\s+min(?:imum)?\s+of\s+|over\s+|more\s+than\s+|under\s+"
    r"|below\s+|fewer\s+than\s+|less\s+than\s+|at\s+most\s+|no\s+more\s+than\s+)?"
    r"(?P<num>\d+(?:\.\d+)?)(?P<plus>\+)?(?:\s+or\s+(?P<mid>more|fewer|less))?"
    rf"(?:\s+(?:made\s+)?(?P<stat>{_OPP_STAT_WORD}|points?|pts))?"
    r"(?:\s+or\s+(?P<post>more|fewer|less))?(?![\w-])"
)
_PRE = {
    "at least": ("min", 0.0),
    "a minimum of": ("min", 0.0),
    "a min of": ("min", 0.0),
    "over": ("min", 0.0001),
    "more than": ("min", 0.0001),
    "under": ("max", 0.0001),
    "below": ("max", 0.0001),
    "fewer than": ("max", 0.0001),
    "less than": ("max", 0.0001),
    "at most": ("max", 0.0),
    "no more than": ("max", 0.0),
}
_TEAM_WORDS = {"they", "team", "the team", "we"}
# The subject opens a clause: "when the Lakers score 120", "games they had 30
# assists". After "vs Boston" / "for the Lakers" the team is a filter and a
# following verb belongs to the player ("LeBron vs Boston scores 30").
_CLAUSE_OPENER = re.compile(
    r"(?:^|\b(?:when|whenever|where|if|and|while|but|after|games?|that|which))\s*$"
)
# "the other team" / "the opposing team" is the opponent, read elsewhere.
_OPPONENT_WORDS = re.compile(r"\b(?:other|opposing)\s+team$")


def _subject_team(prefix: str) -> tuple[str, int] | None:
    """The team named by the last one to three words of *prefix*, and where
    that subject starts.

    The team is "TEAM" for "they" / "the team", else a team abbreviation.
    """
    for size in (3, 2, 1):
        m = re.search(rf"(?:^|\s)((?:\S+\s+){{{size - 1}}}\S+)\s*$", prefix)
        if m is None:
            continue
        phrase = m.group(1)
        if _OPPONENT_WORDS.search(prefix.rstrip()):
            return None
        if not _CLAUSE_OPENER.search(prefix[: m.start(1)]):
            continue
        bare = re.sub(r"^(?:the|his|her|their)\s+", "", phrase)
        if phrase in _TEAM_WORDS or bare in _TEAM_WORDS:
            return "TEAM", m.start(1)
        if bare == "la":
            # Lakers or Clippers: whichever side of the game is from LA.
            return "LA", m.start(1)
        if bare in TEAM_ALIASES and len(bare) > 3:
            return TEAM_ALIASES[bare], m.start(1)
    return None


def team_subject_stat_conditions(text: str) -> list[dict[str, Any]]:
    """Bounds whose subject is a team: "the Lakers score 120", "they had 30
    assists", "the team makes 15 threes"."""
    found = []
    for verb in _TEAM_STAT_VERB.finditer(text):
        subject = _subject_team(text[: verb.start()])
        if subject is None:
            continue
        team, start = subject
        bound = _BOUND.match(text, verb.end())
        if bound is None:
            continue
        word = bound.group("stat")
        if word is None:
            if not re.fullmatch(_SCORE_VERB, verb.group(1)):
                continue
            stat = "pts"
        else:
            stat = _opponent_stat_word(word, verb.group(1))
        if stat not in PLAYER_GAME_CONTEXT_BASES:
            continue
        value = float(bound.group("num"))
        pre = re.sub(r"\s+", " ", (bound.group("pre") or "").strip())
        mode, epsilon = _PRE.get(pre, ("min", 0.0))
        if re.fullmatch(r"(?:did|does|do)\s+not\s+reach", verb.group(1)):
            mode, epsilon = "max", 0.0001
        tail = bound.group("mid") or bound.group("post")
        if tail in ("fewer", "less"):
            mode, epsilon = "max", 0.0
        found.append(
            {
                "team": team,
                "start": start,
                "end": bound.end(),
                "stat": stat,
                "min_value": value + epsilon if mode == "min" else None,
                "max_value": value - epsilon if mode == "max" else None,
            }
        )
    return found


def _same_bound(cond: dict, other: dict) -> bool:
    return all(
        (cond.get(k) is None and other.get(k) is None)
        or (
            cond.get(k) is not None
            and other.get(k) is not None
            and abs(float(cond[k]) - float(other[k])) < 1e-3
        )
        for k in ("min_value", "max_value")
    )


# The joining word before a removed team clause: "... with 30 points when".
_DANGLING_JOIN = re.compile(r"\s*,?\s*(?:and|but|while|when|where|if|in\s+games?)?\s*$")


def _without_team_clauses(text: str, found: list[dict]) -> str:
    for item in sorted(found, key=lambda f: f["start"], reverse=True):
        left = _DANGLING_JOIN.sub("", text[: item["start"]])
        text = f"{left} {text[item['end'] :]}"
    return re.sub(r"\s+", " ", text).strip()


def _kwargs_conditions(route_kwargs: dict) -> list[dict]:
    conditions = [dict(c) for c in route_kwargs.get("conditions") or []]
    if conditions or not route_kwargs.get("stat"):
        return conditions
    if route_kwargs.get("min_value") is None and route_kwargs.get("max_value") is None:
        return []
    return [
        {
            "stat": route_kwargs["stat"],
            "min_value": route_kwargs.get("min_value"),
            "max_value": route_kwargs.get("max_value"),
        }
    ]


def _is_context_stat(stat: str) -> bool:
    return stat.startswith(("team_", "opponent_"))


def _clear_covered_event_refusal(route_kwargs: dict, own: list[dict]) -> None:
    """Drop the "event list not executable" refusal once every requested
    player event ("30 point games") is among the player's own bounds."""
    auth = route_kwargs.get("compound_event_authorization") or {}
    unsupported = list(route_kwargs.get("unsupported_filters") or [])
    marker = "compound_event_request_unexecutable"
    if marker not in unsupported or auth.get("reason") != marker:
        return
    requested = auth.get("requested_event_conditions") or []
    if not requested or not all(
        any(c["stat"] == r.get("stat") and _same_bound(c, r) for c in own) for r in requested
    ):
        return
    unsupported.remove(marker)
    if unsupported:
        route_kwargs["unsupported_filters"] = unsupported
    else:
        route_kwargs.pop("unsupported_filters", None)
    for key in (
        "compound_event_authorization",
        "requested_event_conditions",
        "unsupported_scope",
    ):
        route_kwargs.pop(key, None)


# "Celtics fewest points allowed", "games with the most points allowed": a
# team list ranked by the opponent's score (it ranked the team's own points).
_ALLOWED_RANK = re.compile(
    r"\b(?P<dir>fewest|lowest|least|most|highest)\s+(?:\d+\s+)?(?:points?|pts)\s+"
    r"(?:allowed|given\s+up|conceded)\b"
    r"|\b(?P<dir2>fewest|lowest|least|most|highest)\s+opponents?'?\s+(?:points?|scoring)\b"
)


def _apply_allowed_ranking(route: str | None, route_kwargs: dict, text: str) -> None:
    if route != "game_finder" or route_kwargs.get("stat") not in (None, "pts"):
        return
    m = _ALLOWED_RANK.search(text)
    if (
        not m
        or route_kwargs.get("min_value") is not None
        or route_kwargs.get("max_value") is not None
    ):
        return
    word = m.group("dir") or m.group("dir2")
    route_kwargs["stat"] = "opponent_pts"
    route_kwargs["sort_by"] = "stat"
    route_kwargs["ascending"] = word in ("fewest", "lowest", "least")


# An opponent stat after "opponent": one word, or the multi-word ones
# ("free throw attempts", "3 pointers", "field goals").
_OPP_STAT_WORDS = (
    r"(?:(?:effective\s+field\s+goal|true\s+shooting|field[\s-]+goal|free[\s-]+throw"
    r"|(?:3|three)[\s-]*(?:point|pt)|fg|ft|3p|efg|ts)\s*(?:percentage|pct|%)"
    r"|free[\s-]+throws?(?:\s+(?:attempts|made|makes))?"
    r"|(?:3|three)[\s-]*(?:pointers?|pt|point)(?:\s+(?:attempts|shots|made|makes))?"
    r"|field[\s-]+goals?(?:\s+(?:attempts|made|makes))?"
    r"|(?:offensive|defensive)\s+rebounds?"
    r"|[a-z0-9-]+)"
)
_OPP_WORD = r"opponents?(?:'s?|s')?"
_OPP_STAT_RANK = re.compile(
    # "Lakers games with the most opponent turnovers", "top 5 games by
    # opponent rebounds", "fewest opponents' threes".
    rf"(?<!\bat\s)\b(?P<dir>most|fewest|least|lowest|highest|top|bottom)\s+(?:\d+\s+)?"
    rf"(?:games?\s+by\s+(?:the\s+)?(?:most\s+)?)?{_OPP_WORD}\s+(?P<stat>{_OPP_STAT_WORDS})"
    # "where (the) opponents had / made the most threes".
    r"|\b(?:the\s+)?(?:opponents?|other\s+team|opposing\s+team)\s+(?:had|made|hit|grabbed|"
    rf"committed|shot|recorded|got)\s+the\s+(?P<dir2>most|fewest|least)\s+(?P<stat2>{_OPP_STAT_WORDS})"
    # "games where they / the Lakers forced the most turnovers" (not "the
    # opponent forced").
    r"|(?<![\w'])(?:the\s+)?(?!(?:opponents?|other|opposing|team)\b)[a-z0-9.']+\s+forced\s+"
    r"the\s+(?P<dir3>most|fewest|least)\s+turnovers\b"
    # "ranked / sorted by opponent points".
    rf"|\b(?:ranked|sorted|ordered)\s+by\s+(?:the\s+)?{_OPP_WORD}\s+(?P<stat4>{_OPP_STAT_WORDS})"
    r"(?P<asc4>,?\s+(?:ascending|lowest\s+first|fewest\s+first|least\s+first))?"
)


# "at least 15 opponent turnovers", "over 120 opponent points": a bound on the
# opponent's number, not a ranking.
_OPP_STAT_BOUND = re.compile(
    r"\b(?P<op>at\s+least|at\s+most|over|under|more\s+than|fewer\s+than|less\s+than)\s+"
    rf"(?P<num>\d+)\s+{_OPP_WORD}\s+(?P<stat>{_OPP_STAT_WORDS})"
    rf"|\b(?P<num2>\d+)\+\s*{_OPP_WORD}\s+(?P<stat2>{_OPP_STAT_WORDS})"
    # "120 points allowed", "at most 10 threes given up": the opponent's.
    r"|(?:\b(?P<op3>at\s+least|at\s+most|over|under|more\s+than|fewer\s+than|less\s+than)\s+)?"
    r"\b(?P<num3>\d+)(?:\+|\s+or\s+(?P<orx>more|fewer|less))?\s+"
    rf"(?P<stat3>{_OPP_STAT_WORDS})\s+(?:allowed|given\s+up)\b"
    # "with 15 opponent turnovers", "10 or fewer opponent turnovers": a bare
    # count is a floor, as the team's own counts are.
    r"|(?<![\d.])\b(?P<num4>\d+)(?:\s+or\s+(?P<orx4>more|fewer|less))?\s+"
    rf"{_OPP_WORD}\s+(?P<stat4>{_OPP_STAT_WORDS})\b(?:\s+or\s+(?P<orx5>more|fewer|less))?"
)
_OPP_BOUND_MODE = {
    "at least": ("min", 0.0),
    "at most": ("max", 0.0),
    "over": ("min", 0.0001),
    "more than": ("min", 0.0001),
    "under": ("max", 0.0001),
    "fewer than": ("max", 0.0001),
    "less than": ("max", 0.0001),
}
# Spellings the stat reader misses.
_OPP_STAT_SPELLINGS = (
    (re.compile(r"free throw attempts|free throws? (?:attempts|shots)"), "fta"),
    (re.compile(r"free throws?(?: made| makes)?"), "ftm"),
    (re.compile(r"(?:3|three) ?(?:pointers?|pt|point) (?:attempts|shots)"), "fg3a"),
    (re.compile(r"(?:3|three) ?(?:pointers?|pt|point)(?: made| makes)?"), "fg3m"),
    (re.compile(r"field goals? attempts|field goal attempts"), "fga"),
    (re.compile(r"field goals?(?: made| makes)?"), "fgm"),
    (re.compile(r"defensive rebounds?"), "dreb"),
)


def _opponent_stat(word: str) -> str | None:
    """The opponent column a stat word names ("free throws" -> opponent_ftm)."""
    from nbatools.commands.game_finder import ALLOWED_STATS

    words = re.sub(r"[\s-]+", " ", word.strip())
    stat = next((s for rx, s in _OPP_STAT_SPELLINGS if rx.fullmatch(words)), None)
    stat = stat or _stat_word(words)
    return f"opponent_{stat}" if stat and f"opponent_{stat}" in ALLOWED_STATS else None


# "held the opponent to 100", "held them to under 90 points and 10 threes":
# ceilings on the opponent's numbers, each item read with its own stat.
_HELD = re.compile(r"\bheld\s+(?:the\s+)?(?:opponents?|other\s+team|them)\s+to\s+")
_HELD_ITEM = re.compile(
    r"(?P<op>under\s+|fewer\s+than\s+|less\s+than\s+|at\s+most\s+)?(?P<num>\d+(?:\.\d+)?)"
    r"(?:\s+or\s+(?:fewer|less|under))?(?:\s+made)?"
    rf"(?:\s+(?P<stat>{_OPP_STAT_WORDS}))?"
)
# What may follow a bare "held them to 100": the points ceiling ends there.
_HELD_POINTS_END = re.compile(
    r"\s*(?:$|[,.?!]|(?:in|on|at|this|last|since|and|with|when|while|during|vs|versus|against|"
    r"games?|from|before|after|over)\b)"
)
_HELD_JOIN = re.compile(r"\s*(?:,\s*(?:and\s+)?|\s+and\s+)(?=(?:under|fewer|less|at\s+most|\d))")
_HELD_NOT_A_STAT = re.compile(r"\s*(?:%|percent\b|pct\b|shooting\b|from\b)")


class _Span:
    """A bound's text span, read like a match by the callers below."""

    def __init__(self, start: int, end: int) -> None:
        self._span = (start, end)

    def span(self) -> tuple[int, int]:
        return self._span

    def group(self, _name: str) -> None:
        return None


def _held_bounds(text: str) -> list[tuple[_Span, dict]]:
    found: list[tuple[_Span, dict]] = []
    for lead in _HELD.finditer(text):
        pos, items = lead.end(), []
        while True:
            item = _HELD_ITEM.match(text, pos)
            if not item or _HELD_NOT_A_STAT.match(text, item.end("num")):
                # "held them to 40% shooting": a rate this reader leaves alone.
                items = []
                break
            words = item.group("stat")
            stat = _opponent_stat(words) if words else "opponent_pts"
            end = item.end()
            if stat is None:
                # "held them to 100 in wins": points, when nothing stat-like
                # follows the number; anything else is left to the readers.
                if not _HELD_POINTS_END.match(text, item.end("num")):
                    items = []
                    break
                stat, end = "opponent_pts", item.end("num")
            if stat.endswith("_pct"):
                items = []
                break
            strict = bool(item.group("op")) and not item.group("op").startswith("at")
            value = float(item.group("num"))
            items.append(
                {"stat": stat, "min_value": None, "max_value": value - (0.0001 if strict else 0.0)}
            )
            pos = end
            join = _HELD_JOIN.match(text, pos)
            if not join:
                break
            pos = join.end()
        if items:
            found.extend((_Span(lead.start(), pos), bound) for bound in items)
    return found


# "games where the opponent shot under 40 percent", "held opponents to 30%
# from three": the opponent's shooting rate (the team's own was filtered).
_RATE_OP = (
    r"(?P<op>under|below|less\s+than|over|above|more\s+than|at\s+least|at\s+most|"
    r"no\s+more\s+than)"
)
_RATE_TAIL = (
    r"(?P<num>\d+(?:\.\d+)?)\s*(?:%|percent\b|pct\b)(?:\s+shooting\b)?"
    r"(?:\s+(?P<area>(?:(?:from\s+)?(?:behind|beyond)|from|at|on|in)\s+(?:the\s+)?(?:three|3|deep|downtown|distance|"
    r"long\s+range|outside|arc|(?:three|3)[\s-]point\s+(?:line|range)|field|floor|line|stripe|"
    r"charity\s+stripe|free[\s-]throw\s+line|threes|3s|free\s+throws)\b))?"
)
_OPP_SHOOTING = re.compile(
    r"\b(?:where\s+|when\s+|while\s+)?(?:the\s+)?(?:opponents?|other\s+team|opposing\s+teams?|"
    r"opposition)\s+(?:shot|shoots|shoot|shooting|were\s+shooting|was\s+shooting)\s+"
    # "when opponents shoot 50%": a bare rate is a floor, as the team's own is.
    rf"(?:(?:{_RATE_OP}\s+)?{_RATE_TAIL}"
    # "opponents shot between 40 and 50 percent": both bounds.
    r"|between\s+(?P<lo>\d+(?:\.\d+)?)\s*(?:%|percent\b)?\s+and\s+"
    + _RATE_TAIL.replace("?P<num>", "?P<num3>").replace("?P<area>", "?P<area3>")
    + ")"
    r"|\b(?:held|holding|holds?|limited|limiting|limits?|keeps?|kept|keeping)\s+(?:the\s+)?"
    r"(?:opponents?|other\s+team|them|teams)\s+(?:to\s+)?"
    rf"(?:{_RATE_OP.replace('?P<op>', '?P<op2>')}\s+)?"
    + _RATE_TAIL.replace("?P<num>", "?P<num2>").replace("?P<area>", "?P<area2>")
)
# What follows the opponent's shooting with no new subject is still the
# opponent's ("and scored under 100", ", scoring over 110", "and under 35
# percent from three", "and 110 points"), or an area the reader does not know
# ("from the corner"): not read, so refuse.
_SECOND_OPPONENT_CLAUSE = re.compile(
    r"\s*(?:,\s*|\s+(?:and|but|while|with)\s+)(?:and\s+)?"
    r"(?:(?:scor\w*|had|has|have|made|makes?|making|hit|hits|hitting|grabb\w*|committ\w*|put\w*\s+up|"
    r"allow\w*|shoot\w*|shot|went)\s+)?"
    r"(?:(?:under|over|below|above|at\s+least|at\s+most|less\s+than|more\s+than|fewer\s+than|"
    # A season after the clause is the sample ("..., 2024-25", "from last
    # season").
    r"no\s+more\s+than)\s+)?(?!(?:19|20)\d{2}\b)\.?\d"
    # (Month-name ranges are not read anywhere yet, so they still refuse.)
    r"|\s+from\s+(?!(?:19|20)\d{2}\b|(?:last|this|next|previous)\b|"
    r"the\s+(?:(?:19|20)\d{2}\b|last\b|previous\b))"
)
_RATE_OR_TAIL = re.compile(r"\s+or\s+(better|more|higher|above|worse|less|lower|below)\b")
_RATE_MODE = {
    "under": ("max", 0.0001),
    "below": ("max", 0.0001),
    "less than": ("max", 0.0001),
    "over": ("min", 0.0001),
    "above": ("min", 0.0001),
    "more than": ("min", 0.0001),
    "at least": ("min", 0.0),
    "at most": ("max", 0.0),
    "no more than": ("max", 0.0),
}

_ALLOWED_RATE = re.compile(
    r"\b(?:allow(?:s|ed|ing)?|gave\s+up|give\s+up|gives\s+up|giving\s+up"
    r"|opponents?\s+at)\s+(?:\w+\s+){0,2}?"
    # "allow between 40 and 50% shooting".
    r"(?:between\s+\d+(?:\.\d+)?\s*(?:%|percent)?\s+and\s+)?\d+(?:\.\d+)?\s*(?:%|percent)"
)
# Another side's rate the readers do not place ("keep the Celtics under 55%",
# "against teams under 55% shooting"): read as the subject's own it filtered
# the wrong team, so refuse unless the opponent reader took it.
_OTHER_SIDE_RATE = re.compile(
    # "vs Celtics on 50% shooting" is the subject's own rate in those games;
    # "hold opponents on under 50% shooting" is not.
    r"(?:\b(?:keep\w*|kept|hold\w*|held|limit\w*)\s+"
    r"(?:(?!(?:shoot\w*|shot|when|while|if|and|with|to)\b)[a-z.']+\s+){0,4}?"
    r"|\b(?:against|vs\.?|versus)\s+"
    r"(?:(?!(?:shoot\w*|shot|when|while|if|and|with|on|to)\b)[a-z.']+\s+){0,3}?)"
    r"(?:(?:under|below|over|above|at\s+least|at\s+most|less\s+than|more\s+than"
    r"|no\s+more\s+than)\s+|between\s+\d+(?:\.\d+)?\s*(?:%|percent)?\s+and\s+)?"
    r"\d+(?:\.\d+)?\s*(?:%|percent)"
)
# "when LeBron forces 3 turnovers", "when the Celtics force 15 turnovers": not
# the team's own forcing (which is rewritten to the opponent's turnovers).
_UNREAD_FORCED = re.compile(
    r"\bforc(?:e|es|ed|ing)\s+(?:[a-z]+\s+){0,2}?\d+\+?\s+(?:or\s+[a-z]+\s+)?turnovers?\b"
)


def _opponent_shooting_bounds(text: str) -> list[tuple[re.Match, dict]]:
    found = []
    for m in _OPP_SHOOTING.finditer(text):
        op = m.group("op") or m.group("op2") or "at most"  # "held them to 40%": a ceiling
        if m.group("num") and not m.group("op"):
            tail = _RATE_OR_TAIL.match(text, m.end())
            op = (
                "at most"
                if tail and tail.group(1) in {"worse", "less", "lower", "below"}
                else "at least"
            )
        mode, eps = _RATE_MODE[re.sub(r"\s+", " ", op)]
        area = m.group("area") or m.group("area2") or m.group("area3") or ""
        if re.search(r"three|3|deep|arc|downtown|distance|long|outside", area) and not re.search(
            r"free", area
        ):
            stat = "opponent_fg3_pct"
        elif re.search(r"line|free|stripe", area):
            stat = "opponent_ft_pct"
        else:
            stat = "opponent_fg_pct"
        if m.group("lo"):
            low, high = sorted((float(m.group("lo")), float(m.group("num3"))))
            found.append((m, {"stat": stat, "min_value": low / 100, "max_value": high / 100}))
            continue
        value = float(m.group("num") or m.group("num2")) / 100
        found.append(
            (
                m,
                {
                    "stat": stat,
                    "min_value": value + eps if mode == "min" else None,
                    "max_value": value - eps if mode == "max" else None,
                },
            )
        )
    return found


def _opponent_bounds(text: str) -> list[tuple[re.Match | _Span, dict]]:
    found: list[tuple[re.Match | _Span, dict]] = list(_held_bounds(text))
    found.extend(_opponent_shooting_bounds(text))
    for m in _OPP_STAT_BOUND.finditer(text):
        stat = _opponent_stat(
            m.group("stat") or m.group("stat2") or m.group("stat3") or m.group("stat4") or ""
        )
        op = m.group("op") or m.group("op3")
        if not stat:
            continue
        orx = m.group("orx") or m.group("orx4") or m.group("orx5")
        if not op and orx:
            op = "at least" if orx == "more" else "at most"
        mode, eps = _OPP_BOUND_MODE[re.sub(r"\s+", " ", op or "at least")]
        value = float(m.group("num") or m.group("num2") or m.group("num3") or m.group("num4"))
        if stat.endswith("_pct") and value > 1:
            # "at least 50 opponent field goal percentage": the rate as a fraction.
            value /= 100
        found.append(
            (
                m,
                {
                    "stat": stat,
                    "min_value": value + eps if mode == "min" else None,
                    "max_value": value - eps if mode == "max" else None,
                },
            )
        )
    return found


def _own_bounds(text: str, spans: list[tuple[int, int]]) -> list[dict]:
    """The team's own bounds, read with the opponent phrases taken out ("at
    least 15 turnovers and at least 15 opponent turnovers": the own floor was
    dropped as a misreading of the opponent's)."""
    from nbatools.commands.natural_query import _build_parse_state

    rest = text
    for start, end in sorted(spans, reverse=True):
        rest = rest[:start] + " " + rest[end:]
    state = _build_parse_state(rest)
    found = list(state.get("threshold_conditions") or [])
    if (
        not found
        and state.get("stat")
        and (state.get("min_value") is not None or state.get("max_value") is not None)
    ):
        found = [state]
    own = []
    for item in found:
        bound = {k: item.get(k) for k in ("stat", "min_value", "max_value")}
        if bound["stat"] and not any(c["stat"] == bound["stat"] for c in own):
            own.append(bound)
    return own


def _refuse(route_kwargs: dict, name: str) -> None:
    blocked = list(route_kwargs.get("unsupported_filters") or [])
    if name not in blocked:
        route_kwargs["unsupported_filters"] = [*blocked, name]


def _apply_opponent_stat_bounds(route: str | None, route_kwargs: dict, text: str) -> None:
    """ "Lakers games with at least 15 opponent turnovers": an opponent bound
    (the team's own turnovers were filtered)."""
    if route and _UNREAD_FORCED.search(text):
        _refuse(route_kwargs, "forced_turnovers")
        return
    if route:
        read = [m.span() for m in _OPP_SHOOTING.finditer(text)]
        for m in _OTHER_SIDE_RATE.finditer(text):
            if not any(start <= m.end() and m.start() <= end for start, end in read):
                _refuse(route_kwargs, "opponent_shooting")
                return
    if route and _ALLOWED_RATE.search(text):
        # "when they allow 45% shooting": the opponent's rate, not read in
        # this wording (it was dropped).
        blocked = list(route_kwargs.get("unsupported_filters") or [])
        if "opponent_shooting" not in blocked:
            route_kwargs["unsupported_filters"] = [*blocked, "opponent_shooting"]
        return
    if route not in ("game_finder", "team_record"):
        if route and _OPP_SHOOTING.search(text):
            # "Lakers record when opponents shoot under 40 percent": only team
            # game lists read the opponent's rate; elsewhere it filtered the
            # subject's own shooting, so refuse.
            blocked = list(route_kwargs.get("unsupported_filters") or [])
            if "opponent_shooting" not in blocked:
                route_kwargs["unsupported_filters"] = [*blocked, "opponent_shooting"]
        return
    found = _opponent_bounds(text)
    if not found:
        return
    for m, _ in found:
        if getattr(m, "re", None) is _OPP_SHOOTING and _SECOND_OPPONENT_CLAUSE.match(text, m.end()):
            # "the opponent shot under 45 percent and scored under 100": the
            # second clause is the opponent's too; not read, so refuse.
            blocked = list(route_kwargs.get("unsupported_filters") or [])
            route_kwargs["unsupported_filters"] = [*blocked, "opponent_shooting"]
            return
    bounds = [bound for _, bound in found]
    spans = [m.span() for m, _ in found]
    ranked = _OPP_STAT_RANK.search(text)
    if ranked:
        spans.append(ranked.span())
    own = _own_bounds(text, spans)
    route_kwargs["conditions"] = own + bounds
    # "Lakers games with 120 points allowed" was refused as a 120-point event
    # the list cannot run; it is the opponent's bound, now applied.
    _clear_covered_event_refusal(
        route_kwargs,
        own
        + [
            {**bound, "stat": bound["stat"][len("opponent_") :]}
            for m, bound in found
            if getattr(m, "re", None) is not _OPP_SHOOTING and m.group("stat3")
        ],
    )
    bases = {b["stat"][len("opponent_") :] for b in bounds}
    if any(getattr(m, "re", None) is _OPP_SHOOTING for m, _ in found):
        # "opponent shot under 75 percent from the line" was also read as the
        # team's own field goal rate.
        bases |= {"fg_pct", "fg3_pct", "ft_pct", "efg_pct", "ts_pct"} - {o["stat"] for o in own}
    if route_kwargs.get("stat") in bases or not route_kwargs.get("stat"):
        # The bound was read as the team's own: it moves to the opponent's.
        route_kwargs.update(
            stat=bounds[-1]["stat"],
            min_value=bounds[-1]["min_value"],
            max_value=bounds[-1]["max_value"],
        )
        if route_kwargs.get("sort_by") == "stat" and not _RANKING_WORDS.search(text):
            route_kwargs["sort_by"] = "game_date"


def _apply_opponent_stat_ranking(route: str | None, route_kwargs: dict, text: str) -> None:
    """Rank a team's games by the opponent's number ("most opponent
    turnovers" ranked the team's own turnovers)."""
    if route != "game_finder":
        return
    m = _OPP_STAT_RANK.search(text)
    if not m:
        return
    word = m.group("dir") or m.group("dir2") or m.group("dir3") or "most"
    if m.group("dir3"):
        stat = "opponent_tov"
    else:
        stat = _opponent_stat(m.group("stat") or m.group("stat2") or m.group("stat4") or "")
    if not stat:
        return
    # "most opponent turnovers with 120 points": the team's own bounds stay
    # conditions (they were dropped), and opponent bounds stay too.
    found = _opponent_bounds(text)
    conditions = _own_bounds(text, [m.span()] + [b.span() for b, _ in found])
    conditions += [bound for _, bound in found]
    if conditions:
        route_kwargs["conditions"] = conditions
    else:
        route_kwargs.pop("conditions", None)
    route_kwargs["min_value"] = route_kwargs["max_value"] = None
    route_kwargs["stat"] = stat
    route_kwargs["sort_by"] = "stat"
    route_kwargs["ascending"] = word in ("fewest", "least", "lowest", "bottom") or bool(
        m.group("asc4")
    )


def apply_player_game_context(route: str | None, route_kwargs: dict, text: str) -> None:
    """Read team/opponent bounds and the ranking stat of a player game list."""
    # Ownership checks must see the complete opponent set and actual subject,
    # not a scalar detection that mistook the last opponent for the team.
    _apply_opponent_list(route, route_kwargs, text)
    _apply_allowed_ranking(route, route_kwargs, text)
    _apply_opponent_stat_bounds(route, route_kwargs, text)
    _apply_opponent_stat_ranking(route, route_kwargs, text)
    _apply_team_context(route, route_kwargs, text)
    _apply_own_team_clauses(route, route_kwargs, text)
    _refuse_unread_held_to(route, route_kwargs, text)
    _refuse_game_clock(route, route_kwargs, text)
    _refuse_other_player_stat(route, route_kwargs, text)
    _refuse_team_shooting(route, route_kwargs, text)
    _apply_any_player_stat(route, route_kwargs, text)
    _apply_shooting_with_events(route, route_kwargs, text)
    _apply_ranked_events(route, route_kwargs, text)
    _apply_ranking_stat(route, route_kwargs, text)
    _apply_ranking_direction(route, route_kwargs, text)
    _refuse_team_as_own_opponent(route_kwargs)
    _refuse_unread_samples(route, route_kwargs, text)


_LIST_ROUTES = (
    "team_compare",
    "player_compare",
    "team_record",
    "game_finder",
    "game_summary",
    "player_game_finder",
    "player_game_summary",
    "team_streak_finder",
    "player_streak_finder",
    # Team stretches read their own lists; a player's stretch does not.
    "player_stretch_leaderboard",
    "team_split_summary",
    "player_split_summary",
)


def _apply_opponent_list(route: str | None, route_kwargs: dict, text: str) -> None:
    """ "vs Celtics, Knicks and Heat": games against any of them (only the
    first was kept)."""
    from nbatools.commands._parse_helpers import opponent_lists

    if route not in _LIST_ROUTES or not isinstance(route_kwargs.get("opponent"), str):
        return
    lists = opponent_lists(text)
    if len(lists) != 1:
        return
    start, end, teams = lists[0]
    if _CLAUSE_VERB.match(text, end):
        # "vs Celtics and the Knicks score 110", "LeBron games vs Celtics and
        # Lakers won": a clause about the last team.
        return
    from nbatools.commands.entity_resolution import mask_copula_team_lookalikes
    from nbatools.commands.natural_query import _teams_in_order

    # Resolve the subject outside the complete opponent span, in either clause
    # order. Mask in full context before removing spans: "what was New York"
    # contains a verb, while an explicit "WAS record" still names Washington.
    masked = mask_copula_team_lookalikes(text)
    outside = masked[:start] + " " * (end - start) + masked[end:]
    owners = [team for _, _, team in _teams_in_order(outside)]
    before = [team for _, _, team in _teams_in_order(masked[:start])]
    if route != "team_compare" and (len(owners) == 1 or len(before) == 1):
        # A later condition may name another team. Keep the sole prefix
        # subject so the ownership guard can reject that condition honestly.
        route_kwargs["team"] = owners[0] if len(owners) == 1 else before[0]
    elif not owners and route.startswith("player_"):
        route_kwargs["team"] = None
    if route_kwargs["opponent"] != teams[0] or route_kwargs.get("team") in teams:
        return
    route_kwargs["opponent"] = list(dict.fromkeys(teams))


# "vs Celtics and Knicks": a second opponent the routes do not combine (only
# the first was kept).
_TWO_OPPONENTS = re.compile(
    r"\b(?:vs\.?|versus|against)\s+(?:the\s+)?(?P<a>[a-z.']+(?:\s+[a-z.']+)?)"
    r"\s*(?:,|and|&|or)\s+(?:the\s+)?(?P<b>[a-z.']+(?:\s+[a-z.']+)?)\b"
)
# "the Celtics' opponents score 110" on a Lakers record: another team's
# opponents (it answered with Boston's record).
_NAMED_OPPONENTS = re.compile(
    r"\b(?P<name>(?:(?!(?:when|while|if|and|where|vs|versus|against|the|with|did|do|does)\b)"
    r"[a-z.']+\s+)?(?!(?:when|while|if|and|where|vs|versus|against|the|with|did|do|does)\b)"
    r"[a-z.]+)(?:'s?|s')?\s+opponents?\b"
)
# "Lakers 120 point seasons", "40% shooting seasons", "seasons with 40%
# shooting": a season list, which the game lists answered with games.
_CONDITION_SEASONS = re.compile(
    r"\b(?:points?|pts|shooting|assists?|rebounds?|threes?|\d+%)\s+seasons\b"
    r"|\bseasons\s+(?:with|shooting|where|when|in\s+which)\s+(?:at\s+least\s+|over\s+|under\s+)?\d"
)
# "vs ranked opponents", "vs LA teams": groups the readers do not define
# (they answered with every game).
_UNREAD_GROUP = re.compile(
    r"\b(?:vs\.?|versus|against)\s+(?:the\s+)?(?:ranked|la|l\.a\.|los\s+angeles)"
    r"\s+(?:opponents|teams)\b"
)
# "vs teams that shoot 50%", "vs teams that won 50 games", "vs poor shooting
# teams": opponents described by their own season, which is not loaded (the
# clause was read as the subject's own stat or dropped).
_DESCRIBED_OPPONENTS = re.compile(
    r"\b(?:vs\.?|versus|against|facing)\s+(?:the\s+)?(?:teams?|opponents?)\s+(?:that|who|which)\s+"
    r"(?!(?:made|make|qualified|qualify|missed|miss)\s+(?:the\s+)?(?:playoffs|postseason)\b)"
    r"(?!(?:are|were|is|was)\s+(?:over|above|under|below|\.500|winning|losing)\b)"
    r"[a-z]"
    r"|\b(?:vs\.?|versus|against|facing)\s+(?:the\s+)?"
    # "vs good / top / bad defensive teams" are the rating groups.
    r"(?!(?:top|best|elite|great|good|strong|bottom|worst|bad|poor|weak)\s+"
    r"(?:defensive|offensive)\s+teams\b)"
    r"(?:[a-z]+\s+)?"
    r"(?:shooting|scoring|defensive|defending|offensive|rebounding|passing)\s+(?:teams|opponents)\b"
)
# "when the score was 120": which side's points is not said (dropped).
# "when the score is tied / close": the in-game score is not loaded.
_BARE_SCORE = re.compile(
    r"\b(?:the\s+)?(?:final\s+)?score\s+(?:was|is|of|were)\s+(?:\d|tied\b|close\b|even\b)"
)


_CLAUSE_VERB = re.compile(
    r"\s+(?:scor\w*|won|wins?|winning|lost|los\w*|beat\w*|ha[sd]|have|mak\w*|made|shoot\w*"
    r"|shot|allow\w*|gave|give\w*|play\w*|held|hold\w*)\b"
)
_SAMPLE_ROUTES = (
    "team_record",
    "game_finder",
    "game_summary",
    "player_game_finder",
    "player_game_summary",
)


def _refuse_unread_samples(route: str | None, route_kwargs: dict, text: str) -> None:
    if not route:
        return
    from nbatools.commands._matchup_utils import detect_team_in_text
    from nbatools.commands.entity_resolution import mask_copula_team_lookalikes

    # Resolve verb/team lookalikes in full context before chopping a clause
    # into short opponent fragments such as "what was". Masking preserves
    # offsets used by the clause readers below.
    text = mask_copula_team_lookalikes(text)

    if _UNREAD_GROUP.search(text):
        _refuse(route_kwargs, "opponent_group")
    if _DESCRIBED_OPPONENTS.search(text):
        _refuse(route_kwargs, "opponent_description")
    if _BARE_SCORE.search(text):
        _refuse(route_kwargs, "unattributed_score")
    if route in ("game_finder", "player_game_finder") and _CONDITION_SEASONS.search(text):
        _refuse(route_kwargs, "season_condition_list")
    # One opponent, or none when the list's first team became the subject
    # ("Lakers record vs Celtics, Knicks and Heat" answered Boston's record).
    single = isinstance(route_kwargs.get("opponent"), (str, type(None)))
    for m in _TWO_OPPONENTS.finditer(text) if single and route in _LIST_ROUTES else ():
        first, second = detect_team_in_text(m.group("a")), detect_team_in_text(m.group("b"))
        if second == route_kwargs.get("team") or _CLAUSE_VERB.match(text, m.end()):
            # "vs Celtics and the Lakers score 120": the subject's own clause.
            continue
        if first and second and first != second:
            _refuse(route_kwargs, "multiple_opponents")
            break
    from nbatools.commands.natural_query import _teams_in_order

    # The subject is the first team named that is not the opponent ("LeBron
    # games vs the Celtics when the Lakers' opponents score 110" is his team's).
    opponent = route_kwargs.get("opponent")
    named = [team for _, _, team in _teams_in_order(text) if team != opponent]
    subject = named[0] if named else None
    for m in _NAMED_OPPONENTS.finditer(text):
        team = detect_team_in_text(m.group("name"))
        if team and subject and team != subject:
            _refuse(route_kwargs, "other_team_opponents")
            break


def _refuse_team_as_own_opponent(route_kwargs: dict) -> None:
    """A clause read the wrong way round can leave the team as its own
    opponent ("BOS record vs Lakers when the Lakers shoot 50%"); that sample
    is always empty, so refuse instead of answering "no games"."""
    team, opponent = route_kwargs.get("team"), route_kwargs.get("opponent")
    if isinstance(team, str) and isinstance(opponent, str) and team == opponent:
        blocked = list(route_kwargs.get("unsupported_filters") or [])
        if "team_is_opponent" not in blocked:
            route_kwargs["unsupported_filters"] = [*blocked, "team_is_opponent"]


# "held to N" the bound rewrites did not read ("when Boston is held to 100",
# "held to 40% shooting and 100 points"): its subject is unclear, so refuse
# rather than answer without the bound.
_UNREAD_HELD_TO = re.compile(
    # "held to 100 points or less" and "held to fewer than 100 points" are read.
    r"\bheld\s+to\s+(?:(?:under|below)\s+)?\d+(?:\.\d+)?"
    r"(?!\d|(?:\s+points?)?\s+or\s+(?:fewer|less)\b)"
)


def _refuse_unread_held_to(route: str | None, route_kwargs: dict, text: str) -> None:
    if route and _UNREAD_HELD_TO.search(text):
        blocked = list(route_kwargs.get("unsupported_filters") or [])
        if "held_to" not in blocked:
            route_kwargs["unsupported_filters"] = [*blocked, "held_to"]


# "with 5 minutes left", "in the final 2 minutes": a point on the game clock,
# not minutes played. Play-by-play is not loaded, so refuse.
_GAME_CLOCK = re.compile(
    r"\b\d+\s+minutes?\s+(?:left|remaining|to\s+go)\b|\b(?:last|final|closing)\s+\d+\s+minutes?\b"
    # "with 5 minutes rest": not minutes played.
    r"|\b\d+\s+(?:minutes?|mins?|hours?|nights?)\s+(?:of\s+)?rest\b"
)


def _refuse_game_clock(route: str | None, route_kwargs: dict, text: str) -> None:
    if route and _GAME_CLOCK.search(text):
        blocked = list(route_kwargs.get("unsupported_filters") or [])
        if "game_clock" not in blocked:
            route_kwargs["unsupported_filters"] = [*blocked, "game_clock"]


# "LeBron games when Anthony Davis scores 30": another player's stat, which
# filtered LeBron's own points. Not read, so refuse.
_OTHER_PLAYER_STAT = re.compile(
    r"\b(?:when|if|while|where|whenever)\s+"
    r"(?!(?:he|she|they|we|the|his|their|opponents?|teams?|other|opposing|la|los\s+angeles)\b)"
    r"(?P<name>[a-z.'-]+(?:\s+[a-z.'-]+){0,2}?)\s+"
    r"(?:scores?|scored|has|had|gets?|got|records?|recorded|grabs?|grabbed|makes?|made"
    r"|hits?|dishes|dished|puts?\s+up)\s+(?:at\s+least\s+|over\s+|under\s+)?\d"
)

_LA_CLAUSE = re.compile(
    r"\b(?:when|if|while|where|whenever|and)\s+(?:la|l\.a\.|los\s+angeles)\s+"
    r"(?:scores?|scored|has|had|gets?|got|makes?|made|hits?|shoots?|shot)\s+"
    r"(?:at\s+least\s+|over\s+|under\s+)?\d"
)

_TEAM_STAT_CLAUSE = re.compile(
    r"\b(?:when|if|while|where|whenever|and)\s+(?:the\s+)?"
    # The name never spans another clause ("Lakers and Celtics when they score").
    r"(?P<name>(?:(?!(?:when|if|while|where|whenever|they|he|we)\b)[a-z.']+\s+){0,3}?"
    r"(?!(?:when|if|while|where|whenever|they|he|we)\b)[a-z.']+)\s+"
    r"(?:scores?|scored|has|had|makes?|made|hits?|shoots?|shot|grabs?|grabbed)\s+"
    r"(?:at\s+least\s+|over\s+|under\s+)?\d"
)


def _refuse_third_team_stat(route_kwargs: dict, text: str) -> None:
    """ "Lakers record vs Celtics when ... the Knicks score 110", "when Knicks
    and Celtics score 110": a team that is neither side of the game was read
    as the subject's own stat, so refuse."""
    from nbatools.commands.natural_query import _teams_in_order

    opponent = route_kwargs.get("opponent")
    opponents = [opponent] if isinstance(opponent, str) else opponent or []
    sides = {route_kwargs.get("team"), *opponents}
    if not route_kwargs.get("team"):
        return
    for m in _TEAM_STAT_CLAUSE.finditer(text):
        named = [t for _, _, t in _teams_in_order(m.group("name"))]
        if len(named) > 1 or (named and named[0] not in sides):
            blocked = list(route_kwargs.get("unsupported_filters") or [])
            if "other_team_stat" not in blocked:
                route_kwargs["unsupported_filters"] = [*blocked, "other_team_stat"]
            return


def _refuse_compare_team_stat(route_kwargs: dict, text: str) -> None:
    """ "Lakers vs Celtics when the Celtics score 110" bounded both teams' own
    points; a clause naming one team (or a third) is not read on a compare."""
    from nbatools.commands.natural_query import _teams_in_order

    for m in _TEAM_STAT_CLAUSE.finditer(text):
        if _teams_in_order(m.group("name")) or _LA_NAME_ONLY.fullmatch(m.group("name")):
            blocked = list(route_kwargs.get("unsupported_filters") or [])
            if "other_team_stat" not in blocked:
                route_kwargs["unsupported_filters"] = [*blocked, "other_team_stat"]
            return


_LA_NAME_ONLY = re.compile(r"la|l\.a\.|los\s+angeles")

_TWO_PLAYER_SUBJECT = re.compile(
    r"\s*(?P<a>[a-z.'\-]+(?:\s+[a-z.'\-]+){0,2}?)\s+(?:and|&)\s+"
    r"(?P<b>[a-z.'\-]+(?:\s+[a-z.'\-]+){0,2}?)\s+"
    r"(?=(?:\d+\+?[- ]\w+\s+)?(?:games?|record|stats|summary|averages?|last|this|in|with|when)\b)"
)


def _refuse_other_player_stat(route: str | None, route_kwargs: dict, text: str) -> None:
    player = route_kwargs.get("player")
    if route and route not in _PLAYER_ROUTES:
        _refuse_unknown_name_stat(route_kwargs, text)
        if route in ("team_record", "game_finder", "game_summary"):
            _refuse_third_team_stat(route_kwargs, text)
        elif route == "team_compare":
            _refuse_compare_team_stat(route_kwargs, text)
        return
    if not player:
        return
    from nbatools.commands._matchup_utils import detect_player, detect_team_in_text

    pair = _TWO_PLAYER_SUBJECT.match(text)
    if pair:
        first, second = detect_player(pair.group("a")), detect_player(pair.group("b"))
        if first and second and first != second:
            # "LeBron and Luka games with 30 points" answered with LeBron's
            # games alone.
            blocked = list(route_kwargs.get("unsupported_filters") or [])
            if "two_players" not in blocked:
                route_kwargs["unsupported_filters"] = [*blocked, "two_players"]
            return

    own = set(str(player).lower().split())
    for m in _OTHER_PLAYER_STAT.finditer(text):
        name = m.group("name")
        shared = set(name.split()) & own
        if detect_team_in_text(name) or (shared and len(name.split()) == 1):
            continue
        other = detect_player(name)
        # "when LeBron James scores 30" is him; "when Bronny James scores 10"
        # shares a surname but is another player.
        if other == player or (shared and other is None):
            continue
        blocked = list(route_kwargs.get("unsupported_filters") or [])
        if "other_player_stat" not in blocked:
            route_kwargs["unsupported_filters"] = [*blocked, "other_player_stat"]
        return


def _refuse_unknown_name_stat(route_kwargs: dict, text: str) -> None:
    """ "Lakers record when Davis scores 30" with no player resolved read the
    team's own 30 points (every game): a name it cannot place refuses."""
    from nbatools.commands._matchup_utils import detect_player, detect_team_in_text

    if _LA_CLAUSE.search(text) and route_kwargs.get("team") not in ("LAL", "LAC"):
        # "Celtics record when they score 120 and LA scores 110": the Lakers or
        # the Clippers; not read, so refuse rather than reading the Celtics' own.
        blocked = list(route_kwargs.get("unsupported_filters") or [])
        if "other_player_stat" not in blocked:
            route_kwargs["unsupported_filters"] = [*blocked, "other_player_stat"]
        return
    for m in _OTHER_PLAYER_STAT.finditer(text):
        name = m.group("name")
        if (
            detect_team_in_text(name)
            or _ANY_PLAYER_SUBJECT.match(name)
            or re.match(r"(?:a|an|any|one|some|another|no|nobody|our|my|your|opposition)\b", name)
            or detect_player(name)
        ):
            continue
        blocked = list(route_kwargs.get("unsupported_filters") or [])
        if "other_player_stat" not in blocked:
            route_kwargs["unsupported_filters"] = [*blocked, "other_player_stat"]
        return


# "Lakers record when a player scores 40", "best record when someone has 40":
# one of the team's players, which read the team's own points. A floor reads
# the team's best single-player line in the game; anything else refuses.
_ANY_PLAYER_STAT = re.compile(
    r"(?:\b(?:when|if|while|where|whenever|in\s+games?\s+(?:where|when)|and|but)\s+|,\s*)"
    r"(?:(?:a|an|any|one|some)\s+(?:(?P<team1>[a-z.']+)\s+)?player|someone|anyone|anybody|somebody)"
    r"(?:\s+(?:on|from|for)\s+(?:the\s+)?(?P<team2>[a-z.']+(?:\s+[a-z.']+)?))?\s+"
    r"(?:scores?|scored|has|had|gets?|got|records?|recorded|grabs?|grabbed|makes?|made"
    r"|hits?|dishes|dished|puts?\s+up)\s+"
    r"(?P<pre>at\s+least\s+|over\s+|more\s+than\s+|under\s+|below\s+|fewer\s+than\s+"
    r"|less\s+than\s+|at\s+most\s+)?(?P<n>\d+)(?P<plus>\+)?"
    r"(?:\s+(?P<post>or\s+(?:more|fewer|less)))?"
    r"(?:\s+(?P<w>[a-z0-9-]+(?:\s+pointers?)?))?"
)
# Words after the number that end the clause rather than name a stat.
_ANY_PLAYER_NOT_A_STAT = re.compile(
    r"and|but|in|at|on|vs|versus|against|or|this|last|since|during|before|after|with"
    r"|without|games?|the|home|away|while|when|for|over|from|of|a|an|\d{4}(?:-\d{2})?"
)
# Every "any player" subject: one the reader cannot place ("nobody scores
# 30", "if any of them score 30") makes the clause count disagree, so refuse.
_ANY_PLAYER_SUBJECT = re.compile(
    r"\b(?:(?:a|an|any|one|some)\s+(?:[a-z.']+\s+)?player|someone|anyone|anybody|somebody"
    r"|nobody|no\s+one|no\s+player|another(?!\s+team)|(?:a\s+)?second\s+player|(?:a\s+)?teammates?"
    r"|(?:an)?other\s+players?)\b"
)
# A second stat joined to the same player ("someone scores 30 and has 15
# rebounds", "30 and 10"): one player's line, which a per-team best per stat
# cannot read.
_ANY_PLAYER_JOINED = re.compile(
    r"\s*(?:(?:,\s*(?:and\s+)?|\s+(?:and|with|while)\s+)(?:(?:he|she)\s+)?"
    r"(?:has|have|had|scores?|scored|gets?|got|grabs?|grabbed|records?|recorded|makes?|made"
    r"|hits?|dishes|dished|puts?\s+up|adds?|added|shoots?|shooting|shot|\d)"
    # "on 50% shooting", "on 10 of 15": the scorer's own efficiency.
    r"|\s+on\s+\d)"
)
# Any subject with a stat verb and a number, read or not ("nobody scores 30").
_ANY_PLAYER_LOOSE = re.compile(
    _ANY_PLAYER_SUBJECT.pattern + r"(?:\s+[a-z.']+){0,3}?\s+"
    r"(?:scores?|scored|has|had|gets?|got|records?|recorded|grabs?|grabbed|makes?|made"
    r"|hits?|dishes|dished|puts?\s+up)\s+(?:[a-z]+\s+){0,2}?\d"
)


def _any_player_end(m: re.Match) -> int:
    """Where the clause's bound ends: after its stat word when it names one."""
    word = m.group("w")
    if word and _stat_word(word):
        return m.end("w")
    return max(m.end(g) for g in ("n", "plus", "post") if m.group(g))


_ANY_PLAYER_ROUTES = ("team_record", "game_finder", "game_summary", "team_record_leaderboard")


def _any_player_bound(m: re.Match, route_team: str | None, text: str) -> dict | None:
    """The bound a match reads, or None when it cannot be read."""
    from nbatools.commands._condition_utils import TOP_PLAYER_BASES
    from nbatools.commands._matchup_utils import detect_team_in_text

    pre = (m.group("pre") or "").strip()
    post = m.group("post") or ""
    if pre in ("under", "below", "fewer than", "less than", "at most") or re.search(
        r"fewer|less", post
    ):
        # "when a player scores under 10" is not "the best line is under 10".
        return None
    named = m.group("team1") or m.group("team2")
    if named and named != "single":
        # "a Lakers player" is the subject's own; "a Celtics player" beside
        # the Lakers is not read.
        from nbatools.commands.natural_query import _team_mentions

        team = detect_team_in_text(named)
        head = text[: m.start()]
        before = [t for a, b, t in _team_mentions(head) if head[a:b] not in _WORD_ALIASES]
        if team is None or team != route_team or not before or before[0] != team:
            return None
    word = m.group("w")
    stat = _stat_word(word) if word else None
    if word and stat is None and not _ANY_PLAYER_NOT_A_STAT.fullmatch(word):
        return None
    stat = stat or "pts"
    if stat not in TOP_PLAYER_BASES:
        return None
    value = float(m.group("n"))
    if pre in ("over", "more than"):
        value += 0.0001
    return {"stat": f"top_player_{stat}", "min_value": value, "max_value": None, "base": stat}


def _apply_any_player_stat(route: str | None, route_kwargs: dict, text: str) -> None:
    matches = list(_ANY_PLAYER_STAT.finditer(text))
    if not route or route in _PLAYER_ROUTES:
        return
    if not matches and not _ANY_PLAYER_LOOSE.search(text):
        return
    bounds = [_any_player_bound(m, route_kwargs.get("team"), text) for m in matches]
    unread = (
        len(bounds) > 1
        or len(_ANY_PLAYER_SUBJECT.findall(text)) != len(matches)
        or any(_ANY_PLAYER_JOINED.match(text, _any_player_end(m)) for m in matches)
    )
    if route not in _ANY_PLAYER_ROUTES or None in bounds or unread:
        blocked = list(route_kwargs.get("unsupported_filters") or [])
        if "any_player_stat" not in blocked:
            route_kwargs["unsupported_filters"] = [*blocked, "any_player_stat"]
        return
    bound = bounds[0]
    base = bound.pop("base")
    # The clause was read as the team's own stat: replace that bound.
    conditions = [
        c
        for c in _kwargs_conditions(route_kwargs)
        if not (
            c["stat"] == base
            and c.get("min_value") is not None
            and abs(c["min_value"] - bound["min_value"]) < 1
        )
    ]
    conditions.append(bound)
    route_kwargs["conditions"] = conditions
    if route_kwargs.get("stat") == base or not route_kwargs.get("stat"):
        route_kwargs.update(stat=bound["stat"], min_value=bound["min_value"], max_value=None)


# "LeBron games vs Celtics when the Celtics shoot 50%": a team's shooting
# rate, which filtered the player's own. Player rows do not carry the team
# rates, so refuse.
_TEAM_SHOOTING = re.compile(
    r"\b(?:when|if|while|whenever|where|and|but)\s+(?:the\s+|his\s+)?"
    r"(?P<name>[a-z.']+(?:\s+[a-z.']+)?)\s+(?:shoots?|shot|shooting"
    # "when the Lakers have 50% shooting".
    # "have at least 55% shooting", "had between 40 and 50% shooting".
    r"|ha(?:s|d|ve)\s+(?:(?:under|below|over|above|at\s+least|at\s+most|less\s+than"
    r"|more\s+than|no\s+more\s+than)\s+|between\s+\d+(?:\.\d+)?\s*(?:%|percent)?\s+and\s+)?"
    r"\d+(?:\.\d+)?\s*(?:%|percent)\s+shooting)\b"
)
_TEAM_SHOOTING_SUBJECTS = frozenset(
    {"they", "team", "opponents", "opponent", "other team", "opposing team", "teams"}
)


def _refuse_team_shooting(route: str | None, route_kwargs: dict, text: str) -> None:
    if route not in _PLAYER_ROUTES or not route_kwargs.get("player"):
        return
    from nbatools.commands._matchup_utils import detect_team_in_text

    for m in _TEAM_SHOOTING.finditer(text):
        name = m.group("name")
        if name in _TEAM_SHOOTING_SUBJECTS or detect_team_in_text(name):
            blocked = list(route_kwargs.get("unsupported_filters") or [])
            if "team_shooting" not in blocked:
                route_kwargs["unsupported_filters"] = [*blocked, "team_shooting"]
            return


_BARE_OWN_CLAUSE = re.compile(
    r"\band\s+(?:make|makes|made|hit|hits|score|scores|scored|have|has|had|grab|grabs|grabbed"
    r"|record|records|recorded|dish|dishes|dished)\s+(?:at\s+least\s+)?(?P<n>\d+)\+?\s+"
    rf"(?P<w>{STAT_PATTERN})\b(?![\s-]+(?:or\s+(?:fewer|less)|allowed))"
)


_CLAUSE_START = re.compile(r"\b(?:when|if|while|where|whenever)\s+")
_OPPONENT_SUBJECT = re.compile(
    r"(?:the\s+)?(?:opponents?|opposing\s+teams?|other\s+teams?|teams|their\s+opponents?"
    r"|opposition|another\s+team)\b"
)


# "... and they shoot 50%", "... and opponents shoot 50%": a joined clause
# with its own subject.
_JOINED_SUBJECT = re.compile(
    r"\b(?:and|but|while)\s+(?:(?P<own>they|he|we|she|the\s+team)"
    r"|(?P<opp>(?:the\s+)?(?:opponents?|opposing\s+teams?|other\s+teams?|teams|their\s+opponents?"
    r"|opposition|another\s+team)))\b"
)


_WORD_ALIASES = frozenset({"was", "min", "cs", "c's"})


def _opponent_subject(before: str, team: str | None) -> bool:
    """The clause before "and" is led by the opponent, not the team."""
    starts = list(_CLAUSE_START.finditer(before))
    if not starts:
        return False
    clause = before[starts[-1].end() :]
    joined = list(_JOINED_SUBJECT.finditer(clause))
    if joined:
        return bool(joined[-1].group("opp"))
    if _OPPONENT_SUBJECT.match(clause):
        return True
    from nbatools.commands._matchup_utils import detect_team_in_text

    named = detect_team_in_text(" ".join(clause.split()[:3]))
    if not named:
        return False
    # "Lakers record when the Celtics shoot 50%": the parse may have taken
    # the clause's team as the subject; the team named first is.
    from nbatools.commands.natural_query import _team_mentions

    # Some aliases are also common words ("what WAS the Lakers record",
    # "MIN"): they never count as the first team.
    head = before[: starts[-1].start()]
    mentions = [m for m in _team_mentions(head) if head[m[0] : m[1]] not in _WORD_ALIASES]
    first = mentions[0][2] if mentions else None
    return named != (first or team)


def _apply_own_team_clauses(route: str | None, route_kwargs: dict, text: str) -> None:
    """Keep the team's own stat beside an opponent bound on a team route.

    "Lakers record when they make 15 threes and allow under 110" read only
    the opponent's points: the threes became the bare stat the opponent
    bound replaced, so the answer counted every game under 110 allowed.
    """
    if route not in ("team_record", "game_finder", "game_summary"):
        return
    conditions = _kwargs_conditions(route_kwargs)
    # Beside an opponent bound, or beside one own bound of a clause list
    # ("when they score 120 and make 15 threes" kept only the points).
    beside_opponent = any(c["stat"].startswith("opponent_") for c in conditions)
    if not beside_opponent and not conditions:
        return
    team = route_kwargs.get("team")
    added = False
    clauses = team_subject_stat_conditions(text)
    bare_own = False
    # "... allow under 110 and make 15 threes": the subject carries over.
    for m in _BARE_OWN_CLAUSE.finditer(text):
        stat = _stat_word(m.group("w"))
        if stat is None:
            continue
        if _opponent_subject(text[: m.start()], team):
            # "when opponents score 110 and make 15 threes": the threes are
            # the opponent's.
            stat = f"opponent_{stat}"
        else:
            bare_own = True
        clauses.append(
            {"team": "TEAM", "stat": stat, "min_value": float(m.group("n")), "max_value": None}
        )
    own = [c for c in clauses if c["team"] in ("TEAM", team)]
    if (
        not beside_opponent
        and not bare_own
        and not any(
            any(c["stat"] == o["stat"] and _same_bound(c, o) for c in conditions) for o in own
        )
    ):
        # No clause of the list was read: not a list this reads. ("when they
        # score between 110 and 120 and make 15 threes": the range is not a
        # clause it lists, but the joined "and make 15 threes" is the team's.)
        return
    for clause in own:
        cond = {k: clause[k] for k in ("stat", "min_value", "max_value")}
        if any(c["stat"] == cond["stat"] for c in conditions):
            continue
        conditions.append(cond)
        added = True
    if added:
        route_kwargs["conditions"] = conditions


# "lowest scoring games", "fewest turnovers": rank from the bottom. The low
# word must sit on the ranked stat; "vs teams with the fewest wins" or "at
# least" says nothing about the order, and "fewest points allowed" ranks the
# opponent's score, not the team's.
_RANKED_STAT = (
    rf"[\s-]+(?:scoring|shooting|efficient|plus[\s-]?minus|{STAT_PATTERN})\b"
    r"(?![\s-]+(?:allowed|given))"
)
# A count before an adjective form ("lowest 3 scoring games"); "best 50
# point games" is a 50-point bound, not a count.
_COUNT_BEFORE_ADJ = r"\s+\d+(?=\s+(?:scoring|rebounding|passing|assist|shooting)\b)"
# "lowest 3 scoring games", "worst 3 scoring games": a count may sit between
# the rank word and the stat (it ranked highest first).
_ASCENDING_RANK = re.compile(
    rf"\b(?:lowest|fewest|(?<!\bat )least)(?:{_COUNT_BEFORE_ADJ})?{_RANKED_STAT}"
)
_WORST_RANK = re.compile(rf"\bworst(?:{_COUNT_BEFORE_ADJ})?{_RANKED_STAT}")
# Stats where a high value is the bad one: "worst turnover games" is the most.
_HIGH_IS_BAD = frozenset({"tov", "pf"})
_DESCENDING_RANK = re.compile(
    rf"\b(?:highest|most|top|best|biggest|largest)(?:{_COUNT_BEFORE_ADJ})?{_RANKED_STAT}"
)


def _apply_ranking_direction(route: str | None, route_kwargs: dict, text: str) -> None:
    """A player or team game list ranked by a stat runs lowest first when asked."""
    if route not in ("player_game_finder", "game_finder") or route_kwargs.get("sort_by") != "stat":
        return
    if _DESCENDING_RANK.search(text):
        return
    low_by = re.search(r"\b(lowest|fewest|least|worst)(?:\s+\d+)?\s+games?\s+by\b", text)
    if (
        _ASCENDING_RANK.search(text)
        or (_WORST_RANK.search(text) and route_kwargs.get("stat") not in _HIGH_IS_BAD)
        # "lowest 3 games by assists"; "worst games by turnovers" is the most.
        or (
            low_by and not (low_by.group(1) == "worst" and route_kwargs.get("stat") in _HIGH_IS_BAD)
        )
    ):
        route_kwargs["ascending"] = True


# "highest scoring games", "top 5 games by assists", "most rebounds in a game".
# "at least" and "at most" are bounds, not ranks.
_RANKING_WORDS = re.compile(
    r"\b(?:highest|(?<!\bat )most|top|best|biggest|largest|lowest|fewest|(?<!\bat )least|by)\b"
)


_RANK_WORD = r"(?:highest|most|top|best|biggest|largest|lowest|fewest|(?<!\bat )least)"
_RANKED_BY = re.compile(
    rf"\b{_RANK_WORD}(?:{_COUNT_BEFORE_ADJ})?[\s-]+(?P<a>scoring|plus[\s-]?minus|{STAT_PATTERN})\b"
    rf"|\bby\s+(?:the\s+)?(?:{_RANK_WORD}\s+)?(?P<b>scoring|plus[\s-]?minus|{STAT_PATTERN})\b"
)
# "with 30 points", "in a game with at least 30 points", "30 point games",
# "a 30 minute game": a player's own game condition beside the ranking.
# "10 assists or fewer" is a ceiling the parse already holds, and "5 threes
# allowed" is the defense's stat, so neither is a floor on the player.
_NOT_A_FLOOR = (
    r"(?![\s-]+(?:or\s+(?:fewer|less|under|below|lower)|at\s+most|max\b|allowed|given\s+up))"
)
_EVENT_PATTERNS = (
    re.compile(
        rf"\bwith\s+(?:at\s+least\s+)?(?P<n>\d+)\+?\s+(?P<w>{STAT_PATTERN}|minutes?)\b{_NOT_A_FLOOR}"
    ),
    re.compile(rf"\b(?P<n>\d+)\+?[\s-]+(?P<w>{STAT_PATTERN}|minutes?)[\s-]+games?\b"),
    # "while shooting 5 threes", "where they made 15 threes", "when he had 10
    # assists": the condition was dropped.
    re.compile(
        r"\b(?:while|when|where)\s+(?P<subj>he\s+|she\s+|they\s+|the\s+\w+\s+)?"
        r"(?:shooting|shot|making|made|hitting|hit|scoring|scored|having|had|grabbing|grabbed|"
        r"recording|recorded|dishing|dished|posting|posted)\s+(?:at\s+least\s+)?"
        rf"(?P<n>\d+)\+?\s+(?P<w>{STAT_PATTERN}|minutes?)\b{_NOT_A_FLOOR}"
    ),
    # An explicit zero is a condition, not the ranking metric. Requiring the
    # clause opener keeps opponent/team-owned clauses with their own readers.
    re.compile(
        rf"\b(?P<n>without(?:\s+any)?|with\s+(?:no|zero))\s+(?P<w>{STAT_PATTERN})\b"
        r"(?![\s-]+(?:allowed|given\s+up))"
    ),
)


def _event_condition(match: re.Match, stat: str) -> dict:
    number = match.group("n")
    explicit_zero = not number.isdigit() or (
        float(number) == 0
        and "+" not in match.group()
        and "at least" not in match.group()
        and "or more" not in match.group()
        and not re.match(r"\s+or\s+more\b", match.string[match.end() :])
        and not re.search(r"\bat\s+least\s+$", match.string[: match.start()])
    )
    return {
        "stat": stat,
        "min_value": 0.0 if explicit_zero else float(number),
        "max_value": 0.0 if explicit_zero else None,
    }


# Near NBA single-game records: a bigger count names a team total.
_EVENT_CEILING = {"pts": 82, "reb": 56, "ast": 31, "fg3m": 15, "stl": 12, "blk": 16, "minutes": 70}


def _stat_word(word: str) -> str | None:
    from nbatools.commands._parse_helpers import detect_stat

    word = re.sub(r"[\s-]+", " ", word.strip())
    if re.fullmatch(r"minutes?", word):
        return "minutes"
    return detect_stat(word)


# Player and team game lists rank the same way ("Celtics top 3 games by
# points with 15 threes" dropped the threes; "by threes with 120 points"
# ranked by points).
_RANKED_ROUTES = frozenset({"player_game_finder", "game_finder"})


# A team list's "120 points allowed" / "15 threes given up" bound is the
# opponent's; the ranking readers below take only the team's own stats.
# "fewest points allowed" ranks the opponent's score (_apply_allowed_ranking).
# "top scoring games when the opponent made 15 threes" ranks the team's own
# points with the opponent's bound kept as a condition.
_OPPONENT_BOUND = re.compile(r"\ballowed\b|\bgiven\s+up\b")


def _team_ranking_unread(route: str | None, text: str) -> bool:
    return route == "game_finder" and bool(_OPPONENT_BOUND.search(text))


def _allowed_stats(route: str | None):
    if route == "game_finder":
        from nbatools.commands.game_finder import ALLOWED_STATS
    else:
        from nbatools.commands.player_game_finder import ALLOWED_STATS
    return ALLOWED_STATS


_RANK_BEFORE = re.compile(
    r"\b(?:highest|most|top|best|biggest|largest|lowest|fewest|(?<!\bat\s)least|worst)\s*$"
)


def _not_own_event(route: str | None, m: re.Match, text: str, team: str | None = None) -> bool:
    """A match that is not the subject's own game condition.

    "lowest 3 rebounding games": the 3 is the row count, not a bound. "LeBron
    ... when they / the Lakers made 12 threes": the team's number, which the
    team context already reads; on a team list, "the opponent" is theirs.
    """
    if _RANK_BEFORE.search(text[: m.start()]):
        return True
    subject = (m.groupdict().get("subj") or "").strip()
    if not subject:
        return False
    if route == "player_game_finder":
        return subject not in ("he", "she")
    if subject == "they":
        return False
    # "Celtics games where the Celtics made 20 threes": the team's own name.
    from nbatools.commands._matchup_utils import detect_team_in_text

    return not (team and detect_team_in_text(subject) == team)


def _game_events(text: str, patterns) -> list[dict]:
    """Player game conditions written as "with N stat" or "N stat games"."""
    events = []
    claimed: list[tuple[int, int]] = []
    for pattern in patterns:
        for m in pattern.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in claimed):
                continue
            stat = _stat_word(m.group("w"))
            if stat is None:
                continue
            claimed.append(m.span())
            if pattern is _EVENT_PATTERNS[1] and stat == "pts" and float(m.group("n")) < 10:
                # "3 point games" are games decided by 3 points.
                continue
            events.append(_event_condition(m, stat))
    return events


def _apply_ranked_events(route: str | None, route_kwargs: dict, text: str) -> None:
    """Rank by the stat a rank word names and keep the game conditions.

    "most rebounds in a game with 30 points" read the 30 as a rebound bound
    and refused; "top 5 games by assists with 30 points" dropped the 30
    points; "fewest points in a 30 minute game" dropped the minutes.
    """
    if route not in _RANKED_ROUTES or route_kwargs.get("sort_by") != "stat":
        return
    if _opponent_ranked(route, route_kwargs):
        return
    if _team_ranking_unread(route, text):
        return
    ranked = {_stat_word(m.group("a") or m.group("b")) for m in _RANKED_BY.finditer(text)} - {None}
    if len(ranked) != 1:
        return
    (ranking,) = ranked
    events = []
    claimed: list[tuple[int, int]] = []
    for pattern in _EVENT_PATTERNS:
        for m in pattern.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in claimed):
                continue
            if _not_own_event(route, m, text, route_kwargs.get("team")):
                continue
            stat = _stat_word(m.group("w"))
            if stat is None:
                continue
            claimed.append(m.span())
            if pattern is _EVENT_PATTERNS[1] and stat == "pts" and float(m.group("n")) < 10:
                # "3 point games" are games decided by 3 points.
                continue
            events.append(_event_condition(m, stat))
    if not events:
        return
    ceiling = _EVENT_CEILING if route == "player_game_finder" else {}
    if any(
        e["min_value"] is not None and e["min_value"] >= ceiling.get(e["stat"], float("inf"))
        for e in events
    ) or any(a["stat"] == b["stat"] and not _same_bound(a, b) for a in events for b in events):
        # "a 120 point game" is the team's total, not the player's; leave
        # the parse's reading (and its refusal) in place.
        return
    if ranking not in _allowed_stats(route):
        return
    kept = [
        c
        for c in _kwargs_conditions(route_kwargs)
        if not (
            c["stat"] == ranking and any(e["stat"] != ranking and _same_bound(c, e) for e in events)
        )
    ]
    # The generic threshold reader encodes bare "with 0 turnovers" as >= 0.
    # The exact-zero event supersedes that vacuous floor, never a positive bound.
    kept = [
        c
        for c in kept
        if not (
            c.get("min_value") == 0
            and c.get("max_value") is None
            and any(e["stat"] == c["stat"] and e.get("max_value") == 0 for e in events)
        )
    ]
    if any(c["stat"] == e["stat"] and not _same_bound(c, e) for c in kept for e in events):
        # The parse read another bound on the same stat ("with 30 points
        # against teams that scored 120"); adding the event would hide it.
        return
    for event in events:
        if not any(c["stat"] == event["stat"] and _same_bound(c, event) for c in kept):
            kept.append(event)
    _clear_covered_event_refusal(route_kwargs, kept)
    route_kwargs["conditions"] = kept
    route_kwargs["stat"] = ranking
    route_kwargs["min_value"] = None
    route_kwargs["max_value"] = None


_GAMES_BY_STAT = re.compile(r"\bgames?\s+by\s+(?:the\s+)?(?:most\s+)?([a-z0-9]+)")


def _opponent_ranked(route: str | None, route_kwargs: dict) -> bool:
    """Already ranked by the opponent's number ("most opponent turnovers"); an
    opponent bound in the slot ("when the Celtics scored 120") is not."""
    return (
        route == "game_finder"
        and str(route_kwargs.get("stat") or "").startswith("opponent_")
        and route_kwargs.get("min_value") is None
        and route_kwargs.get("max_value") is None
    )


# "... and making 15 threes", "scoring 30 points": a verb-led floor beside a
# shooting bound.
_VERB_EVENT = re.compile(
    r"\b(?:making|make|makes|made|hitting|hit|hits|scoring|score|scores|scored)\s+"
    rf"(?:at\s+least\s+)?(?P<n>\d+)\+?\s+(?P<w>{STAT_PATTERN})\b{_NOT_A_FLOOR}"
)


# "ft 80% and 5 fta", "shooting 50% and 5 threes": a joined count beside a rate.
_JOINED_EVENT = re.compile(
    rf"\band\s+(?:at\s+least\s+)?(?P<n>\d+)\+?\s+(?P<w>{STAT_PATTERN})\b{_NOT_A_FLOOR}"
)


_COUNT_OWNER = re.compile(r"\s+(?:from|by)\s+\w")
_CLAUSE_JOINED_COUNT = re.compile(
    rf"\s*(?:,\s*)?and\s+(?:at\s+least\s+)?(?P<n>\d+)\+?\s+(?P<w>{STAT_PATTERN})\b{_NOT_A_FLOOR}"
)


def _apply_shooting_with_events(route: str | None, route_kwargs: dict, text: str) -> None:
    """Keep "with 30 points" beside a shooting percentage.

    "LeBron games shooting over 50% with 30 points" kept only the shooting
    bound, and "with 30 points shooting 50%" refused.
    """
    if not route:
        return
    from nbatools.commands._parse_helpers import _extract_shooting_percentage_conditions

    matches = _extract_shooting_percentage_conditions(text)
    if not matches:
        return
    if any(_opponent_subject(text[: m["start"]], route_kwargs.get("team")) for m in matches):
        # "when opponents shoot 50% and make 15 threes": the opponent's rate,
        # which the bounded reader above handles; anything it missed would
        # filter the team's own shooting, so refuse.
        if not _OPP_SHOOTING.search(text):
            blocked = list(route_kwargs.get("unsupported_filters") or [])
            if "opponent_shooting" not in blocked:
                route_kwargs["unsupported_filters"] = [*blocked, "opponent_shooting"]
        return
    if route not in ("player_game_finder", "player_game_summary", "game_finder", "team_record"):
        return
    shooting = [{k: c[k] for k in ("stat", "min_value", "max_value")} for c in matches]
    events = _game_events(text, (_EVENT_PATTERNS[0], _VERB_EVENT))
    # Only a count joined right onto a rate is the subject's ("fg 50% and 5
    # threes"); "... and opponents score 110 and 15 threes" is another clause's.
    ends = {m["end"] for m in matches}
    for m in _JOINED_EVENT.finditer(text):
        stat = _stat_word(m.group("w"))
        if stat is None or len(text[: m.start()].rstrip()) not in ends:
            continue
        ends.add(m.end())
        if not any(e["stat"] == stat for e in events):
            events.append(_event_condition(m, stat))
    if not events and len(shooting) == 1:
        if _kwargs_conditions(route_kwargs) or (
            route_kwargs.get("min_value") is not None or route_kwargs.get("max_value") is not None
        ):
            return
        # "LeBron games with ts 60%": a rate the parse did not read.
    conditions = shooting + events
    stats = [c["stat"] for c in conditions]
    if len(stats) != len(set(stats)):
        return
    extras = []
    for c in _kwargs_conditions(route_kwargs):
        if not c.get("stat") or any(
            c["stat"] == k["stat"] and _same_bound(c, k) for k in conditions
        ):
            continue
        if c["stat"] in stats or not (c["stat"] == "margin" or c["stat"].startswith("opponent_")):
            # Another bound the parse read; leave the parse alone.
            return
        # "in close games", "when opponents score 100 or fewer": the game's
        # margin or the opponent's line stays beside the shooting bound.
        extras.append(c)
    _clear_covered_event_refusal(route_kwargs, conditions)
    conditions = conditions + extras
    route_kwargs["conditions"] = conditions
    if route == "player_game_finder" and route_kwargs.get("sort_by") == "stat":
        route_kwargs["stat"] = route_kwargs.get("stat") or conditions[0]["stat"]
    else:
        route_kwargs["stat"] = conditions[0]["stat"]
    route_kwargs["min_value"] = conditions[0]["min_value"]
    route_kwargs["max_value"] = conditions[0]["max_value"]


def _apply_ranking_stat(route: str | None, route_kwargs: dict, text: str) -> None:
    """Rank a filtered game list by the stat the question ranks by.

    "LeBron highest scoring games with 10 assists" put the assist bound in
    the ranking slot: the list was ordered by assists, or refused because
    points went unused. The bound stays a condition and points rank.
    """
    if route not in _RANKED_ROUTES or route_kwargs.get("sort_by") != "stat":
        return
    if _opponent_ranked(route, route_kwargs):
        return
    if _team_ranking_unread(route, text):
        return
    if not _RANKING_WORDS.search(text):
        return
    conditions = _kwargs_conditions(route_kwargs)
    if not conditions:
        return
    from nbatools.commands._compound_event_authorization import (
        named_metrics,
        occurrence_count_column_condition,
    )

    filtered = {c["stat"] for c in conditions}
    adjacent = None
    if route == "game_finder":
        # "Lakers highest scoring games when the opponent scored 120": the rank
        # word sits on the team's own points, though the opponent's bound is
        # on points too.
        ranked = next(
            (
                m
                for rx in (_DESCENDING_RANK, _ASCENDING_RANK, _WORST_RANK)
                if (m := rx.search(text))
            ),
            None,
        )
        if ranked:
            adjacent = _stat_word(re.split(r"[\s-]+", ranked.group(0).strip())[-1])
        by_stat = _GAMES_BY_STAT.search(text)
        if adjacent is None and by_stat and _RANKING_WORDS.search(text[: by_stat.start()]):
            # "top 3 games by points" (how "top 3 scoring games" is rewritten).
            adjacent = _stat_word(by_stat.group(1))
    filtered |= {s.split("_", 1)[1] for s in filtered if _is_context_stat(s)}
    candidates = [
        metric
        for metric in named_metrics({"normalized_query": text})
        if metric not in filtered and not occurrence_count_column_condition(metric)
    ]
    if adjacent and adjacent not in {c["stat"] for c in conditions}:
        candidates = [adjacent]
    if len(candidates) != 1:
        return
    if candidates[0] not in _allowed_stats(route):
        return
    route_kwargs["conditions"] = conditions
    route_kwargs["stat"] = candidates[0]
    route_kwargs["min_value"] = None
    route_kwargs["max_value"] = None


def _apply_team_context(route: str | None, route_kwargs: dict, text: str) -> None:
    """Move team-subject bounds on a player route to team/opponent stats.

    The player's own bounds are read again from the question without the team
    clauses: "30 points when the Lakers score 120" kept only the 120 before.
    """
    if route not in _PLAYER_ROUTES or not route_kwargs.get("player"):
        return
    opponent = route_kwargs.get("opponent")
    if (
        isinstance(opponent, str)
        and str(route_kwargs.get("team") or "").upper() == opponent.upper()
    ):
        # "LeBron games vs Celtics when the Celtics score 120": the clause's
        # team was also taken as his; it is the opponent.
        route_kwargs["team"] = None
    own_team = str(route_kwargs.get("team") or "").upper()
    opponents = {
        str(o).upper() for o in ([opponent] if isinstance(opponent, str) else opponent or [])
    }
    items = team_subject_stat_conditions(text)
    from nbatools.commands.natural_query import (
        _OTHER_SEASON_WORDS,
        _player_latest_team,
        _team_mentions,
    )

    named = {item["team"] for item in items}
    # Named only inside the clause ("when the Celtics scored 120"); "LeBron
    # stats with the Celtics when the Celtics scored 120" names his team.
    outside = {
        team
        for start, end, team in _team_mentions(text)
        if not any(item["start"] <= start and end <= item["end"] for item in items)
    }
    his = None
    if own_team and own_team in named and own_team not in outside and not opponents:
        his = (
            None
            if _OTHER_SEASON_WORDS.search(text)
            else _player_latest_team(route_kwargs["player"])
        )
    if his and own_team != his:
        # "LeBron games when the Celtics scored 120": the team in the clause
        # is his opponent, not his team (it filtered him to Celtics games).
        route_kwargs["team"] = None
        route_kwargs["opponent"] = own_team
        opponents = {own_team}
        own_team = his
    found = []
    for item in items:
        team = item["team"]
        if team == "LA":
            # Only an LA team: the player's own when he plays for one, else
            # an LA opponent of the route.
            if own_team in ("LAL", "LAC"):
                team = own_team
            else:
                team = next((t for t in ("LAL", "LAC") if t in opponents), None)
            if team is None and not own_team and not _OTHER_SEASON_WORDS.search(text):
                # "LeBron games when LA scores 120": his team when it is LA.
                latest = _player_latest_team(route_kwargs["player"])
                if latest in ("LAL", "LAC"):
                    route_kwargs["team"] = own_team = team = latest
            if team is None:
                continue
        if team in opponents:
            found.append({**item, "side": "opponent"})
        elif team in ("TEAM", own_team):
            found.append({**item, "side": "team"})
        elif not own_team:
            # "LeBron games vs Boston when the Lakers score 120": the named
            # team is his; keep only his games for it.
            route_kwargs["team"] = own_team = team
            found.append({**item, "side": "team"})
    # "when opponents score 120", "the other team made 15 threes".
    for item in extract_opponent_points_allowed_conditions(text):
        if any(item["start"] < f["end"] and f["start"] < item["end"] for f in found):
            continue
        base = item["stat"][len("opponent_") :]
        found.append({**item, "stat": base, "side": "opponent"})
    if not found:
        return
    # "when the Lakers score 120 and 30 assists": the joined count is the
    # team's too.
    read = {c["stat"] for c in _kwargs_conditions(route_kwargs)}
    for item in list(found):
        end = item["end"]
        while m := _CLAUSE_JOINED_COUNT.match(text, end):
            stat = _stat_word(m.group("w"))
            if (
                stat is None
                or f"{item['side']}_{stat}" in read
                or any(f["stat"] == stat and f["side"] == item["side"] for f in found)
                or _COUNT_OWNER.match(text, m.end())
            ):
                # Already bounded ("allow under 110 and 30 assists"), or
                # given to someone ("and 10 assists from LeBron").
                break
            found.append(
                {
                    **item,
                    "stat": stat,
                    "min_value": float(m.group("n")),
                    "max_value": None,
                    "start": m.start(),
                    "end": m.end(),
                }
            )
            end = m.end()
    conditions = _kwargs_conditions(route_kwargs)
    context = [c for c in conditions if _is_context_stat(c["stat"])]
    own = [c for c in conditions if not _is_context_stat(c["stat"])]
    for item in found:
        target = {
            "stat": f"{item['side']}_{item['stat']}",
            "min_value": item["min_value"],
            "max_value": item["max_value"],
        }
        if not any(c["stat"] == target["stat"] and _same_bound(c, target) for c in context):
            context.append(target)

    from nbatools.commands.natural_query import parse_query

    rest = parse_query(_without_team_clauses(text, found))
    rest_kwargs = rest.get("route_kwargs") or {}
    ranking_stat = None
    if rest.get("route") in _PLAYER_ROUTES and rest_kwargs.get("player") == route_kwargs["player"]:
        own = [c for c in _kwargs_conditions(rest_kwargs) if not _is_context_stat(c["stat"])]
        # "highest scoring games when the Lakers score 120" still ranks by
        # the player's points.
        ranking_stat = rest_kwargs.get("stat")
    else:
        # The team clause's bound was read as the player's own; drop it.
        own = [
            c for c in own if not any(c["stat"] == f["stat"] and _same_bound(c, f) for f in found)
        ]
    conditions = own + context
    _clear_covered_event_refusal(route_kwargs, own)
    route_kwargs["conditions"] = conditions
    primary = next((c for c in conditions if c["stat"] == ranking_stat), None)
    if ranking_stat and primary is None:
        route_kwargs["stat"] = ranking_stat
        route_kwargs["min_value"] = None
        route_kwargs["max_value"] = None
        return
    primary = primary or conditions[0]
    route_kwargs["stat"] = primary["stat"]
    route_kwargs["min_value"] = primary["min_value"]
    route_kwargs["max_value"] = primary["max_value"]
