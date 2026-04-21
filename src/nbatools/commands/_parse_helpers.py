import re

from nbatools.commands._constants import STAT_ALIASES, STAT_PATTERN
from nbatools.commands._glossary import FUZZY_LAST_N_TERMS, OPPONENT_QUALITY_TERMS
from nbatools.commands._leaderboard_utils import (
    detect_player_leaderboard_stat,
    detect_team_leaderboard_stat,
)
from nbatools.commands._matchup_utils import detect_player
from nbatools.commands.entity_resolution import PLAYER_ALIASES


def extract_top_n(text: str) -> int | None:
    # "top N" pattern
    m = re.search(r"\btop\s+(\d+)\b", text)
    if m:
        value = int(m.group(1))
        return value if value > 0 else None
    # "bottom N" pattern
    m = re.search(r"\bbottom\s+(\d+)\b", text)
    if m:
        value = int(m.group(1))
        return value if value > 0 else None
    # "rank N" / "best N" / "worst N" pattern (e.g. "best 10 scorers")
    m = re.search(r"\b(?:best|worst)\s+(\d+)\b", text)
    if m:
        value = int(m.group(1))
        return value if value > 0 else None
    return None


def wants_leaderboard(text: str) -> bool:
    if re.search(
        r"\bseason leaders?\b|\bled the league\b|\bleaders?\s+in\b"
        r"|\bleads?\s+(?:the\s+)?(?:nba|league)\s+in\b"
        r"|\b(?:career|playoff|all[- ]?time)\s+(?:\w+\s+)*leaders?\b"
        r"|\bleaders?\s+(?:since|last|past|this|over)\b"
        r"|\brank\b|\branked\b|\branking\b|\bwho\s+(?:has|had|leads?|led)\s+the\s+most\b"
        r"|\brank\s+(?:players?|teams?)\s+by\b",
        text,
    ):
        return True

    if re.search(
        r"\bin a game\b|\bsingle game\b|\bgame high\b|\bgame-high\b|\bseason[- ]?high\b", text
    ):
        return False

    # "highest/best scoring games" → single-game-best, not leaderboard
    if re.search(r"\b(?:highest|best)\s+(?:scoring\s+)?games?\b", text):
        return False

    if detect_player_leaderboard_stat(text) is None:
        return False

    # Stat-alias + the noun "leaders" anywhere is a strong leaderboard signal.
    # Covers `scoring leaders`, `points leaders`, `last 10 scoring leaders`,
    # etc., where no operator word like `most`/`best` is present.
    if re.search(r"\bleaders?\b", text):
        return True

    return bool(
        re.search(
            r"\btop(?:\s+\d+)?\b|\bhighest\b|\bmost\b|\bbest\b|\blowest\b|\bfewest\b|\bleast\b|\bworst\b|\bbottom(?:\s+\d+)?\b",
            text,
        )
    )


# ---------------------------------------------------------------------------
# Position / subset filtering for leaderboard queries
# ---------------------------------------------------------------------------

_POSITION_GROUP_PATTERNS: dict[str, str] = {
    "guards": "guards",
    "guard": "guards",
    "point guards": "guards",
    "shooting guards": "guards",
    "forwards": "forwards",
    "forward": "forwards",
    "small forwards": "forwards",
    "power forwards": "forwards",
    "centers": "centers",
    "center": "centers",
    "bigs": "bigs",
    "big men": "bigs",
    "big man": "bigs",
    "wings": "wings",
    "wing": "wings",
}


def extract_position_filter(text: str) -> str | None:
    """Extract a position-group filter from the query text.

    Returns the canonical position group name or None.
    """
    # "among guards", "among centers", "among big men", etc.
    m = re.search(r"\bamong\s+([\w\s]+?)(?:\s+(?:since|this|last|over|in|from|during|$))", text)
    if m:
        candidate = m.group(1).strip()  # already lowercase from pipeline normalization
        if candidate in _POSITION_GROUP_PATTERNS:
            return _POSITION_GROUP_PATTERNS[candidate]

    # "by guards", "for centers", etc.
    m = re.search(r"\b(?:by|for)\s+(guards?|forwards?|centers?|bigs?|big\s+men|wings?)\b", text)
    if m:
        candidate = m.group(1).strip()  # already lowercase from pipeline normalization
        if candidate in _POSITION_GROUP_PATTERNS:
            return _POSITION_GROUP_PATTERNS[candidate]

    return None


def wants_team_leaderboard(text: str) -> bool:
    if detect_team_leaderboard_stat(text) is not None:
        return True

    if re.search(r"\bteams?\b", text):
        if re.search(
            r"\b(best|highest|most|top(?:\s+\d+)?|rank|ranked|ranking|lowest|fewest|least|worst|bottom(?:\s+\d+)?)\b",
            text,
        ):
            return True

    # "rank teams by ..."
    if re.search(r"\brank\s+teams?\s+by\b", text):
        return True

    return False


def extract_season(text: str) -> str | None:
    m = re.search(r"\b(?:19|20)\d{2}-\d{2}\b", text)
    return m.group(0) if m else None


def extract_season_range(text: str) -> tuple[str | None, str | None]:
    m = re.search(r"\bfrom\s+((?:19|20)\d{2}-\d{2})\s+to\s+((?:19|20)\d{2}-\d{2})\b", text)
    if m:
        return m.group(1), m.group(2)
    return None, None


# ---------------------------------------------------------------------------
# Historical span detection
# ---------------------------------------------------------------------------


def detect_career_intent(text: str) -> bool:
    """Detect career / all-time intent in a query."""
    return bool(re.search(r"\b(career|all[- ]?time|lifetime)\b", text))


def extract_since_season(text: str) -> str | None:
    """Extract a 'since SEASON' or 'since YEAR' pattern.

    Returns the season string (e.g. '2020-21') or None.
    'since 2020-21' -> '2020-21'
    'since 2020'    -> '2020-21'  (the season starting in that year)
    """
    # Explicit season format first
    m = re.search(r"\bsince\s+((?:19|20)\d{2}-\d{2})\b", text)
    if m:
        return m.group(1)
    # Bare year
    m = re.search(r"\bsince\s+((?:19|20)\d{2})\b", text)
    if m:
        from nbatools.commands._seasons import int_to_season

        return int_to_season(int(m.group(1)))
    return None


def extract_last_n_seasons(text: str) -> int | None:
    """Extract 'last N seasons' / 'over the last N seasons' / 'past N seasons'.

    Returns N or None.
    """
    m = re.search(
        r"\b(?:(?:over|in)\s+the\s+)?(?:last|past)\s+(\d+)\s+seasons?\b",
        text,
    )
    if m:
        value = int(m.group(1))
        return value if value > 0 else None
    return None


def extract_last_n(text: str) -> int | None:
    # Fuzzy time words → fixed last-N values (glossary / spec §18.1)
    for term, last_n in FUZZY_LAST_N_TERMS.items():
        if re.search(rf"\b{re.escape(term)}\b", text):
            return last_n

    patterns = [
        r"\blast\s+(\d+)\s+games?\b",
        r"\bpast\s+(\d+)\s+games?\b",
        r"\brecent\s+(\d+)\s+games?\b",
        r"\blast\s+(\d+)(?!\s+(?:seasons?|weeks?|days?|months?))\b",
        r"\bpast\s+(\d+)(?!\s+(?:seasons?|weeks?|days?|months?))\b",
        r"\brecent\s+(\d+)(?!\s+(?:seasons?|weeks?|days?|months?))\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            value = int(m.group(1))
            return value if value > 0 else None
    return None


STREAK_SPECIAL_PATTERNS = {
    "made_three": [
        r"\bconsecutive\s+games?\s+with\s+(?:a|an|at\s+least\s+one)?\s*(?:made\s+three|made\s+3|3pm|three-pointer|three pointer)\b",  # noqa: E501
        r"\blongest\s+streak\s+of\s+(?:a|an|at\s+least\s+one)?\s*(?:made\s+three|made\s+3|3pm|three-pointer|three pointer)\b",  # noqa: E501
    ],
    "triple_double": [
        r"\blongest\s+triple[- ]double\s+streak\b",
    ],
}


def extract_streak_request(text: str) -> dict | None:
    # Receives pre-normalized text from _build_parse_state; no per-detector
    # normalization needed.
    normalized = text

    if not re.search(r"\b(streak|straight|consecutive)\b", normalized):
        return None

    for pattern in STREAK_SPECIAL_PATTERNS["triple_double"]:
        if re.search(pattern, normalized):
            return {
                "special_condition": "triple_double",
                "stat": None,
                "min_value": None,
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    m = re.search(
        r"\b(\d+)\s+straight\s+games?\s+with\s+(?:a|an|at\s+least\s+one)?\s*(?:made\s+three|made\s+3|3pm|three-pointer|three pointer)\b",  # noqa: E501
        normalized,
    )
    if m:
        return {
            "special_condition": "made_three",
            "stat": None,
            "min_value": None,
            "max_value": None,
            "min_streak_length": int(m.group(1)),
            "longest": False,
        }

    for pattern in STREAK_SPECIAL_PATTERNS["made_three"]:
        if re.search(pattern, normalized):
            return {
                "special_condition": "made_three",
                "stat": None,
                "min_value": None,
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    m = re.search(
        r"\b(\d+)\s+straight\s+games?\s+with\s+(\d+)\+\s+([a-z0-9 .%-]+?)(?=\s+(?:from|to|in|on|at|with|home|away|road|wins?|loss(?:es)?|summary|average|averages|record|for|during|playoff|playoffs|postseason|last|past|recent|form|split|over|under|between|and|or)\b|$)",  # noqa: E501
        normalized,
    )
    if m:
        stat = detect_stat(m.group(3))
        if stat:
            return {
                "special_condition": None,
                "stat": stat,
                "min_value": float(m.group(2)),
                "max_value": None,
                "min_streak_length": int(m.group(1)),
                "longest": False,
            }

    m = re.search(
        r"\blongest\s+streak\s+of\s+(\d+)(?:\+)?\s+([a-z0-9 .%-]+?)\s+games?\b",
        normalized,
    )
    if m:
        stat = detect_stat(m.group(2))
        if stat:
            return {
                "special_condition": None,
                "stat": stat,
                "min_value": float(m.group(1)),
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    # `longest streak with (at least) N STAT` — e.g.
    # "Curry longest streak with at least 3 threes"
    # "longest Curry streak with at least 3 threes" (word-order variant)
    m = re.search(
        (
            r"\blongest\s+(?:[a-z .'\-]+\s+)?streak\s+with\s+"
            r"(?:at\s+least\s+)?(\d+)(?:\+)?\s+([a-z0-9 .%-]+?)(?=\s|$)"
        ),
        normalized,
    )
    if m:
        stat = detect_stat(m.group(2))
        if stat:
            return {
                "special_condition": None,
                "stat": stat,
                "min_value": float(m.group(1)),
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    # `N+ STAT streak` or `current N+ STAT streak` — e.g.
    # "LeBron current 20+ point streak", "Jokic longest 30-point streak"
    m = re.search(
        r"\b(?:longest|current)?\s*(\d+)(?:\+)?[- ]([a-z0-9 .%-]+?)\s+streak\b",
        normalized,
    )
    if m:
        stat = detect_stat(m.group(2))
        if stat:
            longest = "longest" in normalized or "current" not in normalized
            return {
                "special_condition": None,
                "stat": stat,
                "min_value": float(m.group(1)),
                "max_value": None,
                "min_streak_length": None,
                "longest": longest,
            }

    # `consecutive N STAT games (longest)` — e.g.
    # "Jokic consecutive 30 point games longest"
    m = re.search(
        r"\bconsecutive\s+(\d+)(?:\+)?[- ]?([a-z0-9 .%-]+?)\s+games?\b",
        normalized,
    )
    if m:
        stat = detect_stat(m.group(2))
        if stat:
            longest = "longest" in normalized
            return {
                "special_condition": None,
                "stat": stat,
                "min_value": float(m.group(1)),
                "max_value": None,
                "min_streak_length": None,
                "longest": longest,
            }

    return None


TEAM_STREAK_SPECIAL_PATTERNS = {
    "wins": [
        r"\blongest\s+[a-z0-9 .&'\-]+\s+winning\s+streak\b",
        r"\blongest\s+winning\s+streak\b",
    ],
    "losses": [
        r"\blongest\s+[a-z0-9 .&'\-]+\s+losing\s+streak\b",
        r"\blongest\s+losing\s+streak\b",
    ],
}


def extract_team_streak_request(text: str) -> dict | None:
    # Receives pre-normalized text from _build_parse_state; no per-detector
    # normalization needed.
    normalized = text

    if not re.search(r"\b(streak|straight|consecutive)\b", normalized):
        return None

    m = re.search(
        r"\b(?:[a-z0-9 .&'\-]+?)\s+(\d+)\s+straight\s+games?\s+scoring\s+(\d+)\+(?:\s+(?:points?|pts))?(?=\s|$)",  # noqa: E501
        normalized,
    )
    if m:
        return {
            "special_condition": None,
            "stat": "pts",
            "min_value": float(m.group(2)),
            "max_value": None,
            "min_streak_length": int(m.group(1)),
            "longest": False,
        }

    for pattern in TEAM_STREAK_SPECIAL_PATTERNS["wins"]:
        if re.search(pattern, normalized):
            return {
                "special_condition": "wins",
                "stat": None,
                "min_value": None,
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    for pattern in TEAM_STREAK_SPECIAL_PATTERNS["losses"]:
        if re.search(pattern, normalized):
            return {
                "special_condition": "losses",
                "stat": None,
                "min_value": None,
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    m = re.search(
        r"\b(\d+)\s+straight\s+games?\s+scoring\s+(\d+)\+(?:\s+(?:points?|pts))?(?=\s|$)",
        normalized,
    )
    if m:
        return {
            "special_condition": None,
            "stat": "pts",
            "min_value": float(m.group(2)),
            "max_value": None,
            "min_streak_length": int(m.group(1)),
            "longest": False,
        }

    m = re.search(
        r"\b(\d+)\s+straight\s+games?\s+with\s+(\d+)\+\s+(?:points?|pts)\b",
        normalized,
    )
    if m:
        return {
            "special_condition": None,
            "stat": "pts",
            "min_value": float(m.group(2)),
            "max_value": None,
            "min_streak_length": int(m.group(1)),
            "longest": False,
        }

    m = re.search(
        r"\b([a-z0-9 .&'\-]+?)\s+consecutive\s+games?\s+with\s+(\d+)\+\s+(points?|pts|threes|3pm|rebounds?|reb|assists?|ast)\b",  # noqa: E501
        normalized,
    )
    if m:
        stat_text = m.group(3)
        stat = detect_stat(stat_text)
        if stat:
            return {
                "special_condition": None,
                "stat": stat,
                "min_value": float(m.group(2)),
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    m = re.search(
        r"\blongest\s+[a-z0-9 .&'\-]+\s+streak\s+with\s+(\d+)\+\s+(points?|pts|threes|3pm|rebounds?|reb|assists?|ast)\b",  # noqa: E501
        normalized,
    )
    if m:
        stat_text = m.group(2)
        stat = detect_stat(stat_text)
        if stat:
            return {
                "special_condition": None,
                "stat": stat,
                "min_value": float(m.group(1)),
                "max_value": None,
                "min_streak_length": None,
                "longest": True,
            }

    return None


def detect_stat(text: str) -> str | None:
    # Word-boundary match so short codes like "ast" do not falsely match
    # substrings in words like "last" — the pre-fix behavior of `key in text`
    # caused `top scorers last 10 games` to resolve stat to 'ast'.
    for key in sorted(STAT_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", text):
            return STAT_ALIASES[key]
    return None


def detect_season_type(text: str) -> str:
    if re.search(r"\b(playoff|playoffs|postseason)\b", text):
        return "Playoffs"
    return "Regular Season"


def default_season_for_context(season_type: str) -> str:
    if season_type == "Playoffs":
        return "2024-25"
    return "2025-26"


def detect_split_type(text: str) -> str | None:
    if re.search(r"\bhome\s+(?:vs\.?|versus)\s+away\b|\bhome\s+away\b|\baway\s+home\b", text):
        return "home_away"
    if re.search(
        r"\bwins?\s+(?:vs\.?|versus)\s+loss(?:es)?\b|\bwins?\s+loss(?:es)?\b|\bwins_losses\b|\bin\s+wins\s+(?:and|&)\s+loss(?:es)?\b",
        text,
    ):
        return "wins_losses"
    return None


def _parse_threshold_match(
    value_text: str, stat_text: str, mode: str, epsilon: float
) -> tuple[str, float | None, float | None]:
    value = float(value_text)
    stat = detect_stat(stat_text)
    if stat is None:
        raise ValueError(f"Unsupported stat phrase: {stat_text}")
    if mode == "min":
        return stat, value + epsilon, None
    return stat, None, value - epsilon


def extract_threshold_conditions(text: str) -> list[dict]:
    _NUM = r"(\d+(?:\.\d+)?|\.\d+)"

    # Standard patterns: operator NUMBER STAT
    patterns = [
        (
            rf"\bbetween\s+{_NUM}\s+and\s+{_NUM}\s+{STAT_PATTERN}\b",
            "between",
            0.0,
        ),
        (
            rf"\bover\s+{_NUM}\s+{STAT_PATTERN}\b",
            "min",
            0.0001,
        ),
        (
            rf"\bat least\s+{_NUM}\s+{STAT_PATTERN}\b",
            "min",
            0.0,
        ),
        (
            rf"\b{_NUM}\s+or\s+more\s+{STAT_PATTERN}\b",
            "min",
            0.0,
        ),
        (
            rf"\bunder\s+{_NUM}\s+{STAT_PATTERN}\b",
            "max",
            0.0001,
        ),
        (
            rf"\bless than\s+{_NUM}\s+{STAT_PATTERN}\b",
            "max",
            0.0001,
        ),
        (
            rf"\bfewer than\s+{_NUM}\s+{STAT_PATTERN}\b",
            "max",
            0.0001,
        ),
        # Shorthand: N+ STAT — "30+ points", "5+ threes" (implicit >=)
        (
            rf"\b{_NUM}\+\s*{STAT_PATTERN}\b",
            "min",
            0.0,
        ),
    ]

    # Reverse patterns: STAT operator NUMBER (for advanced stats like "TS% over .700")
    reverse_patterns = [
        (
            rf"{STAT_PATTERN}\s+over\s+{_NUM}",
            "min",
            0.0001,
        ),
        (
            rf"{STAT_PATTERN}\s+above\s+{_NUM}",
            "min",
            0.0001,
        ),
        (
            rf"{STAT_PATTERN}\s+at least\s+{_NUM}",
            "min",
            0.0,
        ),
        (
            rf"{STAT_PATTERN}\s+under\s+{_NUM}",
            "max",
            0.0001,
        ),
        (
            rf"{STAT_PATTERN}\s+below\s+{_NUM}",
            "max",
            0.0001,
        ),
        (
            rf"{STAT_PATTERN}\s+between\s+{_NUM}\s+and\s+{_NUM}",
            "between",
            0.0,
        ),
    ]

    matches = []
    for pattern, mode, epsilon in patterns:
        for m in re.finditer(pattern, text):
            if mode == "between":
                low = float(m.group(1))
                high = float(m.group(2))
                if low > high:
                    low, high = high, low
                stat = detect_stat(m.group(3))
                if stat is None:
                    continue
                matches.append(
                    {
                        "start": m.start(),
                        "end": m.end(),
                        "stat": stat,
                        "min_value": low,
                        "max_value": high,
                        "text": m.group(0),
                    }
                )
            else:
                if detect_stat(m.group(2)) is None:
                    continue
                stat, min_value, max_value = _parse_threshold_match(
                    m.group(1), m.group(2), mode, epsilon
                )
                matches.append(
                    {
                        "start": m.start(),
                        "end": m.end(),
                        "stat": stat,
                        "min_value": min_value,
                        "max_value": max_value,
                        "text": m.group(0),
                    }
                )

    # Reverse patterns: STAT comes first, then operator, then number
    for pattern, mode, epsilon in reverse_patterns:
        for m in re.finditer(pattern, text):
            stat_text = m.group(1)
            stat = detect_stat(stat_text)
            if stat is None:
                continue
            if mode == "between":
                low = float(m.group(2))
                high = float(m.group(3))
                if low > high:
                    low, high = high, low
                matches.append(
                    {
                        "start": m.start(),
                        "end": m.end(),
                        "stat": stat,
                        "min_value": low,
                        "max_value": high,
                        "text": m.group(0),
                    }
                )
            else:
                value = float(m.group(2))
                if mode == "min":
                    min_value = value + epsilon
                    max_value = None
                else:
                    min_value = None
                    max_value = value - epsilon
                matches.append(
                    {
                        "start": m.start(),
                        "end": m.end(),
                        "stat": stat,
                        "min_value": min_value,
                        "max_value": max_value,
                        "text": m.group(0),
                    }
                )

    matches.sort(key=lambda x: x["start"])

    deduped = []
    seen = set()
    for item in matches:
        key = (item["start"], item["end"], item["stat"], item["min_value"], item["max_value"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped


def extract_min_value(text: str, stat: str | None) -> float | None:
    """Fallback threshold extraction for when extract_threshold_conditions
    finds no stat-aware match.

    Handles stat-less generic patterns (``30+``, ``at least 30``) and bare
    ``N STAT`` phrases using the unified alias table from ``STAT_PATTERN``.
    """
    # Generic stat-less patterns (no stat word adjacent to number)
    patterns = [
        r"\b(\d+)\+",
        r"\bat least (\d+)\b",
        r"\bminimum (\d+)\b",
        r"\bmin(?:imum)? (\d+)\b",
        r"\b(\d+)\s+or\s+more\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return float(m.group(1))

    if stat is None:
        return None

    # Bare N STAT — uses the unified alias table instead of per-stat
    # hardcoded patterns.  Order matters: "N STAT games" is more specific
    # than bare "N STAT", so try it first.
    # Guard against matching count/limit numbers that happen to precede
    # a stat word (e.g. "last 10 scoring" where 10 is last_n, not a threshold).
    _CG = r"(?<!last )(?<!past )(?<!top )(?<!first )(?<!bottom )"
    bare_patterns = [
        rf"{_CG}\b(\d+)\s+{STAT_PATTERN}\s+games?\b",  # "30 point games"
        rf"{_CG}\b(\d+)-{STAT_PATTERN}\s+games?\b",  # "30-point games"
        rf"{_CG}\b(\d+)\s+{STAT_PATTERN}\b",  # "30 points"
        rf"{_CG}\b(\d+)-{STAT_PATTERN}\b",  # "30-points"
    ]
    for pattern in bare_patterns:
        m = re.search(pattern, text)
        if m and detect_stat(m.group(2)) == stat:
            return float(m.group(1))

    return None


def detect_home_away(text: str) -> tuple[bool, bool]:
    home_only = bool(re.search(r"\bhome\b", text))
    away_only = bool(re.search(r"\baway\b|\broad\b", text))
    return home_only, away_only


def detect_opponent_quality(text: str) -> dict | None:
    patterns = [
        (r"\b(?:against|vs\.?|versus)\s+contenders\b", "contenders"),
        (r"\b(?:against|vs\.?|versus)\s+good\s+teams\b", "good teams"),
        (r"\b(?:against|vs\.?|versus)\s+top\s+teams\b", "top teams"),
        (r"\b(?:against|vs\.?|versus)\s+playoff\s+teams\b", "playoff teams"),
        (r"\b(?:against|vs\.?|versus)\s+teams?\s+over\s+\.500\b", "teams over .500"),
        (r"\b(?:against|vs\.?|versus)\s+top[- ]10\s+defenses\b", "top-10 defenses"),
    ]
    for pattern, term in patterns:
        if re.search(pattern, text):
            policy = OPPONENT_QUALITY_TERMS[term]
            return {
                "type": "opponent_quality",
                "surface_term": term,
                "definition": dict(policy.resolved_definition),
            }
    return None


def build_opponent_quality_note(opponent_quality: dict | None = None) -> str | None:
    if opponent_quality is None:
        return None

    surface_term = opponent_quality.get("surface_term", "opponent-quality bucket")
    definition = opponent_quality.get("definition") or {}
    metric = definition.get("metric")
    value = definition.get("value")

    if metric == "conference_rank":
        return f"opponent_quality: {surface_term} -> conference rank <= {value}"
    if metric == "win_pct":
        return f"opponent_quality: {surface_term} -> win_pct {definition.get('operator')} {value}"
    if metric == "def_rating_rank":
        return f"opponent_quality: {surface_term} -> top {value} by defensive rating"
    if metric == "off_rating_rank":
        return f"opponent_quality: {surface_term} -> top {value} by offensive rating"
    return f"opponent_quality: {surface_term}"


def detect_wins_losses(text: str) -> tuple[bool, bool]:
    wins_only = bool(re.search(r"\bwins?\b|\bwon\b", text))
    losses_only = bool(re.search(r"\bloss(?:es)?\b|\blost\b", text))
    return wins_only, losses_only


def detect_clutch(text: str) -> bool:
    """Detect clutch context filter.

    Surface forms: ``clutch``, ``in the clutch``, ``clutch time``,
    ``late-game`` / ``late game``.
    """
    return bool(
        re.search(r"\bclutch\b|\bin\s+the\s+clutch\b|\bclutch\s+time\b|\blate[- ]game\b", text)
    )


def detect_back_to_back(text: str) -> bool:
    """Detect back-to-back schedule context filters."""
    return bool(
        re.search(
            r"\b(?:back[- ]to[- ]backs?|b2b)\b"
            r"|\bsecond\s+of\s+(?:a\s+)?(?:back[- ]to[- ]back|b2b)\b",
            text,
        )
    )


def detect_rest_days(text: str) -> str | int | None:
    """Detect rest-context filters.

    Returns ``"advantage"`` / ``"disadvantage"`` for relative rest phrases,
    or an integer for specific-day-rest phrases such as ``on 2 days rest``.
    """
    if re.search(r"\brest\s+advantage\b", text):
        return "advantage"
    if re.search(r"\brest\s+disadvantage\b", text):
        return "disadvantage"
    if re.search(r"\b(?:on|with|after)\s+no\s+rest\b", text):
        return 0

    number_words = {
        "zero": 0,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
    }
    word_pattern = "|".join(number_words)

    m = re.search(r"\b(?:on|with|after)\s+(\d+)\s+days?\s+rest\b", text)
    if m:
        return int(m.group(1))

    m = re.search(rf"\b(?:on|with|after)\s+({word_pattern})\s+days?\s+rest\b", text)
    if m:
        return number_words[m.group(1)]

    return None


def detect_one_possession(text: str) -> bool:
    """Detect one-possession game context filters."""
    return bool(
        re.search(
            r"\bone[- ]possession(?:\s+games?)?\b|\bwithin\s+one\s+possession\b",
            text,
        )
    )


def detect_nationally_televised(text: str) -> bool:
    """Detect national-TV context filters."""
    return bool(
        re.search(
            r"\bnationally\s+televised\b|\bon\s+national\s+tv\b|\bnational\s+tv\b",
            text,
        )
    )


def detect_role(text: str) -> str | None:
    """Detect starter/bench role filters for player-context queries."""
    if re.search(r"\bas\s+(?:a\s+)?starter\b|\bstarting\b", text):
        return "starter"
    if re.search(r"\boff\s+the\s+bench\b|\bcoming\s+off\s+the\s+bench\b", text):
        return "bench"
    if re.search(r"\bbench\b|\breserve\b", text):
        return "bench"
    return None


def detect_quarter(text: str) -> str | None:
    """Detect quarter-level context filters.

    Surface forms: ``1st quarter`` / ``first quarter`` through
    ``4th quarter`` / ``fourth quarter``, plus ``overtime`` / ``OT``.
    """
    patterns = (
        (r"\b(?:1st|first)\s+quarter\b|\bq1\b", "1"),
        (r"\b(?:2nd|second)\s+quarter\b|\bq2\b", "2"),
        (r"\b(?:3rd|third)\s+quarter\b|\bq3\b", "3"),
        (r"\b(?:4th|fourth)\s+quarter\b|\bq4\b", "4"),
        (r"\b(?:overtime|ot)\b", "OT"),
    )
    for pattern, value in patterns:
        if re.search(pattern, text):
            return value
    return None


def detect_half(text: str) -> str | None:
    """Detect half-level context filters.

    Surface forms: ``first half`` / ``1st half`` and
    ``second half`` / ``2nd half``.
    """
    if re.search(r"\b(?:1st|first)\s+half\b", text):
        return "first"
    if re.search(r"\b(?:2nd|second)\s+half\b", text):
        return "second"
    return None


def build_period_filter_note(
    quarter: str | None = None,
    half: str | None = None,
) -> str | None:
    """Describe the current quarter/half-filter limitation honestly.

    The parser recognizes these surface forms, but the current game-log
    layer does not expose period-level splits, so results remain unfiltered.
    """
    if quarter is not None:
        return (
            "quarter: filter detected but quarter/half splits are not yet available "
            "in the current game-log data; results are unfiltered"
        )
    if half is not None:
        return (
            "half: filter detected but quarter/half splits are not yet available "
            "in the current game-log data; results are unfiltered"
        )
    return None


def detect_on_off(text: str) -> dict | None:
    """Detect single-player on/off phrasing."""
    phrase_patterns = (
        (r"\bwith\s+([a-z0-9 .&'\-]+?)\s+on\s+(?:the\s+)?floor\b", "on"),
        (r"\bwith\s+([a-z0-9 .&'\-]+?)\s+on\s+court\b", "on"),
        (r"\bwithout\s+([a-z0-9 .&'\-]+?)\s+on\s+(?:the\s+)?floor\b", "off"),
        (r"\bwithout\s+([a-z0-9 .&'\-]+?)\s+on\s+court\b", "off"),
        (r"\b([a-z0-9 .&'\-]+?)\s+on\s+court\b", "on"),
        (r"\b([a-z0-9 .&'\-]+?)\s+off\s+court\b", "off"),
        (r"\b([a-z0-9 .&'\-]+?)\s+sitting\b", "off"),
    )

    for pattern, presence_state in phrase_patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        player = detect_player(match.group(1).strip())
        if player:
            return {
                "lineup_members": [player],
                "presence_state": presence_state,
            }

    if re.search(r"\bon/off\b", text):
        player = detect_player(text)
        if player:
            return {
                "lineup_members": [player],
                "presence_state": "both",
            }

    return None


def build_on_off_note(
    lineup_members: list[str] | None = None,
    presence_state: str | None = None,
) -> str | None:
    """Describe the current on/off placeholder behavior honestly."""
    if not lineup_members or presence_state is None:
        return None
    return (
        "on_off: query recognized but on/off splits require play-by-play or lineup-stint "
        "data that is not yet available in the current data layer; placeholder route returned"
    )


def _extract_stretch_window_size(text: str) -> int | None:
    patterns = (
        r"\b(\d+)\s*(?:-\s*|\s+)games?(?:\s+[a-z0-9%.'/-]+){0,3}\s+stretch\b",
        r"\brolling\s+(\d+)\s*(?:-\s*|\s+)games?\b",
        r"\brolling\s+(\d+)\s+games?\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        value = int(match.group(1))
        return value if value > 0 else None
    return None


def detect_stretch_query(text: str) -> dict | None:
    """Detect rolling-window stretch leaderboard queries."""
    stretch_marker = bool(re.search(r"\bstretch\b", text))
    rolling_marker = bool(re.search(r"\brolling\b", text))
    if not stretch_marker and not rolling_marker:
        return None

    window_size = _extract_stretch_window_size(text)
    if window_size is None:
        return None

    if re.search(r"\b(?:winning|losing)\s+streak\b", text):
        return None

    if re.search(r"\bgame\s+score\b", text):
        stretch_metric = "game_score"
    else:
        explicit_stat = detect_stat(text)
        if explicit_stat is not None:
            stretch_metric = explicit_stat
        elif re.search(r"\b(?:efficient|efficiency)\b", text):
            stretch_metric = "ts_pct"
        else:
            stretch_metric = "game_score"

    return {
        "window_size": window_size,
        "stretch_metric": stretch_metric,
    }


def _extract_player_mentions(text: str) -> list[str]:
    matched_spans: list[tuple[int, int]] = []
    ordered_matches: list[tuple[int, str]] = []
    sorted_aliases = sorted(
        PLAYER_ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for alias, canonical in sorted_aliases:
        for match in re.finditer(rf"\b{re.escape(alias)}\b", text):
            span = match.span()
            if any(not (span[1] <= start or span[0] >= end) for start, end in matched_spans):
                continue
            matched_spans.append(span)
            ordered_matches.append((span[0], canonical))
            break

    players: list[str] = []
    seen: set[str] = set()
    for _, canonical in sorted(ordered_matches, key=lambda item: item[0]):
        if canonical in seen:
            continue
        players.append(canonical)
        seen.add(canonical)
    return players


def detect_lineup_query(text: str) -> dict | None:
    """Detect lineup and unit phrasing that should route to lineup placeholders."""
    lineup_marker = bool(re.search(r"\b(?:lineups?|units?|combos?)\b", text))
    together_marker = bool(re.search(r"\btogether\b", text))
    leaderboard_marker = bool(re.search(r"\b(?:best|top|leaders?|highest|lowest)\b", text))
    with_lineup_marker = bool(re.search(r"\blineup\s+with\b", text))

    if not lineup_marker and not together_marker and not with_lineup_marker:
        return None

    unit_size_match = re.search(r"\b([235])\s*(?:-\s*|\s+)man\b", text)
    unit_size = int(unit_size_match.group(1)) if unit_size_match else None

    minute_patterns = (
        r"\bat\s+least\s+(\d+)\+?\s+minutes\b",
        r"\bwith\s+(\d+)\+?\s+minutes\b",
        r"\b(\d+)\+\s+minutes\b",
        r"\b(\d+)\s+minutes\b",
    )
    minute_minimum = None
    for pattern in minute_patterns:
        match = re.search(pattern, text)
        if match:
            minute_minimum = int(match.group(1))
            break

    lineup_members = _extract_player_mentions(text)
    if not lineup_marker and not together_marker and len(lineup_members) < 2:
        return None

    route = "lineup_leaderboard"
    if lineup_members and (with_lineup_marker or together_marker) and not leaderboard_marker:
        route = "lineup_summary"

    if unit_size is None and lineup_members:
        unit_size = len(lineup_members)

    return {
        "route": route,
        "lineup_members": lineup_members,
        "unit_size": unit_size,
        "minute_minimum": minute_minimum,
    }


def build_lineup_note(
    lineup_members: list[str] | None = None,
    unit_size: int | None = None,
    minute_minimum: int | None = None,
) -> str | None:
    """Describe the current lineup placeholder behavior honestly."""
    if not lineup_members and unit_size is None and minute_minimum is None:
        return None
    return (
        "lineup: query recognized but lineup-unit stats require lineup tables or stint-level "
        "data that is not yet available in the current data layer; placeholder route returned"
    )


def build_game_context_filter_notes(
    *,
    back_to_back: bool = False,
    rest_days: str | int | None = None,
    one_possession: bool = False,
    nationally_televised: bool = False,
) -> list[str]:
    """Describe current schedule-context limitations honestly.

    The parser recognizes these surface forms, but the current query engine
    does not yet join the needed schedule/context features into route
    execution, so results remain unfiltered.
    """
    notes: list[str] = []

    if back_to_back:
        notes.append(
            "back_to_back: filter detected but schedule/context feature tables are not yet "
            "joined into the current query engine; results are unfiltered"
        )
    if rest_days is not None:
        notes.append(
            "rest: filter detected but schedule/context feature tables are not yet joined "
            "into the current query engine; results are unfiltered"
        )
    if one_possession:
        notes.append(
            "one_possession: filter detected but schedule/context feature tables are not yet "
            "joined into the current query engine; results are unfiltered"
        )
    if nationally_televised:
        notes.append(
            "national_tv: filter detected but national-TV schedule metadata is not yet joined "
            "into the current query engine; results are unfiltered"
        )

    return notes


def build_role_filter_note(role: str | None = None) -> str | None:
    """Describe the current starter/bench role-filter limitation honestly."""
    if role is None:
        return None
    return (
        f"role: {role} filter detected but starter/bench filtering is not yet wired into "
        "the current query engine; results are unfiltered"
    )


def wants_summary(text: str) -> bool:
    # Word-bounded so `record` does not match `recorded` etc.
    if re.search(
        r"\bsummary\b|\bsummarize\b|\baverage\b|\baverages\b|\bavg\b"
        r"|\brecord\b|\bwhat is the record\b|\bwhat was the record\b",
        text,
    ):
        return True
    # Verb-phrase triggers for summary intent. Word-bounded so that
    # substrings like `perform` don't accidentally match `form`, and tight
    # enough not to pick up `how many` / `how often` (which are counting
    # intents, handled elsewhere).
    if re.search(
        r"\bhow\s+(?:has|have|did|do|does)\s+(?:the\s+)?[\w'\-]+"
        r"(?:\s+[\w'\-]+){0,4}\s+"
        r"(?:perform|performs|performed|play|plays|played|shoot|shoots|shot"
        r"|score|scores|scored|rebound|rebounds|rebounded|done|fared|fare)\b",
        text,
    ):
        return True
    if re.search(r"\brecent\s+form\b|\bform\b", text):
        # Preserve pre-existing `form` / `recent form` detection, but guard
        # with a word boundary so substrings like `perform` do not count.
        return True
    return False


def wants_finder(text: str) -> bool:
    """Detect explicit list/finder intent.

    Triggers on phrases like 'show me', 'list', 'find', 'give me',
    'what games', 'which games', 'show all', 'show every', 'show games'.
    """
    return bool(
        re.search(
            r"\b(show\s+me|list|find|give\s+me|what\s+games|which\s+games"
            r"|show\s+all|show\s+every|show\s+games)\b",
            text,
        )
    )


def wants_count(text: str) -> bool:
    """Detect explicit count intent.

    Triggers on phrases like 'how many', 'count', 'number of',
    'total number', 'total count', 'total games'.
    """
    return bool(
        re.search(
            r"\b(how\s+many|count|number\s+of|total\s+(?:number|count|games))\b",
            text,
        )
    )


def detect_season_high_intent(text: str) -> bool:
    """Detect single-game-best / season-high intent.

    Triggers on:
    - 'season high' / 'season-high'
    - 'best game' / 'best single game'
    - 'highest game' / 'highest single game'
    - 'game high' / 'game-high'
    - 'best scoring game(s)'
    - 'highest scoring game(s)'
    """
    return bool(
        re.search(
            r"\bseason[- ]?high\b"
            r"|\bbest\s+(?:single\s+)?(?:scoring\s+)?games?\b"
            r"|\bhighest\s+(?:single\s+)?(?:scoring\s+)?games?\b"
            r"|\bgame[- ]?high\b"
            r"|\bsingle[- ]?game\s+(?:high|best|record)\b",
            text,
        )
    )


def detect_distinct_player_count(text: str) -> bool:
    """Detect 'how many players' / 'number of players' counting intent.

    Triggers on queries asking for count of distinct players meeting a condition.
    Example: 'How many players have recorded 10+ assists in a game this year?'
    """
    return bool(
        re.search(
            r"\bhow\s+many\s+players?\b"
            r"|\bnumber\s+of\s+players?\b"
            r"|\bcount\s+(?:of\s+)?(?:distinct\s+)?players?\b",
            text,
        )
    )


def detect_distinct_team_count(text: str) -> bool:
    """Detect 'how many teams' counting intent."""
    return bool(
        re.search(
            r"\bhow\s+many\s+teams?\b"
            r"|\bnumber\s+of\s+teams?\b"
            r"|\bcount\s+(?:of\s+)?(?:distinct\s+)?teams?\b",
            text,
        )
    )


def wants_recent_form(text: str) -> bool:
    return bool(re.search(r"\b(recent form|form)\b", text))


def wants_split_summary(text: str) -> bool:
    return "split" in text or detect_split_type(text) is not None
