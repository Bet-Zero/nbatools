import json
import re
from calendar import monthcalendar, monthrange
from collections.abc import Callable
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from nbatools.commands._constants import STAT_ALIASES, STAT_PATTERN
from nbatools.commands.format_output import (
    METADATA_LABEL,
    build_error_output,
    build_no_result_output,
    format_pretty_from_result,
    format_pretty_output,
    parse_labeled_sections,
    parse_metadata_block,
    route_to_query_class,
    wrap_raw_output,
    wrap_result_with_metadata,
    write_csv_from_result,
    write_json_from_result,
)
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.game_finder import build_result as game_finder_build_result
from nbatools.commands.game_finder import run as game_finder_run
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
from nbatools.commands.game_summary import (
    run as game_summary_run,
)
from nbatools.commands.player_compare import (
    build_result as player_compare_build_result,
)
from nbatools.commands.player_compare import run as player_compare_run
from nbatools.commands.player_game_finder import (
    build_result as player_game_finder_build_result,
)
from nbatools.commands.player_game_finder import run as player_game_finder_run
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
from nbatools.commands.player_game_summary import (
    run as player_game_summary_run,
)
from nbatools.commands.player_split_summary import (
    build_result as player_split_summary_build_result,
)
from nbatools.commands.player_split_summary import run as player_split_summary_run
from nbatools.commands.player_streak_finder import (
    build_result as player_streak_finder_build_result,
)
from nbatools.commands.player_streak_finder import run as player_streak_finder_run
from nbatools.commands.query_boolean_parser import (
    evaluate_condition_tree,
    expression_contains_boolean_ops,
    parse_condition_text,
)
from nbatools.commands.season_leaders import (
    build_result as season_leaders_build_result,
)
from nbatools.commands.season_leaders import run as season_leaders_run
from nbatools.commands.season_team_leaders import (
    build_result as season_team_leaders_build_result,
)
from nbatools.commands.season_team_leaders import run as season_team_leaders_run
from nbatools.commands.structured_results import (
    FinderResult,
    LeaderboardResult,
    NoResult,
    StreakResult,
)
from nbatools.commands.team_compare import (
    build_result as team_compare_build_result,
)
from nbatools.commands.team_compare import run as team_compare_run
from nbatools.commands.team_split_summary import (
    build_result as team_split_summary_build_result,
)
from nbatools.commands.team_split_summary import run as team_split_summary_run
from nbatools.commands.team_streak_finder import (
    build_result as team_streak_finder_build_result,
)
from nbatools.commands.team_streak_finder import run as team_streak_finder_run
from nbatools.commands.top_player_games import (
    build_result as top_player_games_build_result,
)
from nbatools.commands.top_player_games import run as top_player_games_run
from nbatools.commands.top_team_games import (
    build_result as top_team_games_build_result,
)
from nbatools.commands.top_team_games import run as top_team_games_run

TEAM_ALIASES = {
    "atlanta": "ATL",
    "hawks": "ATL",
    "boston": "BOS",
    "celtics": "BOS",
    "brooklyn": "BKN",
    "nets": "BKN",
    "charlotte": "CHA",
    "hornets": "CHA",
    "chicago": "CHI",
    "bulls": "CHI",
    "cleveland": "CLE",
    "cavs": "CLE",
    "cavaliers": "CLE",
    "dallas": "DAL",
    "mavericks": "DAL",
    "mavs": "DAL",
    "denver": "DEN",
    "nuggets": "DEN",
    "detroit": "DET",
    "pistons": "DET",
    "golden state": "GSW",
    "warriors": "GSW",
    "houston": "HOU",
    "rockets": "HOU",
    "indiana": "IND",
    "pacers": "IND",
    "clippers": "LAC",
    "la clippers": "LAC",
    "los angeles clippers": "LAC",
    "lakers": "LAL",
    "la lakers": "LAL",
    "los angeles lakers": "LAL",
    "memphis": "MEM",
    "grizzlies": "MEM",
    "miami": "MIA",
    "heat": "MIA",
    "milwaukee": "MIL",
    "bucks": "MIL",
    "minnesota": "MIN",
    "wolves": "MIN",
    "timberwolves": "MIN",
    "new orleans": "NOP",
    "pelicans": "NOP",
    "new york": "NYK",
    "knicks": "NYK",
    "oklahoma city": "OKC",
    "thunder": "OKC",
    "orlando": "ORL",
    "magic": "ORL",
    "philadelphia": "PHI",
    "sixers": "PHI",
    "76ers": "PHI",
    "phoenix": "PHX",
    "suns": "PHX",
    "portland": "POR",
    "blazers": "POR",
    "trail blazers": "POR",
    "sacramento": "SAC",
    "kings": "SAC",
    "san antonio": "SAS",
    "spurs": "SAS",
    "toronto": "TOR",
    "raptors": "TOR",
    "utah": "UTA",
    "jazz": "UTA",
    "washington": "WAS",
    "wizards": "WAS",
}

PLAYER_ALIASES = {
    "kobe": "Kobe Bryant",
    "lebron": "LeBron James",
    "jokic": "Nikola Jokić",
    "nikola jokic": "Nikola Jokić",
    "embiid": "Joel Embiid",
    "joel embiid": "Joel Embiid",
    "luka": "Luka Dončić",
    "harden": "James Harden",
    "iverson": "Allen Iverson",
    "dirk": "Dirk Nowitzki",
    "rodman": "Dennis Rodman",
    "tim duncan": "Tim Duncan",
}

STOP_WORDS = r"(?:from|to|in|on|at|with|home|away|road|wins?|loss(?:es)?|summary|average|averages|record|for|during|playoff|playoffs|postseason|last|past|recent|form|split|over|under|between|and|or)"  # noqa: E501


MATCHUP_NOISE_PATTERN = r"\b(?:head\s*[- ]\s*to\s*[- ]\s*head|h2h|matchup|matchups)\b"


def strip_matchup_noise(text: str) -> str:
    return normalize_text(re.sub(MATCHUP_NOISE_PATTERN, " ", text))


def detect_head_to_head(text: str) -> bool:
    return bool(re.search(MATCHUP_NOISE_PATTERN, text))


LEADERBOARD_STAT_ALIASES = {
    "true shooting percentage": "ts_pct",
    "true shooting %": "ts_pct",
    "true shooting": "ts_pct",
    "effective field goal percentage": "efg_pct",
    "effective field goal %": "efg_pct",
    "effective field goal": "efg_pct",
    "effective fg %": "efg_pct",
    "effective fg": "efg_pct",
    "assists per game": "ast",
    "rebounds per game": "reb",
    "points per game": "pts",
    "three pointers made": "fg3m",
    "three-point makes": "fg3m",
    "threes made": "fg3m",
    "30-point games": "games_30p",
    "30 point games": "games_30p",
    "40-point games": "games_40p",
    "40 point games": "games_40p",
    "20-point games": "games_20p",
    "20 point games": "games_20p",
    "10-assist games": "games_10a",
    "10 assist games": "games_10a",
    "10-rebound games": "games_10r",
    "10 rebound games": "games_10r",
    "scorers": "pts",
    "scoring": "pts",
    "points": "pts",
    "rebounding": "reb",
    "rebounders": "reb",
    "rebounds": "reb",
    "assists": "ast",
    "apg": "ast",
    "rpg": "reb",
    "ppg": "pts",
    "3pm": "fg3m",
    "threes": "fg3m",
    "ts pct": "ts_pct",
    "ts%": "ts_pct",
    "efg pct": "efg_pct",
    "efg%": "efg_pct",
}


def extract_top_n(text: str) -> int | None:
    m = re.search(r"\btop\s+(\d+)\b", text)
    if not m:
        return None
    value = int(m.group(1))
    return value if value > 0 else None


def _matches_loose_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text))


def detect_player_leaderboard_stat(text: str) -> str | None:
    for key in sorted(LEADERBOARD_STAT_ALIASES.keys(), key=len, reverse=True):
        if _matches_loose_phrase(text, key):
            return LEADERBOARD_STAT_ALIASES[key]
    return None


def wants_leaderboard(text: str) -> bool:
    if re.search(
        r"\bseason leaders?\b|\bled the league\b|\bleaders?\s+in\b"
        r"|\b(?:career|playoff|all[- ]?time)\s+(?:\w+\s+)*leaders?\b"
        r"|\bleaders?\s+(?:since|last|past)\b",
        text,
    ):
        return True

    if re.search(r"\bin a game\b|\bsingle game\b|\bgame high\b|\bgame-high\b", text):
        return False

    if detect_player_leaderboard_stat(text) is None:
        return False

    return bool(re.search(r"\btop(?:\s+\d+)?\b|\bhighest\b|\bmost\b|\bbest\b", text))


TEAM_LEADERBOARD_STAT_ALIASES = {
    "best offensive teams": "off_rating",
    "offensive teams": "off_rating",
    "best offense": "off_rating",
    "offensive rating": "off_rating",
    "off rating": "off_rating",
    "teams with most threes": "fg3m",
    "most threes per game teams": "fg3m",
    "most threes per game": "fg3m",
    "teams with best efg%": "efg_pct",
    "teams with best efg pct": "efg_pct",
    "best team efg%": "efg_pct",
    "best efg% teams": "efg_pct",
    "teams with best ts%": "ts_pct",
    "teams with best ts pct": "ts_pct",
    "best team ts%": "ts_pct",
    "best ts% teams": "ts_pct",
    "best net rating teams": "net_rating",
    "fastest teams": "pace",
}


def detect_team_leaderboard_stat(text: str) -> str | None:
    for key in sorted(TEAM_LEADERBOARD_STAT_ALIASES.keys(), key=len, reverse=True):
        if _matches_loose_phrase(text, key):
            return TEAM_LEADERBOARD_STAT_ALIASES[key]
    return None


def wants_team_leaderboard(text: str) -> bool:
    if detect_team_leaderboard_stat(text) is not None:
        return True

    if re.search(r"\bteams?\b", text):
        if re.search(r"\b(best|highest|most|top(?:\s+\d+)?)\b", text):
            return True

    return False


def normalize_text(text: str) -> str:
    return " ".join(text.lower().strip().split())


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


MONTH_NAME_TO_NUM = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

CURRENT_QUERY_DATE = pd.Timestamp.now(tz=ZoneInfo("America/Detroit")).floor("D").tz_localize(None)

ALL_STAR_BREAK_START_OVERRIDES = {
    "2022-23": "2023-02-20",
    "2023-24": "2024-02-19",
    "2024-25": "2025-02-17",
    "2025-26": "2026-02-16",
}


def _infer_all_star_break_start(season: str | None) -> str | None:
    if season in ALL_STAR_BREAK_START_OVERRIDES:
        return ALL_STAR_BREAK_START_OVERRIDES[season]

    if season and re.match(r"^(?:19|20)\d{2}-\d{2}$", season):
        end_year = int(season.split("-")[0]) + 1
    else:
        end_year = (
            CURRENT_QUERY_DATE.year if CURRENT_QUERY_DATE.month < 7 else CURRENT_QUERY_DATE.year + 1
        )

    cal = monthcalendar(end_year, 2)
    sundays = [week[6] for week in cal if week[6] != 0]
    if len(sundays) < 3:
        return None

    third_sunday = sundays[2]
    start_ts = pd.Timestamp(year=end_year, month=2, day=third_sunday) + pd.Timedelta(days=1)
    return start_ts.date().isoformat()


def _resolve_year_for_month_in_season(season: str | None, month_num: int) -> int:
    if season and re.match(r"^(?:19|20)\d{2}-\d{2}$", season):
        start_year = int(season.split("-")[0])
        return start_year if month_num >= 10 else start_year + 1

    current_year = int(CURRENT_QUERY_DATE.year)
    current_month = int(CURRENT_QUERY_DATE.month)
    return current_year if month_num <= current_month else current_year - 1


def extract_date_range(text: str, season: str | None) -> tuple[str | None, str | None]:
    if re.search(r"\b(?:since|after|post)\s+(?:the\s+)?all[- ]star\s+break\b", text):
        return _infer_all_star_break_start(season), None

    m = re.search(r"\blast\s+(\d+)\s+days?\b", text)
    if m:
        days = int(m.group(1))
        if days > 0:
            start = (CURRENT_QUERY_DATE - pd.Timedelta(days=days - 1)).date().isoformat()
            end = CURRENT_QUERY_DATE.date().isoformat()
            return start, end

    month_pattern = "|".join(MONTH_NAME_TO_NUM.keys())

    m = re.search(rf"\bsince\s+({month_pattern})\b", text)
    if m:
        month_num = MONTH_NAME_TO_NUM[m.group(1)]
        year = _resolve_year_for_month_in_season(season, month_num)
        start = f"{year}-{month_num:02d}-01"
        return start, None

    m = re.search(rf"\b(?:in|during)\s+({month_pattern})\b", text)
    if m:
        month_num = MONTH_NAME_TO_NUM[m.group(1)]
        year = _resolve_year_for_month_in_season(season, month_num)
        last_day = monthrange(year, month_num)[1]
        start = f"{year}-{month_num:02d}-01"
        end = f"{year}-{month_num:02d}-{last_day:02d}"
        return start, end

    return None, None


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


def detect_player(text: str) -> str | None:
    for key in sorted(PLAYER_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", text):
            return PLAYER_ALIASES[key]
    return None


def detect_team_in_text(text: str) -> str | None:
    for key in sorted(TEAM_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(key)}\b", text):
            return TEAM_ALIASES[key]
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
    patterns = [
        (
            rf"\bbetween\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)\s+{STAT_PATTERN}\b",
            "between",
            0.0,
        ),
        (
            rf"\bover\s+(\d+(?:\.\d+)?)\s+{STAT_PATTERN}\b",
            "min",
            0.0001,
        ),
        (
            rf"\bat least\s+(\d+(?:\.\d+)?)\s+{STAT_PATTERN}\b",
            "min",
            0.0,
        ),
        (
            rf"\bunder\s+(\d+(?:\.\d+)?)\s+{STAT_PATTERN}\b",
            "max",
            0.0001,
        ),
        (
            rf"\bless than\s+(\d+(?:\.\d+)?)\s+{STAT_PATTERN}\b",
            "max",
            0.0001,
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


def wants_recent_form(text: str) -> bool:
    return bool(re.search(r"\b(recent form|form)\b", text))


def wants_split_summary(text: str) -> bool:
    return "split" in text or detect_split_type(text) is not None


def detect_opponent(text: str) -> tuple[str | None, str]:
    cleaned_text = strip_matchup_noise(text)

    patterns = [
        rf"\bvs\.?\s+([a-z0-9 .&'-]+?)(?=\s+{STOP_WORDS}\b|$)",
        rf"\bversus\s+([a-z0-9 .&'-]+?)(?=\s+{STOP_WORDS}\b|$)",
        rf"\bagainst\s+([a-z0-9 .&'-]+?)(?=\s+{STOP_WORDS}\b|$)",
    ]

    for pattern in patterns:
        m = re.search(pattern, cleaned_text)
        if not m:
            continue

        phrase = m.group(1).strip()
        detected = detect_team_in_text(phrase)
        if detected:
            cleaned = (cleaned_text[: m.start()] + " " + cleaned_text[m.end() :]).strip()
            cleaned = normalize_text(cleaned)
            return detected, cleaned

    return None, cleaned_text


def extract_player_comparison(text: str) -> tuple[str | None, str | None]:
    cleaned_text = strip_matchup_noise(text)

    for alias_a, player_a in sorted(PLAYER_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        stop = STOP_WORDS
        pattern = (  # noqa: E501
            rf"\b{re.escape(alias_a)}\b\s+(?:vs\.?|versus)\s+([a-z0-9 .&'\-]+?)"
            rf"(?=\s+(?:{stop})\b|$)"
        )
        m = re.search(pattern, cleaned_text)
        if not m:
            continue

        phrase_b = m.group(1).strip()
        player_b = detect_player(phrase_b)
        if player_b:
            return player_a, player_b

    return None, None


def extract_team_comparison(text: str) -> tuple[str | None, str | None]:
    cleaned_text = strip_matchup_noise(text)

    team_keys = sorted(TEAM_ALIASES.keys(), key=len, reverse=True)
    for alias_a in team_keys:
        stop = STOP_WORDS
        pattern = (
            rf"\b{re.escape(alias_a)}\b\s+(?:vs\.?|versus)\s+([a-z0-9 .&'\-]+?)"
            rf"(?=\s+(?:{stop})\b|$)"
        )
        m = re.search(pattern, cleaned_text)
        if not m:
            continue

        team_a = TEAM_ALIASES[alias_a]
        phrase_b = m.group(1).strip()
        team_b = detect_team_in_text(phrase_b)
        if team_b and team_b != team_a:
            return team_a, team_b

    return None, None


def _ensure_parent_dir(path_str: str) -> None:
    path = Path(path_str)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)


def _write_text_file(path_str: str, text: str) -> None:
    _ensure_parent_dir(path_str)
    Path(path_str).write_text(text, encoding="utf-8")


_SINGLE_TABLE_LABELS = ("FINDER", "LEADERBOARD", "STREAK", "TABLE", "NO_RESULT", "ERROR")


# ---------------------------------------------------------------------------
# Structured-first build_result map
# ---------------------------------------------------------------------------
# Maps route name → build_result callable, used by the structured-first
# orchestration path so we never need to capture stdout from run().

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
                "player_split_summary": player_split_summary_build_result,
                "team_split_summary": team_split_summary_build_result,
                "player_streak_finder": player_streak_finder_build_result,
                "team_streak_finder": team_streak_finder_build_result,
            }
        )
    return _BUILD_RESULT_MAP


# ---------------------------------------------------------------------------
# Structured-first helpers: work on result objects, not text
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
    This replaces _apply_extra_conditions_to_raw_output for structured-first paths.
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
    """Build a structured result directly from a command's build_result().

    Replaces _execute_capture_raw: no stdout capture, no text stripping.
    """
    if extra_conditions is None:
        extra_conditions = []

    build_fn = _get_build_result_map()[route]
    result = build_fn(**kwargs)

    if extra_conditions:
        result = _apply_extra_conditions_to_result(result, extra_conditions)

    return result


def _combine_or_results(results: list):
    """Combine multiple finder-style results (for OR queries) into one FinderResult.

    Replaces _combine_or_raw_outputs: works with DataFrames directly.
    """
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
            pass

    if "rank" in combined.columns:
        combined = combined.drop(columns="rank")
        combined.insert(0, "rank", range(1, len(combined) + 1))

    if first_columns:
        ordered = [c for c in first_columns if c in combined.columns]
        extras = [c for c in combined.columns if c not in ordered]
        combined = combined[ordered + extras]

    return FinderResult(games=combined)


def _execute_or_query_build_result(query: str):
    """Build a structured result for OR queries.

    Replaces _execute_or_query_capture_raw: uses build_result directly.
    """
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
    """Build a structured result for grouped boolean queries.

    Replaces _execute_grouped_boolean_query_capture_raw: passes pre-filtered
    DataFrames to build_result(df=...) instead of calling run() via stdout.
    """
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
            pass

    if "rank" in df.columns:
        df = df.drop(columns="rank")
        df.insert(0, "rank", range(1, len(df) + 1))

    return FinderResult(games=df)


def _emit_result(
    result,
    parsed: dict,
    query: str,
    grouped_boolean_used: bool,
    pretty: bool,
    export_csv_path: str | None,
    export_txt_path: str | None,
    export_json_path: str | None,
) -> None:
    """Emit output from a structured result — no text round-tripping.

    Replaces _emit: renders, exports, and prints from the result object.
    """
    metadata = _build_metadata_dict(parsed, query, grouped_boolean_used)
    query_class = route_to_query_class(parsed.get("route") if parsed else None)

    # NoResult: use the canonical no-result output format
    if isinstance(result, NoResult):
        reason = result.result_reason or result.reason or "no_match"
        wrapped = build_no_result_output(metadata, reason=reason)
    else:
        wrapped = wrap_result_with_metadata(result, metadata, query_class)

    # Export directly from structured result (no text reparsing)
    if export_csv_path:
        write_csv_from_result(result, export_csv_path)

    if export_json_path:
        write_json_from_result(result, export_json_path, metadata)

    if export_txt_path:
        if pretty:
            text_to_save = format_pretty_from_result(result, query)
        else:
            text_to_save = wrapped
        _write_text_file(
            export_txt_path, text_to_save + ("" if text_to_save.endswith("\n") else "\n")
        )

    # Console output
    if not pretty:
        print(wrapped, end="" if wrapped.endswith("\n") else "\n")
        return

    pretty_text = format_pretty_from_result(result, query)
    print(pretty_text)


def _build_metadata_dict(parsed: dict, query: str, grouped_boolean_used: bool) -> dict:
    if not parsed:
        return {"query_text": query}

    route = parsed.get("route")
    query_class = route_to_query_class(route)

    player = parsed.get("player")
    if not player:
        player_a = parsed.get("player_a")
        player_b = parsed.get("player_b")
        if player_a and player_b:
            player = f"{player_a}, {player_b}"
        else:
            player = player_a or player_b

    team = parsed.get("team")
    if not team:
        team_a = parsed.get("team_a")
        team_b = parsed.get("team_b")
        if team_a and team_b:
            team = f"{team_a}, {team_b}"
        else:
            team = team_a or team_b

    notes = parsed.get("notes") or []

    # -- compute current_through from available season info --
    current_through: str | None = None
    season = parsed.get("season")
    start_season = parsed.get("start_season")
    end_season = parsed.get("end_season")
    season_type = parsed.get("season_type") or "Regular Season"

    if season:
        current_through = compute_current_through_for_seasons([season], season_type)
    elif start_season and end_season:
        from nbatools.commands._seasons import int_to_season, season_to_int

        seasons = [
            int_to_season(y)
            for y in range(season_to_int(start_season), season_to_int(end_season) + 1)
        ]
        current_through = compute_current_through_for_seasons(seasons, season_type)

    meta: dict = {
        "query_text": query,
        "route": route,
        "query_class": query_class,
        "season": season,
        "start_season": start_season,
        "end_season": end_season,
        "season_type": parsed.get("season_type"),
        "start_date": parsed.get("start_date"),
        "end_date": parsed.get("end_date"),
        "player": player,
        "team": team,
        "opponent": parsed.get("opponent"),
        "split_type": parsed.get("split_type"),
        "grouped_boolean_used": grouped_boolean_used,
        "head_to_head_used": bool(parsed.get("head_to_head")),
    }

    if current_through is not None:
        meta["current_through"] = current_through

    if notes:
        meta["notes"] = notes

    return meta


def _wrap_natural_query_raw(
    raw_text: str, parsed: dict, query: str, grouped_boolean_used: bool
) -> str:
    metadata = _build_metadata_dict(parsed, query, grouped_boolean_used)
    query_class = route_to_query_class(parsed.get("route") if parsed else None)
    return wrap_raw_output(raw_text, metadata, query_class)


def _write_csv_from_raw_output(raw_text: str, path_str: str) -> None:
    _ensure_parent_dir(path_str)
    text = (raw_text or "").strip()

    if not text:
        Path(path_str).write_text("", encoding="utf-8")
        return

    if text.lower() == "no matching games":
        Path(path_str).write_text("message\nno matching games\n", encoding="utf-8")
        return

    sections = parse_labeled_sections(text)
    sections_no_meta = {k: v for k, v in sections.items() if k != METADATA_LABEL}

    if not sections_no_meta:
        Path(path_str).write_text("", encoding="utf-8")
        return

    if len(sections_no_meta) == 1:
        only_label, only_block = next(iter(sections_no_meta.items()))
        if only_label in _SINGLE_TABLE_LABELS:
            if only_block.lower() == "no matching games":
                Path(path_str).write_text("message\nno matching games\n", encoding="utf-8")
                return
            try:
                df = pd.read_csv(StringIO(only_block))
                df.to_csv(path_str, index=False)
                return
            except Exception:
                Path(path_str).write_text(
                    only_block + ("\n" if not only_block.endswith("\n") else ""),
                    encoding="utf-8",
                )
                return

    parts: list[str] = []
    for label in (
        "SUMMARY",
        "BY_SEASON",
        "COMPARISON",
        "SPLIT_COMPARISON",
        "FINDER",
        "LEADERBOARD",
        "STREAK",
        "NO_RESULT",
        "ERROR",
    ):
        if label in sections_no_meta:
            parts.append(f"{label}\n{sections_no_meta[label]}")
    if not parts and "TABLE" in sections_no_meta:
        parts.append(sections_no_meta["TABLE"])

    rebuilt = "\n\n".join(parts).strip()
    Path(path_str).write_text(rebuilt + "\n", encoding="utf-8")


def _write_json_from_raw_output(raw_text: str, path_str: str) -> None:
    _ensure_parent_dir(path_str)
    text = (raw_text or "").strip()

    if not text:
        Path(path_str).write_text("[]\n", encoding="utf-8")
        return

    if text.lower() == "no matching games":
        payload = {"message": "no matching games"}
        Path(path_str).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return

    sections = parse_labeled_sections(text)
    metadata_block = sections.pop(METADATA_LABEL, None)

    payload: dict[str, object] = {}

    if metadata_block is not None:
        meta = parse_metadata_block(metadata_block)
        if "notes" in meta and isinstance(meta["notes"], str):
            meta["notes"] = [n for n in meta["notes"].split("|") if n]
        payload["metadata"] = meta

    for label, block in sections.items():
        if not block:
            continue
        key = label.lower() if label != "TABLE" else "table"
        if block.lower() == "no matching games":
            payload[key] = []
            continue
        try:
            df = pd.read_csv(StringIO(block))
            payload[key] = df.to_dict(orient="records")
        except Exception:
            payload[key] = block

    if not payload:
        try:
            df = pd.read_csv(StringIO(text))
            payload_list = df.to_dict(orient="records")
            Path(path_str).write_text(
                json.dumps(payload_list, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return
        except Exception:
            payload = {"raw_text": text}

    Path(path_str).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _apply_extra_conditions_to_raw_output(raw_text: str, extra_conditions: list[dict]) -> str:
    if not extra_conditions:
        return raw_text

    text = raw_text.strip()
    if not text or text.startswith("SUMMARY\n"):
        return raw_text

    try:
        df = pd.read_csv(StringIO(text))
    except Exception:
        return raw_text

    for cond in extra_conditions:
        stat = cond["stat"]
        if stat not in df.columns:
            return "no matching games\n"
        if cond["min_value"] is not None:
            df = df[df[stat] >= cond["min_value"]]
        if cond["max_value"] is not None:
            df = df[df[stat] <= cond["max_value"]]

    if df.empty:
        return "no matching games\n"

    return df.to_csv(index=False)


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
    head_to_head = detect_head_to_head(q)
    streak_request = extract_streak_request(q)
    team_streak_request = extract_team_streak_request(q)

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
        ):
            season = default_season_for_context(season_type)

    player_a, player_b = extract_player_comparison(q)
    team_a, team_b = (None, None)

    if not (player_a and player_b):
        team_a, team_b = extract_team_comparison(q)

    player = None
    if not (player_a and player_b):
        player = detect_player(q)

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
        "range_intent": range_intent,
        "career_intent": career_intent,
        "split_intent": split_intent,
        "leaderboard_intent": leaderboard_intent,
        "team_leaderboard_intent": team_leaderboard_intent,
        "head_to_head": head_to_head,
        "streak_request": streak_request,
        "team_streak_request": team_streak_request,
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
    range_intent = parsed["range_intent"]
    career_intent = parsed.get("career_intent", False)
    leaderboard_intent = parsed.get("leaderboard_intent", False)
    team_leaderboard_intent = parsed.get("team_leaderboard_intent", False)
    head_to_head = parsed.get("head_to_head", False)
    streak_request = parsed.get("streak_request")
    team_streak_request = parsed.get("team_streak_request")

    notes: list[str] = []
    route = None
    route_kwargs = None

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
            "opponent": None,
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

        if team_leaderboard_intent:
            leaderboard_stat = detect_team_leaderboard_stat(q) or stat or "pts"
            if (start_date or end_date) and leaderboard_stat == "off_rating":
                notes.append("stat_fallback: off_rating not available with date window, using pts")
                leaderboard_stat = "pts"
            if (lb_start_season and lb_end_season) and leaderboard_stat in (
                "off_rating",
                "def_rating",
                "net_rating",
                "pace",
            ):
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
                "ascending": False,
                "start_date": start_date,
                "end_date": end_date,
                "start_season": lb_start_season,
                "end_season": lb_end_season,
                "opponent": opponent,
            }
        elif "team" in q or "teams" in q:
            leaderboard_stat = stat or "pts"
            if (start_date or end_date) and leaderboard_stat == "off_rating":
                notes.append("stat_fallback: off_rating not available with date window, using pts")
                leaderboard_stat = "pts"
            if (lb_start_season and lb_end_season) and leaderboard_stat in (
                "off_rating",
                "def_rating",
                "net_rating",
                "pace",
            ):
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
                "ascending": False,
                "start_date": start_date,
                "end_date": end_date,
                "start_season": lb_start_season,
                "end_season": lb_end_season,
                "opponent": opponent,
            }
        else:
            leaderboard_stat = detect_player_leaderboard_stat(q) or stat or "pts"
            if (lb_start_season and lb_end_season) and leaderboard_stat in (
                "usage_rate",
                "net_rating",
                "off_rating",
                "def_rating",
            ):
                notes.append(
                    f"stat_fallback: {leaderboard_stat} not available for multi-season, using pts"
                )
                leaderboard_stat = "pts"
            if opponent and leaderboard_stat in (
                "usage_rate",
                "net_rating",
                "off_rating",
                "def_rating",
            ):
                notes.append(
                    f"stat_fallback: {leaderboard_stat} not available with opponent filter, using pts"
                )
                leaderboard_stat = "pts"
            route = "season_leaders"
            route_kwargs = {
                "season": lb_season,
                "stat": leaderboard_stat,
                "limit": top_n or 10,
                "season_type": season_type,
                "min_games": 1,
                "ascending": False,
                "start_date": start_date,
                "end_date": end_date,
                "start_season": lb_start_season,
                "end_season": lb_end_season,
                "opponent": opponent,
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
            "sample_advanced_metrics: usg_pct, ast_pct, reb_pct recomputed from filtered sample"
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


def _strip_new_section_label(text: str) -> str:
    """Strip FINDER/LEADERBOARD/STREAK label prefix from structured run() output.

    These labels are emitted by the new structured-first run() functions.
    The natural query layer needs raw CSV for post-processing (extra conditions,
    OR combining, grouped boolean evaluation).  SUMMARY/COMPARISON/SPLIT labels
    are left intact because existing bail-out checks depend on them.
    """
    for label in ("FINDER", "LEADERBOARD", "STREAK"):
        prefix = f"{label}\n"
        if text.startswith(prefix):
            return text[len(prefix) :]
    return text


def _execute_capture_raw(
    func: Callable,
    kwargs: dict,
    extra_conditions: list[dict] | None = None,
) -> str:
    if extra_conditions is None:
        extra_conditions = []

    buffer = StringIO()
    with redirect_stdout(buffer):
        func(**kwargs)
    raw_text = _strip_new_section_label(buffer.getvalue())

    if extra_conditions:
        raw_text = _apply_extra_conditions_to_raw_output(raw_text, extra_conditions)

    return raw_text


def _combine_or_raw_outputs(raw_outputs: list[str]) -> str:
    frames = []
    first_columns: list[str] | None = None

    for raw_text in raw_outputs:
        text = raw_text.strip()
        if not text or text.lower() == "no matching games" or text.startswith("SUMMARY\n"):
            continue
        try:
            df = pd.read_csv(StringIO(text))
        except Exception:
            continue

        if first_columns is None:
            first_columns = list(df.columns)
        frames.append(df)

    if not frames:
        return "no matching games\n"

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
            pass

    if "rank" in combined.columns:
        combined = combined.drop(columns="rank")
        combined.insert(0, "rank", range(1, len(combined) + 1))

    if first_columns:
        ordered = [c for c in first_columns if c in combined.columns]
        extras = [c for c in combined.columns if c not in ordered]
        combined = combined[ordered + extras]

    return combined.to_csv(index=False)


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
        r"\b(summary|summarize|average|averages|avg|record|split|form|where|games|game)\b",
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


def _execute_grouped_boolean_query_capture_raw(query: str) -> str:
    parsed = parse_query(query)
    route = parsed["route"]

    if route in {"player_game_summary", "player_split_summary"}:
        condition_text = _extract_grouped_condition_text(query)
        if not expression_contains_boolean_ops(condition_text):
            raise ValueError("No grouped boolean expression detected.")

        tree = parse_condition_text(condition_text)
        base_df = _load_grouped_player_base_df(parsed)

        if base_df.empty:
            return "no matching games\n"

        filtered_df = evaluate_condition_tree(tree, base_df)

        if filtered_df.empty:
            return "no matching games\n"

        buffer = StringIO()
        with redirect_stdout(buffer):
            if route == "player_game_summary":
                player_game_summary_run(
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
                player_split_summary_run(
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
        return buffer.getvalue()

    if route in {"game_summary", "team_split_summary"}:
        condition_text = _extract_grouped_condition_text(query)
        if not expression_contains_boolean_ops(condition_text):
            raise ValueError("No grouped boolean expression detected.")

        tree = parse_condition_text(condition_text)
        base_df = _load_grouped_team_base_df(parsed)

        if base_df.empty:
            return "no matching games\n"

        filtered_df = evaluate_condition_tree(tree, base_df)

        if filtered_df.empty:
            return "no matching games\n"

        buffer = StringIO()
        with redirect_stdout(buffer):
            if route == "game_summary":
                game_summary_run(
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
                team_split_summary_run(
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
        return buffer.getvalue()

    if route not in {"player_game_finder", "game_finder"}:
        raise ValueError(
            "Grouped boolean logic is currently supported for finder, player summary/split, "
            "and team summary/split natural queries."
        )

    condition_text = _extract_grouped_condition_text(query)
    if not expression_contains_boolean_ops(condition_text):
        raise ValueError("No grouped boolean expression detected.")

    tree = parse_condition_text(condition_text)

    base_kwargs = dict(parsed["route_kwargs"])
    base_kwargs["stat"] = None
    base_kwargs["min_value"] = None
    base_kwargs["max_value"] = None
    base_kwargs["sort_by"] = "game_date"
    base_kwargs["ascending"] = False

    func_map = {
        "player_game_finder": player_game_finder_run,
        "game_finder": game_finder_run,
    }
    func = func_map[route]

    raw_text = _execute_capture_raw(func, base_kwargs)
    text = raw_text.strip()

    if not text or text.lower() == "no matching games" or text.startswith("SUMMARY\n"):
        return raw_text

    try:
        df = pd.read_csv(StringIO(text))
    except Exception:
        return raw_text

    df = evaluate_condition_tree(tree, df)

    if df.empty:
        return "no matching games\n"

    if "game_date" in df.columns:
        try:
            df["_game_date_sort"] = pd.to_datetime(df["game_date"], errors="coerce")
            sort_cols = ["_game_date_sort"]
            ascending = [False]
            if "game_id" in df.columns:
                sort_cols.append("game_id")
                ascending.append(False)
            df = df.sort_values(sort_cols, ascending=ascending)
            df = df.drop(columns="_game_date_sort")
        except Exception:
            pass

    if "rank" in df.columns:
        df = df.drop(columns="rank")
        df.insert(0, "rank", range(1, len(df) + 1))

    return df.to_csv(index=False)


def _execute_or_query_capture_raw(query: str) -> str:
    clauses = _split_or_clauses(query)
    if len(clauses) <= 1:
        parsed = parse_query(query)
        func_map = {
            "top_player_games": top_player_games_run,
            "top_team_games": top_team_games_run,
            "season_leaders": season_leaders_run,
            "season_team_leaders": season_team_leaders_run,
            "player_game_summary": player_game_summary_run,
            "game_summary": game_summary_run,
            "player_game_finder": player_game_finder_run,
            "player_streak_finder": player_streak_finder_run,
            "team_streak_finder": team_streak_finder_run,
            "game_finder": game_finder_run,
            "player_compare": player_compare_run,
            "team_compare": team_compare_run,
            "player_split_summary": player_split_summary_run,
            "team_split_summary": team_split_summary_run,
        }
        func = func_map[parsed["route"]]
        return _execute_capture_raw(
            func, parsed["route_kwargs"], parsed.get("extra_conditions", [])
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

    func_map = {
        "player_game_finder": player_game_finder_run,
        "game_finder": game_finder_run,
    }
    route = clause_parsed[0]["route"]
    func = func_map[route]

    raw_outputs = []
    for item in clause_parsed:
        raw_outputs.append(
            _execute_capture_raw(func, item["route_kwargs"], item.get("extra_conditions", []))
        )

    return _combine_or_raw_outputs(raw_outputs)


_ROUTE_FUNC_MAP: dict[str, Callable] = {}


def _get_route_func_map() -> dict[str, Callable]:
    if not _ROUTE_FUNC_MAP:
        _ROUTE_FUNC_MAP.update(
            {
                "top_player_games": top_player_games_run,
                "top_team_games": top_team_games_run,
                "season_leaders": season_leaders_run,
                "season_team_leaders": season_team_leaders_run,
                "player_game_summary": player_game_summary_run,
                "game_summary": game_summary_run,
                "player_game_finder": player_game_finder_run,
                "player_streak_finder": player_streak_finder_run,
                "team_streak_finder": team_streak_finder_run,
                "game_finder": game_finder_run,
                "player_compare": player_compare_run,
                "team_compare": team_compare_run,
                "player_split_summary": player_split_summary_run,
                "team_split_summary": team_split_summary_run,
            }
        )
    return _ROUTE_FUNC_MAP


def _emit(
    raw_text: str,
    parsed: dict,
    query: str,
    grouped_boolean_used: bool,
    pretty: bool,
    export_csv_path: str | None,
    export_txt_path: str | None,
    export_json_path: str | None,
) -> None:
    wrapped = _wrap_natural_query_raw(raw_text, parsed, query, grouped_boolean_used)
    pretty_text = format_pretty_output(wrapped, query)

    if export_csv_path:
        _write_csv_from_raw_output(wrapped, export_csv_path)

    if export_json_path:
        _write_json_from_raw_output(wrapped, export_json_path)

    if export_txt_path:
        text_to_save = wrapped if not pretty else pretty_text
        _write_text_file(
            export_txt_path, text_to_save + ("" if text_to_save.endswith("\n") else "\n")
        )

    if not pretty:
        print(wrapped, end="" if wrapped.endswith("\n") else "\n")
        return

    print(pretty_text)


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
    grouped_boolean_used = metadata.get("grouped_boolean_used", False)
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
        _write_text_file(
            export_txt_path, text_to_save + ("" if text_to_save.endswith("\n") else "\n")
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

    normalized = normalize_text(query)

    grouped_boolean_used = expression_contains_boolean_ops(normalized) and (
        "(" in normalized or ")" in normalized
    )

    qr = execute_natural_query(query)

    # For grouped boolean / OR edge cases where the service returned an
    # error, fall back to the legacy text-based capture path for backward
    # compatibility.
    if not qr.is_ok and getattr(qr.result, "reason", None) == "error":
        if grouped_boolean_used:
            try:
                raw_text = _execute_grouped_boolean_query_capture_raw(query)
                try:
                    parsed = parse_query(query)
                except Exception:
                    parsed = _build_parse_state(query)
                _emit(
                    raw_text,
                    parsed,
                    query,
                    grouped_boolean_used=True,
                    pretty=pretty,
                    export_csv_path=export_csv_path,
                    export_txt_path=export_txt_path,
                    export_json_path=export_json_path,
                )
                return
            except Exception:
                pass  # fall through to render the NoResult from service

        elif " or " in normalized:
            try:
                raw_text = _execute_or_query_capture_raw(query)
                try:
                    parsed = parse_query(query)
                except Exception:
                    parsed = _build_parse_state(query)
                _emit(
                    raw_text,
                    parsed,
                    query,
                    grouped_boolean_used=False,
                    pretty=pretty,
                    export_csv_path=export_csv_path,
                    export_txt_path=export_txt_path,
                    export_json_path=export_json_path,
                )
                return
            except Exception:
                pass  # fall through to render the NoResult from service

    # Render from the service result
    render_query_result(
        qr,
        query,
        pretty=pretty,
        export_csv_path=export_csv_path,
        export_txt_path=export_txt_path,
        export_json_path=export_json_path,
    )
