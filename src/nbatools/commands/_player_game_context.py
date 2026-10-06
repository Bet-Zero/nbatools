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


def apply_player_game_context(route: str | None, route_kwargs: dict, text: str) -> None:
    """Read team/opponent bounds and the ranking stat of a player game list."""
    _apply_team_context(route, route_kwargs, text)
    _apply_ranking_stat(route, route_kwargs, text)
    _apply_ranking_direction(route, route_kwargs, text)


# "lowest scoring games", "fewest turnovers": rank from the bottom. "at least"
# is a bound, not a direction.
_ASCENDING_WORDS = re.compile(r"\b(?:lowest|fewest|(?<!\bat )least)\b")


def _apply_ranking_direction(route: str | None, route_kwargs: dict, text: str) -> None:
    """A player game list ranked by a stat runs lowest first when asked."""
    if route != "player_game_finder" or route_kwargs.get("sort_by") != "stat":
        return
    if _ASCENDING_WORDS.search(text):
        route_kwargs["ascending"] = True


# "highest scoring games", "top 5 games by assists", "most rebounds in a game".
_RANKING_WORDS = re.compile(r"\b(?:highest|most|top|best|biggest|largest|lowest|fewest|least|by)\b")


def _apply_ranking_stat(route: str | None, route_kwargs: dict, text: str) -> None:
    """Rank a filtered game list by the stat the question ranks by.

    "LeBron highest scoring games with 10 assists" put the assist bound in
    the ranking slot: the list was ordered by assists, or refused because
    points went unused. The bound stays a condition and points rank.
    """
    if route != "player_game_finder" or route_kwargs.get("sort_by") != "stat":
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
    from nbatools.commands.player_game_finder import ALLOWED_STATS

    if candidates[0] not in ALLOWED_STATS:
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
