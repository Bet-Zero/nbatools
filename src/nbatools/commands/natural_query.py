import re
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from nbatools.commands._constants import STAT_ALIASES, STAT_PATTERN, normalize_text
from nbatools.commands._date_utils import extract_date_range
from nbatools.commands._leaderboard_utils import (
    detect_player_leaderboard_stat,
    detect_team_leaderboard_stat,
    wants_ascending_leaderboard,
)
from nbatools.commands._matchup_utils import (
    detect_head_to_head,
    detect_opponent,
    detect_player_resolved,
    detect_team_in_text,
    extract_player_comparison,
    extract_team_comparison,
)
from nbatools.commands._occurrence_route_utils import (
    _COMPOUND_STAT_MAP,
    _parse_single_threshold,
    extract_compound_occurrence_event,
    extract_occurrence_event,
    try_compound_occurrence_route,
    try_occurrence_count_route,
    wants_occurrence_leaderboard,
)
from nbatools.commands._playoff_record_route_utils import (
    detect_by_decade_intent,
    detect_by_round_intent,
    detect_playoff_appearance_intent,
    detect_playoff_history_intent,
    detect_playoff_round_filter,
    detect_record_intent,
    try_playoff_record_route,
    try_record_leaderboard_route,
)
from nbatools.commands.entity_resolution import (
    PLAYER_ALIASES,
    TEAM_ALIASES,
    format_ambiguity_message,
)
from nbatools.commands.format_output import (
    build_error_output,
    build_no_result_output,
    format_pretty_from_result,
    route_to_query_class,
    wrap_result_with_metadata,
    write_csv_from_result,
    write_json_from_result,
)
from nbatools.commands.game_finder import build_result as game_finder_build_result
from nbatools.commands.game_summary import (
    _apply_filters as apply_team_summary_filters,
)
from nbatools.commands.game_summary import (
    build_result as game_summary_build_result,
)
from nbatools.commands.game_summary import (
    load_team_games_for_seasons as load_team_summary_games,
)
from nbatools.commands.game_summary import (
    resolve_seasons as resolve_team_summary_seasons,
)
from nbatools.commands.player_compare import (
    build_result as player_compare_build_result,
)
from nbatools.commands.player_game_finder import (
    build_result as player_game_finder_build_result,
)
from nbatools.commands.player_game_summary import (
    _apply_filters as apply_player_summary_filters,
)
from nbatools.commands.player_game_summary import (
    build_result as player_game_summary_build_result,
)
from nbatools.commands.player_game_summary import (
    load_player_games_for_seasons as load_player_summary_games,
)
from nbatools.commands.player_game_summary import (
    resolve_seasons as resolve_player_summary_seasons,
)
from nbatools.commands.player_occurrence_leaders import (
    build_result as player_occurrence_leaders_build_result,
)
from nbatools.commands.player_split_summary import (
    build_result as player_split_summary_build_result,
)
from nbatools.commands.player_streak_finder import (
    build_result as player_streak_finder_build_result,
)
from nbatools.commands.playoff_history import (
    build_matchup_by_decade_result,
    build_playoff_appearances_result,
    build_playoff_history_result,
    build_playoff_matchup_history_result,
    build_playoff_round_record_result,
    build_record_by_decade_leaderboard_result,
    build_record_by_decade_result,
)
from nbatools.commands.query_boolean_parser import (
    evaluate_condition_tree,
    expression_contains_boolean_ops,
    parse_condition_text,
)
from nbatools.commands.season_leaders import (
    build_result as season_leaders_build_result,
)
from nbatools.commands.season_team_leaders import (
    build_result as season_team_leaders_build_result,
)
from nbatools.commands.structured_results import (
    FinderResult,
    LeaderboardResult,
    NoResult,
    StreakResult,
)
from nbatools.commands.team_compare import (
    build_result as team_compare_build_result,
)
from nbatools.commands.team_occurrence_leaders import (
    build_result as team_occurrence_leaders_build_result,
)
from nbatools.commands.team_record import (
    build_matchup_record_result,
    build_record_leaderboard_result,
    build_team_record_result,
)
from nbatools.commands.team_split_summary import (
    build_result as team_split_summary_build_result,
)
from nbatools.commands.team_streak_finder import (
    build_result as team_streak_finder_build_result,
)
from nbatools.commands.top_player_games import (
    build_result as top_player_games_build_result,
)
from nbatools.commands.top_team_games import (
    build_result as top_team_games_build_result,
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
        r"|\b(?:career|playoff|all[- ]?time)\s+(?:\w+\s+)*leaders?\b"
        r"|\bleaders?\s+(?:since|last|past)\b"
        r"|\brank\b|\branked\b|\branking\b|\bwho\s+(?:has|had|leads?|led)\s+the\s+most\b"
        r"|\brank\s+(?:players?|teams?)\s+by\b",
        text,
    ):
        return True

    if re.search(r"\bin a game\b|\bsingle game\b|\bgame high\b|\bgame-high\b", text):
        return False

    if detect_player_leaderboard_stat(text) is None:
        return False

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
    for key in sorted(STAT_ALIASES.keys(), key=len, reverse=True):
        if key in text:
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
            rf"\bunder\s+{_NUM}\s+{STAT_PATTERN}\b",
            "max",
            0.0001,
        ),
        (
            rf"\bless than\s+{_NUM}\s+{STAT_PATTERN}\b",
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
    summary_terms = [
        "summary",
        "summarize",
        "average",
        "averages",
        "avg",
        "record",
        "how did",
        "how has",
        "what is the record",
        "what was the record",
    ]
    if any(term in text for term in summary_terms):
        return True
    if "form" in text or "recent form" in text:
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






def wants_recent_form(text: str) -> bool:
    return bool(re.search(r"\b(recent form|form)\b", text))


def wants_split_summary(text: str) -> bool:
    return "split" in text or detect_split_type(text) is not None


# ---------------------------------------------------------------------------
# build_result map
# ---------------------------------------------------------------------------
# Maps route name → build_result callable, used by the orchestration layer.

_BUILD_RESULT_MAP: dict[str, Callable] = {}


def _get_build_result_map() -> dict[str, Callable]:
    if not _BUILD_RESULT_MAP:
        _BUILD_RESULT_MAP.update(
            {
                "top_player_games": top_player_games_build_result,
                "top_team_games": top_team_games_build_result,
                "season_leaders": season_leaders_build_result,
                "season_team_leaders": season_team_leaders_build_result,
                "player_game_summary": player_game_summary_build_result,
                "game_summary": game_summary_build_result,
                "player_game_finder": player_game_finder_build_result,
                "game_finder": game_finder_build_result,
                "player_compare": player_compare_build_result,
                "team_compare": team_compare_build_result,
                "team_record": build_team_record_result,
                "team_matchup_record": build_matchup_record_result,
                "team_record_leaderboard": build_record_leaderboard_result,
                "player_split_summary": player_split_summary_build_result,
                "team_split_summary": team_split_summary_build_result,
                "player_streak_finder": player_streak_finder_build_result,
                "team_streak_finder": team_streak_finder_build_result,
                "player_occurrence_leaders": player_occurrence_leaders_build_result,
                "team_occurrence_leaders": team_occurrence_leaders_build_result,
                "playoff_history": build_playoff_history_result,
                "playoff_appearances": build_playoff_appearances_result,
                "playoff_matchup_history": build_playoff_matchup_history_result,
                "playoff_round_record": build_playoff_round_record_result,
                "record_by_decade": build_record_by_decade_result,
                "record_by_decade_leaderboard": build_record_by_decade_leaderboard_result,
                "matchup_by_decade": build_matchup_by_decade_result,
            }
        )
    return _BUILD_RESULT_MAP


# ---------------------------------------------------------------------------
# Helpers: work on result objects, not text
# ---------------------------------------------------------------------------


def _get_result_primary_df(result):
    """Extract the primary DataFrame from a structured result object."""
    if isinstance(result, FinderResult):
        return result.games
    if isinstance(result, LeaderboardResult):
        return result.leaders
    if isinstance(result, StreakResult):
        return result.streaks
    if isinstance(result, NoResult):
        return None
    # For summary/comparison/split: not applicable for tabular post-processing
    return None


def _set_result_primary_df(result, df):
    """Return a modified copy of a single-table result with a new DataFrame.

    Only applicable to FinderResult / LeaderboardResult / StreakResult.
    """
    import copy

    new_result = copy.copy(result)
    if isinstance(result, FinderResult):
        new_result.games = df
    elif isinstance(result, LeaderboardResult):
        new_result.leaders = df
    elif isinstance(result, StreakResult):
        new_result.streaks = df
    return new_result


def _apply_extra_conditions_to_result(result, extra_conditions: list[dict]):
    """Apply stat-threshold extra conditions directly to the result's DataFrame.

    Returns a modified result (or NoResult if the filtered DataFrame is empty).
    """
    if not extra_conditions:
        return result

    if isinstance(result, NoResult):
        return result

    df = _get_result_primary_df(result)
    if df is None:
        # Summary/comparison/split types don't support tabular post-filtering
        return result

    for cond in extra_conditions:
        stat = cond["stat"]
        if stat not in df.columns:
            return NoResult(query_class=getattr(result, "query_class", "finder"))
        if cond.get("min_value") is not None:
            df = df[df[stat] >= cond["min_value"]]
        if cond.get("max_value") is not None:
            df = df[df[stat] <= cond["max_value"]]

    if df.empty:
        return NoResult(query_class=getattr(result, "query_class", "finder"))

    return _set_result_primary_df(result, df)


def _execute_build_result(
    route: str,
    kwargs: dict,
    extra_conditions: list[dict] | None = None,
):
    """Build a structured result directly from a command's build_result()."""
    if extra_conditions is None:
        extra_conditions = []

    build_fn = _get_build_result_map()[route]
    result = build_fn(**kwargs)

    if extra_conditions:
        result = _apply_extra_conditions_to_result(result, extra_conditions)

    return result


def _combine_or_results(results: list):
    """Combine multiple finder-style results (for OR queries) into one FinderResult."""
    frames = []
    first_columns: list[str] | None = None
    query_class = "finder"

    for result in results:
        if isinstance(result, NoResult):
            continue
        df = _get_result_primary_df(result)
        if df is None or df.empty:
            continue
        query_class = getattr(result, "query_class", "finder")
        if first_columns is None:
            first_columns = list(df.columns)
        frames.append(df)

    if not frames:
        return NoResult(query_class=query_class)

    combined = pd.concat(frames, ignore_index=True)

    dedupe_keys = [c for c in ["game_id", "player_id", "team_id"] if c in combined.columns]
    if dedupe_keys:
        combined = combined.drop_duplicates(subset=dedupe_keys)
    else:
        combined = combined.drop_duplicates()

    if "game_date" in combined.columns:
        try:
            combined["_game_date_sort"] = pd.to_datetime(combined["game_date"], errors="coerce")
            sort_cols = ["_game_date_sort"]
            ascending = [False]
            if "game_id" in combined.columns:
                sort_cols.append("game_id")
                ascending.append(False)
            combined = combined.sort_values(sort_cols, ascending=ascending)
            combined = combined.drop(columns="_game_date_sort")
        except Exception:
            pass  # sorting is best-effort; failure here is cosmetic only

    if "rank" in combined.columns:
        combined = combined.drop(columns="rank")
        combined.insert(0, "rank", range(1, len(combined) + 1))

    if first_columns:
        ordered = [c for c in first_columns if c in combined.columns]
        extras = [c for c in combined.columns if c not in ordered]
        combined = combined[ordered + extras]

    return FinderResult(games=combined)


def _execute_or_query_build_result(query: str):
    """Build a structured result for OR queries."""
    clauses = _split_or_clauses(query)
    if len(clauses) <= 1:
        parsed = parse_query(query)
        return _execute_build_result(
            parsed["route"], parsed["route_kwargs"], parsed.get("extra_conditions", [])
        )

    base = _build_parse_state(query)
    clause_parsed = [
        _merge_inherited_context(base, _build_parse_state(clause)) for clause in clauses
    ]

    allowed_routes = {"player_game_finder", "game_finder"}
    routes = {item["route"] for item in clause_parsed}
    if len(routes) != 1 or list(routes)[0] not in allowed_routes:
        raise ValueError(
            "Top-level OR is currently supported for finder-style queries, for example: "
            "'Jokic over 25 points or over 10 rebounds' or "
            "'Celtics over 120 points or over 15 threes'."
        )

    results = []
    for item in clause_parsed:
        results.append(
            _execute_build_result(
                item["route"], item["route_kwargs"], item.get("extra_conditions", [])
            )
        )

    return _combine_or_results(results)


def _execute_grouped_boolean_build_result(query: str):
    """Build a structured result for grouped boolean queries."""
    parsed = parse_query(query)
    route = parsed["route"]

    if route in {"player_game_summary", "player_split_summary"}:
        condition_text = _extract_grouped_condition_text(query)
        if not expression_contains_boolean_ops(condition_text):
            raise ValueError("No grouped boolean expression detected.")

        tree = parse_condition_text(condition_text)
        base_df = _load_grouped_player_base_df(parsed)

        if base_df.empty:
            qc = "summary" if route == "player_game_summary" else "split_summary"
            return NoResult(query_class=qc)

        filtered_df = evaluate_condition_tree(tree, base_df)

        if filtered_df.empty:
            qc = "summary" if route == "player_game_summary" else "split_summary"
            return NoResult(query_class=qc)

        build_fn = _get_build_result_map()[route]
        if route == "player_game_summary":
            return build_fn(
                season=parsed["season"],
                start_season=parsed["start_season"],
                end_season=parsed["end_season"],
                season_type=parsed["season_type"],
                player=parsed["player"],
                team=parsed["team"],
                opponent=parsed["opponent"],
                home_only=parsed["home_only"],
                away_only=parsed["away_only"],
                wins_only=parsed["wins_only"],
                losses_only=parsed["losses_only"],
                stat=None,
                min_value=None,
                max_value=None,
                last_n=None,
                df=filtered_df,
            )
        else:
            return build_fn(
                split=parsed["split_type"],
                season=parsed["season"],
                start_season=parsed["start_season"],
                end_season=parsed["end_season"],
                season_type=parsed["season_type"],
                player=parsed["player"],
                team=parsed["team"],
                opponent=parsed["opponent"],
                stat=None,
                min_value=None,
                max_value=None,
                last_n=None,
                df=filtered_df,
            )

    if route in {"game_summary", "team_split_summary"}:
        condition_text = _extract_grouped_condition_text(query)
        if not expression_contains_boolean_ops(condition_text):
            raise ValueError("No grouped boolean expression detected.")

        tree = parse_condition_text(condition_text)
        base_df = _load_grouped_team_base_df(parsed)

        if base_df.empty:
            return NoResult(query_class="summary" if route == "game_summary" else "split_summary")

        filtered_df = evaluate_condition_tree(tree, base_df)

        if filtered_df.empty:
            return NoResult(query_class="summary" if route == "game_summary" else "split_summary")

        build_fn = _get_build_result_map()[route]
        if route == "game_summary":
            return build_fn(
                season=parsed["season"],
                start_season=parsed["start_season"],
                end_season=parsed["end_season"],
                season_type=parsed["season_type"],
                team=parsed["team"],
                opponent=parsed["opponent"],
                home_only=parsed["home_only"],
                away_only=parsed["away_only"],
                wins_only=parsed["wins_only"],
                losses_only=parsed["losses_only"],
                stat=None,
                min_value=None,
                max_value=None,
                last_n=None,
                df=filtered_df,
            )
        else:
            return build_fn(
                split=parsed["split_type"],
                season=parsed["season"],
                start_season=parsed["start_season"],
                end_season=parsed["end_season"],
                season_type=parsed["season_type"],
                team=parsed["team"],
                opponent=parsed["opponent"],
                stat=None,
                min_value=None,
                max_value=None,
                last_n=None,
                df=filtered_df,
            )

    if route not in {"player_game_finder", "game_finder"}:
        raise ValueError(
            "Grouped boolean logic is currently supported for finder, player summary/split, "
            "and team summary/split natural queries."
        )

    condition_text = _extract_grouped_condition_text(query)
    if not expression_contains_boolean_ops(condition_text):
        raise ValueError("No grouped boolean expression detected.")

    tree = parse_condition_text(condition_text)

    # Build a base result without stat filters to get all matching games
    base_kwargs = dict(parsed["route_kwargs"])
    base_kwargs["stat"] = None
    base_kwargs["min_value"] = None
    base_kwargs["max_value"] = None
    base_kwargs["sort_by"] = "game_date"
    base_kwargs["ascending"] = False

    base_result = _execute_build_result(route, base_kwargs)

    df = _get_result_primary_df(base_result)
    if df is None or df.empty:
        return NoResult(query_class="finder")

    df = evaluate_condition_tree(tree, df)

    if df.empty:
        return NoResult(query_class="finder")

    if "game_date" in df.columns:
        try:
            df["_game_date_sort"] = pd.to_datetime(df["game_date"], errors="coerce")
            sort_cols = ["_game_date_sort"]
            ascending_list = [False]
            if "game_id" in df.columns:
                sort_cols.append("game_id")
                ascending_list.append(False)
            df = df.sort_values(sort_cols, ascending=ascending_list)
            df = df.drop(columns="_game_date_sort")
        except Exception:
            pass  # sorting is best-effort; failure here is cosmetic only

    if "rank" in df.columns:
        df = df.drop(columns="rank")
        df.insert(0, "rank", range(1, len(df) + 1))

    return FinderResult(games=df)


def _split_or_clauses(text: str) -> list[str]:
    text = normalize_text(text)
    if " or " not in text:
        return [text]

    raw_parts = re.split(r"\s+or\s+", text, flags=re.IGNORECASE)
    parts = [normalize_text(p) for p in raw_parts if normalize_text(p)]
    return parts if parts else [text]


def _build_parse_state(query: str) -> dict:
    q = normalize_text(query)

    # -- Historical span detection (must run before single-season extraction) --
    start_season, end_season = extract_season_range(q)
    career_intent = False

    if not (start_season and end_season):
        # Try "since SEASON/YEAR"
        since_season = extract_since_season(q)
        if since_season:
            from nbatools.commands._seasons import default_end_season

            season_type_early = detect_season_type(q)
            start_season = since_season
            end_season = default_end_season(season_type_early)

    if not (start_season and end_season):
        # Try "last N seasons"
        last_n_seasons = extract_last_n_seasons(q)
        if last_n_seasons:
            from nbatools.commands._seasons import resolve_last_n_seasons

            season_type_early = detect_season_type(q)
            start_season, end_season = resolve_last_n_seasons(last_n_seasons, season_type_early)

    if not (start_season and end_season):
        # Try "career" / "all-time"
        if detect_career_intent(q):
            from nbatools.commands._seasons import resolve_career

            career_intent = True
            season_type_early = detect_season_type(q)
            start_season, end_season = resolve_career(season_type_early)

    season = None if (start_season and end_season) else extract_season(q)

    season_type = detect_season_type(q)
    stat = detect_stat(q)
    last_n = extract_last_n(q)
    top_n = extract_top_n(q)
    split_type = detect_split_type(q)
    leaderboard_intent = wants_leaderboard(q)
    team_leaderboard_intent = wants_team_leaderboard(q)
    occurrence_event = extract_occurrence_event(q)
    compound_occurrence_conditions = extract_compound_occurrence_event(q)
    occurrence_leaderboard_intent = wants_occurrence_leaderboard(q)
    position_filter = extract_position_filter(q)
    head_to_head = detect_head_to_head(q)
    streak_request = extract_streak_request(q)
    team_streak_request = extract_team_streak_request(q)

    # -- Playoff history / era-bucket intent detection --
    by_decade_intent = detect_by_decade_intent(q)
    playoff_appearance_intent = detect_playoff_appearance_intent(q)
    playoff_history_intent = detect_playoff_history_intent(q)
    playoff_round_filter = detect_playoff_round_filter(q)
    by_round_intent = detect_by_round_intent(q)

    threshold_conditions = extract_threshold_conditions(q)

    extra_conditions = []
    if threshold_conditions:
        primary = threshold_conditions[0]
        stat = primary["stat"]
        min_value = primary["min_value"]
        max_value = primary["max_value"]
        extra_conditions = threshold_conditions[1:]
    else:
        min_value = extract_min_value(q, stat)
        max_value = None

    if last_n is None and wants_recent_form(q):
        last_n = 10

    summary_intent = wants_summary(q)
    finder_intent = wants_finder(q)
    count_intent = wants_count(q)
    record_intent = detect_record_intent(q)
    range_intent = bool(start_season and end_season)
    split_intent = wants_split_summary(q)

    if season is None and start_season is None and end_season is None:
        if (
            last_n is not None
            or split_intent
            or summary_intent
            or stat is not None
            or min_value is not None
            or max_value is not None
            or leaderboard_intent
            or team_leaderboard_intent
            or record_intent
        ):
            season = default_season_for_context(season_type)

    player_a, player_b = extract_player_comparison(q)
    team_a, team_b = (None, None)

    if not (player_a and player_b):
        team_a, team_b = extract_team_comparison(q)

    player = None
    entity_ambiguity: dict | None = None
    if not (player_a and player_b):
        player_result = detect_player_resolved(q)
        if player_result.is_confident:
            player = player_result.resolved
        elif player_result.is_ambiguous:
            entity_ambiguity = {
                "type": "player",
                "input": q,
                "candidates": player_result.candidates,
                "source": player_result.source,
            }

    opponent = None
    q_without_opponent = q
    team = None

    if not (team_a and team_b):
        opponent, q_without_opponent = detect_opponent(q)
        if not (player_a and player_b):
            team = detect_team_in_text(q_without_opponent)

    home_only, away_only = detect_home_away(q)
    wins_only, losses_only = detect_wins_losses(q)

    if season is None and start_season is None and end_season is None:
        if any(
            [
                player,
                team,
                opponent,
                player_a,
                player_b,
                team_a,
                team_b,
            ]
        ):
            season = default_season_for_context(season_type)

    start_date, end_date = extract_date_range(q, season)

    explicit_single_season = extract_season(q)
    explicit_range_start, explicit_range_end = extract_season_range(q)

    if (
        (streak_request or team_streak_request)
        and explicit_single_season is None
        and explicit_range_start is None
        and explicit_range_end is None
        and start_date is None
        and end_date is None
    ):
        default_end = default_season_for_context(season_type)
        end_year = int(default_end.split("-")[0])
        start_year = end_year - 2
        season = None
        start_season = f"{start_year}-{str(start_year + 1)[-2:]}"
        end_season = default_end

    return {
        "normalized_query": q,
        "season": season,
        "start_season": start_season,
        "end_season": end_season,
        "start_date": start_date,
        "end_date": end_date,
        "season_type": season_type,
        "stat": stat,
        "player": player,
        "player_a": player_a,
        "player_b": player_b,
        "team": team,
        "team_a": team_a,
        "team_b": team_b,
        "opponent": opponent,
        "min_value": min_value,
        "max_value": max_value,
        "last_n": last_n,
        "top_n": top_n,
        "split_type": split_type,
        "home_only": home_only,
        "away_only": away_only,
        "wins_only": wins_only,
        "losses_only": losses_only,
        "summary_intent": summary_intent,
        "finder_intent": finder_intent,
        "count_intent": count_intent,
        "record_intent": record_intent,
        "range_intent": range_intent,
        "career_intent": career_intent,
        "split_intent": split_intent,
        "leaderboard_intent": leaderboard_intent,
        "team_leaderboard_intent": team_leaderboard_intent,
        "occurrence_event": occurrence_event,
        "compound_occurrence_conditions": compound_occurrence_conditions,
        "occurrence_leaderboard_intent": occurrence_leaderboard_intent,
        "position_filter": position_filter,
        "head_to_head": head_to_head,
        "streak_request": streak_request,
        "team_streak_request": team_streak_request,
        "entity_ambiguity": entity_ambiguity,
        "by_decade_intent": by_decade_intent,
        "playoff_appearance_intent": playoff_appearance_intent,
        "playoff_history_intent": playoff_history_intent,
        "playoff_round_filter": playoff_round_filter,
        "by_round_intent": by_round_intent,
        "threshold_conditions": [
            {
                "stat": c["stat"],
                "min_value": c["min_value"],
                "max_value": c["max_value"],
                "text": c["text"],
            }
            for c in threshold_conditions
        ],
        "extra_conditions": [
            {
                "stat": c["stat"],
                "min_value": c["min_value"],
                "max_value": c["max_value"],
                "text": c["text"],
            }
            for c in extra_conditions
        ],
    }


def _finalize_route(parsed: dict) -> dict:
    q = parsed["normalized_query"]
    season = parsed["season"]
    start_season = parsed["start_season"]
    end_season = parsed["end_season"]
    start_date = parsed.get("start_date")
    end_date = parsed.get("end_date")
    season_type = parsed["season_type"]
    stat = parsed["stat"]
    player = parsed["player"]
    player_a = parsed["player_a"]
    player_b = parsed["player_b"]
    team = parsed["team"]
    team_a = parsed["team_a"]
    team_b = parsed["team_b"]
    opponent = parsed["opponent"]
    min_value = parsed["min_value"]
    max_value = parsed["max_value"]
    last_n = parsed["last_n"]
    top_n = parsed.get("top_n")
    split_type = parsed["split_type"]
    home_only = parsed["home_only"]
    away_only = parsed["away_only"]
    wins_only = parsed["wins_only"]
    losses_only = parsed["losses_only"]
    summary_intent = parsed["summary_intent"]
    finder_intent = parsed.get("finder_intent", False)
    count_intent = parsed.get("count_intent", False)
    record_intent = parsed.get("record_intent", False)
    range_intent = parsed["range_intent"]
    career_intent = parsed.get("career_intent", False)
    leaderboard_intent = parsed.get("leaderboard_intent", False)
    team_leaderboard_intent = parsed.get("team_leaderboard_intent", False)
    occurrence_event = parsed.get("occurrence_event")
    position_filter = parsed.get("position_filter")
    head_to_head = parsed.get("head_to_head", False)
    streak_request = parsed.get("streak_request")
    team_streak_request = parsed.get("team_streak_request")

    notes: list[str] = []
    route = None
    route_kwargs = None

    # -- Occurrence event: propagate stat/min_value when occurrence event is
    #    detected and no explicit threshold conditions were parsed.  This lets
    #    "how many 40 point games" correctly set stat=pts, min_value=40 even
    #    when the threshold-condition parser didn't fire (no operator word).
    if occurrence_event and "special_event" not in occurrence_event:
        occ_stat = occurrence_event.get("stat")
        occ_min = occurrence_event.get("min_value")
        if stat is None and occ_stat:
            stat = occ_stat
        if min_value is None and occ_min is not None:
            min_value = occ_min

    # -- Entity ambiguity: short-circuit if we can't resolve a required entity --
    entity_ambiguity = parsed.get("entity_ambiguity")
    if entity_ambiguity and not player and not player_a and not player_b and not team:
        out = dict(parsed)
        out["route"] = None
        out["route_kwargs"] = {}
        msg = format_ambiguity_message(
            entity_ambiguity.get("input", ""),
            entity_ambiguity.get("candidates", []),
            entity_ambiguity.get("type", "player"),
        )
        out["notes"] = [msg]
        return out

    if (
        team
        and team_streak_request
        and not team_a
        and not team_b
        and not player
        and not player_a
        and not player_b
    ):
        route = "team_streak_finder"
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "season_type": season_type,
            "team": team,
            "opponent": opponent,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "start_date": start_date,
            "end_date": end_date,
            "last_n": last_n,
            "stat": team_streak_request.get("stat"),
            "min_value": team_streak_request.get("min_value"),
            "max_value": team_streak_request.get("max_value"),
            "special_condition": team_streak_request.get("special_condition"),
            "min_streak_length": team_streak_request.get("min_streak_length"),
            "longest": team_streak_request.get("longest", False),
            "limit": 25,
        }
    # ---------------------------------------------------------------------------
    # Playoff / record / decade routing cluster
    # ---------------------------------------------------------------------------
    elif (ppr := try_playoff_record_route(parsed)) is not None:
        route, route_kwargs = ppr
    elif split_type and player and not player_a and not player_b:
        route = "player_split_summary"
        route_kwargs = {
            "split": split_type,
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "season_type": season_type,
            "player": player,
            "team": team,
            "opponent": opponent,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "last_n": last_n,
        }
    elif split_type and team and not team_a and not team_b:
        route = "team_split_summary"
        route_kwargs = {
            "split": split_type,
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "season_type": season_type,
            "team": team,
            "opponent": opponent,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "last_n": last_n,
        }
    elif player_a and player_b:
        route = "player_compare"
        route_kwargs = {
            "player_a": player_a,
            "player_b": player_b,
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "team": team,
            "opponent": opponent,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "last_n": last_n,
            "head_to_head": head_to_head,
        }
    # ---------------------------------------------------------------------------
    # Record-oriented routing: team-vs-team matchup record
    # ---------------------------------------------------------------------------
    elif team_a and team_b and record_intent:
        route = "team_matchup_record"
        route_kwargs = {
            "team_a": team_a,
            "team_b": team_b,
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "home_only": home_only,
            "away_only": away_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
        }
    elif team_a and team_b:
        route = "team_compare"
        route_kwargs = {
            "team_a": team_a,
            "team_b": team_b,
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "opponent": opponent,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "last_n": last_n,
            "head_to_head": head_to_head,
        }
    elif player and streak_request and not player_a and not player_b:
        route = "player_streak_finder"
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "season_type": season_type,
            "player": player,
            "team": team,
            "opponent": opponent,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "start_date": start_date,
            "end_date": end_date,
            "last_n": last_n,
            "stat": streak_request.get("stat"),
            "min_value": streak_request.get("min_value"),
            "max_value": streak_request.get("max_value"),
            "special_condition": streak_request.get("special_condition"),
            "min_streak_length": streak_request.get("min_streak_length"),
            "longest": streak_request.get("longest", False),
            "limit": 25,
        }
    elif "top" in q and "games" in q and player is None and ("scoring" in q or stat is not None):
        route = "top_player_games"
        route_kwargs = {
            "season": season or default_season_for_context(season_type),
            "stat": stat or "pts",
            "limit": top_n or 10,
            "season_type": season_type,
            "ascending": False,
        }
    elif "top team" in q or ("top" in q and "team games" in q):
        route = "top_team_games"
        route_kwargs = {
            "season": season or default_season_for_context(season_type),
            "stat": stat or "pts",
            "limit": top_n or 10,
            "season_type": season_type,
            "ascending": False,
        }
    # ---------------------------------------------------------------------------
    # Occurrence routing cluster (compound + single leaderboard)
    # ---------------------------------------------------------------------------
    elif (ocr := try_compound_occurrence_route(parsed)) is not None:
        route, route_kwargs = ocr
    # ---------------------------------------------------------------------------
    # Record-leaderboard routing cluster
    # ---------------------------------------------------------------------------
    elif (rlr := try_record_leaderboard_route(parsed)) is not None:
        route, route_kwargs, rl_notes = rlr
        notes.extend(rl_notes)
    elif (
        player is None
        and team is None
        and not player_a
        and not player_b
        and not team_a
        and not team_b
        and (leaderboard_intent or team_leaderboard_intent)
    ):
        # For leaderboards, prefer multi-season params if available
        lb_season = season
        lb_start_season = start_season
        lb_end_season = end_season
        if not lb_season and not lb_start_season and not lb_end_season:
            lb_season = default_season_for_context(season_type)

        lb_ascending = wants_ascending_leaderboard(q)

        # Smart ascending for stats where lower = better:
        # "best defensive teams" → def_rating ascending (lower is better)
        # "best/lowest turnover teams" → turnovers ascending
        # But "worst defensive teams" → def_rating descending (higher = worse)
        _lower_is_better_stats = {"def_rating", "tov", "tov_pct"}

        if team_leaderboard_intent:
            leaderboard_stat = detect_team_leaderboard_stat(q) or stat or "pts"

            # Semantic ascending for lower-is-better stats
            if leaderboard_stat in _lower_is_better_stats:
                if re.search(r"\b(best|top|lowest|fewest|least)\b", q):
                    lb_ascending = True
                elif re.search(r"\b(worst|most|highest)\b", q):
                    lb_ascending = False

            # Season-advanced-only team stats blocked in date-window/multi-season
            _team_season_only = {"off_rating", "def_rating", "net_rating", "pace"}
            if (start_date or end_date) and leaderboard_stat in _team_season_only:
                notes.append(
                    f"stat_fallback: {leaderboard_stat} not available with date window, using pts"
                )
                leaderboard_stat = "pts"
            if (lb_start_season and lb_end_season) and leaderboard_stat in _team_season_only:
                notes.append(
                    f"stat_fallback: {leaderboard_stat} not available for multi-season, using pts"
                )
                leaderboard_stat = "pts"
            route = "season_team_leaders"
            route_kwargs = {
                "season": lb_season,
                "stat": leaderboard_stat,
                "limit": top_n or 10,
                "season_type": season_type,
                "min_games": 1,
                "ascending": lb_ascending,
                "start_date": start_date,
                "end_date": end_date,
                "start_season": lb_start_season,
                "end_season": lb_end_season,
                "opponent": opponent,
                "home_only": home_only,
                "away_only": away_only,
                "wins_only": wins_only,
                "losses_only": losses_only,
            }
        elif "team" in q or "teams" in q:
            leaderboard_stat = stat or "pts"
            _team_season_only = {"off_rating", "def_rating", "net_rating", "pace"}
            if (start_date or end_date) and leaderboard_stat in _team_season_only:
                notes.append(
                    f"stat_fallback: {leaderboard_stat} not available with date window, using pts"
                )
                leaderboard_stat = "pts"
            if (lb_start_season and lb_end_season) and leaderboard_stat in _team_season_only:
                notes.append(
                    f"stat_fallback: {leaderboard_stat} not available for multi-season, using pts"
                )
                leaderboard_stat = "pts"
            route = "season_team_leaders"
            route_kwargs = {
                "season": lb_season,
                "stat": leaderboard_stat,
                "limit": top_n or 10,
                "season_type": season_type,
                "min_games": 1,
                "ascending": lb_ascending,
                "start_date": start_date,
                "end_date": end_date,
                "start_season": lb_start_season,
                "end_season": lb_end_season,
                "opponent": opponent,
                "home_only": home_only,
                "away_only": away_only,
                "wins_only": wins_only,
                "losses_only": losses_only,
            }
        else:
            leaderboard_stat = detect_player_leaderboard_stat(q) or stat or "pts"

            # Semantic ascending for lower-is-better stats
            if leaderboard_stat in _lower_is_better_stats:
                if re.search(r"\b(best|top|lowest|fewest|least)\b", q):
                    lb_ascending = True
                elif re.search(r"\b(worst|most|highest)\b", q):
                    lb_ascending = False

            # Season-advanced-only player stats blocked in multi-season/opponent contexts
            _player_season_only = {"off_rating", "def_rating", "net_rating"}
            if (lb_start_season and lb_end_season) and leaderboard_stat in _player_season_only:
                notes.append(
                    f"stat_fallback: {leaderboard_stat} not available for multi-season, using pts"
                )
                leaderboard_stat = "pts"
            if opponent and leaderboard_stat in _player_season_only:
                notes.append(
                    f"stat_fallback: {leaderboard_stat} not available"
                    " with opponent filter, using pts"
                )
                leaderboard_stat = "pts"
            route = "season_leaders"
            route_kwargs = {
                "season": lb_season,
                "stat": leaderboard_stat,
                "limit": top_n or 10,
                "season_type": season_type,
                "min_games": 1,
                "ascending": lb_ascending,
                "start_date": start_date,
                "end_date": end_date,
                "start_season": lb_start_season,
                "end_season": lb_end_season,
                "opponent": opponent,
                "position": position_filter,
            }
    # ---------------------------------------------------------------------------
    # Single-player special-event occurrence count
    # ---------------------------------------------------------------------------
    elif (oco := try_occurrence_count_route(parsed)) is not None:
        route, route_kwargs = oco
    elif (finder_intent or count_intent) and player and not player_a and not player_b:
        # Explicit list/count intent overrides summary/range routing
        finder_limit = None if count_intent else 25
        route = "player_game_finder"
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "player": player,
            "team": team,
            "opponent": opponent,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "limit": finder_limit,
            "sort_by": "stat" if stat else "game_date",
            "ascending": False,
            "last_n": last_n,
        }
    elif (finder_intent or count_intent) and team and not team_a and not team_b:
        # Explicit list/count intent overrides summary/range routing
        finder_limit = None if count_intent else 25
        route = "game_finder"
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "team": team,
            "opponent": opponent,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "limit": finder_limit,
            "sort_by": "stat" if stat else "game_date",
            "ascending": False,
            "last_n": last_n,
        }
    elif player and (
        summary_intent
        or career_intent
        or range_intent
        or ("record" in q)
        or ("averages" in q)
        or ("average" in q)
    ):
        route = "player_game_summary"
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "player": player,
            "team": team,
            "opponent": opponent,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "last_n": last_n,
        }
    # ---------------------------------------------------------------------------
    # Record-oriented routing: single team record
    # ---------------------------------------------------------------------------
    elif team and record_intent and not team_a and not team_b:
        route = "team_record"
        route_kwargs = {
            "team": team,
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "season_type": season_type,
            "opponent": opponent,
            "home_only": home_only,
            "away_only": away_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "start_date": start_date,
            "end_date": end_date,
        }
    elif team and (
        summary_intent
        or career_intent
        or range_intent
        or ("record" in q)
        or ("averages" in q)
        or ("average" in q)
    ):
        route = "game_summary"
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "team": team,
            "opponent": opponent,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "last_n": last_n,
        }
    elif player:
        route = "player_game_finder"
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "player": player,
            "team": team,
            "opponent": opponent,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "limit": 25,
            "sort_by": "stat" if stat else "game_date",
            "ascending": False,
            "last_n": last_n,
        }
    elif team:
        route = "game_finder"
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "team": team,
            "opponent": opponent,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "limit": 25,
            "sort_by": "stat" if stat else "game_date",
            "ascending": False,
            "last_n": last_n,
        }
    else:
        raise ValueError(
            "Could not map query to a supported pattern yet. "
            "Try queries like: "
            "'Jokic under 20 points', "
            "'Jokic between 20 and 30 points', "
            "'Jokic last 10 games over 25 points and under 15 rebounds', "
            "'Jokic over 25 points or over 10 rebounds', "
            "'Jokic (over 25 points and over 10 rebounds) or over 15 assists', "
            "'Jokic recent form', "
            "'Jokic vs Embiid recent form'."
        )

    out = dict(parsed)
    out["route"] = route
    out["route_kwargs"] = route_kwargs

    date_window_active = start_date is not None or end_date is not None
    if date_window_active and route in ("season_leaders", "season_team_leaders"):
        notes.append(
            "leaderboard_source: game-log derived (season-advanced stats excluded in date window)"
        )

    if route in ("player_game_summary", "player_compare", "player_split_summary"):
        notes.append(
            "sample_advanced_metrics: usg_pct, ast_pct, reb_pct, tov_pct"
            " recomputed from filtered sample"
        )

    if notes:
        out["notes"] = notes

    return out


def parse_query(query: str) -> dict:
    return _finalize_route(_build_parse_state(query))


def _merge_inherited_context(base: dict, clause: dict) -> dict:
    out = dict(clause)

    inherit_keys_if_missing = [
        "season",
        "start_season",
        "end_season",
        "start_date",
        "end_date",
        "season_type",
        "player",
        "player_a",
        "player_b",
        "team",
        "team_a",
        "team_b",
        "opponent",
        "last_n",
        "split_type",
        "head_to_head",
    ]
    for key in inherit_keys_if_missing:
        if out.get(key) in (None, "", False):
            base_value = base.get(key)
            if base_value not in (None, "", False):
                out[key] = base_value

    if not out.get("home_only") and base.get("home_only"):
        out["home_only"] = True
    if not out.get("away_only") and base.get("away_only"):
        out["away_only"] = True
    if not out.get("wins_only") and base.get("wins_only"):
        out["wins_only"] = True
    if not out.get("losses_only") and base.get("losses_only"):
        out["losses_only"] = True
    if not out.get("summary_intent") and base.get("summary_intent"):
        out["summary_intent"] = True
    if not out.get("finder_intent") and base.get("finder_intent"):
        out["finder_intent"] = True
    if not out.get("count_intent") and base.get("count_intent"):
        out["count_intent"] = True
    if not out.get("record_intent") and base.get("record_intent"):
        out["record_intent"] = True
    if not out.get("split_intent") and base.get("split_intent"):
        out["split_intent"] = True

    if (
        out.get("season") is None
        and out.get("start_season") is None
        and out.get("end_season") is None
    ):
        if base.get("season") is not None:
            out["season"] = base["season"]
        else:
            out["start_season"] = base.get("start_season")
            out["end_season"] = base.get("end_season")

    return _finalize_route(out)


def _extract_grouped_condition_text(query: str) -> str:
    normalized = normalize_text(query)
    condition_text = normalized

    for name in sorted(PLAYER_ALIASES.keys(), key=len, reverse=True):
        condition_text = re.sub(rf"\b{re.escape(name)}\b", "", condition_text)

    for name in sorted(TEAM_ALIASES.keys(), key=len, reverse=True):
        condition_text = re.sub(rf"\b{re.escape(name)}\b", "", condition_text)

    condition_text = re.sub(r"\b(?:19|20)\d{2}-\d{2}\b", "", condition_text)
    condition_text = re.sub(
        r"\bfrom\s+(?:19|20)\d{2}-\d{2}\s+to\s+(?:19|20)\d{2}-\d{2}\b", "", condition_text
    )
    condition_text = re.sub(r"\b(last|past|recent)\s+\d+\s+games?\b", "", condition_text)
    condition_text = re.sub(r"\b(last|past|recent)\s+\d+\b", "", condition_text)
    condition_text = re.sub(r"\b(playoff|playoffs|postseason)\b", "", condition_text)
    condition_text = re.sub(r"\bhome\s+vs\.?\s+away\b", "", condition_text)
    condition_text = re.sub(r"\bwins?\s+vs\.?\s+loss(?:es)?\b", "", condition_text)
    condition_text = re.sub(
        r"\b(summary|summarize|average|averages|avg|record|split|form|where|games|game"
        r"|show\s+me|list|find|give\s+me|how\s+many|count|number\s+of)\b",
        "",
        condition_text,
    )
    condition_text = re.sub(r"\b(home|away|road|wins?|loss(?:es)?|won|lost)\b", "", condition_text)
    condition_text = re.sub(r"\b(vs\.?|versus|against)\s+[a-z0-9 .&'\-]+\b", "", condition_text)
    condition_text = re.sub(r"^(vs\.?|versus)\s+", "", condition_text)

    return normalize_text(condition_text)


def _load_grouped_player_base_df(parsed: dict) -> pd.DataFrame:
    seasons = resolve_player_summary_seasons(
        parsed["season"],
        parsed["start_season"],
        parsed["end_season"],
    )
    df = load_player_summary_games(seasons, parsed["season_type"])

    home_only = parsed["home_only"]
    away_only = parsed["away_only"]
    wins_only = parsed["wins_only"]
    losses_only = parsed["losses_only"]

    if parsed["route"] == "player_split_summary":
        home_only = False
        away_only = False
        wins_only = False
        losses_only = False

    df = apply_player_summary_filters(
        df=df,
        player=parsed["player"],
        team=parsed["team"],
        opponent=parsed["opponent"],
        home_only=home_only,
        away_only=away_only,
        wins_only=wins_only,
        losses_only=losses_only,
        stat=None,
        min_value=None,
        max_value=None,
        last_n=parsed["last_n"],
    )
    return df


def _load_grouped_team_base_df(parsed: dict) -> pd.DataFrame:
    seasons = resolve_team_summary_seasons(
        parsed["season"],
        parsed["start_season"],
        parsed["end_season"],
    )
    df = load_team_summary_games(seasons, parsed["season_type"])

    home_only = parsed["home_only"]
    away_only = parsed["away_only"]
    wins_only = parsed["wins_only"]
    losses_only = parsed["losses_only"]

    if parsed["route"] == "team_split_summary":
        home_only = False
        away_only = False
        wins_only = False
        losses_only = False

    df = apply_team_summary_filters(
        df=df,
        team=parsed["team"],
        opponent=parsed["opponent"],
        home_only=home_only,
        away_only=away_only,
        wins_only=wins_only,
        losses_only=losses_only,
        stat=None,
        min_value=None,
        max_value=None,
        last_n=parsed["last_n"],
    )
    return df


def render_query_result(
    query_result,
    query: str,
    pretty: bool = True,
    export_csv_path: str | None = None,
    export_txt_path: str | None = None,
    export_json_path: str | None = None,
) -> None:
    """Render a QueryResult to console and/or export files.

    This is the CLI rendering layer.  It takes a ``QueryResult`` from the
    query service and handles pretty/raw display and CSV/TXT/JSON exports.
    """
    result = query_result.result
    metadata = dict(query_result.metadata)
    query_class = route_to_query_class(query_result.route)

    # Build the wrapped raw output text
    if isinstance(result, NoResult):
        reason = result.result_reason or result.reason or "no_match"
        if result.result_status == "error":
            wrapped = build_error_output(metadata, reason=reason)
        else:
            wrapped = build_no_result_output(metadata, reason=reason)
    else:
        wrapped = wrap_result_with_metadata(result, metadata, query_class)

    # Export directly from structured result
    if export_csv_path:
        write_csv_from_result(result, export_csv_path)

    if export_json_path:
        write_json_from_result(result, export_json_path, metadata)

    if export_txt_path:
        if pretty:
            text_to_save = format_pretty_from_result(result, query)
        else:
            text_to_save = wrapped
        _p = Path(export_txt_path)
        if _p.parent != Path("."):
            _p.parent.mkdir(parents=True, exist_ok=True)
        _p.write_text(
            text_to_save + ("" if text_to_save.endswith("\n") else "\n"),
            encoding="utf-8",
        )

    # Console output
    if not pretty:
        print(wrapped, end="" if wrapped.endswith("\n") else "\n")
        return

    pretty_text = format_pretty_from_result(result, query)
    print(pretty_text)


def run(
    query: str,
    pretty: bool = True,
    export_csv_path: str | None = None,
    export_txt_path: str | None = None,
    export_json_path: str | None = None,
) -> None:
    from nbatools.query_service import execute_natural_query

    qr = execute_natural_query(query)

    render_query_result(
        qr,
        query,
        pretty=pretty,
        export_csv_path=export_csv_path,
        export_txt_path=export_txt_path,
        export_json_path=export_json_path,
    )
