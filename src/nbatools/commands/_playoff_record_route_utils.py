"""Playoff, record, and decade-bucketed route detection and routing helpers.

Extracted from natural_query.py to reduce file size and give the
playoff/record/decade route-family clearer ownership.
"""

from __future__ import annotations

import re

from nbatools.commands._leaderboard_utils import wants_ascending_leaderboard
from nbatools.commands._seasons import default_end_season, resolve_career
from nbatools.commands.playoff_history import ROUND_ALIASES

# ---------------------------------------------------------------------------
# Intent detection helpers
# ---------------------------------------------------------------------------


def detect_record_intent(text: str) -> bool:
    """Detect explicit record-oriented intent.

    Triggers on phrases that strongly signal the user wants a W/L record
    rather than stat averages.  Examples:
    - "best record since 2015"
    - "Lakers vs Celtics all-time record"
    - "home record", "away record", "playoff record"
    - "most wins since 2010", "which teams had the most wins"
    - "win percentage", "winning percentage"
    - "worst record"
    """
    return bool(
        re.search(
            r"\b(?:record|win(?:ning)?\s+(?:percent(?:age)?|pct)|win\s*%"
            r"|most\s+(?:home\s+|away\s+)?wins|most\s+(?:home\s+|away\s+)?losses"
            r"|fewest\s+(?:home\s+|away\s+)?losses"
            r"|best\s+(?:home\s+|away\s+|playoff\s+|postseason\s+)?record"
            r"|worst\s+(?:home\s+|away\s+|playoff\s+|postseason\s+)?record"
            r"|highest\s+win|lowest\s+win"
            r"|home\s+record|away\s+record"
            r"|playoff\s+record|postseason\s+record"
            r"|matchup\s+record|all[- ]?time\s+record)\b",
            text,
        )
    )


def detect_by_decade_intent(text: str) -> bool:
    """Detect 'by decade' bucketing intent."""
    return bool(re.search(r"\bby\s+decade\b", text))


def detect_playoff_appearance_intent(text: str) -> bool:
    """Detect intent for playoff/round appearance queries.

    Triggers on phrases like:
    - "finals appearances"
    - "playoff appearances"
    - "conference finals appearances"
    - "second round appearances"
    """
    return bool(
        re.search(
            r"\b(?:playoff|postseason|finals?|conference\s+finals?|"
            r"(?:first|1st|second|2nd)\s+round|semifinal)"
            r"\s+appearance",
            text,
        )
    )


def detect_playoff_history_intent(text: str) -> bool:
    """Detect explicit playoff history queries.

    Triggers on:
    - "playoff history"
    - "playoff series"
    - "postseason history"
    """
    return bool(
        re.search(
            r"\b(?:playoff|postseason)\s+(?:history|series)\b",
            text,
        )
    )


def detect_playoff_round_filter(text: str) -> str | None:
    """Extract a playoff round filter from natural language.

    Returns a round code ('01'-'04') or None.
    """
    # Receives pre-normalized (lowercased) text from _build_parse_state.
    t = text
    # Longest-match first to avoid "finals" matching before "conference finals"
    sorted_aliases = sorted(ROUND_ALIASES.keys(), key=len, reverse=True)
    for alias in sorted_aliases:
        if alias in t:
            return ROUND_ALIASES[alias]
    return None


def detect_by_round_intent(text: str) -> bool:
    """Detect 'by round' breakdown intent for playoff matchup history."""
    return bool(re.search(r"\bby\s+round\b", text))


# ---------------------------------------------------------------------------
# Route helpers — called from _finalize_route() in natural_query.py
# ---------------------------------------------------------------------------


def _resolve_season_defaults(
    season: str | None,
    start_season: str | None,
    end_season: str | None,
    season_type: str,
) -> tuple[str | None, str | None, str | None]:
    """Fill in season defaults using resolve_career when all are None."""
    if not season and not start_season and not end_season:
        start_season, end_season = resolve_career(season_type)
    return season, start_season, end_season


def try_playoff_record_route(parsed: dict) -> tuple[str, dict] | None:
    """Try to resolve a playoff/record/decade-bucketed route.

    Covers:
    - Playoff appearances
    - Playoff matchup history (team_a vs team_b)
    - Matchup by decade (team_a vs team_b)
    - Playoff history (single team)
    - Record by decade (single team)
    - Record by decade leaderboard
    - Playoff round record leaderboard
    - Playoff history with round filter (team + round + record)

    Returns ``(route, route_kwargs)`` or ``None`` if no match.
    """
    q = parsed["normalized_query"]
    season = parsed["season"]
    start_season = parsed["start_season"]
    end_season = parsed["end_season"]
    season_type = parsed["season_type"]
    player = parsed["player"]
    player_a = parsed["player_a"]
    player_b = parsed["player_b"]
    team = parsed["team"]
    team_a = parsed["team_a"]
    team_b = parsed["team_b"]
    opponent = parsed["opponent"]
    top_n = parsed.get("top_n")
    record_intent = parsed.get("record_intent", False)
    leaderboard_intent = parsed.get("leaderboard_intent", False)
    team_leaderboard_intent = parsed.get("team_leaderboard_intent", False)
    by_decade_intent = parsed.get("by_decade_intent", False)
    playoff_appearance_intent = parsed.get("playoff_appearance_intent", False)
    playoff_history_intent = parsed.get("playoff_history_intent", False)
    playoff_round_filter = parsed.get("playoff_round_filter")
    by_round_intent = parsed.get("by_round_intent", False)

    # -- Playoff appearance routing --
    if playoff_appearance_intent and not player_a and not player_b:
        pa_season, pa_start, pa_end = _resolve_season_defaults(
            season, start_season, end_season, "Playoffs"
        )
        return "playoff_appearances", {
            "team": team,
            "season": pa_season,
            "start_season": pa_start,
            "end_season": pa_end,
            "playoff_round": playoff_round_filter,
            "limit": top_n or 10,
            "ascending": False,
        }

    # -- Playoff matchup history: team_a vs team_b --
    if (
        (playoff_history_intent or (season_type == "Playoffs" and record_intent))
        and team_a
        and team_b
    ):
        pm_season, pm_start, pm_end = _resolve_season_defaults(
            season, start_season, end_season, "Playoffs"
        )
        return "playoff_matchup_history", {
            "team_a": team_a,
            "team_b": team_b,
            "season": pm_season,
            "start_season": pm_start,
            "end_season": pm_end,
            "playoff_round": playoff_round_filter,
            "by_round": by_round_intent,
        }

    # -- Matchup by decade: team_a vs team_b by decade --
    if by_decade_intent and team_a and team_b:
        md_season, md_start, md_end = _resolve_season_defaults(
            season, start_season, end_season, season_type
        )
        return "matchup_by_decade", {
            "team_a": team_a,
            "team_b": team_b,
            "season": md_season,
            "start_season": md_start,
            "end_season": md_end,
            "season_type": season_type,
        }

    # -- Playoff history: single team --
    if playoff_history_intent and team and not team_a and not team_b:
        ph_season, ph_start, ph_end = _resolve_season_defaults(
            season, start_season, end_season, "Playoffs"
        )
        return "playoff_history", {
            "team": team,
            "season": ph_season,
            "start_season": ph_start,
            "end_season": ph_end,
            "playoff_round": playoff_round_filter,
            "by_decade": by_decade_intent,
            "opponent": opponent,
        }

    # -- Record by decade: single team --
    if by_decade_intent and team and not team_a and not team_b:
        bd_season, bd_start, bd_end = _resolve_season_defaults(
            season, start_season, end_season, season_type
        )
        return "record_by_decade", {
            "team": team,
            "season": bd_season,
            "start_season": bd_start,
            "end_season": bd_end,
            "season_type": season_type,
            "opponent": opponent,
        }

    # -- Record by decade leaderboard: no specific team --
    if (
        by_decade_intent
        and (record_intent or leaderboard_intent or team_leaderboard_intent)
        and not team
        and not team_a
        and not team_b
        and not player
    ):
        bdl_season, bdl_start, bdl_end = _resolve_season_defaults(
            season, start_season, end_season, season_type
        )
        record_stat = "wins"
        if re.search(r"\bwin_pct\b|\bwin\s*%\b|\bwinning\s+pct\b", q):
            record_stat = "win_pct"
        elif re.search(r"\bloss", q):
            record_stat = "losses"

        return "record_by_decade_leaderboard", {
            "season": bdl_season,
            "start_season": bdl_start,
            "end_season": bdl_end,
            "season_type": season_type,
            "stat": record_stat,
            "limit": top_n or 10,
            "ascending": False,
            "playoff_round": playoff_round_filter,
        }

    # -- Playoff round record leaderboard --
    if (
        season_type == "Playoffs"
        and playoff_round_filter
        and record_intent
        and not team
        and not team_a
        and not team_b
        and not player
    ):
        prl_season, prl_start, prl_end = _resolve_season_defaults(
            season, start_season, end_season, "Playoffs"
        )
        record_stat = "win_pct"
        if re.search(r"\bmost\s+wins\b", q):
            record_stat = "wins"
        elif re.search(r"\bmost\s+loss", q):
            record_stat = "losses"

        return "playoff_round_record", {
            "season": prl_season,
            "start_season": prl_start,
            "end_season": prl_end,
            "playoff_round": playoff_round_filter,
            "stat": record_stat,
            "limit": top_n or 10,
            "ascending": False,
        }

    # -- Playoff history with round filter: team + playoff + round --
    if (
        team
        and not team_a
        and not team_b
        and season_type == "Playoffs"
        and playoff_round_filter
        and record_intent
    ):
        phrf_season, phrf_start, phrf_end = _resolve_season_defaults(
            season, start_season, end_season, "Playoffs"
        )
        return "playoff_history", {
            "team": team,
            "season": phrf_season,
            "start_season": phrf_start,
            "end_season": phrf_end,
            "playoff_round": playoff_round_filter,
            "by_decade": by_decade_intent,
            "opponent": opponent,
        }

    return None


def try_record_leaderboard_route(parsed: dict) -> tuple[str, dict, list[str]] | None:
    """Try to resolve a record-leaderboard route.

    Covers: "best record since 2015", "most wins since 2010",
    "highest win percentage", etc. — when no specific team is named.

    Returns ``(route, route_kwargs, notes)`` or ``None``.
    """
    q = parsed["normalized_query"]
    record_intent = parsed.get("record_intent", False)
    player = parsed["player"]
    player_a = parsed["player_a"]
    player_b = parsed["player_b"]
    team = parsed["team"]
    team_a = parsed["team_a"]
    team_b = parsed["team_b"]
    occurrence_event = parsed.get("occurrence_event")

    if not (
        record_intent
        and not player
        and not player_a
        and not player_b
        and not team
        and not team_a
        and not team_b
        and not occurrence_event
    ):
        return None

    season = parsed["season"]
    start_season = parsed["start_season"]
    end_season = parsed["end_season"]
    season_type = parsed["season_type"]
    opponent = parsed["opponent"]
    without_player = parsed.get("without_player")
    home_only = parsed["home_only"]
    away_only = parsed["away_only"]
    wins_only = parsed["wins_only"]
    losses_only = parsed["losses_only"]
    start_date = parsed.get("start_date")
    end_date = parsed.get("end_date")
    top_n = parsed.get("top_n")
    playoff_round_filter = parsed.get("playoff_round_filter")

    lb_season = season
    lb_start = start_season
    lb_end = end_season
    if not lb_season and not lb_start and not lb_end:
        lb_season = default_end_season(season_type)

    # Determine the sort stat from query phrasing
    record_stat = "win_pct"
    if re.search(r"\bmost\s+wins\b|\bmost\s+home\s+wins\b|\bmost\s+away\s+wins\b", q):
        record_stat = "wins"
    elif re.search(r"\bmost\s+loss", q):
        record_stat = "losses"
    elif re.search(r"\bfewest\s+loss", q):
        record_stat = "losses"

    lb_ascending = wants_ascending_leaderboard(q)
    # Smart ascending for record stats
    if re.search(r"\b(best|top|highest)\b", q):
        lb_ascending = False
    elif re.search(r"\b(worst|lowest|fewest)\b", q):
        lb_ascending = True
        if record_stat == "losses":
            lb_ascending = True  # fewest losses is ascending

    notes: list[str] = []
    route = "team_record_leaderboard"

    # If a playoff round filter is detected, redirect to playoff_round_record
    if playoff_round_filter:
        route = "playoff_round_record"
        if not lb_season and not lb_start and not lb_end:
            lb_start, lb_end = resolve_career("Playoffs")
            lb_season = None
        route_kwargs = {
            "season": lb_season,
            "start_season": lb_start,
            "end_season": lb_end,
            "playoff_round": playoff_round_filter,
            "stat": record_stat,
            "limit": top_n or 10,
            "ascending": lb_ascending,
        }
    else:
        route_kwargs = {
            "season": lb_season,
            "start_season": lb_start,
            "end_season": lb_end,
            "season_type": season_type,
            "stat": record_stat,
            "opponent": opponent,
            "without_player": without_player,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "limit": top_n or 10,
            "ascending": lb_ascending,
            "start_date": start_date,
            "end_date": end_date,
        }

    return route, route_kwargs, notes
