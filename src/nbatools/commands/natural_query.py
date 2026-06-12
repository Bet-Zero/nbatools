import re

import pandas as pd

from nbatools.commands._condition_utils import normalize_stat_conditions, stat_conditions_cover
from nbatools.commands._confidence import compute_parse_confidence, generate_alternates
from nbatools.commands._constants import (
    LOWER_IS_BETTER_STATS,
    PLAYER_SEASON_ONLY_STATS,
    STAT_ALIASES,
    TEAM_SEASON_ADVANCED_STATS,
    TEAM_SEASON_ONLY_STATS,
    normalize_text,
    route_to_intent,
)
from nbatools.commands._date_utils import (
    CURRENT_QUERY_DATE,
    MONTH_NAME_TO_NUM,
    extract_date_range,
    has_explicit_calendar_date,
    uses_fuzzy_date_term,
)
from nbatools.commands._default_rules import (
    metric_only_leaderboard_default,
    player_stat_context_summary_default,
    player_threshold_finder_default,
    player_timeframe_summary_default,
    streak_default_window,
    team_threshold_finder_default,
)
from nbatools.commands._leaderboard_utils import (
    detect_player_leaderboard_stat,
    detect_team_leaderboard_stat,
    wants_ascending_leaderboard,
)
from nbatools.commands._lineup_on_off_route_utils import try_lineup_on_off_route
from nbatools.commands._matchup_utils import (
    detect_bare_player_vs_player_query,
    detect_head_to_head,
    detect_opponent,
    detect_opponent_player,
    detect_player,
    detect_player_resolved,
    detect_team_resolved,
    detect_unresolved_availability_player,
    detect_unresolved_player_typo,
    detect_with_player,
    detect_without_player,
    extract_adjacent_playoff_team_comparison,
    extract_player_comparison,
    extract_team_comparison,
)
from nbatools.commands._natural_query_execution import (  # noqa: F401
    _apply_extra_conditions_to_result,
    _combine_or_results,
    _execute_build_result,
    _execute_grouped_boolean_build_result,
    _execute_or_query_build_result,
    _get_build_result_map,
    _split_or_clauses,
    render_query_result,
)
from nbatools.commands._occurrence_route_utils import (
    _COMPOUND_STAT_MAP,  # noqa: F401
    _parse_single_threshold,  # noqa: F401
    extract_compound_occurrence_event,
    extract_occurrence_event,
    try_compound_occurrence_route,
    try_occurrence_count_route,
    wants_occurrence_leaderboard,
)
from nbatools.commands._parse_helpers import (
    STREAK_SPECIAL_PATTERNS as STREAK_SPECIAL_PATTERNS,
)
from nbatools.commands._parse_helpers import (
    TEAM_STREAK_SPECIAL_PATTERNS as TEAM_STREAK_SPECIAL_PATTERNS,
)
from nbatools.commands._parse_helpers import (
    build_game_context_filter_notes as build_game_context_filter_notes,
)
from nbatools.commands._parse_helpers import (
    build_on_off_note as build_on_off_note,
)
from nbatools.commands._parse_helpers import (
    build_opponent_quality_note as build_opponent_quality_note,
)
from nbatools.commands._parse_helpers import (
    build_period_filter_note as build_period_filter_note,
)
from nbatools.commands._parse_helpers import (
    build_role_filter_note as build_role_filter_note,
)
from nbatools.commands._parse_helpers import (
    default_season_for_context as default_season_for_context,
)
from nbatools.commands._parse_helpers import (
    detect_award_query_boundary as detect_award_query_boundary,
)
from nbatools.commands._parse_helpers import (
    detect_back_to_back as detect_back_to_back,
)
from nbatools.commands._parse_helpers import (
    detect_career_intent as detect_career_intent,
)
from nbatools.commands._parse_helpers import (
    detect_championship_count_boundary as detect_championship_count_boundary,
)
from nbatools.commands._parse_helpers import (
    detect_clutch as detect_clutch,
)
from nbatools.commands._parse_helpers import (
    detect_distinct_player_count as detect_distinct_player_count,
)
from nbatools.commands._parse_helpers import (
    detect_distinct_team_count as detect_distinct_team_count,
)
from nbatools.commands._parse_helpers import (
    detect_half as detect_half,
)
from nbatools.commands._parse_helpers import (
    detect_home_away as detect_home_away,
)
from nbatools.commands._parse_helpers import (
    detect_lineup_query as detect_lineup_query,
)
from nbatools.commands._parse_helpers import (
    detect_nationally_televised as detect_nationally_televised,
)
from nbatools.commands._parse_helpers import (
    detect_on_off as detect_on_off,
)
from nbatools.commands._parse_helpers import (
    detect_one_possession as detect_one_possession,
)
from nbatools.commands._parse_helpers import (
    detect_opponent_conference as detect_opponent_conference,
)
from nbatools.commands._parse_helpers import (
    detect_opponent_conference_boundary as detect_opponent_conference_boundary,
)
from nbatools.commands._parse_helpers import (
    detect_opponent_conference_geography_boundary as detect_opponent_conference_geography_boundary,
)
from nbatools.commands._parse_helpers import (
    detect_opponent_division as detect_opponent_division,
)
from nbatools.commands._parse_helpers import (
    detect_opponent_division_boundary as detect_opponent_division_boundary,
)
from nbatools.commands._parse_helpers import (
    detect_opponent_quality as detect_opponent_quality,
)
from nbatools.commands._parse_helpers import (
    detect_player_summary_stat_context as detect_player_summary_stat_context,
)
from nbatools.commands._parse_helpers import (
    detect_quarter as detect_quarter,
)
from nbatools.commands._parse_helpers import (
    detect_rest_days as detect_rest_days,
)
from nbatools.commands._parse_helpers import (
    detect_role as detect_role,
)
from nbatools.commands._parse_helpers import (
    detect_role_leaderboard_boundary as detect_role_leaderboard_boundary,
)
from nbatools.commands._parse_helpers import (
    detect_rookie_leaderboard_boundary as detect_rookie_leaderboard_boundary,
)
from nbatools.commands._parse_helpers import (
    detect_schedule_lookup_boundary as detect_schedule_lookup_boundary,
)
from nbatools.commands._parse_helpers import (
    detect_season_high_intent as detect_season_high_intent,
)
from nbatools.commands._parse_helpers import (
    detect_season_type as detect_season_type,
)
from nbatools.commands._parse_helpers import (
    detect_split_type as detect_split_type,
)
from nbatools.commands._parse_helpers import (
    detect_stat as detect_stat,
)
from nbatools.commands._parse_helpers import (
    detect_stretch_query as detect_stretch_query,
)
from nbatools.commands._parse_helpers import (
    detect_team_bench_scoring_boundary as detect_team_bench_scoring_boundary,
)
from nbatools.commands._parse_helpers import (
    detect_team_rolling_stretch_boundary as detect_team_rolling_stretch_boundary,
)
from nbatools.commands._parse_helpers import (
    detect_wins_losses as detect_wins_losses,
)
from nbatools.commands._parse_helpers import (
    extract_last_n as extract_last_n,
)
from nbatools.commands._parse_helpers import (
    extract_last_n_seasons as extract_last_n_seasons,
)
from nbatools.commands._parse_helpers import (
    extract_min_value as extract_min_value,
)
from nbatools.commands._parse_helpers import (
    extract_opponent_points_allowed_conditions as extract_opponent_points_allowed_conditions,
)
from nbatools.commands._parse_helpers import (
    extract_position_filter as extract_position_filter,
)
from nbatools.commands._parse_helpers import (
    extract_relative_season as extract_relative_season,
)
from nbatools.commands._parse_helpers import (
    extract_season as extract_season,
)
from nbatools.commands._parse_helpers import (
    extract_season_range as extract_season_range,
)
from nbatools.commands._parse_helpers import (
    extract_since_season as extract_since_season,
)
from nbatools.commands._parse_helpers import (
    extract_streak_request as extract_streak_request,
)
from nbatools.commands._parse_helpers import (
    extract_team_streak_request as extract_team_streak_request,
)
from nbatools.commands._parse_helpers import (
    extract_threshold_conditions as extract_threshold_conditions,
)
from nbatools.commands._parse_helpers import (
    extract_top_n as extract_top_n,
)
from nbatools.commands._parse_helpers import (
    merge_opponent_points_allowed_conditions as merge_opponent_points_allowed_conditions,
)
from nbatools.commands._parse_helpers import (
    wants_count as wants_count,
)
from nbatools.commands._parse_helpers import (
    wants_finder as wants_finder,
)
from nbatools.commands._parse_helpers import (
    wants_leaderboard as wants_leaderboard,
)
from nbatools.commands._parse_helpers import (
    wants_recent_form as wants_recent_form,
)
from nbatools.commands._parse_helpers import (
    wants_split_summary as wants_split_summary,
)
from nbatools.commands._parse_helpers import (
    wants_summary as wants_summary,
)
from nbatools.commands._parse_helpers import (
    wants_team_leaderboard as wants_team_leaderboard,
)
from nbatools.commands._playoff_record_route_utils import (
    detect_by_decade_intent,
    detect_by_round_intent,
    detect_playoff_appearance_intent,
    detect_playoff_history_intent,
    detect_playoff_round_filter,
    detect_record_intent,
    extract_decade_season_range,
    try_playoff_record_route,
    try_record_leaderboard_route,
)
from nbatools.commands.entity_resolution import format_ambiguity_message, resolve_stat
from nbatools.commands.freshness import compute_current_through
from nbatools.commands.query_boolean_parser import expression_contains_boolean_ops  # noqa: F401

_UNSUPPORTED_BOUNDARY_PHRASES = (
    "cooled off",
    "double-double over",
    "averaged a double-double",
    "paint points",
    "biggest triple-double",
    "drop-off",
    "co-star",
    "star teammate",
    "leading scorer",
    "catch-and-shoot",
    "catch and shoot",
    "draw fouls",
    "draws fouls",
    "drawing fouls",
    "drawn fouls",
    "fouls drawn",
    "transition scorer",
    "isolation defender",
    "shot creator",
    "two-way",
    "all-around",
    "all around",
    "rebounding battle",
    "trailing after 3 quarters",
    "both play",
    "leads the team in scoring",
    "offensive rating when",
    "offensive rating without",
    "10+ assists and 0 turnovers",
    "attempts per game",
    "road by 20",
    "road team won by 20",
    "above .600",
)


def _unsupported_boundary_note(q: str, route: str, route_kwargs: dict) -> str | None:
    if any(phrase in q for phrase in _UNSUPPORTED_BOUNDARY_PHRASES) or re.search(
        r"\bmin(?:imum)?\s+\d+\s+attempts\b", q
    ):
        return (
            "unsupported_boundary: this phrase is outside the shipped support boundary; "
            "returned results, when present, are broad fallbacks and not execution-backed "
            "for the unsupported concept"
        )

    if route == "season_team_leaders":
        stat = route_kwargs.get("stat")
        rolling_window = route_kwargs.get("last_n") is not None or bool(
            route_kwargs.get("start_date") or route_kwargs.get("end_date")
        )
        if rolling_window and stat in {"off_rating", "def_rating", "net_rating", "pace"}:
            return (
                "unsupported_boundary: rolling/date-window team advanced rating leaderboards "
                "are outside the shipped support boundary"
            )

    return None


def _single_team_advanced_stat_summary_boundary(parsed: dict) -> bool:
    """Detect single-team season-advanced stat lookups with no scalar contract."""
    if parsed.get("stat") not in TEAM_SEASON_ADVANCED_STATS:
        return False
    if not parsed.get("team") or parsed.get("team_a") or parsed.get("team_b"):
        return False
    if parsed.get("player") or parsed.get("player_a") or parsed.get("player_b"):
        return False
    if parsed.get("lineup_members") or parsed.get("presence_state") is not None:
        return False
    if parsed.get("record_intent") or parsed.get("finder_intent") or parsed.get("count_intent"):
        return False
    if parsed.get("min_value") is not None or parsed.get("max_value") is not None:
        return False
    if parsed.get("threshold_conditions"):
        return False
    if (
        parsed.get("split_type")
        or parsed.get("streak_request")
        or parsed.get("team_streak_request")
    ):
        return False
    if parsed.get("window_size") is not None:
        return False
    return True


def _multi_player_availability_boundary(q: str) -> bool:
    """Detect unsupported multi-player availability phrasing."""
    with_player, _ = detect_with_player(q)
    without_player, _ = detect_without_player(q)
    if with_player and without_player and with_player != without_player:
        return True

    if re.search(
        r"\b(?:both\s+play(?:ing)?|play(?:ing)?\s+together|"
        r"(?:(?:are|were|is|was)\s+)?both\s+out)\b",
        q,
    ):
        return True

    with_without = re.search(
        r"\b(?:with|without|w/o)\s+(.+?)(?=\s+(?:record|games?|this|that|last|in|for)\b|$)",
        q,
    )
    if not with_without or " and " not in with_without.group(1):
        return False

    left, right = [part.strip(" .") for part in with_without.group(1).split(" and ", 1)]
    return bool(detect_player(left) and detect_player(right))


def _team_record_availability_intent(
    *,
    record_intent: bool,
    wins_only: bool,
    stat: str | None,
    min_value: int | float | None,
    max_value: int | float | None,
    occurrence_event: dict | None,
) -> bool:
    """Return whether a team availability phrase is asking for a W/L record."""
    if record_intent:
        return True
    return (
        wins_only
        and stat is None
        and min_value is None
        and max_value is None
        and occurrence_event is None
    )


_RECORD_LEADERBOARD_PREFIXES = (
    "best",
    "worst",
    "top",
    "highest",
    "lowest",
    "most",
    "fewest",
    "team",
    "teams",
    "nba",
    "league",
    "home",
    "away",
    "road",
    "playoff",
    "postseason",
)


def _levenshtein_distance_at_most(value: str, target: str, max_distance: int) -> bool:
    if abs(len(value) - len(target)) > max_distance:
        return False

    previous = list(range(len(target) + 1))
    for i, value_char in enumerate(value, start=1):
        current = [i]
        row_min = i
        for j, target_char in enumerate(target, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            replace_cost = previous[j - 1] + (value_char != target_char)
            cost = min(insert_cost, delete_cost, replace_cost)
            current.append(cost)
            row_min = min(row_min, cost)
        if row_min > max_distance:
            return False
        previous = current

    return previous[-1] <= max_distance


def _looks_like_known_stat_typo(token: str) -> bool:
    if len(token) < 4 or token in STAT_ALIASES:
        return False

    stat_words = {
        alias for alias in STAT_ALIASES if alias.isalpha() and len(alias) >= 4 and " " not in alias
    }
    return any(
        sorted(token) == sorted(alias) or _levenshtein_distance_at_most(token, alias, 1)
        for alias in stat_words
    )


def _looks_like_month_typo(token: str) -> bool:
    if len(token) < 3 or token in MONTH_NAME_TO_NUM:
        return False

    month_words = {
        month
        for month in MONTH_NAME_TO_NUM
        if len(month) >= 3 and abs(len(month) - len(token)) <= 1
    }
    return any(
        sorted(token) == sorted(month) or _levenshtein_distance_at_most(token, month, 1)
        for month in month_words
    )


def _unresolved_team_record_boundary(parsed: dict) -> str | None:
    q = parsed["normalized_query"]
    if not parsed.get("record_intent"):
        return None
    if any(
        parsed.get(key) for key in ("team", "team_a", "team_b", "player", "player_a", "player_b")
    ):
        return None
    if parsed.get("occurrence_event"):
        return None

    match = re.match(
        r"^(?:the\s+)?(?P<fragment>[a-z][a-z'.-]*(?:\s+[a-z][a-z'.-]*){0,2})"
        r"\s+(?:home\s+|road\s+|away\s+)?record\b",
        q,
    )
    if not match:
        return None

    fragment = match.group("fragment")
    if fragment.split()[0] in _RECORD_LEADERBOARD_PREFIXES:
        return None
    return fragment


def _unresolved_leaderboard_stat_boundary(parsed: dict) -> str | None:
    q = parsed["normalized_query"]
    if parsed.get("stat") is not None:
        return None
    if not (parsed.get("leaderboard_intent") or parsed.get("team_leaderboard_intent")):
        return None

    for match in re.finditer(r"\b(?:in|for|by)?\s*([a-z][a-z-]{3,})\s+per\s+game\b", q):
        token = match.group(1).replace("-", "")
        if _looks_like_known_stat_typo(token):
            return token
    return None


def _unsupported_date_anchor_boundary(parsed: dict) -> str | None:
    if not (parsed.get("leaderboard_intent") or parsed.get("team_leaderboard_intent")):
        return None

    q = parsed["normalized_query"]
    if re.search(r"\b(?:since|after|post)\s+(?:the\s+)?trade\s+deadline\b", q):
        return "trade_deadline"
    return None


def _unresolved_date_boundary(parsed: dict) -> str | None:
    if parsed.get("start_date") or parsed.get("end_date"):
        return None
    if not (parsed.get("leaderboard_intent") or parsed.get("team_leaderboard_intent")):
        return None

    q = parsed["normalized_query"]
    for match in re.finditer(
        r"\b(?:in|during|since|after|post)\s+(?:the\s+)?([a-z]{3,9})\b",
        q,
    ):
        token = match.group(1)
        if _looks_like_month_typo(token):
            return token
    return None


def _unresolved_player_typo_boundary(parsed: dict) -> str | None:
    if parsed.get("split_type"):
        return None

    q = parsed["normalized_query"]
    if parsed.get("player_a") and parsed.get("player_b"):
        return detect_unresolved_player_typo(q, comparison=True)
    if parsed.get("player") and not parsed.get("player_a") and not parsed.get("player_b"):
        return detect_unresolved_player_typo(q, summary=True)
    return None


def _unresolved_player_stretch_boundary(parsed: dict) -> str | None:
    q = parsed["normalized_query"]
    if parsed.get("window_size") is None or parsed.get("stretch_metric") is None:
        return None
    if any(
        parsed.get(key) for key in ("player", "player_a", "player_b", "team", "team_a", "team_b")
    ):
        return None

    if re.match(r"^(?:who|which|what|best|top|hottest|most|longest)\b", q):
        return None

    match = re.match(
        r"^(?P<fragment>[a-z][a-z'.-]{2,})"
        r"\s+(?:hottest|best|top|longest|most\s+efficient|\d+\s*(?:-\s*|\s+)games?)\b",
        q,
    )
    if match:
        return match.group("fragment")
    return None


def _unsupported_route_kwargs(
    filter_id: str,
    *,
    season: str | None,
    start_season: str | None,
    end_season: str | None,
    start_date: str | None,
    end_date: str | None,
    season_type: str,
    stat: str | None = None,
    limit: int | None = None,
    window_size: int | None = None,
    stretch_metric: str | None = None,
) -> dict:
    route_kwargs = {
        "season": season,
        "start_season": start_season,
        "end_season": end_season,
        "start_date": start_date,
        "end_date": end_date,
        "season_type": season_type,
        "unsupported_filters": [filter_id],
    }
    if stat is not None:
        route_kwargs["stat"] = stat
    if limit is not None:
        route_kwargs["limit"] = limit
    if window_size is not None:
        route_kwargs["window_size"] = window_size
    if stretch_metric is not None:
        route_kwargs["stretch_metric"] = stretch_metric
    return route_kwargs


_AMBIGUOUS_FRAGMENT_PATTERNS = (
    (r"^celtics recently$", "team + recent fragment needs summary, finder, or record intent"),
    (r"^tatum vs knicks$", "player/team matchup fragment needs summary or game-list intent"),
    (r"^jokic triple doubles$", "achievement fragment needs count, list, or leaderboard intent"),
    (r"^best games booker$", "best-games fragment needs a stat or clearer player-game intent"),
    (r"^thunder clutch$", "team + clutch fragment needs record, summary, or game-list intent"),
)


def _stretch_display_mode(q: str, player: str | None) -> str | None:
    """Classify rolling-stretch display intent when the query says so plainly."""
    if not re.search(r"\b(?:stretch(?:es)?|windows?|rolling)\b", q):
        return None
    if player:
        return "named_player"
    if re.search(r"\bwhich\s+players?\b", q):
        return "players"
    if re.search(r"\b(?:best|top|hottest)\b.*\b(?:stretch(?:es)?|windows?)\b", q):
        return "windows"
    return "windows"


def _specific_date_top_scorer_intent(q: str, start_date: str | None, end_date: str | None) -> bool:
    """Detect explicit-date top-scorer phrasing that needs game-level rows."""
    if not start_date or not end_date or start_date != end_date:
        return False
    if not has_explicit_calendar_date(q):
        return False
    return bool(
        re.search(
            r"\bwho\s+(?:scored|had)\s+(?:the\s+)?most\s+points\b"
            r"|\bmost\s+points\s+(?:on|in)\b",
            q,
        )
    )


def _wants_top_team_games(q: str) -> bool:
    """Detect team single-game performance intent without catching team seasons."""
    return bool(
        re.search(
            r"\b(?:top|highest|best|biggest)\s+team\s+"
            r"(?:(?:points?|scoring)\s+)?(?:games?|performances?|nights?)\b",
            q,
        )
        or re.search(
            r"\b(?:top|highest|best|biggest)\s+"
            r"(?:(?:points?|scoring)\s+)?team\s+"
            r"(?:games?|performances?|nights?)\b",
            q,
        )
        or re.search(r"\bmost\s+points\s+by\s+a\s+team\s+in\s+a\s+game\b", q)
    )


def _team_how_did_do_record_intent(q: str) -> bool:
    """Detect narrow team W/L summary phrasing like ``how did the Lakers do``."""
    return bool(
        re.search(
            r"\bhow\s+did\s+(?:the\s+)?[\w'.-]+(?:\s+[\w'.-]+){0,4}\s+do\b",
            q,
        )
    )


def _explicit_washington_reference(raw_query: str, normalized_query: str) -> bool:
    if re.search(r"\b(?:washington|wizards|wiz)\b", normalized_query):
        return True
    return bool(re.search(r"\bWAS\b", raw_query))


def _was_team_alias_is_auxiliary(raw_query: str, normalized_query: str) -> bool:
    if _explicit_washington_reference(raw_query, normalized_query):
        return False
    return bool(re.search(r"^\s*(?:what|how|who|which|when|where)\s+was\b", normalized_query))


def _ambiguous_fragment_note(q: str) -> str | None:
    for pattern, reason in _AMBIGUOUS_FRAGMENT_PATTERNS:
        if re.search(pattern, q):
            return f"ambiguous: {reason}"
    return None


def _placeholder_template_note(q: str) -> str | None:
    if re.search(r"_{2,}", q):
        return (
            "unsupported_boundary: fill-in placeholder templates are documentation examples, "
            "not runnable shipped queries; replace the placeholder with a player, team, or stat"
        )
    return None


__all__ = [
    # Core public API
    "parse_query",
    "run",
    # Rendering / execution re-exports (from _natural_query_execution)
    "render_query_result",
    # Leaderboard helpers (from _leaderboard_utils)
    "detect_player_leaderboard_stat",
    "detect_team_leaderboard_stat",
    "wants_ascending_leaderboard",
    # Occurrence helpers (from _occurrence_route_utils)
    "extract_occurrence_event",
    "extract_compound_occurrence_event",
    "wants_occurrence_leaderboard",
    # Playoff / record helpers (from _playoff_record_route_utils)
    "detect_by_decade_intent",
    "detect_by_round_intent",
    "detect_playoff_appearance_intent",
    "detect_playoff_history_intent",
    "detect_playoff_round_filter",
    "detect_record_intent",
    "extract_decade_season_range",
    # Parsing helpers (from _parse_helpers)
    "STREAK_SPECIAL_PATTERNS",
    "TEAM_STREAK_SPECIAL_PATTERNS",
    "default_season_for_context",
    "detect_career_intent",
    "detect_distinct_player_count",
    "detect_distinct_team_count",
    "detect_home_away",
    "detect_back_to_back",
    "detect_rest_days",
    "detect_one_possession",
    "detect_nationally_televised",
    "detect_lineup_query",
    "detect_on_off",
    "detect_role",
    "detect_stretch_query",
    "detect_team_rolling_stretch_boundary",
    "detect_opponent_conference",
    "detect_opponent_conference_boundary",
    "detect_opponent_conference_geography_boundary",
    "detect_opponent_division",
    "detect_opponent_division_boundary",
    "detect_opponent_quality",
    "detect_quarter",
    "detect_half",
    "detect_season_high_intent",
    "detect_season_type",
    "detect_split_type",
    "detect_stat",
    "detect_wins_losses",
    "extract_last_n",
    "extract_last_n_seasons",
    "extract_min_value",
    "extract_opponent_points_allowed_conditions",
    "extract_position_filter",
    "extract_relative_season",
    "extract_season",
    "extract_season_range",
    "extract_since_season",
    "extract_streak_request",
    "extract_team_streak_request",
    "extract_threshold_conditions",
    "merge_opponent_points_allowed_conditions",
    "extract_top_n",
    "wants_count",
    "wants_finder",
    "wants_leaderboard",
    "wants_recent_form",
    "wants_split_summary",
    "wants_summary",
    "wants_team_leaderboard",
    # Text normalisation (from _constants)
    "normalize_text",
    "detect_player",
]


def _build_parse_state(query: str) -> dict:
    q = normalize_text(query)
    season_type = detect_season_type(q)

    # -- Historical span detection (must run before single-season extraction) --
    start_season, end_season = extract_season_range(q)
    career_intent = False

    if not (start_season and end_season):
        decade_start, decade_end = extract_decade_season_range(q)
        if decade_start and decade_end:
            start_season, end_season = decade_start, decade_end

    if not (start_season and end_season):
        # Try "since SEASON/YEAR"
        since_season = extract_since_season(q)
        if since_season:
            from nbatools.commands._seasons import default_end_season

            start_season = since_season
            end_season = default_end_season(season_type)

    if not (start_season and end_season):
        # Try "last N seasons"
        last_n_seasons = extract_last_n_seasons(q)
        if last_n_seasons:
            from nbatools.commands._seasons import resolve_last_n_seasons

            start_season, end_season = resolve_last_n_seasons(last_n_seasons, season_type)

    if not (start_season and end_season):
        # Try "career" / "all-time"
        if detect_career_intent(q):
            from nbatools.commands._seasons import resolve_career

            career_intent = True
            start_season, end_season = resolve_career(season_type)

    explicit_relative_season = False
    season = None
    if not (start_season and end_season):
        season = extract_season(q)
        if season is None:
            season = extract_relative_season(q, season_type)
            explicit_relative_season = season is not None

    stat = detect_stat(q)
    last_n = extract_last_n(q)
    top_n = extract_top_n(q)
    split_type = detect_split_type(q)
    leaderboard_intent = wants_leaderboard(q)
    team_leaderboard_intent = wants_team_leaderboard(q)
    stretch_request = detect_stretch_query(q)
    window_size = stretch_request["window_size"] if stretch_request else None
    stretch_metric = stretch_request["stretch_metric"] if stretch_request else None
    team_rolling_stretch_boundary = detect_team_rolling_stretch_boundary(q)
    rookie_leaderboard_boundary = detect_rookie_leaderboard_boundary(q)
    role_leaderboard_boundary = detect_role_leaderboard_boundary(q)
    team_bench_scoring_boundary = detect_team_bench_scoring_boundary(q)
    award_query_boundary = detect_award_query_boundary(q)
    championship_count_boundary = detect_championship_count_boundary(q)
    schedule_lookup_boundary = detect_schedule_lookup_boundary(q)
    opponent_conference = detect_opponent_conference(q)
    opponent_conference_boundary = opponent_conference is not None
    opponent_conference_geography_boundary = detect_opponent_conference_geography_boundary(q)
    opponent_division = detect_opponent_division(q)
    opponent_division_boundary = detect_opponent_division_boundary(q)
    if opponent_division_boundary:
        opponent_conference = None
        opponent_conference_boundary = False
    if (
        stretch_request
        and top_n == window_size
        and window_size is not None
        and re.search(rf"\b(?:best|top|worst)\s+{window_size}\s*(?:-\s*|\s+)games?\b", q)
    ):
        top_n = None

    # Fallback: if no STAT_ALIASES hit but leaderboard intent is present,
    # promote a leaderboard-only alias (e.g. "scoring", "scorers") into the
    # `stat` slot so question/search/shorthand forms produce identical states.
    if stat is None and leaderboard_intent:
        stat = detect_player_leaderboard_stat(q)
    if stat is None and team_leaderboard_intent:
        stat = detect_team_leaderboard_stat(q)
    occurrence_event = extract_occurrence_event(q)
    compound_occurrence_conditions = extract_compound_occurrence_event(q)
    occurrence_leaderboard_intent = wants_occurrence_leaderboard(q)
    position_filter = extract_position_filter(q)
    head_to_head = detect_head_to_head(q)
    streak_request = extract_streak_request(q)
    team_streak_request = extract_team_streak_request(q)
    season_high_intent = detect_season_high_intent(q)
    top_team_game_intent = _wants_top_team_games(q)
    distinct_player_count = detect_distinct_player_count(q)
    distinct_team_count = detect_distinct_team_count(q)

    # -- Playoff history / era-bucket intent detection --
    by_decade_intent = detect_by_decade_intent(q)
    playoff_appearance_intent = detect_playoff_appearance_intent(q)
    playoff_history_intent = detect_playoff_history_intent(q)
    playoff_round_filter = detect_playoff_round_filter(q)
    by_round_intent = detect_by_round_intent(q)
    if playoff_round_filter and season_type != "Playoffs":
        from nbatools.commands._seasons import default_end_season

        regular_default_end = default_end_season(season_type)
        season_type = "Playoffs"
        if start_season and end_season == regular_default_end:
            end_season = default_end_season("Playoffs")
    historical_route_intent = bool(
        by_decade_intent
        or playoff_appearance_intent
        or playoff_history_intent
        or playoff_round_filter
        or by_round_intent
    )

    threshold_conditions = merge_opponent_points_allowed_conditions(
        extract_threshold_conditions(q),
        extract_opponent_points_allowed_conditions(q),
    )

    extra_conditions = []
    stat_context_only = False
    if threshold_conditions:
        primary = threshold_conditions[0]
        stat = primary["stat"]
        min_value = primary["min_value"]
        max_value = primary["max_value"]
        extra_conditions = threshold_conditions[1:]
    else:
        if stat is None and last_n is not None:
            stat_context = detect_player_summary_stat_context(q)
            if stat_context is not None:
                stat = stat_context
                stat_context_only = True
        min_value = extract_min_value(q, stat)
        max_value = None

    # Stat resolution confidence: "confident" when a recognized alias was
    # matched, "none" when no stat was detected.
    stat_resolution = resolve_stat(stat)
    stat_resolution_confidence = stat_resolution.confidence

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
            or window_size is not None
        ) and not historical_route_intent:
            season = default_season_for_context(season_type)

    player_a, player_b = extract_player_comparison(q)
    bare_player_vs_player = False
    if player_a and player_b:
        bare_a, bare_b = detect_bare_player_vs_player_query(q)
        bare_player_vs_player = bool(bare_a == player_a and bare_b == player_b)
    team_a, team_b = (None, None)

    if not (player_a and player_b):
        team_a, team_b = extract_team_comparison(q)
        if not (team_a and team_b):
            team_a, team_b = extract_adjacent_playoff_team_comparison(q)

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
    opponent_quality = None
    opponent_player = None
    q_without_opponent = q
    team = None
    on_off_request = detect_on_off(q)
    lineup_request = detect_lineup_query(q)
    lineup_members = on_off_request["lineup_members"] if on_off_request else []
    presence_state = on_off_request["presence_state"] if on_off_request else None
    if not lineup_members and lineup_request:
        lineup_members = lineup_request["lineup_members"]
    unit_size = lineup_request["unit_size"] if lineup_request else None
    minute_minimum = lineup_request["minute_minimum"] if lineup_request else None
    lineup_query_mode = lineup_request["route"] if lineup_request else None
    with_player = None
    without_player = None
    unresolved_with_player = None
    unresolved_without_player = None

    team_resolution_confidence = "none"

    if not (team_a and team_b):
        opponent, q_without_opponent = detect_opponent(q)

        # If no team opponent found via "vs", check if "vs" targets a player
        if opponent is None and not (player_a and player_b):
            opp_player, q_cleaned = detect_opponent_player(q)
            if opp_player:
                opponent_player = opp_player
                q_without_opponent = q_cleaned

        if opponent is None and opponent_player is None:
            opponent_quality = detect_opponent_quality(q)

        if not (player_a and player_b):
            team_result = detect_team_resolved(q_without_opponent)
            if team_result.is_confident:
                team = team_result.resolved
                team_resolution_confidence = "confident"
            else:
                team_resolution_confidence = team_result.confidence

    # Detect game-absence only when the query is not an on/off-court request.
    if on_off_request is None:
        with_player, q_without_presence = detect_with_player(q)
        without_player, q_without_absence = detect_without_player(q)
        unresolved_with_player = (
            detect_unresolved_availability_player(q, mode="with") if with_player is None else None
        )
        unresolved_without_player = (
            detect_unresolved_availability_player(q, mode="without")
            if without_player is None
            else None
        )
        if with_player and (not player or player.upper() == with_player.upper()):
            player_without_presence = detect_player_resolved(q_without_presence)
            if player_without_presence.is_confident:
                player = player_without_presence.resolved
        if without_player and (not player or player.upper() == without_player.upper()):
            player_without_absence = detect_player_resolved(q_without_absence)
            if player_without_absence.is_confident:
                player = player_without_absence.resolved

    wins_only, losses_only = detect_wins_losses(q)

    # If without_player is the same as the detected player, clear player so the
    # query routes to the team path (e.g., "Lakers record without LeBron")
    if without_player and player and without_player.upper() == player.upper():
        player = None

    if (
        team
        and _team_record_availability_intent(
            record_intent=record_intent,
            wins_only=wins_only,
            stat=stat,
            min_value=min_value,
            max_value=max_value,
            occurrence_event=occurrence_event,
        )
        and with_player
        and player
        and with_player.upper() == player.upper()
    ):
        player = None

    if team == "MIN" and re.search(r"\bmin(?:imum)?\s+\d+", q):
        team = None
        team_resolution_confidence = "none"
    if team == "WAS" and (re.search(r"\bwas\s+out\b", q) or _was_team_alias_is_auxiliary(query, q)):
        team = None
        team_resolution_confidence = "none"

    role = detect_role(q) if any([player, player_a, player_b]) else None

    home_only, away_only = detect_home_away(q)
    clutch = detect_clutch(q)
    back_to_back = detect_back_to_back(q)
    rest_days = detect_rest_days(q)
    one_possession = detect_one_possession(q)
    nationally_televised = detect_nationally_televised(q)
    quarter = detect_quarter(q)
    half = detect_half(q)

    if season is None and start_season is None and end_season is None:
        if (
            any(
                [
                    player,
                    team,
                    opponent,
                    player_a,
                    player_b,
                    team_a,
                    team_b,
                ]
            )
            and not historical_route_intent
        ):
            season = default_season_for_context(season_type)

    # Anchor rolling date windows to the data end date when data is stale.
    # Without this, a 14-day window ("last couple weeks") computed from
    # today can miss all data when the dataset hasn't been refreshed.
    anchor_date = None
    if season:
        ct = compute_current_through(season, season_type or "Regular Season")
        if ct is not None:
            ct_ts = pd.Timestamp(ct)
            if ct_ts < CURRENT_QUERY_DATE:
                anchor_date = ct_ts

    start_date, end_date = extract_date_range(q, season, anchor_date=anchor_date)
    fuzzy_date_window = bool((start_date or end_date) and uses_fuzzy_date_term(q))
    stretch_display_mode = _stretch_display_mode(q, player)

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
        streak_default_window = True
    else:
        streak_default_window = False

    return {
        "normalized_query": q,
        "season": season,
        "start_season": start_season,
        "end_season": end_season,
        "explicit_relative_season": explicit_relative_season,
        "start_date": start_date,
        "end_date": end_date,
        "season_type": season_type,
        "stat": stat,
        "player": player,
        "player_a": player_a,
        "player_b": player_b,
        "bare_player_vs_player": bare_player_vs_player,
        "team": team,
        "team_a": team_a,
        "team_b": team_b,
        "opponent": opponent,
        "opponent_quality": opponent_quality,
        "lineup_members": lineup_members,
        "presence_state": presence_state,
        "unit_size": unit_size,
        "minute_minimum": minute_minimum,
        "lineup_query_mode": lineup_query_mode,
        "window_size": window_size,
        "stretch_metric": stretch_metric,
        "stretch_display_mode": stretch_display_mode,
        "team_rolling_stretch_boundary": team_rolling_stretch_boundary,
        "rookie_leaderboard_boundary": rookie_leaderboard_boundary,
        "role_leaderboard_boundary": role_leaderboard_boundary,
        "team_bench_scoring_boundary": team_bench_scoring_boundary,
        "award_query_boundary": award_query_boundary,
        "championship_count_boundary": championship_count_boundary,
        "schedule_lookup_boundary": schedule_lookup_boundary,
        "fuzzy_date_window": fuzzy_date_window,
        "opponent_conference": opponent_conference,
        "opponent_conference_boundary": opponent_conference_boundary,
        "opponent_conference_geography_boundary": opponent_conference_geography_boundary,
        "opponent_division": opponent_division,
        "opponent_division_boundary": opponent_division_boundary,
        "min_value": min_value,
        "max_value": max_value,
        "last_n": last_n,
        "top_n": top_n,
        "split_type": split_type,
        "home_only": home_only,
        "away_only": away_only,
        "wins_only": wins_only,
        "losses_only": losses_only,
        "clutch": clutch,
        "back_to_back": back_to_back,
        "rest_days": rest_days,
        "one_possession": one_possession,
        "nationally_televised": nationally_televised,
        "role": role,
        "quarter": quarter,
        "half": half,
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
        "streak_default_window": streak_default_window,
        "season_high_intent": season_high_intent,
        "top_team_game_intent": top_team_game_intent,
        "distinct_player_count": distinct_player_count,
        "distinct_team_count": distinct_team_count,
        "opponent_player": opponent_player,
        "with_player": with_player,
        "without_player": without_player,
        "unresolved_with_player": unresolved_with_player,
        "unresolved_without_player": unresolved_without_player,
        "entity_ambiguity": entity_ambiguity,
        "team_resolution_confidence": team_resolution_confidence,
        "stat_resolution_confidence": stat_resolution_confidence,
        "stat_context_only": stat_context_only,
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


def _conditions_for_route(parsed: dict, route: str, route_kwargs: dict) -> list[dict]:
    """Return canonical condition-list filters consumed by the selected route."""
    route_conditions = normalize_stat_conditions(route_kwargs.get("conditions"))
    if route_conditions:
        return route_conditions

    if route in {"player_game_finder", "game_finder"}:
        threshold_conditions = normalize_stat_conditions(parsed.get("threshold_conditions"))
        if len(threshold_conditions) >= 2:
            return threshold_conditions

        compound_conditions = normalize_stat_conditions(
            parsed.get("compound_occurrence_conditions")
        )
        if len(compound_conditions) >= 2:
            return compound_conditions

    return []


def _apply_route_conditions(parsed: dict, route: str, route_kwargs: dict) -> None:
    """Attach compound conditions to routes and clear duplicate post-filters."""
    conditions = _conditions_for_route(parsed, route, route_kwargs)
    if not conditions:
        return

    route_kwargs["conditions"] = conditions
    parsed["conditions"] = conditions

    if not parsed.get("threshold_conditions"):
        parsed["threshold_conditions"] = conditions

    if parsed.get("extra_conditions") and stat_conditions_cover(
        conditions,
        parsed.get("extra_conditions"),
    ):
        parsed["extra_conditions"] = []

    if route not in {"player_game_finder", "game_finder"}:
        return

    primary = conditions[0]
    route_kwargs["stat"] = primary["stat"]
    route_kwargs["min_value"] = primary.get("min_value")
    route_kwargs["max_value"] = primary.get("max_value")
    parsed["stat"] = primary["stat"]
    parsed["min_value"] = primary.get("min_value")
    parsed["max_value"] = primary.get("max_value")


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
    bare_player_vs_player = parsed.get("bare_player_vs_player", False)
    team = parsed["team"]
    team_a = parsed["team_a"]
    team_b = parsed["team_b"]
    opponent = parsed["opponent"]
    opponent_quality = parsed.get("opponent_quality")
    min_value = parsed["min_value"]
    max_value = parsed["max_value"]
    last_n = parsed["last_n"]
    top_n = parsed.get("top_n")
    split_type = parsed["split_type"]
    home_only = parsed["home_only"]
    away_only = parsed["away_only"]
    wins_only = parsed["wins_only"]
    losses_only = parsed["losses_only"]
    clutch = parsed.get("clutch", False)
    back_to_back = parsed.get("back_to_back", False)
    rest_days = parsed.get("rest_days")
    one_possession = parsed.get("one_possession", False)
    nationally_televised = parsed.get("nationally_televised", False)
    role = parsed.get("role")
    quarter = parsed.get("quarter")
    half = parsed.get("half")
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
    season_high_intent = parsed.get("season_high_intent", False)
    top_team_game_intent = parsed.get("top_team_game_intent", False)
    distinct_player_count = parsed.get("distinct_player_count", False)
    opponent_player = parsed.get("opponent_player")
    with_player = parsed.get("with_player")
    without_player = parsed.get("without_player")
    unresolved_with_player = parsed.get("unresolved_with_player")
    unresolved_without_player = parsed.get("unresolved_without_player")
    lineup_members = parsed.get("lineup_members") or []
    presence_state = parsed.get("presence_state")
    lineup_query_mode = parsed.get("lineup_query_mode")
    window_size = parsed.get("window_size")
    stretch_metric = parsed.get("stretch_metric")
    stretch_display_mode = parsed.get("stretch_display_mode")
    team_rolling_stretch_boundary = parsed.get("team_rolling_stretch_boundary", False)
    rookie_leaderboard_boundary = parsed.get("rookie_leaderboard_boundary", False)
    role_leaderboard_boundary = parsed.get("role_leaderboard_boundary", False)
    team_bench_scoring_boundary = parsed.get("team_bench_scoring_boundary", False)
    award_query_boundary = parsed.get("award_query_boundary", False)
    championship_count_boundary = parsed.get("championship_count_boundary", False)
    schedule_lookup_boundary = parsed.get("schedule_lookup_boundary", False)
    opponent_conference = parsed.get("opponent_conference")
    opponent_conference_boundary = parsed.get("opponent_conference_boundary", False)
    opponent_conference_geography_boundary = parsed.get(
        "opponent_conference_geography_boundary", False
    )
    opponent_division = parsed.get("opponent_division")
    opponent_division_boundary = parsed.get("opponent_division_boundary", False)
    supported_opponent_division_record_scope = (
        bool(opponent_division)
        and season_type == "Regular Season"
        and not any(
            [
                with_player,
                without_player,
                unresolved_with_player,
                unresolved_without_player,
            ]
        )
    )

    notes: list[str] = []
    route = None
    route_kwargs = None

    # "<team> when <player> <condition>" ("knicks when brunson scores 30")
    # is a record-shaped ask even without the word "record" — answer with
    # the summary (record + averages) like the triple-double phrasing
    # does, not with a game list.
    if (
        team
        and player
        and not summary_intent
        and re.search(r"\bwhen\b", q)
        and (min_value is not None or occurrence_event)
    ):
        summary_intent = True
        parsed["summary_intent"] = True

    # Playoff season honesty: never silently substitute the previous
    # completed playoffs for an explicit current-season ask, and say so
    # when an unanchored playoff ask falls back to the default.
    if (
        season_type == "Playoffs"
        and season is not None
        and season == default_season_for_context("Playoffs")
        and extract_season(q) is None
        and not parsed.get("explicit_relative_season")
    ):
        if re.search(r"\bthis\s+(?:year|season)\b|\bcurrent\s+season\b", q):
            season = default_season_for_context("Regular Season")
            parsed["season"] = season
            notes.append(
                f"current-season playoffs requested: showing the {season} "
                f"playoffs; an empty result means no {season} playoff data is loaded"
            )
        else:
            notes.append(
                f"no season specified: defaulted to the {season} playoffs, "
                f"the most recent completed playoffs in the data"
            )

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
    special_event = (
        occurrence_event.get("special_event")
        if isinstance(occurrence_event, dict) and occurrence_event.get("special_event") is not None
        else None
    )
    team_record_availability_intent = _team_record_availability_intent(
        record_intent=record_intent,
        wins_only=wins_only,
        stat=stat,
        min_value=min_value,
        max_value=max_value,
        occurrence_event=occurrence_event,
    )

    # -- Entity ambiguity: short-circuit if we can't resolve a required entity --
    entity_ambiguity = parsed.get("entity_ambiguity")
    if (
        entity_ambiguity
        and not player
        and not player_a
        and not player_b
        and not team
        and not lineup_query_mode
    ):
        out = dict(parsed)
        out["route"] = None
        out["route_kwargs"] = {}
        out["intent"] = "unsupported"
        msg = format_ambiguity_message(
            entity_ambiguity.get("input", ""),
            entity_ambiguity.get("candidates", []),
            entity_ambiguity.get("type", "player"),
        )
        out["notes"] = [msg]
        out["confidence"] = compute_parse_confidence(out)
        out["alternates"] = generate_alternates(out)
        return out

    if ambiguous_note := _ambiguous_fragment_note(q):
        out = dict(parsed)
        out["route"] = None
        out["route_kwargs"] = {}
        out["intent"] = "unsupported"
        out["entity_ambiguity"] = {
            "type": "intent",
            "input": q,
            "candidates": [],
            "source": "ambiguous_fragment",
        }
        out["notes"] = [ambiguous_note]
        out["confidence"] = compute_parse_confidence(out)
        out["alternates"] = generate_alternates(out)
        return out

    if placeholder_note := _placeholder_template_note(q):
        out = dict(parsed)
        out["route"] = None
        out["route_kwargs"] = {}
        out["intent"] = "unsupported"
        out["entity_ambiguity"] = {
            "type": "intent",
            "input": q,
            "candidates": [],
            "source": "placeholder_template",
        }
        out["notes"] = [placeholder_note]
        out["confidence"] = compute_parse_confidence(out)
        out["alternates"] = generate_alternates(out)
        return out

    if award_query_boundary:
        out = dict(parsed)
        out["route"] = None
        out["route_kwargs"] = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "unsupported_filters": ["award_query"],
        }
        out["intent"] = "unsupported"
        out["notes"] = [
            "unsupported_boundary: NBA awards and award winners are not supported "
            "by the current stats query contract"
        ]
        out["confidence"] = compute_parse_confidence(out)
        out["alternates"] = generate_alternates(out)
        return out

    if championship_count_boundary:
        out = dict(parsed)
        out["route"] = None
        out["route_kwargs"] = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "unsupported_filters": ["championship_count"],
        }
        out["intent"] = "unsupported"
        out["notes"] = [
            "unsupported_boundary: championship, ring, and title counts are not "
            "in the game-stats data; the engine answers game-level stat questions"
        ]
        out["confidence"] = compute_parse_confidence(out)
        out["alternates"] = generate_alternates(out)
        return out

    if schedule_lookup_boundary:
        out = dict(parsed)
        out["route"] = None
        out["route_kwargs"] = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "unsupported_filters": ["schedule_lookup"],
        }
        out["intent"] = "unsupported"
        out["notes"] = [
            "unsupported_boundary: future schedule lookups are not supported; "
            "the engine answers questions about games already played"
        ]
        out["confidence"] = compute_parse_confidence(out)
        out["alternates"] = generate_alternates(out)
        return out

    if unresolved_team_fragment := _unresolved_team_record_boundary(parsed):
        route = "team_record_leaderboard"
        notes.append(
            "unsupported_boundary: unresolved team record fragment was not "
            "broadened to a team record leaderboard"
        )
        route_kwargs = _unsupported_route_kwargs(
            "unresolved_team",
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
            stat="win_pct",
            limit=top_n or 10,
        )
        route_kwargs["unresolved_team_fragment"] = unresolved_team_fragment
    elif unresolved_stat_fragment := _unresolved_leaderboard_stat_boundary(parsed):
        route = "season_team_leaders" if team_leaderboard_intent else "season_leaders"
        notes.append(
            "unsupported_boundary: unresolved leaderboard stat fragment was not "
            "broadened to the default points leaderboard"
        )
        route_kwargs = _unsupported_route_kwargs(
            "unresolved_stat",
            season=season or default_season_for_context(season_type),
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
            limit=top_n or 10,
        )
        route_kwargs["unresolved_stat_fragment"] = unresolved_stat_fragment
    elif unsupported_date_anchor := _unsupported_date_anchor_boundary(parsed):
        route = "season_team_leaders" if team_leaderboard_intent else "season_leaders"
        notes.append(
            "unsupported_boundary: unsupported date anchor was not broadened to "
            "a full-scope leaderboard"
        )
        route_kwargs = _unsupported_route_kwargs(
            "unsupported_date_anchor",
            season=season or default_season_for_context(season_type),
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
            stat=stat,
            limit=top_n or 10,
        )
        route_kwargs["unsupported_date_anchor"] = unsupported_date_anchor
    elif unresolved_date_fragment := _unresolved_date_boundary(parsed):
        route = "season_team_leaders" if team_leaderboard_intent else "season_leaders"
        notes.append(
            "unsupported_boundary: unresolved date fragment was not broadened to "
            "a full-scope leaderboard"
        )
        route_kwargs = _unsupported_route_kwargs(
            "unresolved_date",
            season=season or default_season_for_context(season_type),
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
            stat=stat,
            limit=top_n or 10,
        )
        route_kwargs["unresolved_date_fragment"] = unresolved_date_fragment
    elif unresolved_player_fragment := _unresolved_player_stretch_boundary(parsed):
        route = "player_stretch_leaderboard"
        notes.append(
            "unsupported_boundary: unresolved player rolling-stretch fragment was "
            "not broadened to a league-wide stretch leaderboard"
        )
        route_kwargs = _unsupported_route_kwargs(
            "unresolved_player",
            season=season or default_season_for_context(season_type),
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
            stat=stat,
            limit=top_n or 10,
            window_size=window_size,
            stretch_metric=stretch_metric,
        )
        route_kwargs["unresolved_player_fragment"] = unresolved_player_fragment
    elif unresolved_player_fragment := _unresolved_player_typo_boundary(parsed):
        if player_a and player_b:
            route = "player_compare"
        else:
            route = "player_game_summary"
        notes.append(
            "unsupported_boundary: unresolved player typo was not corrected to a "
            "confident player identity"
        )
        route_kwargs = _unsupported_route_kwargs(
            "unresolved_player",
            season=season or default_season_for_context(season_type),
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
            stat=stat,
            limit=top_n or 10,
        )
        route_kwargs["unresolved_player_fragment"] = unresolved_player_fragment
    elif (lineup_route := try_lineup_on_off_route(parsed)) is not None:
        route, route_kwargs = lineup_route
    elif (
        team_rolling_stretch_boundary
        and window_size is not None
        and stretch_metric is not None
        and not player
        and not player_a
        and not player_b
    ):
        route = "player_stretch_leaderboard"
        notes.append(
            "unsupported_boundary: team rolling-stretch leaderboards are not "
            "supported with current routes"
        )
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "player": None,
            "team": team,
            "opponent": opponent,
            "opponent_player": opponent_player,
            "without_player": without_player,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "last_n": last_n,
            "window_size": window_size,
            "stretch_metric": stretch_metric,
            "dedupe_players": False,
            "limit": top_n or 10,
            "unsupported_filters": ["team_rolling_stretch"],
        }
    elif (
        window_size is not None
        and stretch_metric is not None
        and not player_a
        and not player_b
        and not team_a
        and not team_b
        and not (team and player is None)
    ):
        route = "player_stretch_leaderboard"
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
            "opponent_player": opponent_player,
            "without_player": without_player,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "last_n": last_n,
            "window_size": window_size,
            "stretch_metric": stretch_metric,
            "dedupe_players": stretch_display_mode == "players",
            "limit": top_n or 10,
        }

    # ---------------------------------------------------------------------------
    # Season-high / single-game-best routing
    # ---------------------------------------------------------------------------
    elif (
        season_high_intent and top_team_game_intent and not player and not player_a and not player_b
    ):
        route = "top_team_games"
        route_kwargs = {
            "season": season or default_season_for_context(season_type),
            "stat": stat or "pts",
            "limit": top_n or 10,
            "season_type": season_type,
            "ascending": False,
            "start_date": start_date,
            "end_date": end_date,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "last_n": last_n,
            "opponent": opponent,
        }
        notes.append("default: top team games ranked by " + (stat or "pts"))
    elif season_high_intent and player and not player_a and not player_b:
        # Single player season-high: "Cade Cunningham season high"
        # Route to finder, limit 1, sort by stat descending
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
            "opponent_player": opponent_player,
            "without_player": without_player,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat or "pts",
            "min_value": min_value,
            "max_value": max_value,
            "limit": top_n or 5,
            "sort_by": "stat",
            "ascending": False,
            "last_n": last_n,
        }
        notes.append("season_high: showing top single-game performances")
    elif (
        season_high_intent
        and not player
        and not player_a
        and not player_b
        and not team
        and not team_a
        and not team_b
    ):
        # League-wide season-high: "highest scoring games this season"
        route = "top_player_games"
        route_kwargs = {
            "season": season or default_season_for_context(season_type),
            "stat": stat or "pts",
            "limit": top_n or 10,
            "season_type": season_type,
            "ascending": False,
            "start_date": start_date,
            "end_date": end_date,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "last_n": last_n,
            "opponent": opponent,
        }
        notes.append("season_high: league-wide top single-game performances")
    # ---------------------------------------------------------------------------
    # Distinct player/team count routing
    # ---------------------------------------------------------------------------
    elif distinct_player_count and (occurrence_event or (stat and min_value is not None)):
        # "How many players have had a 40 point game this season?"
        # "How many players scored 40 points this season?"
        route = "player_occurrence_leaders"
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "season_type": season_type,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "occurrence_event": occurrence_event,
            "limit": None,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "start_date": start_date,
            "end_date": end_date,
        }
        notes.append("distinct_count: counting distinct players meeting condition")
    elif (
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
        _fires, _note = streak_default_window(parsed)
        if _fires:
            notes.append(_note)
    # ---------------------------------------------------------------------------
    # Playoff / record / decade routing cluster
    # ---------------------------------------------------------------------------
    elif (ppr := try_playoff_record_route(parsed)) is not None:
        route, route_kwargs = ppr
        if route_kwargs.get("unsupported_filters") == ["single_team_playoff_round_record"]:
            notes.append(
                "unsupported_boundary: single-team playoff round records are not supported "
                "until the route and round-data contract is approved"
            )
    elif (
        opponent_division_boundary
        and record_intent
        and not any([player, player_a, player_b, team_a, team_b])
        and not supported_opponent_division_record_scope
    ):
        notes.append(
            "unsupported_boundary: opponent-division filters are not supported "
            "for this record scope"
        )
        if team:
            route = "team_record"
            route_kwargs = {
                "team": team,
                "season": season,
                "start_season": start_season,
                "end_season": end_season,
                "season_type": season_type,
                "opponent": opponent,
                "without_player": without_player,
                "home_only": home_only,
                "away_only": away_only,
                "wins_only": wins_only,
                "losses_only": losses_only,
                "stat": stat,
                "min_value": min_value,
                "max_value": max_value,
                "start_date": start_date,
                "end_date": end_date,
                "opponent_division": opponent_division,
                "unsupported_filters": ["opponent_division"],
            }
        else:
            route = "team_record_leaderboard"
            route_kwargs = {
                "season": season,
                "start_season": start_season,
                "end_season": end_season,
                "season_type": season_type,
                "stat": "win_pct",
                "opponent": opponent,
                "without_player": without_player,
                "home_only": home_only,
                "away_only": away_only,
                "wins_only": wins_only,
                "losses_only": losses_only,
                "limit": top_n or 10,
                "ascending": False,
                "start_date": start_date,
                "end_date": end_date,
                "opponent_division": opponent_division,
                "unsupported_filters": ["opponent_division"],
            }
    elif (
        team_bench_scoring_boundary
        and team
        and not any([player, player_a, player_b, team_a, team_b])
    ):
        route = "game_finder"
        notes.append(
            "unsupported_boundary: team bench scoring is not supported by the "
            "current team game finder contract"
        )
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "team": team,
            "opponent": opponent,
            "with_player": with_player,
            "without_player": without_player,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat or "pts",
            "min_value": min_value,
            "max_value": max_value,
            "limit": 25,
            "sort_by": "stat",
            "ascending": False,
            "last_n": last_n,
            "unsupported_filters": ["team_bench_scoring"],
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
    elif player_a and player_b and bare_player_vs_player:
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
            "ambiguous_intent": "bare_player_vs_player",
            "clarification_options": [
                {
                    "intent": "player_stat_comparison",
                    "query": f"Compare {player_a} and {player_b} this season",
                },
                {
                    "intent": "player_head_to_head",
                    "query": f"{player_a} head-to-head vs {player_b}",
                },
                {
                    "intent": "player_opponent_games",
                    "query": f"{player_a} stats vs {player_b}",
                },
            ],
        }
        notes.append(
            "ambiguous_query: bare player-vs-player phrasing can mean stat "
            "comparison, head-to-head games, or player-opponent stats; add "
            "comparison, head-to-head, or stats wording"
        )
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
    # ---------------------------------------------------------------------------
    # Record-oriented routing: team-vs-team matchup record
    #
    # Rule: two teams + any W/L-outcome keyword (record, win, lose, record,
    # head-to-head, matchup) → team_matchup_record.
    # Without a record-intent keyword the query is treated as a side-by-side
    # stat comparison → team_compare.
    # The ``record_intent`` flag (set by ``detect_record_intent``) is the
    # canonical gate; do not add duplicate guards here.
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
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
        }
    elif team_a and team_b:
        # Two teams without a record-intent keyword → side-by-side stat comparison.
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
        _fires, _note = streak_default_window(parsed)
        if _fires:
            notes.append(_note)
    elif (
        "top" in q
        and "games" in q
        and player is None
        and team is None
        and team_a is None
        and team_b is None
        and ("scoring" in q or stat is not None)
        and not leaderboard_intent
    ):
        route = "top_player_games"
        route_kwargs = {
            "season": season or default_season_for_context(season_type),
            "stat": stat or "pts",
            "limit": top_n or 10,
            "season_type": season_type,
            "ascending": False,
            "start_date": start_date,
            "end_date": end_date,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "last_n": last_n,
            "opponent": opponent,
        }
        notes.append("default: top games ranked by " + (stat or "pts"))
    elif top_team_game_intent and not player and not player_a and not player_b:
        # Expanded trigger: catches "highest-scoring team games", "best team
        # performances", "biggest team scoring nights" in addition to the
        # literal "top team" / "top ... team games" phrasings.
        route = "top_team_games"
        route_kwargs = {
            "season": season or default_season_for_context(season_type),
            "stat": stat or "pts",
            "limit": top_n or 10,
            "season_type": season_type,
            "ascending": False,
            "start_date": start_date,
            "end_date": end_date,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "last_n": last_n,
            "opponent": opponent,
        }
        notes.append("default: top team games ranked by " + (stat or "pts"))
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
    elif rookie_leaderboard_boundary and not any(
        [player, player_a, player_b, team, team_a, team_b]
    ):
        route = "season_leaders"
        notes.append(
            "unsupported_boundary: rookie leaderboards are not supported until "
            "roster-experience semantics are approved"
        )
        route_kwargs = {
            "season": season or default_season_for_context(season_type),
            "stat": stat or detect_player_leaderboard_stat(q) or "pts",
            "limit": top_n or 10,
            "season_type": season_type,
            "min_games": 1,
            "ascending": wants_ascending_leaderboard(q),
            "start_date": start_date,
            "end_date": end_date,
            "start_season": start_season,
            "end_season": end_season,
            "opponent": opponent,
            "position": position_filter,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "last_n": last_n,
            "unsupported_filters": ["rookie_leaderboard"],
        }
    elif role_leaderboard_boundary and not any([player, player_a, player_b, team, team_a, team_b]):
        route = "season_leaders"
        notes.append(
            "unsupported_boundary: league-wide starter/bench leaderboards are "
            "not supported by the current season leaderboard contract"
        )
        route_kwargs = {
            "season": season or default_season_for_context(season_type),
            "stat": stat or detect_player_leaderboard_stat(q) or "pts",
            "limit": top_n or 10,
            "season_type": season_type,
            "min_games": 1,
            "ascending": wants_ascending_leaderboard(q),
            "start_date": start_date,
            "end_date": end_date,
            "start_season": start_season,
            "end_season": end_season,
            "opponent": opponent,
            "position": position_filter,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "last_n": last_n,
            "unsupported_filters": ["role_leaderboard"],
        }
    elif (
        opponent_conference_geography_boundary
        and team
        and record_intent
        and not any([team_a, team_b])
    ):
        route = "team_record"
        notes.append(
            "unsupported_boundary: east/west coast geography filters are not "
            "supported as opponent-conference record filters"
        )
        route_kwargs = {
            "team": team,
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "season_type": season_type,
            "opponent": opponent,
            "opponent_division": opponent_division,
            "with_player": with_player,
            "without_player": without_player,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "start_date": start_date,
            "end_date": end_date,
            "unsupported_filters": ["opponent_conference"],
        }
    elif opponent_conference_boundary and team and record_intent and not any([team_a, team_b]):
        route = "team_record"
        route_kwargs = {
            "team": team,
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "season_type": season_type,
            "opponent": opponent,
            "opponent_conference": opponent_conference,
            "without_player": without_player,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "start_date": start_date,
            "end_date": end_date,
            "opponent_division": opponent_division,
        }
    elif _single_team_advanced_stat_summary_boundary(parsed):
        route = "game_summary"
        notes.append(
            "unsupported_boundary: single-team advanced-stat summaries are not "
            "supported until a route/result contract is approved"
        )
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "team": team,
            "opponent": opponent,
            "without_player": without_player,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "last_n": last_n,
            "unsupported_filters": ["single_team_advanced_stat_summary"],
        }
    elif (
        _specific_date_top_scorer_intent(q, start_date, end_date)
        and not player
        and not team
        and not player_a
        and not player_b
        and not team_a
        and not team_b
    ):
        route = "top_player_games"
        route_kwargs = {
            "season": season or default_season_for_context(season_type),
            "stat": "pts",
            "limit": top_n or 10,
            "season_type": season_type,
            "ascending": False,
            "start_date": start_date,
            "end_date": end_date,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "last_n": last_n,
            "opponent": opponent,
        }
        notes.append("specific_date_top_scorer: using game-level top performances")
    elif (
        not player
        and not team
        and not player_a
        and not player_b
        and not team_a
        and not team_b
        and not stat
        and not leaderboard_intent
        and not team_leaderboard_intent
        and (opponent_quality or clutch)
    ):
        route = "season_leaders"
        route_kwargs = {
            "season": season or default_season_for_context(season_type),
            "stat": "pts",
            "limit": top_n or 10,
            "season_type": season_type,
            "min_games": 1,
            "ascending": False,
            "start_date": start_date,
            "end_date": end_date,
            "start_season": start_season,
            "end_season": end_season,
            "opponent": opponent,
            "position": position_filter,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "last_n": last_n,
        }
        notes.append(
            "boundary_fragment: context detected without a player, team, or stat; "
            "returning a broad points leaderboard fallback"
        )
    elif (_lb := metric_only_leaderboard_default(parsed))[0]:
        # No subject entity → league-wide leaderboard default (spec §15.2)
        notes.append(_lb[1])
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
        if team_leaderboard_intent:
            leaderboard_stat = detect_team_leaderboard_stat(q) or stat or "pts"

            # Semantic ascending for lower-is-better stats
            if leaderboard_stat in LOWER_IS_BETTER_STATS:
                if re.search(r"\b(best|top|lowest|fewest|least)\b", q):
                    lb_ascending = True
                elif re.search(r"\b(worst|most|highest)\b", q):
                    lb_ascending = False

            # Season-advanced-only team stats blocked in date-window/multi-season
            if (start_date or end_date) and leaderboard_stat in TEAM_SEASON_ONLY_STATS:
                notes.append(
                    f"stat_fallback: {leaderboard_stat} not available with date window, using pts"
                )
                leaderboard_stat = "pts"
            if lb_start_season and lb_end_season and leaderboard_stat in TEAM_SEASON_ONLY_STATS:
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
                "last_n": last_n,
            }
        elif "team" in q or "teams" in q:
            leaderboard_stat = stat or "pts"
            if (start_date or end_date) and leaderboard_stat in TEAM_SEASON_ONLY_STATS:
                notes.append(
                    f"stat_fallback: {leaderboard_stat} not available with date window, using pts"
                )
                leaderboard_stat = "pts"
            if lb_start_season and lb_end_season and leaderboard_stat in TEAM_SEASON_ONLY_STATS:
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
                "last_n": last_n,
            }
        else:
            leaderboard_stat = detect_player_leaderboard_stat(q) or stat or "pts"

            # Semantic ascending for lower-is-better stats
            if leaderboard_stat in LOWER_IS_BETTER_STATS:
                if re.search(r"\b(best|top|lowest|fewest|least)\b", q):
                    lb_ascending = True
                elif re.search(r"\b(worst|most|highest)\b", q):
                    lb_ascending = False

            # Season-advanced-only player stats blocked in multi-season/opponent contexts
            if lb_start_season and lb_end_season and leaderboard_stat in PLAYER_SEASON_ONLY_STATS:
                notes.append(
                    f"stat_fallback: {leaderboard_stat} not available for multi-season, using pts"
                )
                leaderboard_stat = "pts"
            if opponent and leaderboard_stat in PLAYER_SEASON_ONLY_STATS:
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
                "home_only": home_only,
                "away_only": away_only,
                "wins_only": wins_only,
                "losses_only": losses_only,
                "last_n": last_n,
            }
    # ---------------------------------------------------------------------------
    # Team-record player availability routing
    # ---------------------------------------------------------------------------
    elif team and team_record_availability_intent and _multi_player_availability_boundary(q):
        # Multi-player availability is requested but not execution-backed.
        # Preserve the team-record route context, then let execution return an
        # honest unsupported-filter result instead of an unfiltered record.
        route = "team_record"
        notes.append(
            "unsupported_boundary: multi-player availability filters are outside "
            "the current record execution boundary"
        )
        route_kwargs = {
            "team": team,
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "season_type": season_type,
            "opponent": opponent,
            "with_player": with_player,
            "without_player": without_player,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "start_date": start_date,
            "end_date": end_date,
            "unsupported_filters": ["multi_player_availability"],
        }
    elif (
        team
        and team_record_availability_intent
        and (unresolved_with_player or unresolved_without_player)
    ):
        route = "team_record"
        raw_fragment = unresolved_with_player or unresolved_without_player
        notes.append(
            "unsupported_boundary: requested availability player could not be resolved; "
            "no broad team record was returned"
        )
        route_kwargs = {
            "team": team,
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "season_type": season_type,
            "opponent": opponent,
            "with_player": with_player,
            "without_player": without_player,
            "unresolved_availability_player": raw_fragment,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "start_date": start_date,
            "end_date": end_date,
            "unsupported_filters": ["unresolved_player_availability"],
        }
    elif team and team_record_availability_intent and with_player and not without_player:
        route = "team_record"
        route_kwargs = {
            "team": team,
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "season_type": season_type,
            "opponent": opponent,
            "with_player": with_player,
            "without_player": without_player,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "start_date": start_date,
            "end_date": end_date,
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
            "opponent_player": opponent_player,
            "without_player": without_player,
            "special_event": special_event,
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
            "without_player": without_player,
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
        or bool(re.search(r"\brecord\b", q))
        or ("averages" in q)
        or ("average" in q)
        or without_player
        or parsed.get("stat_context_only")
        or player_stat_context_summary_default(parsed)[0]
        or player_timeframe_summary_default(parsed)[0]
    ):
        route = "player_game_summary"
        _fires, _note = player_stat_context_summary_default(parsed)
        if _fires:
            notes.append(_note)
        _fires, _note = player_timeframe_summary_default(parsed)
        if _fires:
            notes.append(_note)
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
            "opponent_player": opponent_player,
            "without_player": without_player,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
            "last_n": last_n,
            "career_intent": career_intent,
            "special_event": special_event,
        }
    # ---------------------------------------------------------------------------
    # Record-oriented routing: single team record
    #
    # Rule: single team + (explicit record intent OR a without-player clause
    # with no stat filter) → team_record.
    # A "without" clause alone (e.g. "Lakers without LeBron record") qualifies
    # only when the query has no stat threshold, so the result is a W/L record
    # rather than a stat finder.
    # ---------------------------------------------------------------------------
    elif (
        team
        and not team_a
        and not team_b
        and (
            record_intent
            or (without_player and stat is None and re.search(r"\b(?:without|w/o)\b", q))
            or (
                _team_how_did_do_record_intent(q)
                and not any(
                    [
                        finder_intent,
                        count_intent,
                        leaderboard_intent,
                        team_leaderboard_intent,
                        occurrence_event,
                        season_high_intent,
                        streak_request,
                        team_streak_request,
                        window_size,
                    ]
                )
                and stat is None
                and min_value is None
                and max_value is None
            )
        )
    ):
        route = "team_record"
        route_kwargs = {
            "team": team,
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "season_type": season_type,
            "opponent": opponent,
            "opponent_division": opponent_division,
            "with_player": with_player,
            "without_player": without_player,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
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
        or bool(re.search(r"\brecord\b", q))
        or ("averages" in q)
        or ("average" in q)
        or without_player
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
            "without_player": without_player,
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
        _fires, _note = player_threshold_finder_default(parsed)
        if _fires:
            notes.append(_note)
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
            "opponent_player": opponent_player,
            "without_player": without_player,
            "special_event": special_event,
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
            "without_player": without_player,
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
        _fires, _note = team_threshold_finder_default(parsed)
        if _fires:
            notes.append(_note)
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

    route_kwargs["back_to_back"] = back_to_back
    route_kwargs["rest_days"] = rest_days
    route_kwargs["one_possession"] = one_possession
    route_kwargs["nationally_televised"] = nationally_televised
    route_kwargs["clutch"] = clutch
    route_kwargs["role"] = role
    route_kwargs["opponent_quality"] = opponent_quality
    route_kwargs["quarter"] = quarter
    route_kwargs["half"] = half
    _apply_route_conditions(parsed, route, route_kwargs)

    out = dict(parsed)
    out["route"] = route
    out["route_kwargs"] = route_kwargs
    if route in {
        "playoff_appearances",
        "playoff_history",
        "playoff_matchup_history",
        "playoff_round_record",
    }:
        out["season_type"] = "Playoffs"
    if route == "season_team_leaders" and route_kwargs.get("stat"):
        out["stat"] = route_kwargs["stat"]
    out["intent"] = route_to_intent(route, count_intent=count_intent)

    if clutch:
        notes.append(
            "clutch: filter detected; supported routes require trusted "
            "play-by-play-derived clutch coverage"
        )
    if route not in {"player_game_finder", "team_record"} and (
        period_note := build_period_filter_note(quarter=quarter, half=half)
    ):
        notes.append(period_note)
    if route not in {"player_game_summary", "team_record"}:
        notes.extend(
            build_game_context_filter_notes(
                back_to_back=back_to_back,
                rest_days=rest_days,
                one_possession=one_possession,
                nationally_televised=nationally_televised,
            )
        )
    if route not in {"player_game_summary", "player_game_finder"}:
        if role_note := build_role_filter_note(role=role):
            notes.append(role_note)
    if opponent_quality_note := build_opponent_quality_note(opponent_quality=opponent_quality):
        notes.append(opponent_quality_note)
    if on_off_note := build_on_off_note(
        lineup_members=lineup_members,
        presence_state=presence_state,
    ):
        notes.append(on_off_note)
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
    if not route_kwargs.get("unsupported_filters") and (
        boundary_note := _unsupported_boundary_note(q, route, route_kwargs)
    ):
        notes.append(boundary_note)

    if notes:
        out["notes"] = notes

    out["confidence"] = compute_parse_confidence(out)
    out["alternates"] = generate_alternates(out)

    return out


def parse_query(query: str) -> dict:
    return _finalize_route(_build_parse_state(query))


def _merge_inherited_context(base: dict, clause: dict) -> dict:
    out = dict(clause)

    inherit_keys_if_missing = [
        "season",
        "start_season",
        "end_season",
        "explicit_relative_season",
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
        "opponent_quality",
        "opponent_conference",
        "lineup_members",
        "presence_state",
        "unit_size",
        "minute_minimum",
        "window_size",
        "stretch_metric",
        "last_n",
        "split_type",
        "role",
        "rest_days",
        "quarter",
        "half",
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
    if not out.get("back_to_back") and base.get("back_to_back"):
        out["back_to_back"] = True
    if not out.get("one_possession") and base.get("one_possession"):
        out["one_possession"] = True
    if not out.get("nationally_televised") and base.get("nationally_televised"):
        out["nationally_televised"] = True
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
