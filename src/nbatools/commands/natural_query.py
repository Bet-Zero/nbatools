import re

import pandas as pd

from nbatools.commands._confidence import compute_parse_confidence, generate_alternates
from nbatools.commands._constants import normalize_text, route_to_intent
from nbatools.commands._date_utils import CURRENT_QUERY_DATE, extract_date_range
from nbatools.commands._default_rules import (
    metric_only_leaderboard_default,
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
from nbatools.commands._matchup_utils import (
    detect_head_to_head,
    detect_opponent,
    detect_opponent_player,
    detect_player,
    detect_player_resolved,
    detect_team_resolved,
    detect_without_player,
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
    build_lineup_note as build_lineup_note,
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
    detect_back_to_back as detect_back_to_back,
)
from nbatools.commands._parse_helpers import (
    detect_career_intent as detect_career_intent,
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
    detect_opponent_quality as detect_opponent_quality,
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
    extract_position_filter as extract_position_filter,
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
    try_playoff_record_route,
    try_record_leaderboard_route,
)
from nbatools.commands.entity_resolution import format_ambiguity_message, resolve_stat
from nbatools.commands.freshness import compute_current_through
from nbatools.commands.query_boolean_parser import expression_contains_boolean_ops  # noqa: F401

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
    "extract_position_filter",
    "extract_season",
    "extract_season_range",
    "extract_since_season",
    "extract_streak_request",
    "extract_team_streak_request",
    "extract_threshold_conditions",
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
    distinct_player_count = detect_distinct_player_count(q)
    distinct_team_count = detect_distinct_team_count(q)

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
    without_player = None

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
        without_player, _ = detect_without_player(q)

    # If without_player is the same as the detected player, clear player so the
    # query routes to the team path (e.g., "Lakers record without LeBron")
    if without_player and player and without_player.upper() == player.upper():
        player = None

    role = detect_role(q) if any([player, player_a, player_b]) else None

    home_only, away_only = detect_home_away(q)
    wins_only, losses_only = detect_wins_losses(q)
    clutch = detect_clutch(q)
    back_to_back = detect_back_to_back(q)
    rest_days = detect_rest_days(q)
    one_possession = detect_one_possession(q)
    nationally_televised = detect_nationally_televised(q)
    quarter = detect_quarter(q)
    half = detect_half(q)

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
        "opponent_quality": opponent_quality,
        "lineup_members": lineup_members,
        "presence_state": presence_state,
        "unit_size": unit_size,
        "minute_minimum": minute_minimum,
        "lineup_query_mode": lineup_query_mode,
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
        "distinct_player_count": distinct_player_count,
        "distinct_team_count": distinct_team_count,
        "opponent_player": opponent_player,
        "without_player": without_player,
        "entity_ambiguity": entity_ambiguity,
        "team_resolution_confidence": team_resolution_confidence,
        "stat_resolution_confidence": stat_resolution_confidence,
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
    distinct_player_count = parsed.get("distinct_player_count", False)
    opponent_player = parsed.get("opponent_player")
    without_player = parsed.get("without_player")
    lineup_members = parsed.get("lineup_members") or []
    presence_state = parsed.get("presence_state")
    unit_size = parsed.get("unit_size")
    minute_minimum = parsed.get("minute_minimum")
    lineup_query_mode = parsed.get("lineup_query_mode")

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

    if lineup_members and presence_state is not None:
        route = "player_on_off"
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "player": player or lineup_members[0],
            "team": team,
            "opponent": opponent,
            "lineup_members": lineup_members,
            "presence_state": presence_state,
            "last_n": last_n,
        }
    elif lineup_query_mode == "lineup_summary":
        route = "lineup_summary"
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "team": team,
            "opponent": opponent,
            "lineup_members": lineup_members,
            "unit_size": unit_size,
            "minute_minimum": minute_minimum,
            "stat": stat,
            "last_n": last_n,
        }
    elif lineup_query_mode == "lineup_leaderboard":
        route = "lineup_leaderboard"
        route_kwargs = {
            "season": season,
            "start_season": start_season,
            "end_season": end_season,
            "start_date": start_date,
            "end_date": end_date,
            "season_type": season_type,
            "team": team,
            "opponent": opponent,
            "lineup_members": lineup_members,
            "unit_size": unit_size,
            "minute_minimum": minute_minimum,
            "stat": stat,
            "limit": top_n or 10,
            "last_n": last_n,
        }

    # ---------------------------------------------------------------------------
    # Season-high / single-game-best routing
    # ---------------------------------------------------------------------------
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
    elif season_high_intent and not player and not player_a and not player_b:
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
            "wins_only": wins_only,
            "losses_only": losses_only,
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
        _fires, _note = streak_default_window(parsed)
        if _fires:
            notes.append(_note)
    elif (
        "top" in q
        and "games" in q
        and player is None
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
    elif "top team" in q or ("top" in q and "team games" in q):
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
                "last_n": last_n,
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
                "last_n": last_n,
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
                "home_only": home_only,
                "away_only": away_only,
                "wins_only": wins_only,
                "losses_only": losses_only,
                "last_n": last_n,
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
        or player_timeframe_summary_default(parsed)[0]
    ):
        route = "player_game_summary"
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

    out = dict(parsed)
    route_kwargs["back_to_back"] = back_to_back
    route_kwargs["rest_days"] = rest_days
    route_kwargs["one_possession"] = one_possession
    route_kwargs["nationally_televised"] = nationally_televised
    route_kwargs["role"] = role
    route_kwargs["opponent_quality"] = opponent_quality
    route_kwargs["quarter"] = quarter
    route_kwargs["half"] = half
    out["route"] = route
    out["route_kwargs"] = route_kwargs
    out["intent"] = route_to_intent(route, count_intent=count_intent)

    if clutch:
        notes.append(
            "clutch: filter detected but play-by-play clutch splits not yet available; "
            "results are unfiltered"
        )
    if period_note := build_period_filter_note(quarter=quarter, half=half):
        notes.append(period_note)
    notes.extend(
        build_game_context_filter_notes(
            back_to_back=back_to_back,
            rest_days=rest_days,
            one_possession=one_possession,
            nationally_televised=nationally_televised,
        )
    )
    if role_note := build_role_filter_note(role=role):
        notes.append(role_note)
    if opponent_quality_note := build_opponent_quality_note(opponent_quality=opponent_quality):
        notes.append(opponent_quality_note)
    if on_off_note := build_on_off_note(
        lineup_members=lineup_members,
        presence_state=presence_state,
    ):
        notes.append(on_off_note)
    if lineup_note := build_lineup_note(
        lineup_members=lineup_members,
        unit_size=unit_size,
        minute_minimum=minute_minimum,
    ):
        notes.append(lineup_note)

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
        "lineup_members",
        "presence_state",
        "unit_size",
        "minute_minimum",
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
