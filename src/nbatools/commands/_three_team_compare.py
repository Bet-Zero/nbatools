"""Three teams side by side: "Lakers vs Celtics vs Knicks", "compare A, B and C".

The comparison readers take two teams, so the first or the third was
dropped ("Lakers vs Celtics vs Knicks" compared Boston and New York, and
"compare Lakers, Celtics and Knicks" listed Boston's games).
"""

from __future__ import annotations

import re
from functools import lru_cache

from nbatools.commands.entity_resolution import TEAM_ALIASES


@lru_cache(maxsize=1)
def _team_pattern() -> str:
    keys = sorted(TEAM_ALIASES, key=len, reverse=True)
    return r"(?:the\s+)?(" + "|".join(re.escape(k) for k in keys) + r")"


def _patterns() -> tuple[re.Pattern, ...]:
    t = _team_pattern()
    vs = r"\s+(?:vs\.?|versus)\s+"
    return (
        re.compile(rf"^(?:compare\s+)?{t}{vs}{t}{vs}{t}\b(.*)$"),
        re.compile(rf"^compare\s+{t}\s*,\s*{t}\s*,?\s+(?:and|&)\s+{t}\b(.*)$"),
        re.compile(rf"^compare\s+{t}\s+(?:and|&)\s+{t}\s+(?:and|&)\s+{t}\b(.*)$"),
        re.compile(rf"^{t}\s*,\s*{t}\s*,?\s+(?:and|&)\s+{t}\s+compared\b(.*)$"),
    )


# Scope the comparison reads on its own; anything else (an opponent, a
# condition) would apply to the teams in ways this reading cannot check.
_READ_REST = re.compile(
    r"^(?:\s+(?:in|during|for|this|last|since|from|to|through|the|season|seasons|"
    r"regular|playoffs?|postseason|at|home|on|road|away|games?|stats?|records?|"
    r"comparison|per|game|points|ppg|scoring|averages?|of|and|"
    r"january|february|march|april|may|june|october|november|december|"
    r"\d{4}(?:-\d{2})?|\d+))*\s*[?.!]?$"
)


def three_teams(query: str) -> tuple[list[str], bool] | None:
    """The three teams a comparison names, and whether the rest is read scope."""
    q = query.strip()
    for rx in _patterns():
        m = rx.match(q)
        if not m:
            continue
        teams = [TEAM_ALIASES[m.group(i)] for i in (1, 2, 3)]
        if len(set(teams)) != 3:
            return None
        rest = m.group(4)
        if _READ_REST.match(rest):
            return teams, True
        if _STRETCH.search(rest):
            # "Lakers vs Celtics vs Knicks best 5 game stretch": the stretch board's.
            return None
        # "in wins", "longest win streak", "head to head": not read for three
        # teams, and another reader would drop one of them.
        return teams, False
    return None


_STRETCH = re.compile(r"\b(?:stretch(?:es)?|span|window|run)\b")
