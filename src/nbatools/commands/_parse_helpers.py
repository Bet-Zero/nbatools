import re

from nbatools.commands._constants import STAT_ALIASES, STAT_PATTERN, normalize_text
from nbatools.commands._leaderboard_utils import (
    detect_player_leaderboard_stat,
    detect_team_leaderboard_stat,
)


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
        candidate = m.group(1).strip().lower()
        if candidate in _POSITION_GROUP_PATTERNS:
            return _POSITION_GROUP_PATTERNS[candidate]

    # "by guards", "for centers", etc.
    m = re.search(r"\b(?:by|for)\s+(guards?|forwards?|centers?|bigs?|big\s+men|wings?)\b", text)
    if m:
        candidate = m.group(1).strip().lower()
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
    patterns = [
        r"\blast\s+(\d+)\s+games?\b",
        r"\bpast\s+(\d+)\s+games?\b",
        r"\brecent\s+(\d+)\s+games?\b",
        r"\blast\s+(\d+)(?!\s+seasons?)\b",
        r"\bpast\s+(\d+)(?!\s+seasons?)\b",
        r"\brecent\s+(\d+)(?!\s+seasons?)\b",
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
    normalized = normalize_text(text)

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
    normalized = normalize_text(text)

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
    if re.search(r"\bhome\s+vs\s+away\b|\bhome\s+away\b|\baway\s+home\b", text):
        return "home_away"
    if re.search(r"\bwins?\s+vs\s+loss(?:es)?\b|\bwins?\s+loss(?:es)?\b|\bwins_losses\b", text):
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

    stat_phrase_patterns = {
        "pts": [
            r"\b(\d+)\s+point games?\b",
            r"\b(\d+)\s+points\b",
            r"\b(\d+)-point games?\b",
            r"\b(\d+)-points?\b",
        ],
        "reb": [
            r"\b(\d+)\s+rebound games?\b",
            r"\b(\d+)\s+rebounds\b",
            r"\b(\d+)-rebound games?\b",
        ],
        "ast": [
            r"\b(\d+)\s+assist games?\b",
            r"\b(\d+)\s+assists\b",
            r"\b(\d+)-assist games?\b",
        ],
        "stl": [
            r"\b(\d+)\s+steal games?\b",
            r"\b(\d+)\s+steals\b",
            r"\b(\d+)-steal games?\b",
        ],
        "blk": [
            r"\b(\d+)\s+block games?\b",
            r"\b(\d+)\s+blocks\b",
            r"\b(\d+)-block games?\b",
        ],
        "fg3m": [
            r"\b(\d+)\s+three games?\b",
            r"\b(\d+)\s+threes\b",
            r"\b(\d+)\s+3s\b",
            r"\b(\d+)\s+3pm\b",
            r"\b(\d+)\s+threes made\b",
        ],
        "tov": [
            r"\b(\d+)\s+turnover games?\b",
            r"\b(\d+)\s+turnovers\b",
            r"\b(\d+)-turnover games?\b",
        ],
    }

    for pattern in stat_phrase_patterns.get(stat, []):
        m = re.search(pattern, text)
        if m:
            return float(m.group(1))

    return None


def detect_home_away(text: str) -> tuple[bool, bool]:
    home_only = bool(re.search(r"\bhome\b", text))
    away_only = bool(re.search(r"\baway\b|\broad\b", text))
    return home_only, away_only


def detect_wins_losses(text: str) -> tuple[bool, bool]:
    wins_only = bool(re.search(r"\bwins?\b|\bwon\b", text))
    losses_only = bool(re.search(r"\bloss(?:es)?\b|\blost\b", text))
    return wins_only, losses_only


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
