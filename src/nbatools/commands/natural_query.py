import re

import pandas as pd

from nbatools.commands._compound_event_authorization import (
    CompoundEventAuthorization,
    authorize_compound_event_route,
    declared_event_conditions,
    unrouted_compound_event_reason,
)
from nbatools.commands._condition_utils import normalize_stat_conditions, stat_conditions_cover
from nbatools.commands._confidence import compute_parse_confidence, generate_alternates
from nbatools.commands._constants import (
    LOWER_IS_BETTER_STATS,
    STAT_ALIASES,
    STAT_PATTERN,
    TEAM_SEASON_ADVANCED_STATS,
    normalize_text,
    route_to_intent,
)
from nbatools.commands._date_utils import (
    CURRENT_QUERY_DATE,
    MONTH_NAME_TO_NUM,
    explicit_date_is_open_ended,
    extract_date_range,
    has_explicit_calendar_date,
    invalid_explicit_date,
    seasons_for_explicit_dates,
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
from nbatools.commands._leaderboard_eligibility import (
    METRIC_SCOPE_UNSUPPORTED as LEADERBOARD_METRIC_SCOPE_UNSUPPORTED,
)
from nbatools.commands._leaderboard_eligibility import (
    MULTIPLE_METRICS as LEADERBOARD_MULTIPLE_METRICS,
)
from nbatools.commands._leaderboard_eligibility import (
    NO_REQUESTED_METRIC as LEADERBOARD_METRIC_REQUIRED,
)
from nbatools.commands._leaderboard_eligibility import (
    SINGLE_GAME_RANKING,
    LeaderboardEligibility,
    anchored_leaderboard_metric,
    assess_leaderboard_request,
    requested_leaderboard_metrics,
    season_leaderboard_stat,
    unrouted_ranking_reason,
)
from nbatools.commands._leaderboard_eligibility import (
    UNCLEAR_REQUEST as LEADERBOARD_REQUEST_UNCLEAR,
)
from nbatools.commands._leaderboard_eligibility import (
    UNSUPPORTED_AGGREGATION as LEADERBOARD_AGGREGATION_UNSUPPORTED,
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
    names_other_player_availability,
    presence_states_player_condition,
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
    try_league_game_finder_route,
    try_league_streak_route,
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
    canonicalize_sample_phrases as canonicalize_sample_phrases,
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
    detect_last_n_scope as detect_last_n_scope,
)
from nbatools.commands._parse_helpers import (
    detect_lineup_query as detect_lineup_query,
)
from nbatools.commands._parse_helpers import (
    detect_multi_player_aggregate as detect_multi_player_aggregate,
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
    detect_series_comeback as detect_series_comeback,
)
from nbatools.commands._parse_helpers import (
    detect_series_situation as detect_series_situation,
)
from nbatools.commands._parse_helpers import (
    detect_sophomore_leaderboard_boundary as detect_sophomore_leaderboard_boundary,
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
    detect_subjective_best_player as detect_subjective_best_player,
)
from nbatools.commands._parse_helpers import (
    detect_team_bench_scoring_boundary as detect_team_bench_scoring_boundary,
)
from nbatools.commands._parse_helpers import (
    detect_team_leader_stat as detect_team_leader_stat,
)
from nbatools.commands._parse_helpers import (
    detect_team_rolling_stretch_boundary as detect_team_rolling_stretch_boundary,
)
from nbatools.commands._parse_helpers import (
    detect_team_stretch_request as detect_team_stretch_request,
)
from nbatools.commands._parse_helpers import (
    detect_wins_losses as detect_wins_losses,
)
from nbatools.commands._parse_helpers import (
    extract_bare_year_pair as extract_bare_year_pair,
)
from nbatools.commands._parse_helpers import (
    extract_bare_year_season as extract_bare_year_season,
)
from nbatools.commands._parse_helpers import (
    extract_last_n as extract_last_n,
)
from nbatools.commands._parse_helpers import (
    extract_last_n_seasons as extract_last_n_seasons,
)
from nbatools.commands._parse_helpers import (
    extract_min_attempts,
    text_without_min_attempts,
)
from nbatools.commands._parse_helpers import (
    extract_min_games as extract_min_games,
)
from nbatools.commands._parse_helpers import (
    extract_min_occurrences as extract_min_occurrences,
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
    extract_top_n_games as extract_top_n_games,
)
from nbatools.commands._parse_helpers import (
    last_n_reach_back_seasons as last_n_reach_back_seasons,
)
from nbatools.commands._parse_helpers import (
    merge_opponent_points_allowed_conditions as merge_opponent_points_allowed_conditions,
)
from nbatools.commands._parse_helpers import (
    names_current_season as names_current_season,
)
from nbatools.commands._parse_helpers import (
    upper_bound_boundary as upper_bound_boundary,
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
    _DECADE_SUPERLATIVE,
    detect_by_decade_intent,
    detect_by_round_intent,
    detect_how_did_playoffs,
    detect_playoff_appearance_intent,
    detect_playoff_history_intent,
    detect_playoff_round_filter,
    detect_record_intent,
    extract_decade_season_range,
    try_playoff_record_route,
    try_record_leaderboard_route,
)
from nbatools.commands.entity_resolution import (
    TEAM_ALIASES,
    format_ambiguity_message,
    resolve_stat,
)
from nbatools.commands.freshness import compute_current_through
from nbatools.commands.query_boolean_parser import expression_contains_boolean_ops  # noqa: F401

# "leading at the half" (not "at the halfway point of the season")
_AT_THE_HALF = re.compile(r"\bat\s+the\s+half\b(?![- ]?way)")
_UNSUPPORTED_BOUNDARY_PHRASES = (
    # Score state during a game (no period scores are loaded).
    "in-game lead",
    "at halftime",
    "after 3 quarters",
    "after three quarters",
    "in the paint",
    "last 5 minutes",
    "last five minutes",
    "last 2 minutes",
    "last two minutes",
    "final 5 minutes",
    "final five minutes",
    "cooled off",
    "double-double over",
    "averaged a double-double",
    "paint points",
    "biggest triple-double",
    "drop-off",
    "co-star",
    "star teammate",
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
    "offensive rating when",
    "offensive rating without",
    "road by 20",
    "road team won by 20",
    "above .600",
    "salary",
    "contract",
)


# A minimum-attempts qualifier, in either the short or long form: "min 5
# attempts", "with at least 4 attempts per game". A number is what makes this a
# qualifier - the same test the metric boundary applies, where a metric next to
# a number is a condition rather than a ranking key.
#
# This used to be the bare phrase "attempts per game", which also swallowed
# "three-point attempts per game leaders" - a plain ranking whose metric and
# aggregation the product understands perfectly well. A generic "this phrase is
# unsupported" answer preempted the specific one, so the reader was told the
# question was unrecognizable rather than that only the season total exists.
#
# The player shooting-percentage leaderboard executes the qualifier
# (``min_attempts``); every other route still refuses it rather than drop it.
_ATTEMPT_QUALIFIER = re.compile(
    r"\bmin(?:imum)?\s+\d+\s+attempts\b|\b\d+\s+attempts?\s+per\s+game\b"
)


def _unsupported_phrase_boundary_note(q: str) -> str | None:
    if any(phrase in q for phrase in _UNSUPPORTED_BOUNDARY_PHRASES) or _AT_THE_HALF.search(q):
        return (
            "unsupported_boundary: this phrase is outside the shipped support boundary; "
            "no result was executed for the unsupported concept"
        )
    return None


def _unexecuted_attempt_qualifier_note(q: str, route: str, route_kwargs: dict) -> str | None:
    """Refuse a shot-attempt minimum the selected route would drop."""
    if not (extract_min_attempts(q) or _ATTEMPT_QUALIFIER.search(q)):
        return None
    if route == "season_leaders" and route_kwargs.get("min_attempts") is not None:
        return None
    return (
        "unsupported_boundary: a shot-attempt minimum applies only to player "
        "shooting-percentage leaderboards; no result was executed without it"
    )


def _min_attempts_kwargs(parsed: dict, stat: str | None) -> dict:
    """The attempt qualifier as season_leaders kwargs, for shooting rates only."""
    from nbatools.commands.season_leaders import ALLOWED_STATS, PERCENTAGE_STATS

    qualifier = parsed.get("min_attempts")
    if not qualifier or ALLOWED_STATS.get(str(stat or "").lower()) not in PERCENTAGE_STATS:
        return {}
    return {
        "min_attempts": qualifier["value"],
        "min_attempts_per_game": qualifier["per_game"],
        "attempt_stat": qualifier["attempt_stat"],
    }


def _unsupported_boundary_note(
    q: str,
    route: str,
    route_kwargs: dict,
    *,
    requested_stat: str | None = None,
) -> str | None:
    if boundary_note := _unsupported_phrase_boundary_note(q):
        return boundary_note
    if attempt_note := _unexecuted_attempt_qualifier_note(q, route, route_kwargs):
        return attempt_note

    if route == "season_team_leaders":
        stat = requested_stat or route_kwargs.get("stat")
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


# Routes whose build_result() actually filters by a whole-game teammate
# presence/absence flag. Every other route only ever receives with_player /
# without_player as display metadata (set unconditionally by the parser) with
# nothing downstream applying it - see _player_availability_unsupported_markers.
_WITH_PLAYER_SUPPORTED_ROUTES = {"team_record"}
_WITHOUT_PLAYER_SUPPORTED_ROUTES = {
    "team_record",
    "player_split_summary",
    "team_split_summary",
    "team_record_leaderboard",
    "game_finder",
    "game_summary",
    "player_stretch_leaderboard",
    "player_game_finder",
    "player_game_summary",
}
# "lineup with X and Y" is a distinct, already-correctly-handled feature
# (lineup composition via lineup_members), not a whole-game availability
# filter. It shares surface phrasing with detect_with_player, so with_player
# ends up set here too, but that's incidental parser noise, not an unapplied
# filter - gating on it would block a working, unrelated feature.
_PLAYER_AVAILABILITY_NOT_APPLICABLE_ROUTES = {"lineup_summary", "lineup_leaderboard"}


def _player_availability_unsupported_markers(parsed: dict, route: str | None) -> list[str]:
    """Return unsupported_filters markers for availability filters this route can't apply.

    detect_with_player/detect_without_player run unconditionally over every
    query regardless of which route it ends up on, so parsed["with_player"] /
    parsed["without_player"] get set even for routes that never learned to
    filter by them. Without this check those routes silently ignore the
    filter while the UI still shows it as applied.

    Deliberately does not gate on unresolved_with_player/unresolved_without_player:
    that fallback fragment detector is too imprecise to use as a blocking signal
    outside its original team-record-only context (e.g. it flags "with at least
    3 threes" as an unresolved availability player, which would incorrectly
    block ordinary stat-threshold queries on every other route).
    """
    if route in _PLAYER_AVAILABILITY_NOT_APPLICABLE_ROUTES:
        return []
    markers = []
    if parsed.get("with_player") and route not in _WITH_PLAYER_SUPPORTED_ROUTES:
        markers.append("with_player")
    if parsed.get("without_player") and route not in _WITHOUT_PLAYER_SUPPORTED_ROUTES:
        markers.append("without_player")
    return markers


# Routes whose build_result() actually applies a position-group filter. The
# parser sets parsed["position_filter"] on every query, but `position` is only
# ever forwarded into route_kwargs on the season_leaders branches, so any other
# route showed a "Position" badge over an unfiltered list.
_POSITION_FILTER_SUPPORTED_ROUTES = {"season_leaders"}

# Routes whose build_result() accepts and applies last_n. Derived from the
# build_result signatures in _natural_query_execution._get_build_result_map;
# routes outside this set (team_record, team_matchup_record, playoff_*,
# record_by_decade*, the occurrence leaders, ...) have no last_n parameter at
# all, so "last 10 games" silently returned the full span behind a
# "Last N games" badge.
_LAST_N_SUPPORTED_ROUTES = {
    "game_finder",
    "game_summary",
    "player_compare",
    "player_game_finder",
    "player_game_summary",
    "player_split_summary",
    "player_streak_finder",
    "player_stretch_leaderboard",
    "season_leaders",
    "season_team_leaders",
    "team_stretch_leaderboard",
    "team_compare",
    "team_record",
    "team_split_summary",
    "team_streak_finder",
    "top_player_games",
    "top_team_games",
}

# Game-log routes that can choose a last-N time window before applying game
# results and stat conditions (see detect_last_n_scope).
_LAST_N_WINDOW_ROUTES = {
    "game_finder",
    "game_summary",
    "player_game_finder",
    "player_game_summary",
    "player_split_summary",
    "team_record",
    "team_split_summary",
}


# Filters the parser attaches to `parsed` (where query_service builds badges
# from) but only forwards into route_kwargs on the routes that execute them.
# For these, presence in route_kwargs is the authoritative signal: a route that
# supports the filter always receives it, and a route that merely detected it
# never does. Checking build_result signatures instead would be wrong, because
# some of these are transformed before execution - opponent_conference and
# opponent_division are resolved into a list of `opponent` teams, so the routes
# that support them do not take a parameter by that name at all.
_ROUTE_KWARG_BACKED_FILTERS = {
    "opponent_conference": "opponent conference",
    "opponent_division": "opponent division",
    "wins_only": "wins-only",
    "losses_only": "losses-only",
    "home_only": "home-only",
    "away_only": "away-only",
    "start_date": "date range",
    "end_date": "date range",
}

# A split query sets the fields naming its own axis - "home vs away" sets
# home_only *and* away_only, "wins vs losses" sets both outcome flags - as the
# thing being split by, not as filters. The split routes handle that through
# `split`, so gating on the axis fields would block a working feature, exactly
# as gating with_player would break lineup composition queries. Only the axis
# of the split actually requested is exempt: "home vs away splits in wins"
# still has a genuine, unapplied wins-only filter on top.
_SPLIT_AXIS_FIELDS = {
    "home_away": ("home_only", "away_only"),
    "wins_losses": ("wins_only", "losses_only"),
}
_SPLIT_AXIS_ROUTES = {"player_split_summary", "team_split_summary"}

# Routes that take an opponent conference or division (mirrors
# _natural_query_execution._OPPONENT_GROUP_ROUTES).
_OPPONENT_GROUP_ROUTES = {
    "team_record",
    "team_streak_finder",
    "player_streak_finder",
    "team_occurrence_leaders",
    "player_occurrence_leaders",
    "team_record_leaderboard",
    "player_game_summary",
    "player_game_finder",
    "player_split_summary",
    "game_summary",
    "game_finder",
    "team_split_summary",
    "player_compare",
    "team_compare",
}


def _start_reach_back_at_served_data(route_kwargs: dict) -> None:
    """Move a reach-back start up to the first season the filters can read."""
    from nbatools.commands._seasons import int_to_season, season_to_int
    from nbatools.data_source import data_exists

    start, end = route_kwargs.get("start_season"), route_kwargs.get("end_season")
    if not start or not end:
        return
    suffix = "playoffs" if route_kwargs.get("season_type") == "Playoffs" else "regular_season"
    paths = ["data/raw/team_game_stats/{season}_" + suffix + ".csv"]
    if route_kwargs.get("opponent_quality"):
        paths.append("data/raw/standings_snapshots/{season}_regular_season.csv")
    year = season_to_int(start)
    while year < season_to_int(end) and not all(
        data_exists(path.format(season=int_to_season(year))) for path in paths
    ):
        year += 1
    route_kwargs["start_season"] = int_to_season(year)


def _team_compare_reach_back(route_kwargs: dict, parsed: dict) -> int:
    """Seasons a team comparison's last-N window may need to fill itself."""
    if route_kwargs.get("season_type") == "Playoffs":
        return 100
    if route_kwargs.get("head_to_head") or route_kwargs.get("opponent"):
        per_season = 2
    elif parsed.get("opponent_division"):
        per_season = 12
    elif parsed.get("opponent_conference") or route_kwargs.get("opponent_quality"):
        per_season = 24
    else:
        per_season = 60
    if any(
        route_kwargs.get(flag) for flag in ("home_only", "away_only", "wins_only", "losses_only")
    ):
        per_season = max(1, per_season // 2)
    return -(-int(route_kwargs["last_n"]) // per_season) + 1 + (per_season <= 2)


def _joined_team_pair(parsed: dict) -> bool:
    """ "Lakers and Warriors record" asks about each team, not their meetings."""
    from nbatools.commands._matchup_utils import _extract_compare_and_teams, strip_matchup_noise

    text = parsed.get("normalized_query") or ""
    if re.search(
        r"\b(?:each\s+other|one\s+another|head[- ]to[- ]head|h2h|meetings?|"
        r"matchups?|series|between)\b",
        text,
    ):
        return False
    return _extract_compare_and_teams(strip_matchup_noise(text))[0] is not None


def _third_team_opponent(text: str, team_a: str, team_b: str) -> str | None:
    from nbatools.commands._matchup_utils import _non_overlapping_team_mentions

    for start, _end, team in _non_overlapping_team_mentions(text):
        if team in {team_a, team_b}:
            continue
        if re.search(r"\b(?:vs\.?|versus|against)\s+(?:the\s+)?$", text[:start]):
            return team
    return None


def _team_vs_team_meetings(parsed: dict) -> bool:
    """ "Lakers vs Warriors last 10 games" means their last 10 meetings.

    Two teams joined by "vs" with a last-N window and nothing else to measure
    read as the games between them; "compare the Lakers and Warriors last 10
    games" (or a stat threshold) still compares each team's own last 10.
    """
    text = parsed.get("normalized_query") or ""
    return bool(
        parsed.get("last_n")
        and re.search(r"\b(?:vs\.?|versus|against)\b", text)
        and not parsed.get("opponent")
        and not _joined_team_pair(parsed)
        and not re.search(r"\bcompar", text)
        and parsed.get("min_value") is None
        and parsed.get("max_value") is None
        and not parsed.get("opponent_conference")
        and not parsed.get("opponent_division")
        and not parsed.get("opponent_quality")
    )


def _unexecuted_filter_markers(parsed: dict, route: str | None, route_kwargs: dict) -> list[str]:
    """Return unsupported_filters markers for filters this route parses but never applies.

    Same failure mode as _player_availability_unsupported_markers: the parser
    detects these unconditionally and query_service renders them as applied
    filter badges straight off ``parsed``, so a route that never received the
    corresponding kwarg answered a different question than the badge claimed.

    special_event is keyed off route_kwargs rather than a route allowlist
    because the routes that consume it do so through three different paths:
    an explicit ``special_event`` kwarg (finder/summary routes and occurrence
    counting), and ``special_condition`` on the streak finders, which encode
    "longest triple-double streak" as the streak's condition. Routes that
    merely detected it set neither - e.g. "team triple double leaders" reached
    team_occurrence_leaders, which silently counted 100-point games instead.
    """
    markers = []
    if parsed.get("position_filter") and route not in _POSITION_FILTER_SUPPORTED_ROUTES:
        markers.append("position_filter")
    if parsed.get("last_n") is not None and route not in _LAST_N_SUPPORTED_ROUTES:
        markers.append("last_n")
    occurrence_event = parsed.get("occurrence_event")
    detected_special_event = (
        occurrence_event.get("special_event") if isinstance(occurrence_event, dict) else None
    )
    executed_special_event = route_kwargs.get("special_event") or route_kwargs.get(
        "special_condition"
    )
    if detected_special_event and executed_special_event != detected_special_event:
        markers.append("special_event")

    axis_fields: tuple[str, ...] = ()
    if route in _SPLIT_AXIS_ROUTES:
        split_type = route_kwargs.get("split") or parsed.get("split_type")
        axis_fields = _SPLIT_AXIS_FIELDS.get(split_type, ())

    for field in _ROUTE_KWARG_BACKED_FILTERS:
        if not parsed.get(field) or field in axis_fields:
            continue
        if not route_kwargs.get(field):
            markers.append(field)

    return markers


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
        # "lebron vs cury against winning teams": the typoed second player
        # must not silently fall away behind the opponent filter.
        typo = detect_unresolved_player_typo(q, summary=True)
        if typo:
            return typo
        # "lebron vs curry's warriors" names a team after "vs", not a typo.
        match = _VS_SECOND_OPERAND_RE.search(q)
        if match and _vs_clause_is_opponent_group(q, match):
            return None
        return detect_unresolved_player_typo(q, comparison=True)
    return None


_VS_SECOND_OPERAND_RE = re.compile(r"\b(?:vs\.?|versus)\s+(?:the\s+)?([a-z][a-z'.\-]+)")
# Words after "vs" that mark a split or scope, not a second player name.
_VS_NON_PLAYER_OPERANDS = frozenset(
    {"home", "away", "road", "wins", "win", "losses", "loss", "last", "past", "recent"}
)


# Words that open an opponent group after "vs" ("vs the West", "vs Pacific").
_VS_GROUP_OPERANDS = frozenset(
    {
        "east",
        "eastern",
        "west",
        "western",
        "atlantic",
        "central",
        "southeast",
        "northwest",
        "pacific",
        "southwest",
        "midwest",
        "winning",
        "losing",
        "top",
        "best",
        "good",
        "bad",
        "playoff",
        "non",
        "contenders",
        "teams",
    }
)


def _detect_team_in_text(text: str):
    from nbatools.commands._matchup_utils import detect_team_in_text

    return detect_team_in_text(text)


def _league_occurrence_role(q: str) -> str | None:
    """Bench/starter wording on a league-wide occurrence leaderboard.

    Stricter than ``detect_role``: a bare "starting" is usually time ("starting
    in 2023-24"), so only lineup wording counts.
    """
    if re.search(r"\boff\s+the\s+bench\b|\bbench\b|\breserves?\b", q):
        return "bench"
    if re.search(
        r"\bas\s+(?:a\s+)?starters?\b|\bstarters\b|\bstarting\s+(?:five|lineup|unit|role)\b",
        q,
    ):
        return "starter"
    return None


def _mask_opponent_group_phrase(q: str, conference: str | None, division: str | None) -> str:
    """Hide "vs the West" from the player scan: West is a surname, not a player."""
    if conference:
        word = str(conference).lower() + r"(?:ern)?(?:\s+conference)?"
    elif division:
        word = re.escape(str(division).lower()) + r"(?:\s+division)?"
    else:
        return q
    return re.sub(rf"\b(?:against|vs\.?|versus)\s+(?:the\s+)?{word}\b", " ", q)


def _vs_clause_is_opponent_group(q: str, match: re.Match) -> bool:
    """The clause after "vs" names a team, quality bar or conference/division."""
    clause = re.split(r"\s+(?:against|vs\.?|versus)\s+", q[match.start(1) :])[0]
    return bool(
        _detect_team_in_text(clause)
        or detect_opponent_quality("vs " + clause)
        or clause.split()[0] in _VS_GROUP_OPERANDS
    )


def _unresolved_player_comparison_boundary(parsed: dict) -> str | None:
    """Detect a "<player> vs <name>" comparison whose second name did not resolve.

    "lebron vs jordan career" must not silently collapse into a one-player
    summary; when the second operand is an unidentified player name (not a
    team, opponent player, or split), refuse and ask the user to clarify.
    """
    if parsed.get("player_a") and parsed.get("player_b"):
        return None
    if not parsed.get("player"):
        return None
    # Any resolved opponent / split / situational interpretation means the
    # "vs" is already understood and must not be second-guessed.
    if any(
        parsed.get(key)
        for key in (
            "opponent_player",
            "split_type",
            "head_to_head",
            "presence_state",
            "lineup_members",
        )
    ):
        return None
    q = parsed["normalized_query"]
    match = _VS_SECOND_OPERAND_RE.search(q)
    if not match:
        return None
    operand = match.group(1)
    if operand in _VS_NON_PLAYER_OPERANDS:
        return None
    if any(
        parsed.get(key)
        for key in ("opponent", "opponent_quality", "opponent_conference", "opponent_division")
    ):
        # The opponent filter explains this "vs" unless another clause
        # ("... against winning teams") carries it: "lebron vs cury against
        # winning teams" still has an unidentified second player.
        if _vs_clause_is_opponent_group(q, match):
            return None
        if not re.search(r"\s+(?:against|vs\.?|versus)\s+", q[match.end(1) :]):
            return None
    return operand


def _player_team_comparison(parsed: dict) -> bool:
    """ "compare LeBron and the Lakers": one player and one team.

    Read as LeBron's games for the Lakers it silently drops the comparison;
    read as games against them it guesses. Either way the answer would not
    be the comparison asked for, so it refuses with both readings to pick.
    """
    if parsed.get("player_a") or parsed.get("team_a") or parsed.get("opponent"):
        return False
    if not (parsed.get("player") and parsed.get("team")):
        return False
    return bool(
        re.search(
            r"^\s*compar(?:e|ing)\s+.+?\s+(?:and|with|to)\s+",
            parsed.get("normalized_query") or "",
        )
    )


def _unresolved_player_stretch_boundary(parsed: dict) -> str | None:
    q = parsed["normalized_query"]
    if parsed.get("window_size") is None or parsed.get("stretch_metric") is None:
        return None
    if any(
        parsed.get(key) for key in ("player", "player_a", "player_b", "team", "team_a", "team_b")
    ):
        return None

    if re.match(
        r"^(?:who|which|what|best|top|hottest|most|longest|worst|coldest|poorest|ugliest)\b", q
    ):
        return None

    match = re.match(
        r"^(?P<fragment>[a-z][a-z'.-]{2,})"
        r"\s+(?:hottest|best|top|longest|most\s+efficient|\d+\s*(?:-\s*|\s+)games?)\b",
        q,
    )
    if match:
        return match.group("fragment")
    return None


# Why a league-wide ranking was refused, in the parse notes. Each reason needs
# different guidance, so they do not share copy.
#: "season high" and "top scoring games" have meant points here since before
#: this boundary existed, and both are documented in the query catalog and
#: guide. Points is written out only where the query wording carries one of
#: those approved shorthands - never as a stand-in for a metric nobody named.
SCORING_SHORTHAND = "pts"

_LEADERBOARD_REFUSAL_NOTES = {
    LEADERBOARD_METRIC_REQUIRED: (
        "this asks for a ranking without naming a stat to rank by, and there is no default metric"
    ),
    LEADERBOARD_AGGREGATION_UNSUPPORTED: (
        "the aggregation this asks for is not the one this stat's leaderboard ranks"
    ),
    LEADERBOARD_REQUEST_UNCLEAR: (
        "part of this question is outside what a league-wide leaderboard can express"
    ),
    LEADERBOARD_MULTIPLE_METRICS: (
        "this asks for more than one stat, and a ranking orders by exactly one"
    ),
    LEADERBOARD_METRIC_SCOPE_UNSUPPORTED: (
        "the requested stat cannot be computed for the requested window, and no other "
        "stat was substituted for it"
    ),
}


def _ranking_refusal_kwargs(
    eligibility,
    *,
    season: str | None,
    start_season: str | None,
    end_season: str | None,
    start_date: str | None,
    end_date: str | None,
    season_type: str,
    team: str | None = None,
) -> tuple[dict, str]:
    """Typed refusal kwargs and note for any ranking branch, from one decision.

    Every variable-metric ranking branch refuses the same shape, so a
    specialized population cannot invent its own softer boundary, and every
    refusal publishes the same truthful metadata.

    Carries no ``stat``. Nothing ran, so there is no executed metric to report;
    publishing the detector's pick would present a partial interpretation of a
    refused question as its answer. What the user actually asked for travels in
    ``requested_stat`` and ``requested_metrics`` instead.
    """
    route_kwargs = _unsupported_route_kwargs(
        eligibility.reason,
        season=season,
        start_season=start_season,
        end_season=end_season,
        start_date=start_date,
        end_date=end_date,
        season_type=season_type,
    )
    if team is not None:
        route_kwargs["team"] = team
    route_kwargs["leaderboard_eligibility"] = eligibility.to_dict()
    if eligibility.published_requested_stat:
        route_kwargs["requested_stat"] = eligibility.published_requested_stat
    if eligibility.published_requested_metrics:
        route_kwargs["requested_metrics"] = list(eligibility.published_requested_metrics)
    # Both sides of an aggregation mismatch, so the copy can name the direction
    # instead of assuming one.
    if eligibility.requested_aggregation:
        route_kwargs["requested_aggregation"] = eligibility.requested_aggregation
    if eligibility.available_aggregation:
        route_kwargs["available_aggregation"] = eligibility.available_aggregation
    note = (
        "unsupported_boundary: "
        + _aggregation_refusal_note(eligibility)
        + "; no substituted leaderboard was returned"
    )
    return route_kwargs, note


_AGGREGATION_WORDS = {
    "total": "a season total",
    "per_game": "a per-game figure",
    "rate": "a rate or percentage",
    "count": "a season count",
}


def _aggregation_refusal_note(eligibility) -> str:
    """The reason text, naming the direction of an aggregation mismatch.

    A single fixed sentence used to say "asks for a season total of a stat the
    leaderboard ranks per game" for every aggregation refusal, which is exactly
    backwards for `minutes per game leaders`.
    """
    base = _LEADERBOARD_REFUSAL_NOTES[eligibility.reason]
    requested = _AGGREGATION_WORDS.get(eligibility.requested_aggregation or "")
    available = _AGGREGATION_WORDS.get(eligibility.available_aggregation or "")
    if requested and available:
        return f"this asks for {requested} of a stat the leaderboard ranks as {available}"
    return base


def _apply_compound_refusal_kwargs(
    route_kwargs: dict,
    authorization: CompoundEventAuthorization,
) -> None:
    """Attach what a compound refusal asked for, and no executed stat.

    ``stat`` is cleared for the same reason the metric boundary clears it:
    nothing ran, so there is no metric to report as the one that did - and on
    this boundary the stat sitting there is usually a *condition* metric, which
    published as the ranking key is exactly the confusion being removed.
    """
    route_kwargs.pop("stat", None)
    route_kwargs["compound_event_authorization"] = authorization.to_dict()
    if authorization.requested_event_conditions:
        route_kwargs["requested_event_conditions"] = [
            dict(condition) for condition in authorization.requested_event_conditions
        ]
    if authorization.requested_stat:
        route_kwargs["requested_stat"] = authorization.requested_stat
    if authorization.unsupported_scope:
        route_kwargs["unsupported_scope"] = authorization.unsupported_scope
    if authorization.unsupported_availability:
        existing = route_kwargs.get("unsupported_availability") or {}
        route_kwargs["unsupported_availability"] = {
            **existing,
            **authorization.unsupported_availability,
        }


def _compound_refusal_note(authorization: CompoundEventAuthorization) -> str:
    """Why the compound request was refused, naming the part that could not run."""
    if authorization.unsupported_availability:
        detail = "the availability condition this asks for is not execution-backed"
    elif authorization.requested_stat:
        detail = (
            f"this asks to rank by {authorization.requested_stat}, which "
            f"{authorization.unsupported_scope or 'this ranking'} cannot order by"
        )
    elif authorization.requested_event_conditions:
        detail = (
            "this states event conditions no available route can execute together "
            "with the rest of the request"
        )
    else:
        detail = "part of this request could not be executed as asked"
    return f"unsupported_boundary: {detail}; no reduced version of the question was answered"


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


_TEAM_PAIR_ALIASES = "|".join(
    re.escape(name)
    for name in sorted(TEAM_ALIASES, key=len, reverse=True)
    # "cs" doubles as a word; "was"/"min" only count inside a list of teams.
    if name not in {"cs", "c's"}
)
_TEAM_ONE = rf"(?:the\s+)?(?:{_TEAM_PAIR_ALIASES})(?![\w'])"
_TEAM_LIST_SEP = r"(?:\s*,\s*(?:(?:and|&)\s+)?|\s+(?:and|&)\s+)"
_TEAM_LIST_PATTERN = re.compile(rf"(?<![\w']){_TEAM_ONE}(?:{_TEAM_LIST_SEP}{_TEAM_ONE})+")
_TEAM_ONE_PATTERN = re.compile(rf"(?<![\w'])(?:the\s+)?({_TEAM_PAIR_ALIASES})(?![\w'])")
_OPPONENT_LEAD = re.compile(r"\b(?:vs\.?|versus|against|over|facing|beat|beating)\s*$")
_TEAM_VERSUS_CHAIN = re.compile(
    rf"(?<![\w']){_TEAM_ONE}(?:\s+(?:vs\.?|versus|v\.?)\s+{_TEAM_ONE})+"
)
# Aliases that are also everyday words count as teams only inside a list.
_WORD_TEAM_ALIASES = frozenset({"was", "min"})


# Title questions that ask more than a count: never answer them with one.
_TITLE_EXTRA_CONDITION = re.compile(
    r"back[- ]to[- ]back|repeat|three[- ]?peat|clinch|\bstats?\b|\bgames?\b|\broster\b"
    r"|\bwithout\b|\bwith\s+(?!(?:the\s+)?most\b)[a-z]"
)
_LEAGUE_TITLE_WORDING = re.compile(
    r"\b(?:which|what)\s+(?:nba\s+)?(?:teams?|franchises?)\b|\bteams?\b|\bfranchises?\b"
    r"|\bchampions?\b|\bwinners?\b|\bwho\s+won\s+the\b(?!.*\bmost\b)"
    r"|^(?!.*\b(?:who|players?)\b).*\bmost\b"
)
_BARE_YEAR = re.compile(r"(?<![\d-])(?:19|20)\d{2}(?!-\d{2}\b)(?!\d)")


def _title_year_left_unused(q: str) -> bool:
    """A year the title route would not apply ("titles from 1990 to 2010",
    "titles 2014"): refuse rather than count every season."""
    years = _BARE_YEAR.findall(q)
    if not years:
        return False
    if all(extract_season_range(q)):
        # "titles from 2000 to 2010": both years bound the span.
        return False
    if len(years) > 1:
        # "since 2010 until 2020": only one year is ever applied.
        return True
    return not (extract_season(q) or extract_since_season(q) or re.search(r"\b(?:19|20)\d0s\b", q))


_TEAM_TITLE_COUNT = re.compile(r"\b(?:championships?|champions?|titles?)\b")
# Rings belong to players; division and conference titles are not Finals wins.
_NON_LEAGUE_TITLE = re.compile(
    r"\brings?\b|\b(?:division|divisional|conference|east(?:ern)?|west(?:ern)?)\s+"
    r"(?:titles?|championships?|champions?)\b|\bscoring\s+(?:titles?|champions?)\b"
)

# A player's rings: "how many rings does LeBron have", "LeBron championships".
_PLAYER_RING_WORDS = re.compile(r"\brings?\b|\bchampionships?\b|\btitles?\b")
_NOT_A_RING = re.compile(
    r"\b(?:division|divisional|conference|east(?:ern)?|west(?:ern)?)\s+"
    r"(?:titles?|championships?|champions?)\b|\bscoring\s+(?:titles?|champions?)\b"
    r"|\b(?:mvp|dpoy|roy|awards?)\b"
)
# "players with the most rings", "who has the most rings": the players board.
# Every word a plain ring question can use once the spans the parser resolves are
# removed. Anything else (a second player, an opponent, "in a row", "at age 27",
# "by a center", "in the East", a bare number, "last year") is a qualifier the
# ring count cannot honour, so the question refuses instead of answering the
# whole total.
_RING_QUESTION_WORDS = frozenset(
    """
    how many much rings ring championships championship titles title does did do has
    have had got gotten won win wins winning the a an most who which what whats player
    players leaders leader is are of in by nba all time ever total overall with
    playoffs postseason career times count number so far currently now for owns own
    any single
    """.split()
)
_RING_SPAN_PHRASES = (
    # "over the last 5 seasons", "in the past 20 years"
    r"\b(?:(?:over|in|during|for)\s+)?(?:the\s+)?(?:last|past)\s+\d{1,2}\s+"
    r"(?:seasons?|years?|playoffs|postseasons?)\b",
    # "this season", "last season"
    r"\b(?:in\s+|during\s+)?(?:this|last|previous|current)\s+season\b",
    # "over his career", "in his whole career"
    r"\b(?:over|in|during|for|throughout)\s+(?:his|her|their)\s+(?:whole\s+|entire\s+)?career\b",
    # "in the 2010s"
    r"\b(?:in|during)\s+the\s+(?:19|20)\d0s\b",
    # "from 2012 to 2016", "between 2012 and 2016". Only these pairs: the parser
    # leaves a lone "through 2016" / "until 2016" unresolved, so it must stay.
    r"\b(?:from|between)\s+(?:the\s+)?(?:19|20)\d{2}(?:\s(?:19|20)?\d{2})?\s+"
    r"(?:to|and|through|thru|until)\s+(?:the\s+)?(?:19|20)\d{2}(?:\s(?:19|20)?\d{2})?"
    r"(?:\s+(?:playoffs|postseason|season))?\b",
    # "since 2015", "in 2012-13", "in the 2020 playoffs" (a lone "from 2015"
    # is not resolved either)
    r"\b(?:since|in|during)\s+(?:the\s+)?"
    r"(?:19|20)\d{2}(?:\s(?:19|20)?\d{2})?(?:\s+(?:playoffs|postseason|season))?\b",
    # "top 5"
    r"\btop\s+\d{1,2}\b",
)


def _ring_question_has_qualifier(q: str, player: str | None) -> bool:
    """True when ``q`` says more than "how many rings [player] [span]"."""
    from nbatools.commands.entity_resolution import (
        _normalize_for_matching,
        allowed_player_reference_tokens,
    )

    text = _normalize_for_matching(re.sub(r"'s\b", "", q)).replace("'", "")
    for phrase in _RING_SPAN_PHRASES:
        text = re.sub(phrase, " ", text)
    allowed = allowed_player_reference_tokens(player) if player else set()
    return any(
        token not in _RING_QUESTION_WORDS and token not in allowed
        for token in re.findall(r"[\w.]+", text)
    )


_PLAYER_RING_BOARD = re.compile(
    r"\brings?\b.*\b(?:most|leaders?)\b|\b(?:most|leaders?)\b.*\brings?\b"
    r"|\bplayers?\b.*\b(?:most|leaders?)\b|\b(?:most|leaders?)\b.*\bplayers?\b"
)

# Title words that qualify another question rather than ask for a title count:
# "record vs the defending champions", "best record by a title winner".
_TITLE_NOT_A_COUNT = re.compile(
    r"\b(?:defending|reigning)\s+champ|\b(?:vs\.?|versus|against|as)\s+(?:the\s+)?champions?\b"
    r"|\brecords?\b|\bbest\b|\bworst\b|\bsince\s+winning\b|\bhow\s+(?:did|do|does)\b"
    r"|\bstats?\b|\bpoints?\b|\baverag\w*"
    r"|(?<!title\s)(?<!championship\s)\bwins\b|\bbeat(?:en|ing|s)?\b|\bplay(?:ing|ed|s)?\b"
    r"|\bodds\b|\bchances?\b"
)


# "games between them", "each other", "in Lakers vs Celtics games": the
# games the two teams played against each other.
_TEAM_MEETING_WORDS = re.compile(
    r"\b(?:between\s+them|each\s+other|one\s+another|meetings?|matchups?|h2h"
    r"|head[\s-]+to[\s-]+head)\b"
    rf"|\b(?:vs\.?|versus|v\.?)\s+{_TEAM_ONE}\s+games\b"
)


def _named_team_pairs(q: str) -> dict:
    """Teams listed with "and"/commas: subjects ("lakers, celtics and knicks
    best stretch") or, after "vs"/"against", opponents ("vs lakers and knicks").
    """
    found: dict[str, list[str]] = {"subjects": [], "opponents": [], "lead": []}
    for match in _TEAM_LIST_PATTERN.finditer(q):
        teams: list[str] = []
        list_end = match.start()
        closed = False
        for one in _TEAM_ONE_PATTERN.finditer(q, match.start(), match.end()):
            if closed:
                break
            # "and" joins the last item: "vs celtics and knicks, lakers best..."
            # ends the list at the knicks.
            closed = bool(re.search(r"(?:\band|&)\s+(?:the\s+)?$", q[list_end : one.start()]))
            abbr = TEAM_ALIASES[one.group(1)]
            if abbr not in teams:
                teams.append(abbr)
            list_end = one.end()
        if len(teams) < 2:
            continue
        role = "opponents" if _OPPONENT_LEAD.search(q[: match.start()]) else "subjects"
        if not found[role]:
            found[role] = teams
            if role == "opponents":
                # The subject is a team named outside the opponent list.
                outside = q[: match.start()] + " " + q[list_end:]
                found["lead"] = [
                    TEAM_ALIASES[one.group(1)] for one in _TEAM_ONE_PATTERN.finditer(outside)
                ]
    # "Lakers vs Celtics best stretch": the teams joined by vs, and any other
    # team named, which counts only as an opponent ("... vs the Knicks").
    chain = _TEAM_VERSUS_CHAIN.search(q)
    found["versus"] = []
    found["versus_others"] = []
    found["versus_opponents"] = []
    if chain:
        found["versus"] = list(
            dict.fromkeys(
                TEAM_ALIASES[one.group(1)] for one in _TEAM_ONE_PATTERN.finditer(chain.group(0))
            )
        )
        rest = q[: chain.start()] + " " * len(chain.group(0)) + q[chain.end() :]
        for one in _TEAM_ONE_PATTERN.finditer(rest):
            if one.group(1) in _WORD_TEAM_ALIASES:
                continue
            abbr = TEAM_ALIASES[one.group(1)]
            found["versus_others"].append(abbr)
            if _OPPONENT_LEAD.search(rest[: one.start()]) or abbr in found["opponents"]:
                found["versus_opponents"].append(abbr)
    found["meeting"] = bool(_TEAM_MEETING_WORDS.search(q))
    return found


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
            rf"\b(?:top|highest|best|biggest|lowest|fewest)\s+(?:\d{{1,3}}\s+)?team\s+"
            rf"(?:(?:points?|scoring|{STAT_PATTERN})\s+)?(?:games?|performances?|nights?)\b",
            q,
        )
        or re.search(
            rf"\b(?:top|highest|best|biggest|lowest|fewest)\s+(?:\d{{1,3}}\s+)?"
            rf"(?:(?:points?|scoring|{STAT_PATTERN})\s+)?team\s+"
            r"(?:games?|performances?|nights?)\b",
            q,
        )
        or re.search(r"\bmost\s+points\s+by\s+a\s+team\s+in\s+a\s+game\b", q)
        # "most threes in a game by a team", "most assists by a team in a single game"
        or re.search(
            r"\b(?:most|fewest)\s+(?:[a-z0-9%-]+\s+){1,3}(?:by|from)\s+an?\s+(?:nba\s+)?team\s+"
            r"in\s+an?\s+(?:single\s+)?game\b"
            r"|\b(?:most|fewest)\s+(?:[a-z0-9%-]+\s+){1,3}in\s+an?\s+(?:single\s+)?game\s+"
            r"(?:by|from)\s+an?\s+(?:nba\s+)?team\b",
            q,
        )
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
    "detect_team_stretch_request",
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
    "extract_min_games",
    "extract_min_value",
    "extract_opponent_points_allowed_conditions",
    "extract_position_filter",
    "extract_relative_season",
    "extract_bare_year_pair",
    "detect_series_situation",
    "detect_series_comeback",
    "extract_bare_year_season",
    "extract_season",
    "extract_season_range",
    "extract_since_season",
    "extract_streak_request",
    "extract_team_streak_request",
    "extract_threshold_conditions",
    "merge_opponent_points_allowed_conditions",
    "extract_top_n",
    "extract_top_n_games",
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


_EVER_WORDS = re.compile(r"\bever\b|\bin\s+(?:nba\s+)?history\b|\bof\s+all\s+time\b")
_NAMED_SEASON_WORDS = re.compile(
    r"(?<!\d)(?:19|20)\d{2}(?!\d)|'\d{2}\b"
    r"|\b(?:this|these|last|current|previous)\s+(?:season|year|postseason|playoffs)\b"
    r"|\b(?:today|tonight|yesterday|week|month)\b"
)


def _top_games_span(
    season: str | None,
    start_season: str | None,
    end_season: str | None,
    season_type: str,
) -> dict:
    """ "most points in a game since 2000" ranks every game in the span."""
    if start_season and end_season and not season:
        return {"season": None, "start_season": start_season, "end_season": end_season}
    return {"season": season or default_season_for_context(season_type)}


# "won it all" is the title: without this it read as regular-season wins.
_WON_IT_ALL = re.compile(r"\b(win|won|wins|winning)\s+it\s+all\b")
# "most points in a finals game" is the single-game question asked of the Finals.
_ROUND_SINGLE_GAME = re.compile(
    r"\b(a|one|single|any)\s+((?:nba\s+)?(?:conference\s+)?(?:finals|semifinals|semis"
    r"|(?:first|second|third|1st|2nd|3rd)[\s-]round))\s+game\b(?!\s*s\b)(?!\s+\d)"
)
_FEWEST_WORDS = re.compile(r"\b(?:fewest|lowest)\b|(?<!\bat\s)\bleast\b")
# "most points in an elimination game" is the single-game question asked of them.
_SITUATION_SINGLE_GAME = re.compile(
    r"\bin\s+(a|an|one|single|any|a\s+single)\s+(elimination|closeout|close-out|clinching"
    r"|series[\s-]clinching|deciding|winner[\s-]take[\s-]all)\s+game\b(?!\s*s\b)"
)
# "most points in a single season", "most wins in a season since 2000":
# one player or team season per row, not totals across the span.
_SINGLE_SEASON_RANKED_ROUTES = frozenset(
    {"season_leaders", "season_team_leaders", "team_record_leaderboard"}
)
_SINGLE_SEASON_UNRANKED_ROUTES = frozenset(
    {"top_player_games", "top_team_games", "team_occurrence_leaders"}
)
# "which decade did the Lakers win the most": the record is ranked.
_WHICH_DECADE_RECORD = re.compile(
    r"\bwhich\s+decade\b.*\b(?:win|won|lose|lost)\s+the\s+most(?!\s+(?:series|titles?))\b"
)
_RANKED_WINS_LOSSES = re.compile(
    r"\b(?:most|fewest|least)\s+(?:(?:road|home|away|playoffs?|postseason|regular[\s-]season)\s+)?"
    r"(?:wins|losses)\b"
    r"|\bwin(?:ning)?\s+(?:percentage|pct)|\bwin(?:ning)?\s*%"
)
# "LeBron best scoring season", "Jokic most rebounds in a single season":
# rank that player's own seasons.
_PLAYER_BEST_SEASON = re.compile(
    r"\b(?:best|highest|top|greatest|worst|lowest)\s+(?:[a-z0-9%-]+\s+){0,4}?seasons?\b"
    r"|\bseasons?\s+(?:ranked|sorted|ordered)\s+by\b"
    r"|\bseasons?\s+with\s+the\s+(?:most|fewest|least|highest|lowest|best|worst)\b"
)
_PLAYER_SEASON_LOW = re.compile(r"\b(?:worst|lowest|fewest)\b|(?<!\bat\s)\bleast\b")
# "per game" is a season average, not a single-game ask.
_PLAYER_SEASON_BLOCKERS = re.compile(r"(?<!\bper\s)\bgames?\b|\bstretch\b|\bseason[\s-]highs?\b")
_PLAYER_SEASON_ROUTES = frozenset({"player_game_finder", "player_game_summary"})
# Route kwargs the player-season board keeps; any other set filter declines.
_PLAYER_SEASON_KEPT = frozenset(
    {
        "season",
        "start_season",
        "end_season",
        "season_type",
        "player",
        "stat",
        "limit",
        "sort_by",
        "ascending",
    }
)
# "LeBron best three point shooting season": the shooting rate, not points.
_SEASON_SHOOTING_PATTERNS = (
    (r"\btrue\s+shooting\s+seasons?\b", "ts_pct"),
    (r"\beffective\s+(?:field\s+goal\s+)?shooting\s+seasons?\b", "efg_pct"),
    # "top 3 shooting seasons" is a count, not 3-point shooting.
    (
        r"(?:\bthree[\s-]?(?:point|pt)?s?|\b3[\s-]?(?:point|pt)s?"
        r"|(?<!\btop\s)(?<!\bbest\s)(?<!\bworst\s)\b3s?)\s+shooting\s+seasons?\b",
        "fg3_pct",
    ),
    (r"\bfree[\s-]?throw\s+shooting\s+seasons?\b", "ft_pct"),
    (r"\bshooting\s+seasons?\b", "fg_pct"),
)


def _season_shooting_stat(q: str) -> str | None:
    for pattern, stat in _SEASON_SHOOTING_PATTERNS:
        if re.search(pattern, q):
            return stat
    return None


# "Celtics best defensive seasons", "Lakers worst offensive season".
_TEAM_SEASON_RATING = (
    (r"\bdefensive\s+(?:rating\s+)?seasons?\b", "def_rating"),
    (r"\boffensive\s+(?:rating\s+)?seasons?\b", "off_rating"),
    (r"\bnet\s+rating\s+seasons?\b", "net_rating"),
)
# "Lakers top 3 seasons by wins", "Lakers best season with the most wins".
_TEAM_SEASON_RECORD_STAT = re.compile(
    r"\b(?:by|with\s+the\s+(?:most|fewest))\s+"
    r"(wins|losses|win(?:ning)?\s*(?:%|percentage|pct))(?![\w%])"
)


def _team_season_stat(q: str) -> str | None:
    for pattern, stat in _TEAM_SEASON_RATING:
        if re.search(pattern, q):
            return stat
    m = _TEAM_SEASON_RECORD_STAT.search(q)
    if m:
        word = m.group(1)
        return word if word in ("wins", "losses") else "win_pct"
    return _season_shooting_stat(q)


_TEAM_SEASON_ROUTES = frozenset({"game_finder", "game_summary", "team_record", "record_by_decade"})
_TEAM_SEASON_KEPT = _PLAYER_SEASON_KEPT - {"player"} | {"team"}
# "Lakers best season", "Lakers worst record in a single season": the record.
_TEAM_PLAIN_BEST_SEASON = re.compile(
    r"\b(?:best|worst|greatest|top\s+\d+)\s+"
    r"(?:(?:playoff|postseason|regular[\s-]season|regular|winning)\s+)?(?:seasons?|records?)\b"
    r"|\brecords?\b"
)
# "best scoring season by a Lakers player", "Lakers points allowed": not the
# team's own stat season.
_TEAM_SEASON_BLOCKERS = re.compile(
    r"\bplayers?\b|\bindividual\b|\bby\s+an?\b|\bwho\b|\ballow(?:ed|ing)?\b|\bgiven\s+up\b"
)
_SINGLE_SEASON_TEAM = re.compile(r"\bby\s+an?\s+team\b|\bwhich\s+teams?\b|\bteams?\b")
_SINGLE_SEASON = re.compile(r"\bin\s+(?:a|one|any)\s+(?:single\s+)?season\b|\bsingle[\s-]season\b")
_TITLE_WORD = re.compile(r"\b(?:titles?|championships?|champions?|rings?)\b")
_TITLE_RELATIVE_YEAR = re.compile(r"\b(this|last|previous)\s+year\b")


# "in '16", "the '90s", "'15-16": apostrophe years. Data starts in 1996-97,
# so '90-'99 are 1990s and everything else is 2000s.
_SHORT_YEAR = re.compile(r"(?<![\w'’])['’](\d{2})(s?)(?:-(\d{2}))?(?![\w%'’])")


# "the 90s", "the 2000s" short form: four digits, like the apostrophe form.
# The 1930s and 1940s can never have data, so "the 30s"/"the 40s" stay
# unread.
_BARE_DECADE = re.compile(r"\bthe\s+([0-25-9])0s\b")
# "games with points in the 20s", "scoring in the 30s": a stat band, not a
# decade.
_STAT_BAND = re.compile(
    r"\b(?:scor\w*|shoot\w*|shot|games?|nights?|with\s+\w+(?:\s+\w+)?)\s+in\s+the\s+\d0s\b"
)
_THIS_DECADE = re.compile(r"\b(?:(?:in|during|of|from)\s+)?this\s+decade\b")
# "who won the most games in a season" is most wins; "in a row" is a streak.
_WON_MOST_GAMES = re.compile(
    r"\b(won|lost)\s+the\s+(most|fewest)\s+games\b"
    r"(?!\s+(?:in\s+a\s+row|straight|consecutive|without|when|by|vs|against))"
)
_WON_LOST = {"won": "wins", "lost": "losses"}


def _expand_short_year(match: re.Match) -> str:
    year = int(match.group(1))
    # A decade ("the '80s") is never in the future; a single year is 2000s
    # unless '90-'99.
    full = (1900 if year >= (30 if match.group(2) else 90) else 2000) + year
    if match.group(3):
        return f"{full}-{match.group(3)}"
    return f"{full}{match.group(2)}"


def _build_parse_state(query: str) -> dict:
    q = canonicalize_sample_phrases(normalize_text(query))
    q = _SHORT_YEAR.sub(_expand_short_year, q)
    if not _STAT_BAND.search(q):
        q = _BARE_DECADE.sub(lambda m: f"the {19 if int(m.group(1)) >= 5 else 20}{m.group(1)}0s", q)
    if _THIS_DECADE.search(q):
        # "this decade": the decade the current season starts in.
        start = int(default_season_for_context("Regular Season")[:4]) // 10 * 10
        q = _THIS_DECADE.sub(f"in the {start}s", q)
    if not re.search(r"\bplayers?\b|\bcoach(?:es)?\b", q):
        # "which player won the most games" is not a team record.
        q = _WON_MOST_GAMES.sub(lambda m: f"had the {m.group(2)} {_WON_LOST[m.group(1)]}", q)
    if not re.search(r"\bcome\s*backs?\b|\bcame\s+back\b|\bcomebacks?\b", q):
        q = _WON_IT_ALL.sub(r"\1 the title", q)
    q = _ROUND_SINGLE_GAME.sub(r"\1 game in the \2", q)
    if not re.search(
        r"\bper\s+game\b|\baverages?\b|\bavg\b|\bppg\b|\b(?:fewest|lowest|least)\b", q
    ):
        # Averages and "fewest" stay on the season board over those games.
        q = _SITUATION_SINGLE_GAME.sub(r"in a game in \2 games", q)
    if _TITLE_WORD.search(q):
        # "who won the title last year": a title belongs to one season, so the
        # year reads as that season instead of falling back to every season.
        q = _TITLE_RELATIVE_YEAR.sub(r"\1 season", q)
    season_type = detect_season_type(q)

    # -- Historical span detection (must run before single-season extraction) --
    start_season, end_season = extract_season_range(q, season_type)
    if start_season and end_season:
        from nbatools.commands._seasons import default_end_season, season_to_int

        # "from 2020 to 2030": the span ends with the latest season played. A
        # span that starts after it is left alone, so it finds no games rather
        # than quietly answering for the latest season.
        latest = default_end_season(season_type)
        if season_to_int(start_season) <= season_to_int(latest) < season_to_int(end_season):
            end_season = latest
    # "2019-2020" is one season written out, not a span.
    written_out_season = start_season if start_season and start_season == end_season else None
    if written_out_season:
        start_season = end_season = None
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
        # Try "career" / "all-time" / "ever" when no season is named
        if detect_career_intent(q) or (_EVER_WORDS.search(q) and not _NAMED_SEASON_WORDS.search(q)):
            from nbatools.commands._seasons import resolve_career

            career_intent = True
            start_season, end_season = resolve_career(season_type)

    explicit_relative_season = False
    bare_year_season = None
    bare_year_span = False
    season = None
    if not (start_season and end_season):
        season = extract_season(q) or written_out_season
        if season is None:
            season = extract_relative_season(q, season_type)
            explicit_relative_season = season is not None
        if season is None:
            # An explicit "<month> <year>" or ISO date pins the season as well as the date
            # window. This has to run before the default_season_for_context
            # fallbacks below, or the season stays on the current one while the
            # date window points at a year that season never covers.
            first_date_season, last_date_season = seasons_for_explicit_dates(q)
            if first_date_season and explicit_date_is_open_ended(q):
                from nbatools.commands._seasons import default_end_season

                last_date_season = max(last_date_season, default_end_season(season_type))
            if first_date_season != last_date_season:
                start_season, end_season = first_date_season, last_date_season
            else:
                season = first_date_season
        if season is None and not (start_season and end_season):
            bare_pair = extract_bare_year_pair(q)
            if bare_pair is not None:
                start_season, end_season = bare_pair
                bare_year_span = True
        if season is None and not (start_season and end_season):
            bare_year = extract_bare_year_season(q)
            if bare_year is not None:
                bare_year_season = bare_year
                season = bare_year[1]

    min_attempts = extract_min_attempts(q)
    # Metric and threshold detection skip the attempt qualifier: "minimum 150
    # three point attempts" qualifies the ranking, it does not name its metric.
    q_metric = text_without_min_attempts(q)
    stat = detect_stat(q_metric)
    last_n = extract_last_n(q)
    min_games = extract_min_games(q)
    top_n = extract_top_n(q)
    split_type = detect_split_type(q)
    leaderboard_intent = wants_leaderboard(q)
    team_leaderboard_intent = wants_team_leaderboard(q)
    stretch_request = detect_stretch_query(q)
    window_size = stretch_request["window_size"] if stretch_request else None
    stretch_metric = stretch_request["stretch_metric"] if stretch_request else None
    window_defaulted = bool(stretch_request and stretch_request.get("window_defaulted"))
    stretch_worst = bool(stretch_request and stretch_request.get("worst"))
    stretch_player_group = stretch_request.get("player_group") if stretch_request else None
    stretch_opponent_description = (
        stretch_request.get("opponent_description") if stretch_request else None
    )
    team_rolling_stretch_boundary = detect_team_rolling_stretch_boundary(q)
    team_stretch_request = detect_team_stretch_request(q)
    if team_stretch_request is not None:
        team_stretch_request.update(_named_team_pairs(q))
        # "Lakers vs Celtics best stretch vs playoff teams": the pair parse skips
        # opponent quality, so read it here for the vs path to honor or refuse.
        team_stretch_request["opponent_quality"] = detect_opponent_quality(q)
    stretch_names_players = bool(stretch_request and re.search(r"\b(?:players?|who)\b", q))
    rookie_leaderboard_boundary = detect_rookie_leaderboard_boundary(q)
    sophomore_leaderboard_boundary = detect_sophomore_leaderboard_boundary(q)
    team_leader_stat = detect_team_leader_stat(q)
    subjective_best_player = detect_subjective_best_player(q)
    multi_player_aggregate = detect_multi_player_aggregate(q)
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
        stat = detect_player_leaderboard_stat(q_metric)
    if stat is None and team_leaderboard_intent:
        stat = detect_team_leaderboard_stat(q_metric)
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
    # "Celtics record in game 7s": a playoff series situation filters playoff
    # games, every season since 1996-97 unless a season is named.
    series_situation = detect_series_situation(q)
    series_comeback = detect_series_comeback(q)
    series_situation_career = False
    if (series_situation or series_comeback) and season_type != "Playoffs":
        from nbatools.commands._seasons import default_end_season

        regular_default_end = default_end_season(season_type)
        season_type = "Playoffs"
        if start_season and end_season == regular_default_end:
            end_season = default_end_season("Playoffs")
    if (
        (series_situation or series_comeback)
        and not (season or start_season or end_season)
        and not explicit_relative_season
        and not re.search(
            r"\b(?:this|current|last|previous)\s+(?:season|year|postseason|playoffs)\b", q
        )
    ):
        from nbatools.commands._seasons import resolve_career

        start_season, end_season = resolve_career("Playoffs")
        series_situation_career = True
    # "LeBron stats in the Finals": a round with no span named covers every
    # playoff season, as a series situation does.
    playoff_round_unnamed_span = bool(
        playoff_round_filter
        and not (season or start_season or end_season)
        and not explicit_relative_season
        and not re.search(
            r"\b(?:this|current|last|previous)\s+(?:season|year|postseason|playoffs)\b", q
        )
    )
    historical_route_intent = bool(
        by_decade_intent
        or playoff_appearance_intent
        or playoff_history_intent
        or playoff_round_filter
        or by_round_intent
    )

    threshold_conditions = merge_opponent_points_allowed_conditions(
        extract_threshold_conditions(q_metric),
        extract_opponent_points_allowed_conditions(q),
    )

    # "between 20 and 30 points and 5 assists": the threshold scan reads only
    # operator-led conditions, so a plain "5 assists" in the same list was
    # dropped and summaries counted the first condition alone.
    threshold_conditions = _complete_threshold_conditions(
        threshold_conditions, compound_occurrence_conditions
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
        min_value = extract_min_value(q_metric, stat)
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

    season_defaulted = False
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
            season_defaulted = True

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
        player_result = detect_player_resolved(
            _mask_opponent_group_phrase(q, opponent_conference, opponent_division)
        )
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

    if team_a and team_b:
        # "compare the Lakers and Warriors vs winning teams", "Lakers and
        # Warriors last 10 games vs the Celtics": a third team is the opponent.
        opponent_quality = detect_opponent_quality(q)
        opponent = _third_team_opponent(q, team_a, team_b)
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
    if (
        re.search(r"\bseries\b", q)
        and not re.search(r"\bgames?\b", q)
        and re.search(r"\b(?:playoffs?|postseason)\b", q)
    ):
        # "how many playoff series have the Lakers won": series won and lost
        # come from the playoff history, not a filter to winning games.
        wins_only = losses_only = False
    if (
        re.search(_RANKED_WINS_LOSSES, q)
        or re.search(_WHICH_DECADE_RECORD, q)
        or _DECADE_SUPERLATIVE.search(q)
    ):
        # "most wins in a single season", "most wins over a 10 game stretch",
        # "which decade did the Lakers win the most": wins are the ranked
        # stat, not a filter to won games.
        wins_only = losses_only = False

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
            season_defaulted = True

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
    explicit_range_start, explicit_range_end = extract_season_range(q, season_type)

    if player and team_streak_request and team_streak_request.get("team_condition_only"):
        # A bare stat condition is a team streak only without a player subject.
        team_streak_request = None
    if (
        (streak_request or team_streak_request)
        # "this season" / "last season" name a season too.
        and not explicit_relative_season
        and not re.search(r"\b(?:this|current)\s+(?:season|year)\b", q)
        and not career_intent
        # "Lakers win streak in 2024" names its season.
        and bare_year_season is None
        and not bare_year_span
        and explicit_single_season is None
        and explicit_range_start is None
        and explicit_range_end is None
        and start_date is None
        and end_date is None
    ):
        pre_streak_scope = (season, start_season, end_season)
        default_end = default_season_for_context(season_type)
        end_year = int(default_end.split("-")[0])
        start_year = end_year - 2
        season = None
        start_season = f"{start_year}-{str(start_year + 1)[-2:]}"
        end_season = default_end
        streak_default_window = True
    else:
        streak_default_window = False
        pre_streak_scope = None

    return {
        "normalized_query": q,
        "season": season,
        "start_season": start_season,
        "end_season": end_season,
        "explicit_relative_season": explicit_relative_season,
        "season_defaulted": season_defaulted and not names_current_season(q),
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
        "window_defaulted": window_defaulted,
        "bare_year_season": bare_year_season,
        "series_situation": series_situation,
        "series_comeback": series_comeback,
        "series_situation_career": series_situation_career,
        "single_season_intent": bool(_SINGLE_SEASON.search(q)),
        "playoff_round_unnamed_span": playoff_round_unnamed_span,
        "stretch_worst": stretch_worst,
        "stretch_player_group": stretch_player_group,
        "stretch_opponent_description": stretch_opponent_description,
        "stretch_metric": stretch_metric,
        "stretch_display_mode": stretch_display_mode,
        "team_rolling_stretch_boundary": team_rolling_stretch_boundary,
        "team_stretch_request": team_stretch_request,
        "stretch_names_players": stretch_names_players,
        "rookie_leaderboard_boundary": rookie_leaderboard_boundary,
        "sophomore_leaderboard_boundary": sophomore_leaderboard_boundary,
        # Only meaningful for a team-scoped leader; a league-wide "top scorers"
        # query carries no team and must stay equivalent to "points leaders".
        "team_leader_stat": team_leader_stat if team else None,
        "subjective_best_player": subjective_best_player,
        "multi_player_aggregate": multi_player_aggregate,
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
        "last_n_scope": detect_last_n_scope(q, threshold_conditions) if last_n else None,
        "min_games": min_games,
        "min_attempts": min_attempts,
        "top_n": top_n,
        "game_top_n": extract_top_n_games(q),
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
        "pre_streak_scope": pre_streak_scope,
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
        "playoff_history_intent": playoff_history_intent
        or bool(team and not player and not player_a and detect_how_did_playoffs(q)),
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


def _complete_threshold_conditions(
    threshold_conditions: list[dict], compound_conditions: list[dict] | None
) -> list[dict]:
    """Add list conditions the operator-led threshold scan missed."""
    compound = list(compound_conditions or [])
    # With no operator-led conditions at all, routes already read the list.
    if not threshold_conditions or len(compound) <= len(threshold_conditions):
        return threshold_conditions
    by_stat = {c["stat"]: c for c in threshold_conditions}
    if not set(by_stat) <= {c.get("stat") for c in compound}:
        return threshold_conditions
    completed = []
    for cond in compound:
        existing = by_stat.get(cond.get("stat"))
        if existing is not None:
            completed.append(existing)
            continue
        completed.append(
            {
                "stat": cond["stat"],
                "min_value": cond.get("min_value"),
                "max_value": cond.get("max_value"),
                "text": cond.get("text") or cond["stat"],
            }
        )
    return completed


def _conditions_for_route(parsed: dict, route: str, route_kwargs: dict) -> list[dict]:
    """Return canonical condition-list filters consumed by the selected route."""
    route_conditions = normalize_stat_conditions(route_kwargs.get("conditions"))
    if route_conditions:
        return route_conditions

    # Summaries and records take the list too: "LeBron summary with 30 points
    # and 10 rebounds" counted only the 10-rebound games.
    if route in {
        "player_game_finder",
        "game_finder",
        "player_game_summary",
        "game_summary",
        "team_record",
        "player_split_summary",
        "team_split_summary",
    }:
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


def _ranks_lower_is_better(stat: str | None) -> bool:
    """True for a lower-is-better metric, in either total or per-game form.

    "best total turnover teams" ranks ``tov_total``; it is still turnovers, so
    "best" still means fewest.
    """
    if not stat:
        return False
    base = stat.removesuffix("_total").removesuffix("_per_game")
    return bool({stat, base, f"{base}_per_game"} & LOWER_IS_BETTER_STATS)


def _is_aggregation_sibling(ranked: str | None, detected: str | None) -> bool:
    """True when *ranked* is *detected* in an explicit total/per-game form."""
    if not ranked or not detected or ranked == detected:
        return False
    return ranked in (f"{detected}_total", f"{detected}_per_game")


def _route_parsed_query(parsed: dict) -> dict:
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
    min_games = parsed.get("min_games")
    top_n = parsed.get("top_n")
    game_top_n = parsed.get("game_top_n")
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
    # "Lakers top 5 team rebounding games" lists the Lakers' games.
    top_team_game_intent = parsed.get("top_team_game_intent", False) and not parsed.get("team")
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
    team_stretch_request = parsed.get("team_stretch_request")
    stretch_names_players = parsed.get("stretch_names_players", False)
    # "Lakers vs Celtics best 10 game stretch": the teams joined by vs, each on
    # its own games. Any other team named must be an opponent, and wording about
    # the games they played each other is a head-to-head stretch instead.
    versus_teams = (team_stretch_request or {}).get("versus", [])
    versus_pair = bool(
        team_stretch_request is not None
        and len(versus_teams) >= 2
        and not head_to_head
        and not team_stretch_request.get("meeting")
        and set(team_stretch_request.get("versus_others", []))
        <= set(team_stretch_request.get("versus_opponents", []))
        # "Lakers vs Celtics and Knicks": the Celtics are also in an opponent
        # list, so the wording does not say who is ranked.
        and not set(versus_teams) & set(team_stretch_request.get("opponents", []))
    )
    if versus_pair and opponent_quality is None:
        opponent_quality = team_stretch_request.get("opponent_quality")
    rookie_leaderboard_boundary = parsed.get("rookie_leaderboard_boundary", False)
    sophomore_leaderboard_boundary = parsed.get("sophomore_leaderboard_boundary", False)
    team_leader_stat = parsed.get("team_leader_stat")
    subjective_best_player = parsed.get("subjective_best_player", False)
    multi_player_aggregate = parsed.get("multi_player_aggregate", False)
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
    supported_opponent_division_record_scope = bool(opponent_division) and not any(
        [
            with_player,
            without_player,
            unresolved_with_player,
            unresolved_without_player,
        ]
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
        and not parsed.get("bare_year_season")
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
        occ_max = occurrence_event.get("max_value")
        if stat is None and occ_stat:
            stat = occ_stat
            if max_value is None and occ_max is not None:
                max_value = occ_max
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

    # Generic semantic/product boundaries must fail before route inference can
    # turn them into plausible player, finder, or leaderboard answers. Keep the
    # dedicated team-record availability boundary more specific than the
    # generic "both play" phrase guard.
    generic_boundary_note = _unsupported_phrase_boundary_note(q)
    dedicated_availability_boundary = bool(
        "both play" in q and team and team_record_availability_intent
    )
    if generic_boundary_note and not dedicated_availability_boundary:
        out = dict(parsed)
        out["route"] = None
        out["route_kwargs"] = _unsupported_route_kwargs(
            "unsupported_concept",
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
            stat=stat,
        )
        out["intent"] = "unsupported"
        out["notes"] = [generic_boundary_note]
        out["confidence"] = compute_parse_confidence(out)
        out["alternates"] = generate_alternates(out)
        return out

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

    if invalid_date := invalid_explicit_date(q):
        out = dict(parsed)
        out["route"] = None
        out["route_kwargs"] = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "unsupported_filters": ["invalid_date"],
        }
        out["intent"] = "unsupported"
        out["notes"] = [
            f"invalid_date: {invalid_date} is not a calendar date; "
            "no reduced version of the question was answered"
        ]
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

    player_ring_question = (
        championship_count_boundary
        and _PLAYER_RING_WORDS.search(q)
        and not team
        and not (player_a or player_b or team_a or team_b)
        and not _NOT_A_RING.search(q)
        and not _TITLE_NOT_A_COUNT.search(q)
        and not _TITLE_EXTRA_CONDITION.search(q)
        and not _title_year_left_unused(q)
        and not (with_player or without_player)
        and not _ring_question_has_qualifier(q, player)
        and not any(
            parsed.get(key)
            for key in (
                "opponent",
                "opponent_quality",
                "opponent_player",
                "opponent_conference",
                "opponent_division",
                "home_only",
                "away_only",
                "stat",
                "min_value",
                "max_value",
                "threshold_conditions",
            )
        )
        and not unresolved_without_player
        and not (
            unresolved_with_player
            and not re.match(r"(?:the\s+)?most\b", str(unresolved_with_player))
        )
    )
    if player_ring_question and (player or _PLAYER_RING_BOARD.search(q)):
        # "how many rings does LeBron have": titles won with the team he played for.
        named_season = (
            extract_season(q)
            or parsed.get("explicit_relative_season")
            or re.search(r"\b(?:this|current|last|previous)\s+season\b", q)
        )
        notes = []
        if not start_season and not end_season and not named_season:
            from nbatools.commands._seasons import resolve_career

            season = None
            start_season, end_season = resolve_career("Playoffs")
            notes.append("default: every playoff season since 1996-97")
        out = dict(parsed)
        out.update(season=season, start_season=start_season, end_season=end_season)
        # The ring board already answers "how many": keep its title seasons.
        out["count_intent"] = False
        out["route"] = "playoff_appearances"
        out["route_kwargs"] = {
            "player": player,
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "titles": True,
            "player_titles": not player,
            "limit": top_n or 10,
        }
        out["intent"] = "summary" if player else "leaderboard"
        out["notes"] = notes
        out["confidence"] = compute_parse_confidence(out)
        out["alternates"] = generate_alternates(out)
        return out

    if (
        (player or player_a or player_b)
        and parsed.get("playoff_round_filter")
        # Player appearance counts have their own typed boundary.
        and not re.search(r"\bappearances?\b|\bpicks?\b|\bdraft(?:ed)?\b", q)
    ):
        # Player rows carry no playoff round, so "LeBron 2016 finals" must not
        # answer with the whole postseason.
        out = dict(parsed)
        out["route"] = None
        out["route_kwargs"] = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "unsupported_filters": ["player_playoff_round"],
        }
        out["intent"] = "unsupported"
        out["notes"] = [
            "unsupported_boundary: player stats by playoff round (Finals, conference "
            "finals, first or second round) are not supported yet; ask for the whole "
            "playoffs instead"
        ]
        out["confidence"] = compute_parse_confidence(out)
        out["alternates"] = generate_alternates(out)
        return out

    if (
        championship_count_boundary
        and team
        and not player
        and not player_a
        and not player_b
        and not team_a
        and not team_b
        and _TEAM_TITLE_COUNT.search(q)
        and not _NON_LEAGUE_TITLE.search(q)
        and not _TITLE_NOT_A_COUNT.search(q)
        and not _TITLE_EXTRA_CONDITION.search(q)
        and not _title_year_left_unused(q)
        and not (with_player or without_player)
        and not (unresolved_with_player or unresolved_without_player)
    ):
        # A team title is a Finals series won: "Lakers titles since 2000".
        last_years = re.search(r"\b(?:last|past)\s+(\d+)\s+years?\b", q)
        if last_years and not start_season and int(last_years.group(1)) > 0:
            from nbatools.commands._seasons import resolve_last_n_seasons

            season = None
            start_season, end_season = resolve_last_n_seasons(int(last_years.group(1)), "Playoffs")
        named_season = (
            extract_season(q)
            or parsed.get("explicit_relative_season")
            or re.search(r"\b(?:this|current|last|previous)\s+season\b", q)
        )
        if not (season or start_season or end_season) and re.search(
            r"\b(?:this|current)\s+season\b", q
        ):
            from nbatools.commands._seasons import default_end_season

            season = default_end_season("Playoffs")
        if not start_season and not end_season and not named_season:
            # "Lakers titles" counts every season, not the default one.
            from nbatools.commands._seasons import resolve_career

            season = None
            start_season, end_season = resolve_career("Playoffs")
        out = dict(parsed)
        out.update(season=season, start_season=start_season, end_season=end_season)
        out["route"] = "playoff_history"
        out["route_kwargs"] = {
            "team": team,
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "opponent": opponent,
        }
        out["intent"] = "summary"
        out["confidence"] = compute_parse_confidence(out)
        out["alternates"] = generate_alternates(out)
        return out

    if (
        championship_count_boundary
        and not team
        and not player
        and not player_a
        and not player_b
        and not team_a
        and not team_b
        and _TEAM_TITLE_COUNT.search(q)
        and _LEAGUE_TITLE_WORDING.search(q)
        and not re.search(r"\bplayers?\b", q)
        and not _NON_LEAGUE_TITLE.search(q)
        and not _TITLE_NOT_A_COUNT.search(q)
        and not _TITLE_EXTRA_CONDITION.search(q)
        and not _title_year_left_unused(q)
        and not (with_player or without_player)
        and not (
            (unresolved_with_player and not re.match(r"(?:the\s+)?most\b", unresolved_with_player))
            or unresolved_without_player
        )
    ):
        # "which team has won the most titles since 2000" / "who won the 2016 title"
        last_years = re.search(r"\b(?:last|past)\s+(\d+)\s+years?\b", q)
        if last_years and not start_season and int(last_years.group(1)) > 0:
            from nbatools.commands._seasons import resolve_last_n_seasons

            season = None
            start_season, end_season = resolve_last_n_seasons(int(last_years.group(1)), "Playoffs")
        named_season = (
            extract_season(q)
            or parsed.get("explicit_relative_season")
            or re.search(r"\b(?:this|current|last|previous)\s+season\b", q)
        )
        if not (season or start_season or end_season) and re.search(
            r"\b(?:this|current)\s+season\b", q
        ):
            from nbatools.commands._seasons import default_end_season

            season = default_end_season("Playoffs")
        if not start_season and not end_season and not named_season:
            from nbatools.commands._seasons import resolve_career

            season = None
            start_season, end_season = resolve_career("Playoffs")
        out = dict(parsed)
        out.update(season=season, start_season=start_season, end_season=end_season)
        out["route"] = "playoff_appearances"
        out["route_kwargs"] = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "playoff_round": "04",
            "titles": True,
            # Every title winner unless a top N is asked: 11 franchises won since 2010.
            "limit": top_n or 30,
        }
        out["intent"] = "leaderboard"
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

    if multi_player_aggregate:
        out = dict(parsed)
        out["route"] = None
        out["route_kwargs"] = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "unsupported_filters": ["multi_player_aggregate"],
        }
        out["intent"] = "unsupported"
        out["notes"] = [
            "unsupported_boundary: combined totals across two players are not "
            "supported; ask for each player separately or use a comparison"
        ]
        out["confidence"] = compute_parse_confidence(out)
        out["alternates"] = generate_alternates(out)
        return out

    # Subjective "best player" with no objective metric — refuse rather than
    # answer with a game list. "best scorer / rebounder" is objective and is
    # handled by the team-leader and leaderboard routes, not here.
    if subjective_best_player and team_leader_stat is None:
        out = dict(parsed)
        out["route"] = None
        out["route_kwargs"] = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "unsupported_filters": ["subjective_query"],
        }
        out["intent"] = "unsupported"
        out["notes"] = [
            "unsupported_boundary: 'best player' is subjective; ask for a "
            "specific stat leader such as 'Lakers leading scorer'"
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
    elif unresolved_compare_operand := _unresolved_player_comparison_boundary(parsed):
        route = "player_compare"
        notes.append(
            "unsupported_boundary: a player-vs-player comparison was requested "
            f"but the second player ('{unresolved_compare_operand}') could not be "
            "identified; no single-player answer was substituted"
        )
        route_kwargs = _unsupported_route_kwargs(
            "unresolved_player",
            season=season or default_season_for_context(season_type),
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
        )
        route_kwargs["unresolved_player_fragment"] = unresolved_compare_operand
    elif _player_team_comparison(parsed):
        route = "player_compare"
        notes.append(
            "unsupported_boundary: comparing a player with a team is ambiguous; "
            "no single-player answer was substituted"
        )
        route_kwargs = _unsupported_route_kwargs(
            "player_team_comparison",
            season=season or default_season_for_context(season_type),
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
        )
    elif (lineup_route := try_lineup_on_off_route(parsed)) is not None:
        route, route_kwargs = lineup_route
    elif window_size is not None and parsed.get("stretch_opponent_description"):
        # "best stretch against the worst defenses": no filter reads that
        # description, so refuse rather than rank stretches against everyone.
        team_scope = bool(team or team_a or team_b or team_rolling_stretch_boundary) and not (
            player or stretch_names_players
        )
        route = "team_stretch_leaderboard" if team_scope else "player_stretch_leaderboard"
        notes.append(
            f"unsupported_boundary: the opponent description "
            f"'{parsed['stretch_opponent_description']}' is not a supported filter; "
            "no unfiltered stretch ranking was substituted"
        )
        route_kwargs = _unsupported_route_kwargs(
            "opponent_description",
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
        )
    elif (
        team_stretch_request is not None
        and window_size is not None
        and not player
        and not player_a
        and not player_b
        # "compare the Lakers and Celtics 10 game stretches" names both teams, and
        # so does "Lakers vs Celtics best 10 game stretch".
        and (
            not (team_a or team_b)
            or len(team_stretch_request.get("subjects", [])) >= 2
            or versus_pair
        )
        and (
            team_rolling_stretch_boundary
            or (
                (team or len(team_stretch_request.get("subjects", [])) >= 2 or versus_pair)
                and not stretch_names_players
            )
        )
    ):
        route = "team_stretch_leaderboard"
        stretch_opponent = team_stretch_request.get("opponents") or opponent
        if versus_pair and team_stretch_request.get("versus_opponents"):
            # "Lakers vs Celtics best stretch vs Knicks": the Knicks are the opponent.
            versus_opponents = team_stretch_request["versus_opponents"]
            stretch_opponent = (
                versus_opponents[0] if len(versus_opponents) == 1 else versus_opponents
            )
        opponents = (
            {stretch_opponent} if isinstance(stretch_opponent, str) else set(stretch_opponent or [])
        )
        subject_teams = [
            abbr for abbr in team_stretch_request.get("subjects", []) if abbr not in opponents
        ]
        if len(subject_teams) < 2 and versus_pair:
            subject_teams = list(versus_teams)
        stretch_team = team
        if team in opponents:
            # "Lakers best stretch vs Celtics, Knicks and Heat": the subject is the
            # team named before the opponent list, else the whole league.
            leads = [abbr for abbr in team_stretch_request.get("lead", []) if abbr not in opponents]
            stretch_team = leads[0] if leads else None
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            # "Lakers and Celtics best 5 game stretch" ranks both teams' best runs.
            "team": stretch_team if len(subject_teams) < 2 else None,
            "teams": subject_teams if len(subject_teams) >= 2 else None,
            "opponent": stretch_opponent,
            "home_only": home_only,
            "away_only": away_only,
            "last_n": last_n,
            "window_size": window_size,
            "stretch_metric": team_stretch_request["metric"],
            "worst": team_stretch_request["worst"],
            "limit": top_n or 10,
        }
    elif (
        team_stretch_request is not None
        and window_size is not None
        and team_a
        and team_b
        and (head_to_head or team_stretch_request.get("meeting"))
        and not player
    ):
        # "Lakers vs Celtics head to head best 10 game stretch": a stretch inside
        # their meetings is not built; refuse rather than compare whole seasons.
        route = "team_stretch_leaderboard"
        notes.append(
            "unsupported_boundary: rolling stretches within head-to-head games are not "
            "supported yet; ask for each team's best stretch or their head-to-head record"
        )
        route_kwargs = _unsupported_route_kwargs(
            "head_to_head_stretch",
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
        )
    elif (
        window_size is not None
        and stretch_names_players
        and not player
        and (len((team_stretch_request or {}).get("subjects", [])) >= 2 or (team_a and team_b))
    ):
        # "which Lakers and Celtics player": one team per player ranking, so refuse
        # rather than rank one team's players.
        route = "player_stretch_leaderboard"
        route_kwargs = _unsupported_route_kwargs(
            "multi_team_player_stretch",
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
            window_size=window_size,
            stretch_metric=stretch_metric,
            limit=top_n or 10,
        )
    elif (
        window_size is not None
        and stretch_metric is not None
        and not player_a
        and not player_b
        and not team_a
        and not team_b
        and not (team and player is None and not stretch_names_players)
        and parsed.get("stretch_player_group")
        and not player
    ):
        # "best stretch by a rookie": the stretch ranking cannot narrow to a
        # player group, so refuse rather than rank every player.
        route = "player_stretch_leaderboard"
        notes.append(
            f"unsupported_boundary: stretches limited to {parsed['stretch_player_group']} "
            "are not supported yet; no all-player ranking was substituted"
        )
        route_kwargs = _unsupported_route_kwargs(
            "player_group_stretch",
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
            window_size=window_size,
            stretch_metric=stretch_metric,
            limit=top_n or 10,
        )
    elif (
        window_size is not None
        and stretch_metric is not None
        and not player_a
        and not player_b
        and not team_a
        and not team_b
        and not (team and player is None and not stretch_names_players)
    ):
        route = "player_stretch_leaderboard"
        route_kwargs = {
            "worst": bool(parsed.get("stretch_worst")),
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
        season_high_intent
        and top_team_game_intent
        and not player
        and not player_a
        and not player_b
        and not (
            _rank_elig := assess_leaderboard_request(parsed, ranking_mode=SINGLE_GAME_RANKING)
        ).authorized
    ):
        # Ranked team games still need a named metric: "best team performances"
        # says which games to look at, not what makes one best.
        route = "top_team_games"
        route_kwargs, _note = _ranking_refusal_kwargs(
            _rank_elig,
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
        )
        notes.append(_note)
    elif (
        season_high_intent and top_team_game_intent and not player and not player_a and not player_b
    ):
        route = "top_team_games"
        route_kwargs = {
            **_top_games_span(season, start_season, end_season, season_type),
            # Non-None: the eligibility guard above refuses an unanchored request.
            "stat": anchored_leaderboard_metric(parsed),
            "limit": game_top_n or 10,
            "season_type": season_type,
            # "fewest points by a team in a game" ranks from the bottom.
            "ascending": bool(_FEWEST_WORDS.search(q)),
            "start_date": start_date,
            "end_date": end_date,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "last_n": last_n,
            "opponent": opponent,
        }
        notes.append(
            "default: top team games ranked by " + str(anchored_leaderboard_metric(parsed))
        )
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
            # "<player> season high" is a documented shorthand for the player's
            # best scoring game, listed in the query catalog and guide. Points
            # here is the request, not a substitute for one.
            "stat": stat or SCORING_SHORTHAND,
            "min_value": min_value,
            "max_value": max_value,
            "limit": game_top_n or 5,
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
        and not (
            _rank_elig := assess_leaderboard_request(parsed, ranking_mode=SINGLE_GAME_RANKING)
        ).authorized
    ):
        route = "top_player_games"
        route_kwargs, _note = _ranking_refusal_kwargs(
            _rank_elig,
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
        )
        notes.append(_note)
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
            **_top_games_span(season, start_season, end_season, season_type),
            # Non-None: the eligibility guard above refuses an unanchored request.
            "stat": anchored_leaderboard_metric(parsed),
            "limit": game_top_n or 10,
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
    elif distinct_player_count and (
        occurrence_event
        or (stat and (min_value is not None or max_value is not None))
        or len(parsed.get("compound_occurrence_conditions") or []) >= 2
    ):
        # "How many players have had a 40 point game this season?"
        # "How many players scored 40 points this season?"
        route = "player_occurrence_leaders"
        from nbatools.commands._seasons import default_end_season

        special_event = (
            occurrence_event.get("special_event") if isinstance(occurrence_event, dict) else None
        )
        compound_conditions = list(parsed.get("compound_occurrence_conditions") or [])
        compound = len(compound_conditions) >= 2
        route_kwargs = {
            # "this season" carries no explicit season of its own.
            "season": season
            or (None if start_season or end_season else default_end_season(season_type)),
            "start_season": start_season,
            "end_season": end_season,
            "season_type": season_type,
            "stat": None if special_event or compound else stat,
            "min_value": None if special_event or compound else min_value,
            "max_value": None if special_event or compound else max_value,
            "special_event": special_event,
            "occurrence_event": occurrence_event,
            # "how many players had 30 points and 10 rebounds": every condition
            # must hold in the same game.
            "conditions": compound_conditions if compound else None,
            "limit": None,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "start_date": start_date,
            "end_date": end_date,
            "opponent": opponent,
            # "how many players had 30 off the bench" counts bench games only.
            "role": detect_role(q),
            "min_occurrences": extract_min_occurrences(q),
        }
        # Metadata (the Role chip and the count headline) reads parsed.
        parsed["role"] = route_kwargs["role"]
        parsed["min_occurrences"] = route_kwargs["min_occurrences"]
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
            "current": bool(team_streak_request.get("current")),
            "limit": 25,
            "conditions": team_streak_request.get("conditions"),
        }
        _fires, _note = streak_default_window(parsed)
        if _fires:
            notes.append(_note)
    # ---------------------------------------------------------------------------
    # Playoff / record / decade routing cluster
    # ---------------------------------------------------------------------------
    elif (ppr := try_playoff_record_route(parsed)) is not None:
        route, route_kwargs = ppr
        if route == "playoff_matchup_history" and route_kwargs.get("start_season"):
            # The pair's whole playoff history ran, not the latest postseason.
            notes[:] = [n for n in notes if not n.startswith("no season specified: defaulted")]
            # Metadata (the season chip) reads these, so publish the window run.
            parsed["season"] = None
            parsed["start_season"] = route_kwargs["start_season"]
            parsed["end_season"] = route_kwargs["end_season"]
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
        # Refusal path: carry whatever stat the query named, never a stand-in.
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
            "stat": stat,
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
        # The split divides the same sample the player summary describes, so
        # every summary filter travels with it (the split axis is dropped by
        # the route itself).
        route_kwargs = {
            "split": split_type,
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
            "special_event": special_event,
        }
    elif split_type and team and not team_a and not team_b:
        route = "team_split_summary"
        route_kwargs = {
            "split": split_type,
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
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
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
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
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
    elif team_a and team_b and record_intent and not _joined_team_pair(parsed):
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
            "head_to_head": head_to_head or _team_vs_team_meetings(parsed),
            "stat": stat,
            "min_value": min_value,
            "max_value": max_value,
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
            "current": bool(streak_request.get("current")),
            "limit": 25,
        }
        if streak_request.get("conditions"):
            route_kwargs["conditions"] = streak_request["conditions"]
        _fires, _note = streak_default_window(parsed)
        if _fires:
            notes.append(_note)
    elif (league_streak := try_league_streak_route(parsed)) is not None:
        route, route_kwargs = league_streak
        _fires, _note = streak_default_window(parsed)
        if _fires:
            notes.append(_note.replace("team streak", "league streak ranking"))
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
        # The condition already requires "scoring" or an explicit stat, so the
        # metric below is the one the query named, not a stand-in for none.
        route = "top_player_games"
        route_kwargs = {
            **_top_games_span(season, start_season, end_season, season_type),
            # Non-None: the eligibility guard above refuses an unanchored request.
            "stat": anchored_leaderboard_metric(parsed),
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
        notes.append("default: top games ranked by " + str(stat or SCORING_SHORTHAND))
    elif (
        top_team_game_intent
        and not player
        and not player_a
        and not player_b
        and not (
            _rank_elig := assess_leaderboard_request(parsed, ranking_mode=SINGLE_GAME_RANKING)
        ).authorized
    ):
        route = "top_team_games"
        route_kwargs, _note = _ranking_refusal_kwargs(
            _rank_elig,
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
        )
        notes.append(_note)
    elif top_team_game_intent and not player and not player_a and not player_b:
        # Expanded trigger: catches "highest-scoring team games", "best team
        # performances", "biggest team scoring nights" in addition to the
        # literal "top team" / "top ... team games" phrasings.
        route = "top_team_games"
        route_kwargs = {
            **_top_games_span(season, start_season, end_season, season_type),
            # Non-None: the eligibility guard above refuses an unanchored request.
            "stat": anchored_leaderboard_metric(parsed),
            "limit": top_n or 10,
            "season_type": season_type,
            # "fewest points by a team in a game" ranks from the bottom.
            "ascending": bool(_FEWEST_WORDS.search(q)),
            "start_date": start_date,
            "end_date": end_date,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "last_n": last_n,
            "opponent": opponent,
        }
        notes.append(
            "default: top team games ranked by " + str(anchored_leaderboard_metric(parsed))
        )
    # ---------------------------------------------------------------------------
    # Occurrence routing cluster (compound + single leaderboard)
    # ---------------------------------------------------------------------------
    elif (ocr := try_compound_occurrence_route(parsed)) is not None:
        route, route_kwargs = ocr
        # "most triple doubles off the bench": the leaderboard counts only games
        # in that role (dropping it ranked every game).
        occurrence_role = (
            _league_occurrence_role(q)
            if route == "player_occurrence_leaders"
            and not route_kwargs.get("role")
            and not route_kwargs.get("player")
            else None
        )
        if occurrence_role:
            route_kwargs["role"] = occurrence_role
            parsed["role"] = occurrence_role
            notes.append(
                f"role_leaderboard: filtered to {occurrence_role} games using trusted "
                "starter-role data"
            )
    elif (lgf := try_league_game_finder_route(parsed)) is not None:
        route, route_kwargs = lgf
    # ---------------------------------------------------------------------------
    # Record-leaderboard routing cluster
    # ---------------------------------------------------------------------------
    elif (rlr := try_record_leaderboard_route(parsed)) is not None:
        route, route_kwargs, rl_notes = rlr
        notes.extend(rl_notes)
    elif (
        team_leader_stat is not None
        and team
        and not player
        and not player_a
        and not player_b
        and not team_a
        and not team_b
        and not (
            _team_elig := assess_leaderboard_request(parsed, metric=team_leader_stat)
        ).authorized
    ):
        # Same rule as the league-wide gate, on the route that would otherwise
        # answer. "Lakers record without their leading scorer" anchors a metric
        # through "leading scorer", but the record intent and the availability
        # clause are things this ranking cannot express - returning the team's
        # top five scorers answers a different question.
        route = "season_leaders"
        route_kwargs, _note = _ranking_refusal_kwargs(
            _team_elig,
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
            team=team,
        )
        notes.append(_note)
    elif (
        team_leader_stat is not None
        and team
        and not player
        and not player_a
        and not player_b
        and not team_a
        and not team_b
    ):
        # Team-scoped player leader ("Lakers leading scorer"): the team's
        # top players for the stat, leader first.
        route = "season_leaders"
        notes.append(f"team_scoped_leader: top {team} players ranked by the requested stat")
        route_kwargs = {
            "season": season or default_season_for_context(season_type),
            "stat": team_leader_stat,
            "limit": top_n or 5,
            "season_type": season_type,
            "min_games": min_games or 1,
            "ascending": team_leader_stat in LOWER_IS_BETTER_STATS,
            "start_date": start_date,
            "end_date": end_date,
            "start_season": start_season,
            "end_season": end_season,
            "team": team,
            "last_n": last_n,
        }
    elif (
        sophomore_leaderboard_boundary
        and not any([player, player_a, player_b, team, team_a, team_b])
        and not (_rank_elig := assess_leaderboard_request(parsed)).authorized
    ):
        # A specialized population says who to rank, never what to rank
        # them by. This branch used to end its metric resolution in
        # `or "pts"`, so "sophomore leaders" ranked by points
        # nobody asked for. Same decision as every other ranking branch.
        route = "season_leaders"
        route_kwargs, _note = _ranking_refusal_kwargs(
            _rank_elig,
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
        )
        notes.append(_note)
    elif sophomore_leaderboard_boundary and not any(
        [player, player_a, player_b, team, team_a, team_b]
    ):
        # Sophomore leaderboards: roster experience_years == 1 per season.
        route = "season_leaders"
        notes.append(
            "sophomore_leaderboard: filtered to players with 1 year of "
            "roster experience in each season"
        )
        route_kwargs = {
            "season": season or default_season_for_context(season_type),
            "stat": season_leaderboard_stat(parsed),
            "limit": top_n or 10,
            "season_type": season_type,
            "min_games": min_games or 1,
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
            "sophomores_only": True,
        }
    elif (
        rookie_leaderboard_boundary
        and not any([player, player_a, player_b, team, team_a, team_b])
        and not (_rank_elig := assess_leaderboard_request(parsed)).authorized
    ):
        # A specialized population says who to rank, never what to rank
        # them by. This branch used to end its metric resolution in
        # `or "pts"`, so "rookie leaders" ranked by points
        # nobody asked for. Same decision as every other ranking branch.
        route = "season_leaders"
        route_kwargs, _note = _ranking_refusal_kwargs(
            _rank_elig,
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
        )
        notes.append(_note)
    elif rookie_leaderboard_boundary and not any(
        [player, player_a, player_b, team, team_a, team_b]
    ):
        # Rookie leaderboards: roster experience_years == 0 per season.
        route = "season_leaders"
        notes.append(
            "rookie_leaderboard: filtered to players with 0 years of "
            "roster experience in each season"
        )
        route_kwargs = {
            "season": season or default_season_for_context(season_type),
            "stat": season_leaderboard_stat(parsed),
            "limit": top_n or 10,
            "season_type": season_type,
            "min_games": min_games or 1,
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
            "rookies_only": True,
        }
    elif (
        role_leaderboard_boundary
        and not any([player, player_a, player_b, team, team_a, team_b])
        and not (_rank_elig := assess_leaderboard_request(parsed)).authorized
    ):
        # A specialized population says who to rank, never what to rank
        # them by. This branch used to end its metric resolution in
        # `or "pts"`, so "starter leaders" ranked by points
        # nobody asked for. Same decision as every other ranking branch.
        route = "season_leaders"
        route_kwargs, _note = _ranking_refusal_kwargs(
            _rank_elig,
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
        )
        notes.append(_note)
    elif role_leaderboard_boundary and not any([player, player_a, player_b, team, team_a, team_b]):
        # Starter/bench leaderboards run against trusted per-game starter
        # flags; seasons without that coverage refuse inside the command.
        leaderboard_role = detect_role(q)
        route = "season_leaders"
        route_kwargs = {
            "season": season or default_season_for_context(season_type),
            "stat": season_leaderboard_stat(parsed),
            "limit": top_n or 10,
            "season_type": season_type,
            "min_games": min_games or 1,
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
        }
        if leaderboard_role is not None:
            notes.append(
                f"role_leaderboard: filtered to {leaderboard_role} games "
                f"using trusted starter-role data"
            )
            route_kwargs["role"] = leaderboard_role
        else:
            notes.append(
                "unsupported_boundary: starter/bench phrasing did not resolve to a role filter"
            )
            route_kwargs["unsupported_filters"] = ["role_leaderboard"]
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
    elif (
        _single_team_advanced_stat_summary_boundary(parsed)
        and not start_date
        and not end_date
        and not start_season
        and not end_season
        and not opponent
        and not (home_only or away_only or wins_only or losses_only)
        and last_n is None
    ):
        # Single-team season advanced-stat scalar ("wolves defensive
        # rating"): answer from the full team leaderboard so the value
        # arrives with its league rank.
        route = "season_team_leaders"
        notes.append(
            "single_team_advanced_stat: answered from the full team "
            "leaderboard with league rank context"
        )
        route_kwargs = {
            "season": season,
            "stat": stat,
            "limit": 30,
            "season_type": season_type,
            "min_games": min_games or 1,
            "ascending": stat in LOWER_IS_BETTER_STATS,
        }
    elif _single_team_advanced_stat_summary_boundary(parsed):
        route = "game_summary"
        notes.append(
            "unsupported_boundary: single-team advanced-stat summaries with "
            "date windows or game filters are not supported"
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
            **_top_games_span(season, start_season, end_season, season_type),
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
        and stat is not None
        and min_value is not None
        and not leaderboard_intent
        and not team_leaderboard_intent
        and not occurrence_event
        and re.search(r"^\s*(?:who|which\s+players?)\b", q)
    ):
        # League-wide threshold games: "who dropped 40 this week",
        # "who scored 40+ points this season" — list every qualifying
        # game, not a capped top-10.
        route = "top_player_games"
        route_kwargs = {
            **_top_games_span(season, start_season, end_season, season_type),
            "stat": stat,
            "limit": 100,
            "season_type": season_type,
            "ascending": False,
            "start_date": start_date,
            "end_date": end_date,
            "min_value": min_value,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "last_n": last_n,
            "opponent": opponent,
        }
        notes.append("league_threshold_games: listing all games at or above the threshold")
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
        # A bare context fragment: clutch or opponent-quality with nothing to
        # apply it to. This used to hand the leaderboard ``stat="pts"`` so the
        # route had something to rank, which invented a metric the question
        # never named - the same defect the eligibility gate below exists to
        # stop, reached by a branch that runs before it. Naming a stat would
        # not rescue these either: with no player, team, or population there is
        # no ranking request to complete, so the request is unclear rather than
        # merely metric-less.
        route = "season_leaders"
        route_kwargs = _unsupported_route_kwargs(
            LEADERBOARD_REQUEST_UNCLEAR,
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
        )
        notes.append(
            "unsupported_boundary: "
            f"{'clutch' if clutch else 'opponent-quality'} context was requested with "
            "no player, team, or stat to apply it to; no substituted leaderboard was "
            "returned"
        )
    elif (_lb := metric_only_leaderboard_default(parsed))[0] and not (
        _elig := assess_leaderboard_request(parsed)
    ).authorized:
        # A league-wide ranking was requested, and it is not one this product
        # can answer: either no metric was named, or the aggregation asked for
        # is not the one leaderboards compute, or part of the question is
        # outside the stat-shaped grammar. Ranking by points anyway would be a
        # confident answer to a different question.
        route = "season_team_leaders" if team_leaderboard_intent else "season_leaders"
        # No substituted ranking metric reaches the blocked route.
        route_kwargs, _note = _ranking_refusal_kwargs(
            _elig,
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
        )
        notes.append(_note)
    elif _lb[0]:
        # No subject entity → league-wide leaderboard default (spec §15.2),
        # reached only once the request is eligible.
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
            # Non-None: the eligibility gate above refuses an unanchored request.
            leaderboard_stat = season_leaderboard_stat(parsed)

            # Semantic ascending for lower-is-better stats
            if _ranks_lower_is_better(leaderboard_stat):
                if re.search(r"\b(best|top|lowest|fewest|least)\b", q):
                    lb_ascending = True
                elif re.search(r"\b(worst|most|highest)\b", q):
                    lb_ascending = False

            # Season-advanced-only team stats blocked in date-window/multi-season
            route = "season_team_leaders"
            route_kwargs = {
                "season": lb_season,
                "stat": leaderboard_stat,
                "limit": top_n or 10,
                "season_type": season_type,
                "min_games": min_games or 1,
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
            leaderboard_stat = season_leaderboard_stat(parsed)
            route = "season_team_leaders"
            route_kwargs = {
                "season": lb_season,
                "stat": leaderboard_stat,
                "limit": top_n or 10,
                "season_type": season_type,
                "min_games": min_games or 1,
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
            leaderboard_stat = season_leaderboard_stat(parsed)

            # Semantic ascending for lower-is-better stats
            if _ranks_lower_is_better(leaderboard_stat):
                if re.search(r"\b(best|top|lowest|fewest|least)\b", q):
                    lb_ascending = True
                elif re.search(r"\b(worst|most|highest)\b", q):
                    lb_ascending = False

            route = "season_leaders"
            route_kwargs = {
                "season": lb_season,
                "stat": leaderboard_stat,
                "limit": top_n or 10,
                "season_type": season_type,
                "min_games": min_games or 1,
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
            route_kwargs.update(_min_attempts_kwargs(parsed, leaderboard_stat))
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
        finder_limit = None if count_intent else (game_top_n or 25)
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
        finder_limit = None if count_intent else (game_top_n or 25)
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
            "limit": game_top_n or 25,
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
            "limit": game_top_n or 25,
            "sort_by": "stat" if stat else "game_date",
            "ascending": False,
            "last_n": last_n,
        }
        _fires, _note = team_threshold_finder_default(parsed)
        if _fires:
            notes.append(_note)
    elif (_unrouted_compound := unrouted_compound_event_reason(parsed)) is not None:
        # Two stated event conditions and nothing saying what to do with them.
        # Executing one reading of it invents the aggregation the question left
        # out; an unrouted error throws both conditions away. Refuse holding
        # them.
        _compound_unrouted = CompoundEventAuthorization(
            authorized=False,
            reason=_unrouted_compound,
            requested_event_conditions=declared_event_conditions(parsed),
        )
        route = "season_team_leaders" if re.search(r"\bteams?\b", q) else "season_leaders"
        route_kwargs = _unsupported_route_kwargs(
            _unrouted_compound,
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
        )
        _apply_compound_refusal_kwargs(route_kwargs, _compound_unrouted)
        notes.append(_compound_refusal_note(_compound_unrouted))
    elif (_unrouted_reason := unrouted_ranking_reason(parsed)) is not None:
        # A legible ranking request that matched no route: it names who to rank
        # but not what by, or names several stats. This used to surface as an
        # unrouted error, which tells the user nothing about what to change.
        route = "season_team_leaders" if re.search(r"\bteams?\b", q) else "season_leaders"
        route_kwargs, _note = _ranking_refusal_kwargs(
            LeaderboardEligibility(
                authorized=False,
                reason=_unrouted_reason,
                requested_metrics=requested_leaderboard_metrics(parsed),
            ),
            season=season,
            start_season=start_season,
            end_season=end_season,
            start_date=start_date,
            end_date=end_date,
            season_type=season_type,
        )
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
    if route_kwargs.get("role") is None:
        # Don't stomp a role set by a routing branch (league-wide
        # starter/bench leaderboards detect role without a player entity).
        route_kwargs["role"] = role
    route_kwargs["opponent_quality"] = opponent_quality
    route_kwargs["quarter"] = quarter
    route_kwargs["half"] = half
    _apply_route_conditions(parsed, route, route_kwargs)

    availability_markers = _player_availability_unsupported_markers(parsed, route)
    if availability_markers:
        # Record what the question asked for before clearing it. The applied
        # slot is cleared because nothing applied it; the request itself still
        # has to travel, or a refusal for an absence filter stops mentioning the
        # absence and reads as a refusal of the rest of the question.
        requested_availability = {
            marker: parsed.get(marker) for marker in availability_markers if parsed.get(marker)
        }
        if requested_availability:
            existing_availability = route_kwargs.get("unsupported_availability") or {}
            route_kwargs["unsupported_availability"] = {
                **existing_availability,
                **requested_availability,
            }
        parsed = dict(parsed)
        if "with_player" in availability_markers:
            parsed["with_player"] = None
        if "without_player" in availability_markers:
            parsed["without_player"] = None
        existing_unsupported = route_kwargs.get("unsupported_filters") or []
        if not isinstance(existing_unsupported, list):
            existing_unsupported = list(existing_unsupported)
        for marker in availability_markers:
            if marker not in existing_unsupported:
                existing_unsupported.append(marker)
        route_kwargs["unsupported_filters"] = existing_unsupported
        notes.append(
            "unsupported_boundary: whole-game teammate presence/absence filtering "
            "is only execution-backed for team records; no unfiltered fallback "
            "was returned for this route"
        )

    if (
        route == "team_record"
        and (route_kwargs.get("with_player") or route_kwargs.get("without_player"))
        and (route_kwargs.get("stat") == "minutes" or presence_states_player_condition(q))
    ):
        # A minutes bound or "plays and scores 30" next to a presence filter
        # is that player's own condition; team rows only carry team totals
        # (~240 minutes, the team's points), so applying it there answered a
        # different question. This happens when another player's clause keeps
        # "when X plays" as presence. Refuse instead.
        existing_unsupported = list(route_kwargs.get("unsupported_filters") or [])
        if "player_minutes_bound" not in existing_unsupported:
            existing_unsupported.append("player_minutes_bound")
        route_kwargs["unsupported_filters"] = existing_unsupported

    if (
        route in ("player_game_summary", "player_game_finder")
        and route_kwargs.get("player")
        and names_other_player_availability(q, route_kwargs["player"])
    ):
        # "in games LeBron plays 35 minutes and Luka sits": the player route
        # reads only its own player, so the second clause would be dropped.
        existing_unsupported = list(route_kwargs.get("unsupported_filters") or [])
        if "multi_player_availability" not in existing_unsupported:
            existing_unsupported.append("multi_player_availability")
        route_kwargs["unsupported_filters"] = existing_unsupported

    if route == "team_record" and last_n is not None and route_kwargs.get("last_n") is None:
        # Every team_record branch selects the same game log, so the last-N
        # window applies to all of them rather than to each kwargs literal.
        route_kwargs["last_n"] = last_n

    if route_kwargs.get("last_n") is not None and route in _LAST_N_WINDOW_ROUTES:
        # "30 point games in his last 10" measures conditions inside the time
        # window; "last 10 games where he scored 30" counts qualifying games.
        route_kwargs["last_n_scope"] = parsed.get("last_n_scope") or "qualifying"
        if (
            parsed.get("season_defaulted")
            and route_kwargs.get("season") == parsed.get("season")
            and not route_kwargs.get("start_season")
            and not route_kwargs.get("start_date")
            and not route_kwargs.get("end_date")
        ):
            # No season was named, so "last 10 games" means the 10 most
            # recent games even when the current season has fewer.
            route_kwargs.update(last_n_reach_back_seasons(route_kwargs["season"]))

    if (
        route == "team_compare"
        and route_kwargs.get("last_n")
        and parsed.get("season_defaulted")
        and route_kwargs.get("season") == parsed.get("season")
        and not route_kwargs.get("start_season")
        and not route_kwargs.get("start_date")
        and not route_kwargs.get("end_date")
    ):
        # "Lakers vs Warriors last 10 games" means their 10 most recent
        # meetings. Regular-season teams meet at least twice a season (bar the
        # 1998-99 and 2011-12 lockouts), so reach back that far plus a margin;
        # playoff meetings are rare, so search every season.
        # Filters that thin the games (an opponent, a conference or division,
        # a quality bar, home/away) need proportionally more seasons.
        seasons_back = _team_compare_reach_back(route_kwargs, parsed)
        route_kwargs.update(
            last_n_reach_back_seasons(route_kwargs["season"], seasons_back=seasons_back)
        )
        _start_reach_back_at_served_data(route_kwargs)

    if route == "season_leaders" and route_kwargs.get("team"):
        # "Lakers and Celtics leading scorers": rank both rosters, not just
        # the last team named.
        from nbatools.commands._matchup_utils import (
            _extract_compare_and_teams,
            strip_matchup_noise,
        )

        pair = _extract_compare_and_teams(strip_matchup_noise(parsed["normalized_query"]))
        if all(pair) and route_kwargs["team"] in pair:
            route_kwargs["team"] = list(pair)

    if route in _OPPONENT_GROUP_ROUTES:
        # Conference/division opponents resolve season by season at
        # execution, on every route that filters games through the shared
        # opponent mask (see _natural_query_execution._OPPONENT_GROUP_ROUTES).
        already_blocked = set(route_kwargs.get("unsupported_filters") or [])
        for field in ("opponent_conference", "opponent_division"):
            if parsed.get(field) and field not in already_blocked:
                route_kwargs.setdefault(field, parsed[field])

    if parsed.get("opponent_conference_geography_boundary"):
        # "vs the West coast" / "vs the Pacific Northwest" is geography, not a
        # conference; refuse rather than answer for every opponent.
        blocked = list(route_kwargs.get("unsupported_filters") or [])
        if "opponent_conference" not in blocked:
            route_kwargs["unsupported_filters"] = [*blocked, "opponent_conference"]

    unexecuted_markers = _unexecuted_filter_markers(parsed, route, route_kwargs)
    if unexecuted_markers:
        parsed = dict(parsed)
        if "position_filter" in unexecuted_markers:
            parsed["position_filter"] = None
        if "last_n" in unexecuted_markers:
            parsed["last_n"] = None
        for marker in unexecuted_markers:
            if marker in _ROUTE_KWARG_BACKED_FILTERS:
                parsed[marker] = None
        existing_unsupported = route_kwargs.get("unsupported_filters") or []
        if not isinstance(existing_unsupported, list):
            existing_unsupported = list(existing_unsupported)
        for marker in unexecuted_markers:
            if marker not in existing_unsupported:
                existing_unsupported.append(marker)
        route_kwargs["unsupported_filters"] = existing_unsupported
        notes.append(
            "unsupported_boundary: this route parses "
            f"{', '.join(unexecuted_markers)} but has no execution path for it; "
            "no unfiltered fallback was returned"
        )

    # An "or fewer" / "at most" bound the parse or the route dropped refuses
    # rather than answering unfiltered.
    if not route_kwargs.get("unsupported_filters"):
        bound_boundary = upper_bound_boundary(
            parsed.get("normalized_query") or "",
            parsed.get("threshold_conditions") or [],
            route_kwargs,
        )
        if bound_boundary:
            route_kwargs["unsupported_filters"] = [bound_boundary]
            notes.append(
                "unsupported_boundary: an upper bound in the question was not "
                "applied; no unfiltered fallback was returned"
            )

    # Compound/event routing integrity. A route may answer only when it accounts
    # for every meaningful part of the request - executes it, is defined by it,
    # or refuses and says so. Runs last so it sees the kwargs that will actually
    # be executed rather than the parser's reading of them.
    compound_authorization = authorize_compound_event_route(parsed, route, route_kwargs)
    if not compound_authorization.authorized:
        existing_unsupported = route_kwargs.get("unsupported_filters") or []
        if not isinstance(existing_unsupported, list):
            existing_unsupported = list(existing_unsupported)
        # First, so the refusal is read as the compound-semantic one it is: a
        # broader boundary that also fired says less about what went wrong.
        route_kwargs["unsupported_filters"] = [
            compound_authorization.reason,
            *(f for f in existing_unsupported if f != compound_authorization.reason),
        ]
        _apply_compound_refusal_kwargs(route_kwargs, compound_authorization)
        notes.append(_compound_refusal_note(compound_authorization))

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
    elif route == "season_leaders" and _is_aggregation_sibling(
        route_kwargs.get("stat"), out.get("stat")
    ):
        # "total rebounds leaders" ranks `reb_total`; publishing the detector's
        # `reb` would name the per-game board that did not run.
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
    if route not in {"player_game_summary", "player_game_finder", "season_leaders"}:
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
        boundary_note := _unsupported_boundary_note(
            q,
            route,
            route_kwargs,
            requested_stat=stat,
        )
    ):
        route_kwargs["unsupported_filters"] = ["unsupported_concept"]
        notes.append(boundary_note)

    if (
        parsed.get("pre_streak_scope")
        and route not in ("player_streak_finder", "team_streak_finder")
        and "season" in route_kwargs
    ):
        # The three-season window is a streak default; a question that ends up
        # on another route keeps the scope it would have had without it.
        pre_season, pre_start, pre_end = parsed["pre_streak_scope"]
        route_kwargs.update(season=pre_season, start_season=pre_start, end_season=pre_end)
        notes = [note for note in notes if "three-season window" not in note]

    if career_intent and route is not None:
        from nbatools.commands._seasons import EARLIEST_SEASON

        if route_kwargs.get("start_season") == EARLIEST_SEASON:
            # The data starts in 1996-97, so a career that began earlier is
            # only partly covered; say so rather than claim the full career.
            notes.append(
                f"career_span: covers {EARLIEST_SEASON} onward; earlier seasons are not in the data"
            )

    if parsed.get("bare_year_season"):
        year, named = parsed["bare_year_season"]
        notes.append(f"default: read {year} as the {named} season, the one that ended in {year}")
        from nbatools.commands._seasons import EARLIEST_SEASON, default_end_season

        latest = default_end_season(parsed.get("season_type") or "Regular Season")
        if named < EARLIEST_SEASON or named > latest:
            notes.append(f"coverage: the data covers {EARLIEST_SEASON} to {latest}")
    if parsed.get("window_defaulted") and route in {
        "player_stretch_leaderboard",
        "team_stretch_leaderboard",
    }:
        notes.append(f"default: no stretch length named; ranked {window_size}-game windows")
    if notes:
        out["notes"] = notes

    out["confidence"] = compute_parse_confidence(out)
    out["alternates"] = generate_alternates(out)

    return out


_SITUATION_BOARD_WORDS = re.compile(
    r"\b(?:who|which|what)\b|\bteams?\b|\bfranchises?\b|\bmost\b|\bbest\b|\bworst\b|"
    r"\bfewest\b|\bleast\b|\bleaders?\b|\branks?\b|\branking\b|\btop\s+\d+\b"
)
_SITUATION_BOARD_PLAYER = re.compile(r"\bplayers?\b|\bscor(?:e|ed|er|ers|ing)\b")
_SITUATION_BOARD_OTHER = re.compile(
    r"\b(?:triple|double|quadruple)[\s-]doubles?\b|\bhome\b|\broad\b|\baway\b|"
    r"\bmargin\b|\bpoints?\b|\brebounds?\b|\bassists?\b|\bthrees?\b"
)


def _series_situation_board_stat(q: str) -> tuple[str, bool]:
    """Stat and sort order for "who has won the most game 7s"-style boards."""
    if re.search(r"\b(?:worst|lowest)\s+(?:record|win)", q):
        return "win_pct", True
    if re.search(
        r"\b(?:best|highest|top)\s+(?:record|win)|\bwin\s*(?:pct|percentage|%)|\brecord\b", q
    ):
        return "win_pct", False
    if re.search(r"\b(?:lost|loss(?:es)?|losing)\b", q):
        return "losses", bool(re.search(r"\b(?:fewest|least)\b", q))
    if re.search(r"\b(?:won|wins?|winning)\b", q):
        return "wins", bool(re.search(r"\b(?:fewest|least)\b", q))
    # "who is the best team in game 7s" ranks by record, not games played.
    if re.search(r"\b(?:worst|lowest)\b", q):
        return "win_pct", True
    if re.search(r"\b(?:best|highest)\b", q):
        return "win_pct", False
    return "games_played", bool(re.search(r"\b(?:fewest|least)\b", q))


def _series_situation_board(parsed: dict) -> dict | None:
    """Route "who has won the most game 7s" to the team playoff record board."""
    q = parsed["normalized_query"]
    if any(
        parsed.get(key)
        for key in ("player", "player_a", "player_b", "team", "team_a", "team_b", "opponent")
    ):
        return None
    if parsed.get("stat") not in (None, "win_pct", "wins", "losses"):
        return None
    # The board ranks overall records: a home/road split or a stat it cannot
    # read ("most triple doubles in game 7s") is another question.
    if parsed.get("home_only") or parsed.get("away_only") or _SITUATION_BOARD_OTHER.search(q):
        return None
    if not _SITUATION_BOARD_WORDS.search(q) or _SITUATION_BOARD_PLAYER.search(q):
        return None
    stat, ascending = _series_situation_board_stat(q)
    out = dict(parsed)
    out["route"] = "playoff_round_record"
    out["route_kwargs"] = {
        "season": parsed["season"],
        "start_season": parsed["start_season"],
        "end_season": parsed["end_season"],
        "playoff_round": parsed.get("playoff_round_filter"),
        "stat": stat,
        "ascending": ascending,
        "limit": parsed.get("top_n") or 10,
    }
    out["intent"] = "leaderboard"
    out["notes"] = []
    return out


def _series_refusal_route(parsed: dict, unsupported: str, note: str) -> dict:
    """Refuse a series question the data cannot answer rather than answer another."""
    out = dict(parsed)
    out["route"] = None
    out["route_kwargs"] = {
        "season": parsed["season"],
        "start_season": parsed["start_season"],
        "end_season": parsed["end_season"],
        "season_type": "Playoffs",
        "unsupported_filters": [unsupported],
    }
    out["intent"] = "unsupported"
    out["notes"] = [f"unsupported_boundary: {note}"]
    return out


def _series_comeback_route(parsed: dict) -> dict:
    """ "teams that came back from 3-1 down": refuse rather than answer a game record."""
    return _series_refusal_route(
        parsed,
        "series_comeback",
        "series comebacks (came back from 3-1, blew a 3-1 lead) can be listed for teams "
        "by opponent, round and season only; this question adds something that list "
        "cannot answer (a player, a count or ranking, a game condition or a team group)",
    )


_COMEBACK_UNSUPPORTED_KEYS = (
    "player",
    "player_a",
    "player_b",
    "stat",
    "min_value",
    "max_value",
    "threshold_conditions",
    "home_only",
    "away_only",
    "opponent_quality",
    "opponent_player",
    "opponent_conference",
    "opponent_division",
    "with_player",
    "without_player",
    "last_n",
)


# Every word a plain comeback-list question can use once the series score, the
# spans the parser resolves, the round and the named teams are removed.
# Anything else ("most", "twice", "in game 7", "with Poole", "western
# conference teams", "in March") asks for something the list cannot answer.
_COMEBACK_QUESTION_WORDS = frozenset(
    """
    teams team which who what whats how many has have had ever the a an did does do in
    from down series playoffs playoff postseason nba come came back coming comeback
    comebacks rallied rally overcome overcame blew blown blow blowing squandered lead
    leads led list all every any anyone anybody been was were is are of that to against
    vs versus there times deficit collapse collapsed collapses hole win won often history and
    """.split()
)
_COMEBACK_EXTRA_SPANS = (
    r"\b(?:in\s+|during\s+)?(?:this|current)\s+(?:postseason|playoffs)\b",
    r"\b(?:in\s+)?(?:the\s+)?(?:19|20)\d{2}(?:\s(?:19|20)?\d{2})?\s+(?:playoffs|postseason)\b",
)


def _team_reference_tokens(abbr: str | None) -> set[str]:
    from nbatools.commands.entity_resolution import TEAM_ALIASES, _normalize_for_matching

    if not abbr:
        return set()
    tokens = {abbr.lower()}
    for key, value in TEAM_ALIASES.items():
        if value == abbr:
            tokens.update(_normalize_for_matching(key).split())
    return tokens


def _comeback_question_has_qualifier(q: str, parsed: dict) -> bool:
    """True when ``q`` says more than "[team] came back from 3-1 [vs X] [round] [span]"."""
    from nbatools.commands.entity_resolution import _normalize_for_matching
    from nbatools.commands.playoff_history import ROUND_ALIASES

    text = _normalize_for_matching(re.sub(r"'s\b", "", q)).replace("'", "")
    spans = [phrase for phrase in _RING_SPAN_PHRASES if "top" not in phrase]
    for phrase in (*_COMEBACK_EXTRA_SPANS, *spans):
        text = re.sub(phrase, " ", text)
    # "conference semifinals": the round names it; for a named team the
    # conference ("Thunder ... western conference finals") adds nothing.
    side = r"(?:(?:western|eastern|west|east)\s+)?" if parsed.get("team") else ""
    text = re.sub(rf"\b{side}conference\s+(?=(?:finals?|semifinals?|semis)\b)", " ", text)
    for alias in sorted(ROUND_ALIASES, key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(_normalize_for_matching(alias))}\b", " ", text)
    # The series score itself ("3-1" reads "3 1" once normalized), once: any
    # other number ("2 times", "in 7") is a qualifier the list cannot answer.
    text = re.sub(r"\b[0-3]\s+(?:games?\s+)?(?:to\s+)?[0-3]\b", " ", text, count=1)
    allowed = _team_reference_tokens(parsed.get("team")) | _team_reference_tokens(
        parsed.get("opponent")
    )
    return any(
        token not in _COMEBACK_QUESTION_WORDS and token not in allowed
        for token in re.findall(r"[\w.]+", text)
    )


def _series_comeback_list_route(parsed: dict) -> dict:
    """ "teams that came back from 3-1 down": the series they won after trailing."""
    q = parsed["normalized_query"]
    if (
        any(parsed.get(key) for key in _COMEBACK_UNSUPPORTED_KEYS)
        or _comeback_question_has_qualifier(q, parsed)
        or re.search(r"\bplayers?\b|\bcoach(?:es|ed|ing)?\b|\bregular[\s-]season\b", q)
        # "came back from 3-1 and won the title": the title is a later series.
        or re.search(
            r"\b(?:win|won|wins|winning)\s+(?:the\s+|it\s+)?(?:championship|title|finals|ring|all)\b",
            q,
        )
        or parsed.get("team_a")
        or parsed.get("team_b")
    ):
        return _series_comeback_route(parsed)
    comeback = parsed["series_comeback"]
    team = parsed.get("team")
    opponent = parsed.get("opponent")
    season = parsed.get("season")
    if not (season or parsed.get("start_season") or parsed.get("end_season")):
        # "this season" / "this postseason": the current playoffs.
        from nbatools.commands._seasons import default_end_season

        season = default_end_season("Playoffs")
    out = dict(parsed)
    out["route"] = "playoff_series_comebacks"
    out["route_kwargs"] = {
        "deficit_wins": comeback["wins"],
        "deficit_losses": comeback["losses"],
        "blown": comeback["blown"],
        "team": team,
        "opponent": opponent,
        "season": season,
        "start_season": parsed.get("start_season"),
        "end_season": parsed.get("end_season"),
        "playoff_round": parsed.get("playoff_round_filter"),
    }
    # The series list already answers "how many" and "has ... ever".
    out["count_intent"] = False
    out["intent"] = "leaderboard"
    return out


# Counting stats whose total is the natural "most points in game 7s" answer.
_SITUATION_TOTAL_STATS = {"pts", "reb", "ast", "fg3m", "stl", "blk", "tov", "oreb", "dreb"}
_PER_GAME_WORDS = re.compile(
    r"\bper\s+game\b|\bpg\b|\baverag(?:e|es|ed|ing)\b|\bavg\b|\b[prab]pg\b|\bmean\b"
)


def _series_situation_totals(out: dict, q: str) -> None:
    """ "who scored the most points in game 7s": a total over those few games."""
    route_kwargs = out.get("route_kwargs") or {}
    if out.get("route") != "season_leaders" or _PER_GAME_WORDS.search(q):
        return
    if route_kwargs.get("stat") not in _SITUATION_TOTAL_STATS:
        return
    out["route_kwargs"] = {**route_kwargs, "stat": f"{route_kwargs['stat']}_total"}
    out["notes"] = [
        *(out.get("notes") or []),
        "default: totals over those games; ask per game for averages",
    ]


# Routes that answer a playoff round themselves; everything else filters game
# rows by the round as a series situation ("round_04", "game_7@04").
_ROUND_NATIVE_ROUTES = {
    "playoff_history",
    "playoff_appearances",
    "playoff_matchup_history",
    "playoff_round_record",
}
_ROUND_AS_SITUATION_REFUSALS = {"player_playoff_round", "leaderboard_request_unclear"}


# Wording that makes a round something other than "only that round's games":
# an exclusion, a conference half, an award or draft pick, teams that reached
# it, a count of trips, a single game, or a relative season the parser misses.
_ROUND_NOT_A_FILTER = re.compile(
    r"\b(?:not|non|excluding|exclude|except|outside|other\s+than|besides|minus|"
    r"east|eastern|west|western|mvps?|picks?|draft(?:ed)?|"
    r"made|make|making|reach(?:ed|es)?|appearances?|trips?|been\s+to|"
    r"most\s+recent|latest|ago)\b"
    r"|\b(?:before|after|without|until|prior\s+to)\s+(?:the\s+)?(?:nba\s+|conference\s+)?"
    r"(?:finals?|semifinals?|semis|championship|(?:first|second|third|1st|2nd|3rd)\s+round)\b"
    r"|\b(?:against|vs\.?|versus)\b.*\bteams?\b"
    r"|\bhow\s+many\s+(?:nba\s+)?finals\b"
    r"|\b(?:finals?|round|semifinals?|semis|championship)\s+game\b(?!\s*s\b)(?!\s+\d)(?!\s+logs?\b)"
)


# A round filters games only where each mention reads "in/during the [2016]
# <round>" or "<round> stats/averages/games/record/game 7". Any other framing
# ("beyond the first round", "every round but the finals", "his first finals",
# "first round series wins") falls back.
_ROUND_LEAD_IN = re.compile(
    r"\b(?:in|during)\s+(?:the\s+)?(?:nba\s+)?(?:(?:19|20)\d{2}(?:\s(?:19|20)?\d{2})?\s+)?"
    r"(?:conference\s+|conf\s+)?$"
    r"|(?<!\d)(?:19|20)\d{2}\s+$"
    # "game 7s of the finals", "game 1 in the first round"
    r"|\bgames?\s+(?:\d|one|two|three|four|five|six|seven)s?\s+(?:of|in)\s+(?:the\s+)?$"
)
# "years he lost in the finals", "runs that ended in the finals", "since the
# 2016 finals": the round dates a clause, not the games asked about.
_ROUND_CLAUSE_LEAD = re.compile(
    r"\b(?:lost|lose|loses|losing|won|winning|played|plays|play|playing|was|were|is|are|"
    r"been|ended|ends|end|ending|got|made|appeared|went|reached|faced|met|swept|fell)\s+"
    r"(?:in|to|into)\s+(?:the\s+)?(?:(?:19|20)\d{2}\s+)?(?:conference\s+)?$"
    r"|\b(?:since|after|before|until|till|from|through|thru|to)\s+(?:the\s+)?"
    r"(?:(?:19|20)\d{2}(?:\s(?:19|20)?\d{2})?\s+)?(?:conference\s+)?$"
)
_ROUND_FOLLOWER = re.compile(
    r"^\s+(?:stats?|statistics|averages?|avg|numbers|line|totals?|games|record"
    r"|game\s+(?:\d|one|two|three|four|five|six|seven)|performances?"
    # "LeBron finals ppg", "Curry finals game log", "Jokic finals triple doubles"
    r"|ppg|rpg|apg|spg|bpg|game\s+logs?|logs?|scoring|shooting"
    r"|(?:points|rebounds|assists|steals|blocks|threes|turnovers)(?:\s+per\s+game)?"
    r"|(?:triple|double)[\s-]doubles?)\b"
)
_ROUND_EXTRA_BLOCKS = re.compile(
    r"\bseries\b|\bnumber\s+of\b|\b(?:his|her|their)\s+(?:first|last|second|final)\b"
    r"|\b(?:exits?|eliminated|eliminating|upsets?|advanc\w*|swept|sweeps?|clinch\w*)\b"
    r"|\b(?:aside\s+from|save\s+for|apart\s+from)\b"
    r"|\b(?:first|second|third|1st|2nd|3rd)\s+(?:and|or|&|to|through)\s+"
    r"(?:the\s+)?(?:first|second|third|1st|2nd|3rd)\b"
)


def _round_mentions(q: str) -> list[tuple[str, int, int]]:
    from nbatools.commands.playoff_history import ROUND_ALIASES

    text = q.replace("-", " ")
    found: list[tuple[str, int, int]] = []
    taken: list[tuple[int, int]] = []
    for alias in sorted(ROUND_ALIASES, key=len, reverse=True):
        for match in re.finditer(rf"\b{re.escape(alias)}\b", text):
            if any(match.start() < end and start < match.end() for start, end in taken):
                continue
            taken.append(match.span())
            found.append((ROUND_ALIASES[alias], *match.span()))
    return found


def _round_reads_as_filter(q: str) -> bool:
    text = q.replace("-", " ")
    mentions = _round_mentions(q)
    if not mentions or len({code for code, _, _ in mentions}) > 1:
        return False
    if _ROUND_EXTRA_BLOCKS.search(text):
        return False
    return all(
        not _ROUND_CLAUSE_LEAD.search(text[:start])
        and (_ROUND_LEAD_IN.search(text[:start]) or _ROUND_FOLLOWER.match(text[end:]))
        for _, start, end in mentions
    )


def _round_as_situation(parsed: dict) -> dict | None:
    """ "LeBron stats in the Finals", "Lakers game 7s in the Finals": the round
    becomes a series situation on game routes instead of being dropped."""
    round_code = parsed.get("playoff_round_filter")
    if not round_code or parsed.get("series_comeback") or parsed.get("by_round_intent"):
        return None
    q = parsed["normalized_query"]
    years = re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", q)
    several_years = len(set(years)) > 1 and not (
        parsed.get("start_season") or parsed.get("end_season")
    )
    two_subjects = (parsed.get("player_a") and parsed.get("player_b")) or (
        parsed.get("team_a") and parsed.get("team_b")
    )
    if _ROUND_NOT_A_FILTER.search(q) or several_years or not _round_reads_as_filter(q):
        # "excluding the first round", "first and second round", "western
        # conference finals", "finals mvp", "most points in a finals game":
        # never answer only one round's games for these.
        return None
    if not (parsed.get("season") or parsed.get("start_season") or parsed.get("end_season")):
        if re.search(r"(?<!\d)(?:19|20)\d{2}(?!\d)", parsed["normalized_query"]):
            # A year the parser did not resolve: never answer another span.
            return None
    from nbatools.commands._natural_query_execution import _SERIES_SITUATION_ROUTES

    situation = parsed.get("series_situation")
    if situation:
        # "which teams won game 4 in the finals": the round record board takes
        # the round itself and names it.
        if _series_situation_board(parsed) is not None:
            return None
    else:
        try:
            trial = _route_parsed_query(parsed)
        except ValueError:
            return None
        route = trial.get("route")
        refused = set((trial.get("route_kwargs") or {}).get("unsupported_filters") or [])
        if route in _ROUND_NATIVE_ROUTES:
            return None
        if route is None and not (refused & _ROUND_AS_SITUATION_REFUSALS):
            return None
        if route is not None and route not in _SERIES_SITUATION_ROUTES:
            return None
    rerouted = dict(parsed)
    if two_subjects:
        # "LeBron vs Curry in the Finals": only a comparison takes two subjects
        # and the round together.
        try:
            compare = _route_parsed_query({**parsed, "playoff_round_filter": None})
        except ValueError:
            return None
        if compare.get("route") not in {"player_compare", "team_compare"}:
            return None
    rerouted["playoff_round_filter"] = None
    # The leaderboard check may count round words as answered only now.
    rerouted["series_situation_round"] = round_code
    rerouted["series_situation"] = (
        f"{situation}@{round_code}" if situation else f"round_{round_code}"
    )
    if parsed.get("playoff_round_unnamed_span") and not parsed.get("series_situation_career"):
        from nbatools.commands._seasons import resolve_career

        rerouted["season"] = None
        rerouted["start_season"], rerouted["end_season"] = resolve_career("Playoffs")
        rerouted["series_situation_career"] = True
    elif not (parsed.get("season") or parsed.get("start_season") or parsed.get("end_season")):
        # "most rebounds in the first round this season": round questions skip
        # the default season, so "this/last season" is resolved here.
        from nbatools.commands._seasons import default_end_season, previous_season

        q = parsed["normalized_query"]
        if re.search(r"\b(?:last|previous)\s+(?:season|year|postseason|playoffs)\b", q):
            rerouted["season"] = previous_season("Playoffs")
        else:
            rerouted["season"] = default_end_season("Playoffs")
    return rerouted


def _single_season_refusal(parsed: dict) -> dict:
    """ "most team points in a single season": refuse rather than rank one season."""
    out = dict(parsed)
    out.update(route=None, intent="unsupported", season=None, start_season=None, end_season=None)
    out["route_kwargs"] = {
        "season": None,
        "start_season": None,
        "end_season": None,
        "season_type": parsed.get("season_type") or "Regular Season",
        "unsupported_filters": ["single_season"],
    }
    out["notes"] = [
        "unsupported_boundary: best single seasons are ranked for player and team "
        'season boards only; ask for one season ("most 40-point games this season") instead'
    ]
    out["confidence"] = compute_parse_confidence(out)
    out["alternates"] = generate_alternates(out)
    return out


_WITH_SUPERLATIVE = re.compile(r"\bwith\s+the\s+(?:most|fewest|least|highest|lowest|best|worst)\b")


def _best_season_scope(parsed: dict, out: dict, kept: frozenset) -> dict | None:
    """Shared checks for "<subject> best <stat> season(s)"; the span, or None."""
    q = parsed["normalized_query"]
    route_kwargs = out.get("route_kwargs") or {}
    if not (parsed.get("single_season_intent") or _PLAYER_BEST_SEASON.search(q)):
        return None
    if _PLAYER_SEASON_BLOCKERS.search(q):
        return None
    if _WITH_SUPERLATIVE.search(q) and detect_unresolved_availability_player(q, mode="with"):
        # "season with the highest scoring teammate": a person, not a stat.
        return None
    if route_kwargs.get("start_season") is None and (
        _NAMED_SEASON_WORDS.search(q) or extract_season(q) is not None
    ):
        # "LeBron best scoring season in 2016" names one season.
        return None
    if _season_shooting_stat(q):
        # "3 point shooting season": the 3 is not a points threshold.
        kept = kept | {"min_value"} if route_kwargs.get("min_value") == 3 else kept
    if any(
        value not in (None, False, "", [], (), {})
        for key, value in route_kwargs.items()
        if key not in kept
    ):
        # "LeBron best scoring season vs Curry / in the clutch / with Luka":
        # the season board would drop the filter.
        return None
    from nbatools.commands._seasons import EARLIEST_SEASON, resolve_career

    season_type = route_kwargs.get("season_type") or "Regular Season"
    notes = list(out.get("notes") or [])
    start, end = route_kwargs.get("start_season"), route_kwargs.get("end_season")
    if not start:
        start, end = resolve_career(season_type)
        notes.append(f"default: every season since {EARLIEST_SEASON}")
    return {
        "season": None,
        "start_season": start,
        "end_season": end,
        "season_type": season_type,
        "per_season": True,
        "limit": parsed.get("top_n") or 10,
        "ascending": bool(_PLAYER_SEASON_LOW.search(q)),
        "notes": notes,
    }


def _rerouted_to_seasons(out: dict, route: str, kwargs: dict, note: str) -> dict:
    notes = kwargs.pop("notes") + [note]
    rerouted = dict(out)
    rerouted.update(route=route, intent="leaderboard", route_kwargs=kwargs)
    for key in ("season", "start_season", "end_season"):
        rerouted[key] = kwargs[key]
    rerouted["notes"] = notes
    return rerouted


def _players_named(q: str, player: str) -> str | list[str]:
    """ "LeBron and Curry best scoring season": both players, else the one."""
    for sep in (" and ", " & "):
        if sep in q:
            left, right = q.split(sep, 1)
            names = [detect_player(left.strip(" .")), detect_player(right.strip(" ."))]
            if all(names) and names[0] != names[1]:
                return names
    return player


_PLAYER_PLAIN_BEST_SEASON = re.compile(
    r"\b(?:best|worst|greatest|top(?:\s+\d+)?)\s+(?:(?:regular[\s-]season|playoff)\s+)?seasons?\b"
)


def _player_best_seasons(parsed: dict, out: dict) -> dict | None:
    """ "LeBron best scoring season": that player's seasons, best first."""
    route_kwargs = out.get("route_kwargs") or {}
    player = parsed.get("player")
    q = parsed["normalized_query"]
    stat = _season_shooting_stat(q) or route_kwargs.get("stat")
    plain = stat is None and _PLAYER_PLAIN_BEST_SEASON.search(q)
    if plain:
        # "LeBron best season" names no stat: rank by scoring and say so.
        stat = "pts"
    if out.get("route") not in _PLAYER_SEASON_ROUTES or not player or not stat:
        return None
    kwargs = _best_season_scope(parsed, out, _PLAYER_SEASON_KEPT)
    if kwargs is None:
        return None
    if plain:
        kwargs["notes"].append("default: best season ranked by points per game")
    kwargs.update(stat=stat, player=_players_named(parsed["normalized_query"], player))
    return _rerouted_to_seasons(
        out,
        "season_leaders",
        kwargs,
        "single_season: each of the player's seasons ranked on its own",
    )


def _team_best_seasons(parsed: dict, out: dict) -> dict | None:
    """ "Lakers best scoring season", "Lakers best record in a single season"."""
    q = parsed["normalized_query"]
    route_kwargs = dict(out.get("route_kwargs") or {})
    team = route_kwargs.get("team")
    kept = _TEAM_SEASON_KEPT
    if (
        out.get("route") == "season_team_leaders"
        and team is None
        and isinstance(parsed.get("team"), str)
    ):
        # "Lakers best offensive rating season" landed on the league board.
        team = parsed["team"]
        kept = kept | {"min_games"}
    elif out.get("route") not in _TEAM_SEASON_ROUTES:
        return None
    if not isinstance(team, str):
        return None
    if parsed.get("player") or parsed.get("team_a") or parsed.get("team_b"):
        return None
    if _TEAM_SEASON_BLOCKERS.search(q):
        return None
    worded = _team_season_stat(q)
    stat = worded or route_kwargs.get("stat")
    if stat in ("wins", "losses", "win_pct"):
        # "by wins" read as wins_only: the stat names the board, not a filter.
        route_kwargs.pop("wins_only", None)
        route_kwargs.pop("losses_only", None)
    if route_kwargs.get("unsupported_filters") == ["single_team_advanced_stat_summary"]:
        # The team's game summary has no ratings; the season board does.
        route_kwargs.pop("unsupported_filters")
    record = stat in (None, "wins", "losses", "win_pct")
    if stat is None and not _TEAM_PLAIN_BEST_SEASON.search(q):
        # "Celtics best clutch season": a stat the parser did not read.
        return None
    kwargs = _best_season_scope(parsed, {**out, "route_kwargs": route_kwargs}, kept)
    if kwargs is None:
        return None
    if stat == "losses" or _ranks_lower_is_better(stat):
        # Lower is better: "most losses" / "highest defensive rating" first
        # when said, else "best" is the lowest and "worst" the highest; a
        # plain "ranked by defensive rating" is lowest first, "losses" most.
        if re.search(r"\b(?:most|highest)\b", q):
            kwargs["ascending"] = False
        elif re.search(r"\b(?:fewest|lowest)\b|(?<!\bat\s)\bleast\b", q):
            kwargs["ascending"] = True
        elif re.search(r"\b(?:best|greatest)\b|\btop\b(?!\s+\d)", q):
            kwargs["ascending"] = True
        elif re.search(r"\bworst\b", q):
            kwargs["ascending"] = False
        else:
            kwargs["ascending"] = stat != "losses"
    kwargs.update(team=team, stat=stat or "win_pct")
    route = "team_record_leaderboard" if record else "season_team_leaders"
    return _rerouted_to_seasons(
        out, route, kwargs, "single_season: each of the team's seasons ranked on its own"
    )


# "Curry best 3 point shooting game", "LeBron top 5 games", "worst shooting
# night": a list of that player's games ranked by one stat.
_PLAYER_GAME_LIST = re.compile(
    r"\b(?:best|worst|top|greatest|highest|lowest)\b(?:\s+[a-z0-9%-]+){0,4}?\s+"
    r"(?:games?|nights?|performances?|outings?)\b"
)
_PLAYER_GAME_LIST_BLOCKERS = re.compile(
    r"\bgame\s+score\b|\bper\s+game\b|\bin\s+a\s+row\b|\bstraight\b|\bstreaks?\b"
    r"|\bstretch(?:es)?\b|\bspan\b|\bseasons\b|\bsingle[\s-]season\b|\bin\s+a\s+season\b"
    r"|\baverage|\bavg\b|\brecord\b|\bdefen[sc]"
)
_GAME_SHOOTING_PATTERNS = tuple(
    (pattern.replace(r"seasons?\b", r"(?:games?|nights?|performances?|outings?)\b"), stat)
    for pattern, stat in _SEASON_SHOOTING_PATTERNS
)
_RATE_STATS = frozenset({"fg_pct", "fg3_pct", "ft_pct", "efg_pct", "ts_pct"})
_GAME_LIST_PERCENT_BOUND = re.compile(
    r"\b(over|above|better\s+than|at\s+least|under|below|less\s+than|worse\s+than)\s+"
    r"(\d+(?:\.\d+)?)\s*(?:%|percent)"
    r"(?:\s+(?:(?:from|at)\s+)?(?:the\s+)?"
    r"(three(?:[\s-]point\s+range)?|3|deep|downtown|(?:free[\s-]throw\s+)?line|stripe|"
    r"free\s+throws?|field))?"
)
_PLAYER_GAME_LIST_ROUTES = frozenset({"player_game_finder", "player_game_summary"})


def _percent_rate(source: str | None, default: str) -> str:
    """The rate a "% from ..." bound names; the ranked rate when none."""
    if not source:
        return default
    if re.search(r"line|stripe|free", source):
        return "ft_pct"
    return "fg_pct" if source == "field" else "fg3_pct"


def _player_game_list(parsed: dict, out: dict) -> dict | None:
    """ "Curry best 3 point shooting game": that player's games, best first."""
    q = parsed["normalized_query"]
    route_kwargs = dict(out.get("route_kwargs") or {})
    player = route_kwargs.get("player")
    if out.get("route") not in _PLAYER_GAME_LIST_ROUTES or not isinstance(player, str):
        return None
    if not _PLAYER_GAME_LIST.search(q) or _PLAYER_GAME_LIST_BLOCKERS.search(q):
        return None
    shooting = next(
        (stat for pattern, stat in _GAME_SHOOTING_PATTERNS if re.search(pattern, q)), None
    )
    if shooting == "fg_pct" and route_kwargs.get("stat") in _RATE_STATS:
        # "best shooting games shooting over 50% from three": the named rate.
        shooting = route_kwargs["stat"]
    if shooting and route_kwargs.get("min_value") == 3 and route_kwargs.get("stat") == "pts":
        # "3 point shooting": the 3 is not a points threshold.
        route_kwargs.pop("min_value")
        route_kwargs.pop("stat")
    elif shooting is None and out["route"] == "player_game_finder":
        # Already a ranked list of the stat asked for.
        return None
    elif (
        shooting
        and route_kwargs.get("stat") not in (None, shooting)
        and (route_kwargs.get("min_value") is not None or route_kwargs.get("max_value") is not None)
    ):
        # "worst shooting games under 15 points": the bound is on another
        # stat; keep it as a condition and rank by the shooting stat.
        bound = {
            "stat": route_kwargs.pop("stat"),
            "min_value": route_kwargs.pop("min_value", None),
            "max_value": route_kwargs.pop("max_value", None),
        }
        route_kwargs["conditions"] = list(route_kwargs.get("conditions") or []) + [bound]
    conditions = list(route_kwargs.get("conditions") or [])
    if shooting and route_kwargs.get("stat") == shooting:
        # A bound on the ranked rate ("over 50%", "at least 50%") becomes a
        # condition, so the finder's attempt floor still applies.
        bound = {
            "stat": shooting,
            "min_value": route_kwargs.pop("min_value", None),
            "max_value": route_kwargs.pop("max_value", None),
        }
        for key in ("min_value", "max_value"):
            if (bound[key] or 0) > 1:
                # "at least 50%" can arrive unscaled; percentages are fractions.
                bound[key] = bound[key] / 100
        if bound["min_value"] is not None or bound["max_value"] is not None:
            conditions.append(bound)
    percents = list(_GAME_LIST_PERCENT_BOUND.finditer(q)) if shooting else []
    named = [_percent_rate(m.group(3), shooting) for m in percents]
    if any(m.group(3) for m in percents):
        # "over 50% from three": the bound names its own rate, so a rate bound
        # the parser read on another rate is dropped.
        conditions = [c for c in conditions if c.get("stat") not in _RATE_STATS]
        if shooting == "fg_pct" and not re.search(r"\bfield[\s-]goal|\bfg\b", q):
            # Plain "shooting games over 50% from three" ranks the named rate.
            shooting = named[0]
            named = [_percent_rate(m.group(3), shooting) for m in percents]
    elif percents and any(c.get("stat") in _RATE_STATS for c in conditions):
        percents = []
    for match, rate in zip(percents, named):
        value = float(match.group(2))
        value = value / 100 if value > 1 else value
        if match.group(1) in ("over", "above", "better than"):
            conditions.append({"stat": rate, "min_value": value + 0.0001, "max_value": None})
        elif match.group(1) == "at least":
            conditions.append({"stat": rate, "min_value": value, "max_value": None})
        else:
            conditions.append({"stat": rate, "min_value": None, "max_value": value - 0.0001})
    if conditions:
        route_kwargs["conditions"] = conditions
    stat = shooting or route_kwargs.get("stat") or "pts"
    route_kwargs.pop("career_intent", None)
    from inspect import signature

    from nbatools.commands.player_game_finder import build_result as finder

    accepted = set(signature(finder).parameters)
    if any(
        value not in (None, False, "", [], (), {})
        for key, value in route_kwargs.items()
        if key not in accepted
    ):
        # A filter the game list cannot apply: keep the original answer.
        return None
    kwargs = {key: value for key, value in route_kwargs.items() if key in accepted}
    kwargs.update(
        stat=stat,
        sort_by="stat",
        limit=parsed.get("top_n") or 10,
        ascending=bool(re.search(r"\b(?:worst|lowest)\b", q)),
    )
    rerouted = dict(out)
    rerouted.update(route="player_game_finder", intent="finder", route_kwargs=kwargs)
    rerouted.update(stat=stat, min_value=kwargs.get("min_value"))
    rerouted["notes"] = list(out.get("notes") or []) + [
        f"game_list: {player}'s games ranked by {stat}"
    ]
    return rerouted


# Short decades ("the 90s", "the '80s") are already four digits here.
_NAMED_DECADE = re.compile(r"\bthe\s+(?:19|20)\d0s\b")
_NAMED_DECADE_PHRASE = re.compile(
    r"\b(?:(?:in|during|of|from|over)\s+)?the\s+(?:19|20)\d0s"
    r"(?:\s+(?:and|to|through|thru)\s+(?:the\s+)?(?:19|20)\d0s)?\b"
)
_DECADE_BUCKETS = re.compile(r"\b(?:by|per|each|every)\s+decade\b|\bdecades\b")
_RECORD_WORDS = re.compile(r"\brecords?\b|\bwin(?:ning)?\s*(?:%|pct|percentage)")


def _decade_stat_board(parsed: dict, out: dict) -> dict | None:
    """ "most points in a season in the 2010s": a stat board over that decade.

    The decade record board ranks team records; a stat question landed there
    and answered wins. The named decade is folded into the equivalent year
    range and the question parsed again, so every other filter (rookies, home,
    totals, minimum games) is kept exactly as the range form keeps it.
    """
    if out.get("route") != "record_by_decade_leaderboard":
        return None
    q = parsed["normalized_query"]
    if not _NAMED_DECADE.search(q) or _DECADE_BUCKETS.search(q):
        return None
    stat = parsed.get("stat")
    record = (
        stat in (None, "wins", "losses", "win_pct")
        or _RANKED_WINS_LOSSES.search(q)
        or _RECORD_WORDS.search(q)
    )
    if record and not parsed.get("single_season_intent") and not _PLAYER_SUBJECT.search(q):
        # "best record in the 2010s": the decade record board.
        return None
    phrases = list(_NAMED_DECADE_PHRASE.finditer(q))
    if len(phrases) != 1:
        # Two decades not joined by "and"/"to" ("the 2010s by a rookie
        # compared to the 2020s"): folding them would drop whatever sits
        # between, and the record board would answer wins. Refuse.
        refused = _single_season_refusal(parsed)
        refused["route_kwargs"]["unsupported_filters"] = ["leaderboard_request_unclear"]
        refused["notes"] = [
            "unsupported_boundary: ask about one decade or one year range at a time"
        ]
        return refused
    starts = [int(year) for m in phrases for year in re.findall(r"\d{4}", m.group(0))]
    # "the 2010s and the 2020s": one span from the first decade to the last.
    first, last = min(starts), max(starts) + 9

    # Playoff years name the season ending in them, so the 2020s playoffs
    # (2020-21 to 2029-30) are "from 2021 to 2030".
    def _reparse(shift: int) -> dict:
        span = f"from {first + shift} to {last + shift}"
        return _finalize_route(
            _build_parse_state(q[: phrases[0].start()] + span + q[phrases[-1].end() :])
        )

    # Playoff years can read as the season ending in them ("the finals"),
    # so check which reading starts the span at the decade's first season.
    want = f"{first}-{str(first + 1)[2:]}"
    rerouted = _reparse(0)
    if (rerouted.get("route_kwargs") or {}).get("start_season") not in (None, want):
        shifted = _reparse(1)
        if (shifted.get("route_kwargs") or {}).get("start_season") == want:
            rerouted = shifted
    if rerouted.get("route") in (None, "record_by_decade_leaderboard"):
        return None
    rerouted["normalized_query"] = q
    rerouted["notes"] = list(rerouted.get("notes") or []) + [f"decade: read as {first} to {last}"]
    if first < 1996:
        rerouted["notes"].append("coverage: data starts in 1996-97")
    return rerouted


# "against rookies" names opponents, not the players ranked.
_ROOKIE_SUBJECT = re.compile(
    r"(?<!\bagainst\s)(?<!\bvs\s)(?<!\bvs\.\s)(?<!\bversus\s)\brookies?\b"
    r"(?!\s+(?:head\s+)?coach)"
)
_PLAYER_SUBJECT = re.compile(
    r"\bplayers?\b|\bby\s+an?\s+(?:player|individual)\b|" + _ROOKIE_SUBJECT.pattern
)
# Team-record kwargs a player wins board can keep.
_PLAYER_WINS_KEPT = frozenset(
    {
        "season",
        "start_season",
        "end_season",
        "season_type",
        "stat",
        "limit",
        "ascending",
        "home_only",
        "away_only",
        "per_season",
    }
)


def _player_wins_board(parsed: dict, out: dict) -> dict | None:
    """ "most playoff wins by a player": players ranked by games won.

    The record board ranks teams; a player's wins are the games he played
    that his team won, and his record ("players with the best record") is
    those wins over the games he played.
    """
    q = parsed["normalized_query"]
    if (
        out.get("route") == "record_by_decade_leaderboard"
        and _PLAYER_SUBJECT.search(q)
        and not re.search(r"\bteams?\b|\bfranchises?\b", q)
    ):
        # "players with the most wins by decade": the decade board ranks
        # teams; a player board per decade is not built yet.
        refused = _single_season_refusal(parsed)
        refused["route_kwargs"]["unsupported_filters"] = ["player_record_by_decade"]
        refused["notes"] = [
            "unsupported_boundary: player wins and records are ranked over one season or "
            'one span ("players with the most wins in the 2010s"), not decade by decade'
        ]
        return refused
    if out.get("route") != "team_record_leaderboard":
        return None
    route_kwargs = out.get("route_kwargs") or {}
    stat = route_kwargs.get("stat")
    if stat not in ("wins", "losses", "win_pct") or not _PLAYER_SUBJECT.search(q):
        return None
    if re.search(r"\bteams?\b|\bfranchises?\b", q):
        # "teams with the most wins when their best players rest".
        return None
    if parsed.get("team") or parsed.get("player"):
        return None
    if any(
        value not in (None, False, "", [], (), {})
        for key, value in route_kwargs.items()
        if key not in _PLAYER_WINS_KEPT
    ):
        # "players with the most road wins": a filter this board would drop.
        return None
    kwargs = {key: route_kwargs.get(key) for key in ("season", "start_season", "end_season")}
    kwargs.update(
        season_type=route_kwargs.get("season_type") or "Regular Season",
        stat="win_pct" if stat == "win_pct" else "games_played",
        limit=route_kwargs.get("limit") or 10,
        ascending=bool(route_kwargs.get("ascending")),
        min_games=1,
        wins_only=stat == "wins",
        losses_only=stat == "losses",
        home_only=bool(route_kwargs.get("home_only")),
        away_only=bool(route_kwargs.get("away_only")),
        per_season=bool(route_kwargs.get("per_season")),
        rookies_only=bool(_ROOKIE_SUBJECT.search(q)),
        role=detect_role(q),
    )
    notes = list(out.get("notes") or [])
    named = bool(_NAMED_SEASON_WORDS.search(q))
    if parsed.get("single_season_intent") and not kwargs["start_season"] and not named:
        # "most wins in a single season by a player": every season since 1996-97.
        from nbatools.commands._seasons import EARLIEST_SEASON, resolve_career

        kwargs["season"] = None
        kwargs["start_season"], kwargs["end_season"] = resolve_career(kwargs["season_type"])
        notes.append(f"default: every season since {EARLIEST_SEASON}")
    if parsed.get("single_season_intent") and kwargs["start_season"]:
        kwargs["per_season"] = True
    rerouted = dict(out)
    rerouted.update(route="season_leaders", intent="leaderboard", route_kwargs=kwargs)
    for key in ("season", "start_season", "end_season"):
        rerouted[key] = kwargs[key]
    outcome = {"wins": "won", "losses": "lost", "win_pct": "won or lost"}[stat]
    rerouted["notes"] = notes + [f"player_{stat}: games played that the player's team {outcome}"]
    return rerouted


# A decade ranked by something other than its record.
_DECADE_STAT_CUE = re.compile(
    r"\b(?:scor\w*|offens\w*|defens\w*|differential|rating|points?|pointers?|threes?|"
    r"rebound\w*|assists?|blocks?|steals?|shooting)\b"
)


def _decade_superlative_stat(parsed: dict, out: dict) -> dict | None:
    """ "best decade for points": refuse rather than rank decades by record.

    "best decade" alone is a record question; with a stat it asks for a
    decade board the record tables cannot give.
    """
    q = parsed["normalized_query"]
    if out.get("route") not in ("record_by_decade", "record_by_decade_leaderboard"):
        return None
    if not _DECADE_SUPERLATIVE.search(q):
        return None
    stat = parsed.get("stat")
    if stat in (None, "wins", "losses", "win_pct") and not _DECADE_STAT_CUE.search(q):
        return None
    refused = _single_season_refusal(parsed)
    refused["route_kwargs"]["unsupported_filters"] = ["decade_stat"]
    refused["notes"] = [
        "unsupported_boundary: decades are ranked by record; ask for one decade's "
        'stat leaders by name ("most points in the 2010s")'
    ]
    return refused


def _finalize_route(parsed: dict) -> dict:
    """Route a parse state, then rank single seasons when one season is asked."""
    out = _finalize_route_inner(parsed)
    decade = _decade_stat_board(parsed, out)
    if decade is not None:
        return decade
    wins = _player_wins_board(parsed, out)
    if wins is not None:
        return wins
    decade_stat = _decade_superlative_stat(parsed, out)
    if decade_stat is not None:
        return decade_stat
    if parsed.get("player") and (
        _DECADE_SUPERLATIVE.search(parsed["normalized_query"])
        or re.search(r"\bby\s+decade\b|\bwhich\s+decade\b", parsed["normalized_query"])
    ):
        # "LeBron best decade", "which decade did LeBron win the most":
        # decades are ranked for team records only.
        refused = _single_season_refusal(parsed)
        refused["route_kwargs"]["unsupported_filters"] = ["player_decade"]
        refused["notes"] = [
            "unsupported_boundary: decades are ranked for team records; ask for a "
            'player\'s decade by name ("LeBron points per game in the 2010s")'
        ]
        return refused
    games = _player_game_list(parsed, out)
    if games is not None:
        return games
    best = _player_best_seasons(parsed, out) or _team_best_seasons(parsed, out)
    if best is not None:
        return best
    if not parsed.get("single_season_intent") or not out.get("route"):
        return out
    route_kwargs = dict(out.get("route_kwargs") or {})
    if route_kwargs.get("unsupported_filters"):
        return out
    q = parsed["normalized_query"]
    named = bool(_NAMED_SEASON_WORDS.search(q))
    if out["route"] in _SINGLE_SEASON_UNRANKED_ROUTES and not named:
        # "most points in a game in a single season" has no per-season board:
        # never answer the current season only.
        return _single_season_refusal(parsed)
    if out["route"] not in _SINGLE_SEASON_RANKED_ROUTES:
        return out
    if out["route"] == "season_leaders" and _SINGLE_SEASON_TEAM.search(q) and not named:
        # A team question that landed on the player board.
        return _single_season_refusal(parsed)
    if route_kwargs.get("without_player") and not named:
        # "most wins in a single season without LeBron": the record board
        # has no absence filter, so refuse rather than answer an empty list.
        return _single_season_refusal(parsed)
    notes = list(out.get("notes") or [])
    if (
        not route_kwargs.get("start_season")
        and not named
        and not (route_kwargs.get("start_date") or route_kwargs.get("end_date"))
    ):
        # "most points in a single season": every season since 1996-97.
        from nbatools.commands._seasons import EARLIEST_SEASON, resolve_career

        season_type = route_kwargs.get("season_type") or "Regular Season"
        route_kwargs["season"] = None
        route_kwargs["start_season"], route_kwargs["end_season"] = resolve_career(season_type)
        notes.append(f"default: every season since {EARLIEST_SEASON}")
    if route_kwargs.get("start_season"):
        route_kwargs["per_season"] = True
        kind = "player" if out["route"] == "season_leaders" else "team"
        notes.append(f"single_season: each {kind} season ranked on its own")
    out = dict(out)
    out["route_kwargs"] = route_kwargs
    # Response metadata reads the span from the parse state.
    for key in ("season", "start_season", "end_season"):
        out[key] = route_kwargs.get(key)
    out["notes"] = notes
    return out


def _finalize_route_inner(parsed: dict) -> dict:
    """Route a parse state; playoff series situations ride on every route."""
    rerouted = _round_as_situation(parsed)
    if rerouted is not None:
        parsed = rerouted
    situation = parsed.get("series_situation")
    q = parsed["normalized_query"]
    refused = True
    if parsed.get("series_comeback"):
        out = _series_comeback_list_route(parsed)
        if out.get("route") and parsed.get("series_situation_career"):
            from nbatools.commands._seasons import EARLIEST_SEASON

            out["notes"] = [
                *(out.get("notes") or []),
                f"default: every playoff season since {EARLIEST_SEASON}",
            ]
        out["confidence"] = compute_parse_confidence(out)
        out["alternates"] = generate_alternates(out)
        return out
    elif situation and re.search(r"\bregular[\s-]season\b", q):
        out = _series_refusal_route(
            parsed,
            "series_situation",
            "series situations (game 7s, closeout games, up 3-1) are playoff games; "
            "the regular season has none",
        )
    elif situation and re.search(r"\bcoach(?:es|ed|ing)?\b", q):
        out = _series_refusal_route(
            parsed, "coach", "coaches are not in the data, so coach records are not supported"
        )
    else:
        refused = False
        board = _series_situation_board(parsed) if situation else None
        out = board if board is not None else _route_parsed_query(parsed)
        if out.get("route") == "team_compare" and parsed.get("playoff_round_filter"):
            # "Celtics vs Heat in the eastern conference finals": a comparison
            # that cannot take the round must not compare whole postseasons.
            out = _series_refusal_route(
                parsed,
                "playoff_round",
                "this comparison cannot be limited to that playoff round; ask for the "
                'teams\' games in that round ("Celtics vs Heat in the conference finals") '
                "or their playoff series history",
            )
            refused = True
        if situation and board is None:
            _series_situation_totals(out, q)
    if refused or not situation:
        if refused:
            out["confidence"] = compute_parse_confidence(out)
            out["alternates"] = generate_alternates(out)
        return out
    notes = list(out.get("notes") or [])
    if situation and out.get("route"):
        from nbatools.commands.playoff_history import series_situation_label

        route_kwargs = dict(out.get("route_kwargs") or {})
        route_kwargs["series_situation"] = situation
        out["route_kwargs"] = route_kwargs
        notes.append(f"series_situation: {series_situation_label(situation)}")
    if parsed.get("series_situation_career"):
        from nbatools.commands._seasons import EARLIEST_SEASON

        notes.append(f"default: every playoff season since {EARLIEST_SEASON}")
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
