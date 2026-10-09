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
    r"|record(?:s|ed)?|dish(?:es|ed)?|commit(?:s|ted)?)\s+"
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


def apply_player_game_context(route: str | None, route_kwargs: dict, text: str) -> None:
    """Read team/opponent bounds and the ranking stat of a player game list."""
    _apply_allowed_ranking(route, route_kwargs, text)
    _apply_team_context(route, route_kwargs, text)
    _apply_ranked_events(route, route_kwargs, text)
    _apply_ranking_stat(route, route_kwargs, text)
    _apply_ranking_direction(route, route_kwargs, text)


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
_RANKING_WORDS = re.compile(r"\b(?:highest|most|top|best|biggest|largest|lowest|fewest|least|by)\b")


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
)


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
_OPPONENT_BOUND = re.compile(r"\ballowed\b|\bgiven\s+up\b|\bopponents?\b|\bopp\b")


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


def _apply_ranked_events(route: str | None, route_kwargs: dict, text: str) -> None:
    """Rank by the stat a rank word names and keep the game conditions.

    "most rebounds in a game with 30 points" read the 30 as a rebound bound
    and refused; "top 5 games by assists with 30 points" dropped the 30
    points; "fewest points in a 30 minute game" dropped the minutes.
    """
    if route not in _RANKED_ROUTES or route_kwargs.get("sort_by") != "stat":
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
            if stat == "pts" and float(m.group("n")) < 10 and pattern is _EVENT_PATTERNS[1]:
                # "3 point games" are games decided by 3 points.
                continue
            events.append({"stat": stat, "min_value": float(m.group("n")), "max_value": None})
    if not events:
        return
    ceiling = _EVENT_CEILING if route == "player_game_finder" else {}
    if any(e["min_value"] >= ceiling.get(e["stat"], float("inf")) for e in events) or any(
        a["stat"] == b["stat"] and not _same_bound(a, b) for a in events for b in events
    ):
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


def _apply_ranking_stat(route: str | None, route_kwargs: dict, text: str) -> None:
    """Rank a filtered game list by the stat the question ranks by.

    "LeBron highest scoring games with 10 assists" put the assist bound in
    the ranking slot: the list was ordered by assists, or refused because
    points went unused. The bound stays a condition and points rank.
    """
    if route not in _RANKED_ROUTES or route_kwargs.get("sort_by") != "stat":
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
    filtered |= {s.split("_", 1)[1] for s in filtered if _is_context_stat(s)}
    candidates = [
        metric
        for metric in named_metrics({"normalized_query": text})
        if metric not in filtered and not occurrence_count_column_condition(metric)
    ]
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
    own_team = str(route_kwargs.get("team") or "").upper()
    opponent = route_kwargs.get("opponent")
    opponents = {
        str(o).upper() for o in ([opponent] if isinstance(opponent, str) else opponent or [])
    }
    found = []
    for item in team_subject_stat_conditions(text):
        team = item["team"]
        if team == "LA":
            # Only an LA team: the player's own when he plays for one, else
            # an LA opponent of the route.
            if own_team in ("LAL", "LAC"):
                team = own_team
            else:
                team = next((t for t in ("LAL", "LAC") if t in opponents), None)
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
