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

    # "top/highest/best scoring games" -> single-game-best, not a season leaderboard.
    if re.search(
        rf"\b(?:top|highest|best)\s+(?:single[- ]?)?(?:(?:team|player)\s+)?"
        rf"{STAT_PATTERN}\s+(?:(?:team|player)\s+)?games?\b",
        text,
    ):
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
            r"\btop(?:\s+\d+)?\b|\bhighest\b|\bmost\b|\bbest\b|\bhottest\b|\blowest\b|\bfewest\b|\bleast\b|\bworst\b|\bbottom(?:\s+\d+)?\b",
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
    "point guard": "guards",
    "shooting guards": "guards",
    "shooting guard": "guards",
    "forwards": "forwards",
    "forward": "forwards",
    "small forwards": "forwards",
    "small forward": "forwards",
    "power forwards": "forwards",
    "power forward": "forwards",
    "centers": "centers",
    "center": "centers",
    "bigs": "bigs",
    "big men": "bigs",
    "big man": "bigs",
    "wings": "wings",
    "wing": "wings",
}


def _position_term_pattern() -> str:
    terms = sorted(_POSITION_GROUP_PATTERNS, key=len, reverse=True)
    return "|".join(re.escape(term) for term in terms)


def extract_position_filter(text: str) -> str | None:
    """Extract a position-group filter from the query text.

    Returns the canonical position group name or None.
    """
    position_pattern = _position_term_pattern()

    # "among guards", "among centers", "among big men", etc.
    m = re.search(
        r"\bamong\s+([\w\s]+?)(?=\s+(?:since|this|last|over|in|from|during)\b|[^\w\s]|$)",
        text,
    )
    if m:
        candidate = m.group(1).strip()  # already lowercase from pipeline normalization
        if candidate in _POSITION_GROUP_PATTERNS:
            return _POSITION_GROUP_PATTERNS[candidate]

    # "by guards", "for centers", etc.
    m = re.search(rf"\b(?:by|for)\s+({position_pattern})\b", text)
    if m:
        candidate = m.group(1).strip()  # already lowercase from pipeline normalization
        if candidate in _POSITION_GROUP_PATTERNS:
            return _POSITION_GROUP_PATTERNS[candidate]

    # Noun-prefix leaderboard forms:
    # "centers rebound leaders", "guard scoring leaders",
    # "Which centers have the most rebounds".
    m = re.search(
        rf"^(?:which\s+|what\s+)?({position_pattern})\b"
        r"(?=\s+(?:"
        r"have|has|had|average|averages|averaged|lead|leads|led|leaders?|"
        r"scoring|score|scores|points?|pts|rebound(?:s|ing)?|reb|assists?|ast|"
        r"blocks?|blk|steals?|stl|turnovers?|tov|fg|field|effective|true|"
        r"three|3|ts|efg|ft|free"
        r")\b)",
        text,
    )
    if m:
        candidate = m.group(1).strip()
        if candidate in _POSITION_GROUP_PATTERNS:
            return _POSITION_GROUP_PATTERNS[candidate]

    return None


def detect_rookie_leaderboard_boundary(text: str) -> bool:
    """Detect unsupported rookie leaderboard requests."""
    return bool(re.search(r"\brookies?\b", text) and wants_leaderboard(text))


def detect_role_leaderboard_boundary(text: str) -> bool:
    """Detect unsupported league-wide starter/bench leaderboard requests."""
    if not wants_leaderboard(text):
        return False
    return bool(
        re.search(
            r"\b(?:bench|off\s+the\s+bench|reserves?|starters?|starting)\b",
            text,
        )
    )


def detect_team_bench_scoring_boundary(text: str) -> bool:
    """Detect unsupported team bench scoring requests."""
    return bool(
        re.search(r"\b(?:bench|reserves?)\b", text)
        and re.search(r"\b(?:scoring|score|points?|pts)\b", text)
    )


_AWARD_TERMS_PATTERN = (
    r"(?:"
    r"\bmvp\b|"
    r"\bmost\s+valuable\s+player\b|"
    r"\brookie\s+of\s+the\s+year\b|"
    r"\bdefensive\s+player\s+of\s+the\s+year\b|"
    r"\bdpoy\b|"
    r"\bsixth\s+man(?:\s+of\s+the\s+year)?\b|"
    r"\bmost\s+improved(?:\s+player)?\b|"
    r"\bmip\b|"
    r"\bcoach\s+of\s+the\s+year\b|"
    r"\bclutch\s+player\s+of\s+the\s+year\b|"
    r"\bawards?\b"
    r")"
)


def detect_award_query_boundary(text: str) -> bool:
    """Detect unsupported awards-result requests without inferring from stats."""
    if not re.search(_AWARD_TERMS_PATTERN, text):
        return False

    return bool(
        re.search(r"\b(?:who|which|what)\s+(?:player\s+)?won\b", text)
        or re.search(r"\bwon\s+(?:the\s+)?", text)
        or re.search(r"\bwinners?\b", text)
    )


def detect_opponent_conference(text: str) -> str | None:
    """Extract a normalized opponent-conference filter from supported phrasing."""
    patterns = [
        r"\b(?:against|vs\.?|versus)\s+(?:the\s+)?"
        r"(?P<direction>eastern|western)\s+conference\s+(?:teams?|opponents?)\b",
        r"\b(?:against|vs\.?|versus)\s+(?:the\s+)?"
        r"(?P<direction>east|west)\s+(?:teams?|opponents?)\b",
        r"\b(?:against|vs\.?|versus)\s+(?:the\s+)?"
        r"(?P<direction>eastern|western)\s+conference\b(?!\s+finals?\b)",
        r"\b(?:against|vs\.?|versus)\s+(?:the\s+)?"
        r"(?P<direction>east|west)\b(?!\s+(?:coast|conference\s+finals?|finals?)\b)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        direction = match.group("direction")
        if direction in {"east", "eastern"}:
            return "East"
        if direction in {"west", "western"}:
            return "West"
    return None


def detect_opponent_conference_boundary(text: str) -> bool:
    """Detect supported opponent-conference filter phrasing."""
    return detect_opponent_conference(text) is not None


def detect_opponent_conference_geography_boundary(text: str) -> bool:
    """Detect unsupported geography wording that resembles a conference filter."""
    return bool(
        re.search(
            r"\b(?:against|vs\.?|versus)\s+(?:the\s+)?(?:east|west)\s+coast\s+teams?\b",
            text,
        )
    )


_DIVISION_NAMES_PATTERN = r"atlantic|central|southeast|northwest|pacific|southwest"
_OPPONENT_DIVISION_PATTERN = re.compile(
    rf"\b(?:against|vs\.?|versus)\s+(?:the\s+)?"
    rf"(?P<conference_prefix>(?:east|west|eastern|western)\s+(?:conference\s+)?)?"
    rf"(?P<division>{_DIVISION_NAMES_PATTERN})\s+division"
    rf"(?:\s+(?:teams?|opponents?))?\b"
)


def _normalize_division_name(value: str) -> str:
    return {
        "atlantic": "Atlantic",
        "central": "Central",
        "southeast": "Southeast",
        "northwest": "Northwest",
        "pacific": "Pacific",
        "southwest": "Southwest",
    }[value.strip().lower()]


def detect_opponent_division(text: str) -> str | None:
    """Extract a normalized opponent-division filter for accepted phrasing."""
    match = _OPPONENT_DIVISION_PATTERN.search(text)
    if not match:
        return None
    if match.group("conference_prefix"):
        return None
    return _normalize_division_name(match.group("division"))


def detect_opponent_division_boundary(text: str) -> bool:
    """Detect explicit NBA opponent-division record filters."""
    return bool(_OPPONENT_DIVISION_PATTERN.search(text))


def wants_team_leaderboard(text: str) -> bool:
    if detect_team_leaderboard_stat(text) is not None:
        return True

    if re.search(r"\bteam\s+records?\b", text):
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


def extract_relative_season(text: str, season_type: str) -> str | None:
    """Extract singular relative season phrases such as ``last season``."""
    if re.search(r"\b(?:last|previous)\s+season\b", text):
        from nbatools.commands._seasons import previous_season

        return previous_season(season_type)
    return None


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
    normalized = re.sub(r"[?.!,]+$", "", text)

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


def detect_player_summary_stat_context(text: str) -> str | None:
    """Detect narrow stat-context phrases that should not imply thresholds."""
    if re.search(r"\bfrom\s+(?:three|3)\b", text):
        return "fg3m"
    return None


_OPPONENT_QUALITY_PREFIX_PATTERN = (
    r"(?:against|vs\.?|versus)\s+(?:the\s+)?"
    r"(?:(?:east|west|eastern|western)(?:\s+conference)?\s+)?"
)

_PLAYOFF_TEAM_OPPONENT_QUALITY_PATTERNS = [
    rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}(?:playoff|postseason)\s+teams\b",
    r"\b(?:against|vs\.?|versus)\s+teams?\s+that\s+(?:made|make|qualified\s+for|qualify\s+for)\s+(?:the\s+)?(?:playoffs|postseason)\b",
    rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}playoff\s+qualifiers\b",
]

_NON_PLAYOFF_TEAM_OPPONENT_QUALITY_PATTERNS = [
    rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}(?:non[- ]playoff|non[- ]postseason)\s+teams\b",
    r"\b(?:against|vs\.?|versus)\s+teams?\s+that\s+(?:missed|miss)\s+(?:the\s+)?(?:playoffs|postseason)\b",
]


def detects_playoff_team_opponent_quality(text: str) -> bool:
    return any(
        re.search(pattern, text)
        for pattern in (
            *_PLAYOFF_TEAM_OPPONENT_QUALITY_PATTERNS,
            *_NON_PLAYOFF_TEAM_OPPONENT_QUALITY_PATTERNS,
        )
    )


def _has_explicit_playoff_competition_context(text: str) -> bool:
    patterns = [
        r"\b(?:in|during)\s+(?:the\s+)?(?:playoffs|postseason)\b",
        r"\b(?:playoff|postseason)\s+(?:record|history|games?|series|summary|leaders?|leaderboard|appearances?)\b",
        r"\b(?:record|games?|summary|leaders?|leaderboard)\s+(?:in|during|for)\s+(?:the\s+)?(?:playoffs|postseason)\b",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def detect_season_type(text: str) -> str:
    if re.search(r"\b(playoff|playoffs|postseason)\b", text):
        if detects_playoff_team_opponent_quality(
            text
        ) and not _has_explicit_playoff_competition_context(text):
            return "Regular Season"
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


_PERCENTAGE_THRESHOLD_STATS = {"fg_pct", "fg3_pct", "ft_pct", "efg_pct", "ts_pct"}


def _normalize_threshold_value(value_text: str, stat: str) -> float:
    value = float(value_text)
    if stat in _PERCENTAGE_THRESHOLD_STATS and value > 1:
        return value / 100
    return value


def _threshold_bounds(
    value_text: str,
    stat: str,
    mode: str,
    epsilon: float,
) -> tuple[float | None, float | None]:
    value = _normalize_threshold_value(value_text, stat)
    if mode == "min":
        return value + epsilon, None
    return None, value - epsilon


def _parse_threshold_match(
    value_text: str, stat_text: str, mode: str, epsilon: float
) -> tuple[str, float | None, float | None]:
    stat = detect_stat(stat_text)
    if stat is None:
        raise ValueError(f"Unsupported stat phrase: {stat_text}")
    min_value, max_value = _threshold_bounds(value_text, stat, mode, epsilon)
    return stat, min_value, max_value


def _shooting_percentage_stat_for_context(match_text: str) -> str:
    if re.search(r"\b(?:from\s+)?(?:three|3)\b", match_text):
        return "fg3_pct"
    if re.search(r"\b(?:free\s+throws?|from\s+the\s+line)\b", match_text):
        return "ft_pct"
    return "fg_pct"


def _extract_shooting_percentage_conditions(text: str) -> list[dict]:
    """Infer shooting percentage thresholds from clear shooting contexts only."""
    _NUM = r"(\d+(?:\.\d+)?|\.\d+)(?:\s*(?:%|percent))?"
    operator = r"(over|above|at\s+least|under|below|less\s+than)"
    patterns = [
        rf"\b(?:shoots?|shooting|shot)\s+{operator}\s+{_NUM}(?:\s+from\s+(?:the\s+)?(?:field|three|3))?\b",
        rf"\b(?:from\s+(?:the\s+)?(?:field|three|3))\s+{operator}\s+{_NUM}\b",
        rf"\b(?:free\s+throws?|from\s+the\s+line)\s+{operator}\s+{_NUM}\b",
    ]

    matches = []
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            op = m.group(1)
            value_text = m.group(2)
            mode = "min" if op in {"over", "above", "at least"} else "max"
            epsilon = 0.0 if op == "at least" else 0.0001
            stat = _shooting_percentage_stat_for_context(m.group(0))
            min_value, max_value = _threshold_bounds(value_text, stat, mode, epsilon)
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
    return matches


def extract_threshold_conditions(text: str) -> list[dict]:
    _NUM = r"(\d+(?:\.\d+)?|\.\d+)(?:\s*(?:%|percent))?"

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
                stat = detect_stat(m.group(3))
                if stat is None:
                    continue
                low = _normalize_threshold_value(m.group(1), stat)
                high = _normalize_threshold_value(m.group(2), stat)
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
                low = _normalize_threshold_value(m.group(2), stat)
                high = _normalize_threshold_value(m.group(3), stat)
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
                min_value, max_value = _threshold_bounds(m.group(2), stat, mode, epsilon)
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

    matches.extend(_extract_shooting_percentage_conditions(text))

    matches.sort(key=lambda x: x["start"])

    deduped = []
    seen = set()
    for item in matches:
        key = (item["start"], item["end"], item["stat"], item["min_value"], item["max_value"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped


def extract_opponent_points_allowed_conditions(text: str) -> list[dict]:
    """Extract defensive points-allowed thresholds.

    Phrases like "held opponents under 100 points" describe the opponent's
    score, not the subject team's points. Keep them out of the generic
    ``pts`` threshold path so team finders filter on ``opponent_pts``.
    """
    _NUM = r"(\d+(?:\.\d+)?|\.\d+)"
    _POINT_SUFFIX = (
        r"(?:\s+(?:points?|pts))?"
        r"(?=\s*(?:[?.!,]|$|\b(?:this|that|in|during|last|season|year|record|when|and|or)\b))"
    )
    patterns = [
        rf"\bheld\s+(?:opponents?|teams?|them)\s+(?:to\s+)?(?:under|below)\s+{_NUM}{_POINT_SUFFIX}",
        rf"\blimited\s+opponents\s+to\s+(?:under|below)\s+{_NUM}{_POINT_SUFFIX}",
        rf"\bkept\s+the\s+other\s+team\s+below\s+{_NUM}{_POINT_SUFFIX}",
        rf"\ballow(?:s|ing|ed)?\s+(?:under|below|fewer\s+than|less\s+than)\s+{_NUM}{_POINT_SUFFIX}",
        rf"\b(?:points?|pts)\s+allowed\s+(?:under|below|fewer\s+than|less\s+than)\s+{_NUM}\b",
        rf"\b(?:opponent|opp)\s+(?:points?|pts)\s+(?:under|below|fewer\s+than|less\s+than)\s+{_NUM}\b",
        rf"\b(?:gave|given|giving)\s+up\s+(?:under|below|fewer\s+than|less\s+than)\s+{_NUM}{_POINT_SUFFIX}",
        rf"\bopponents?\s+under\s+{_NUM}(?:\s+(?:points?|pts))?\b",
    ]

    matches = []
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            value = float(m.group(1))
            matches.append(
                {
                    "start": m.start(),
                    "end": m.end(),
                    "stat": "opponent_pts",
                    "min_value": None,
                    "max_value": value - 0.0001,
                    "text": m.group(0),
                }
            )

    matches.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
    deduped = []
    accepted_spans: list[tuple[int, int]] = []
    for item in matches:
        span = (item["start"], item["end"])
        if any(not (span[1] <= start or span[0] >= end) for start, end in accepted_spans):
            continue
        accepted_spans.append(span)
        deduped.append(item)
    return deduped


def merge_opponent_points_allowed_conditions(
    threshold_conditions: list[dict],
    opponent_conditions: list[dict],
) -> list[dict]:
    """Prefer opponent-points conditions over overlapping generic pts ones."""
    if not opponent_conditions:
        return threshold_conditions

    def overlaps_opponent_condition(condition: dict) -> bool:
        start = condition.get("start")
        end = condition.get("end")
        if start is None or end is None:
            return False
        return any(
            not (end <= opponent["start"] or start >= opponent["end"])
            for opponent in opponent_conditions
        )

    merged = [
        condition
        for condition in threshold_conditions
        if not overlaps_opponent_condition(condition)
    ]
    merged.extend(opponent_conditions)
    merged.sort(key=lambda item: item.get("start", 0))
    return merged


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
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}contenders\b", "contenders"),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}good\s+teams\b", "good teams"),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}bad\s+teams\b", "bad teams"),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}top\s+teams\b", "top teams"),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}top[- ]10\s+teams\b", "top 10 teams"),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}top[- ]5\s+teams\b", "top 5 teams"),
        (
            rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}top[- ]seeded\s+teams\b",
            "top seeded teams",
        ),
        *[(pattern, "playoff teams") for pattern in _PLAYOFF_TEAM_OPPONENT_QUALITY_PATTERNS],
        *[
            (pattern, "non-playoff teams")
            for pattern in _NON_PLAYOFF_TEAM_OPPONENT_QUALITY_PATTERNS
        ],
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}winning\s+teams\b", "winning teams"),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}losing\s+teams\b", "losing teams"),
        (
            rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}teams?\s+(?:over|above)\s+\.500\b",
            "teams over .500",
        ),
        (
            rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}teams?\s+(?:under|below)\s+\.500\b",
            "teams under .500",
        ),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}top[- ]10\s+defenses\b", "top-10 defenses"),
        (rf"\b{_OPPONENT_QUALITY_PREFIX_PATTERN}top\s+defenses\b", "top-10 defenses"),
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
    del opponent_quality
    # Opponent-quality filters are represented as applied-filter chips in
    # result metadata, so repeating them as notes only leaks implementation
    # detail into the user-facing UI.
    return None


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
            "quarter filter is not supported with current data; try removing this filter "
            "or asking for full-game stats."
        )
    if half is not None:
        return (
            "half filter is not supported with current data; try removing this filter "
            "or asking for full-game stats."
        )
    return None


def detect_on_off(text: str) -> dict | None:
    """Detect single-player on/off phrasing."""
    player_fragment = r"[\w .&'\-]+?"
    phrase_patterns = (
        (rf"\bwith\s+({player_fragment})\s+on\s+(?:the\s+)?floor\b", "on"),
        (rf"\bwith\s+({player_fragment})\s+on\s+court\b", "on"),
        (rf"\bwithout\s+({player_fragment})\s+on\s+(?:the\s+)?floor\b", "off"),
        (rf"\bwithout\s+({player_fragment})\s+on\s+court\b", "off"),
        (rf"\b({player_fragment})\s+on\s+court\b", "on"),
        (rf"\b({player_fragment})\s+off\s+court\b", "off"),
        (rf"\b({player_fragment})\s+sitting\b", "off"),
    )

    for pattern, presence_state in phrase_patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        player = detect_player(match.group(1).strip())
        if player:
            if presence_state == "on" and re.search(
                r"\b(?:vs\.?|versus)\s+off\s+(?:the\s+)?(?:floor|court)\b", text
            ):
                presence_state = "both"
            return {
                "lineup_members": [player],
                "presence_state": presence_state,
            }

    if re.search(r"\bon\s*(?:/|-|\s)\s*off\b", text):
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
        r"\b(\d+)\s*(?:-\s*|\s+)games?(?:\s+[a-z0-9%.'/-]+){0,3}\s+stretch(?:es)?\b",
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
    stretch_marker = bool(re.search(r"\bstretch(?:es)?\b", text))
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


def detect_team_rolling_stretch_boundary(text: str) -> bool:
    """Detect explicit team-scoped rolling-stretch wording.

    Team rolling-window leaderboards do not have a route/result contract yet.
    This detector only covers clear generic team scope so player rolling-stretch
    queries continue to use ``player_stretch_leaderboard``.
    """
    if detect_stretch_query(text) is None:
        return False

    team_scope_patterns = (
        r"\bwhich\s+teams?\b",
        r"\bteams?\s+have\b",
        r"\bteam\s+\d+\s*(?:-\s*|\s+)games?\b",
        r"\b\d+\s*(?:-\s*|\s+)games?\s+team\b",
        r"\bstretch(?:es)?\s+by\s+(?:a\s+)?team\b",
        r"\bby\s+(?:a\s+)?team\b",
    )
    return any(re.search(pattern, text) for pattern in team_scope_patterns)


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
    """Detect lineup and unit phrasing that should route to lineup routes."""
    lineup_marker = bool(re.search(r"\b(?:lineups?|units?|combos?)\b", text))
    together_marker = bool(re.search(r"\btogether\b", text))
    leaderboard_marker = bool(re.search(r"\b(?:best|top|leaders?|highest|lowest)\b", text))
    with_lineup_marker = bool(re.search(r"\blineups?\s+with\b", text))

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
    """Describe missing lineup coverage honestly."""
    if not lineup_members and unit_size is None and minute_minimum is None:
        return None
    return (
        "lineup: trusted league_lineup_viz coverage is unavailable for the requested slice; "
        "unsupported route response returned"
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
            "back_to_back filter is not supported with current data; try removing this "
            "filter or asking for games without schedule-context filters."
        )
    if rest_days is not None:
        notes.append(
            "rest filter is not supported with current data; try removing this filter "
            "or asking for games without schedule-context filters."
        )
    if one_possession:
        notes.append(
            "one_possession filter is not supported with current data; try removing this "
            "filter or asking for games without close-game filters."
        )
    if nationally_televised:
        notes.append(
            "national_tv filter is not supported with current data; try removing this "
            "filter or asking for games without national-TV filters."
        )

    return notes


def build_role_filter_note(role: str | None = None) -> str | None:
    """Describe the current starter/bench role-filter limitation honestly."""
    if role is None:
        return None
    return (
        f"role filter ({role}) is not supported with current data; try removing this "
        "filter or asking for player stats without starter/bench role filters."
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

    Triggers on phrases like 'how many', 'how often', 'count', 'number of',
    'total number', 'total count', 'total games'.
    """
    return bool(
        re.search(
            r"\b(how\s+many|how\s+often|count|number\s+of|total\s+(?:number|count|games))\b",
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
    - 'top/highest scoring game(s)'
    - 'biggest scoring game(s)'
    - 'most dominant game(s)'
    """
    if re.search(
        r"\bseason[- ]?high\b"
        r"|\b(?:best|highest)\s+(?:single[- ]?)?games?\b"
        rf"|\b(?:top|best|highest)\s+(?:single[- ]?)?(?:(?:team|player)\s+)?"
        rf"{STAT_PATTERN}\s+(?:(?:team|player)\s+)?games?\b"
        r"|\bbiggest\s+(?:single\s+)?(?:scoring\s+|triple[- ]double\s+)?games?\b"
        r"|\bmost\s+dominant\s+(?:single\s+)?games?\b"
        r"|\bgame[- ]?high\b"
        r"|\bsingle[- ]?game\s+(?:high|best|record)\b",
        text,
    ):
        return True

    if detect_stat(text) is None:
        return False

    single_game_marker = re.search(r"\bin a game\b|\bsingle[- ]game\b", text)
    ranking_marker = re.search(
        r"\b(?:most|highest|biggest|best|top|leaders?)\b",
        text,
    )
    if single_game_marker and ranking_marker:
        return True

    stat_games_marker = re.search(
        rf"\b(?:highest|biggest|best)\s+{STAT_PATTERN}\s+games?\b",
        text,
    )
    return bool(stat_games_marker)


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
