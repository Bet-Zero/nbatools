"""Occurrence and compound-occurrence detection, extraction, and route helpers.

Extracted from natural_query.py to reduce file size and give the
occurrence route-family clearer ownership.
"""

from __future__ import annotations

import re

from nbatools.commands._seasons import default_end_season

# ---------------------------------------------------------------------------
# Single occurrence event extraction
# ---------------------------------------------------------------------------


def extract_occurrence_event(text: str) -> dict | None:
    """Detect and extract an occurrence-event definition from natural language.

    Returns a dict with either:
    - {"stat": str, "min_value": float}  for single-stat thresholds
    - {"special_event": str}  for multi-stat events (triple_double, double_double)

    Returns None if no occurrence event is detected.

    Examples:
        "40 point games"       → {"stat": "pts", "min_value": 40}
        "40-point games"       → {"stat": "pts", "min_value": 40}
        "5+ three games"       → {"stat": "fg3m", "min_value": 5}
        "triple doubles"       → {"special_event": "triple_double"}
        "double doubles"       → {"special_event": "double_double"}
        "15 rebound games"     → {"stat": "reb", "min_value": 15}
        "120 point games"      → {"stat": "pts", "min_value": 120}
        "games with 5+ threes" → {"stat": "fg3m", "min_value": 5}
    """
    # Special events: triple double / double double
    if re.search(r"\btriple[- ]?doubles?\b", text):
        return {"special_event": "triple_double"}
    if re.search(r"\bdouble[- ]?doubles?\b", text):
        return {"special_event": "double_double"}

    # Pattern: "NUMBER+ STAT games" or "NUMBER STAT games" or "NUMBER-STAT games"
    stat_event_patterns = [
        # "40+ point games", "5+ three games", "15+ rebound games"
        (r"\b(\d+)\+?\s*[- ]?(point|pts|scoring)\s+games?\b", "pts"),
        (r"\b(\d+)\+?\s*[- ]?(rebound|reb|rebounds)\s+games?\b", "reb"),
        (r"\b(\d+)\+?\s*[- ]?(assist|ast|assists)\s+games?\b", "ast"),
        (r"\b(\d+)\+?\s*[- ]?(steal|stl|steals)\s+games?\b", "stl"),
        (r"\b(\d+)\+?\s*[- ]?(block|blk|blocks)\s+games?\b", "blk"),
        (r"\b(\d+)\+?\s*[- ]?(three|3pm|threes|3s|three-pointer|fg3m)\s+games?\b", "fg3m"),
        (r"\b(\d+)\+?\s*[- ]?(turnover|tov|turnovers)\s+games?\b", "tov"),
    ]

    for pattern, stat in stat_event_patterns:
        m = re.search(pattern, text)
        if m:
            return {"stat": stat, "min_value": float(m.group(1))}

    # Pattern: "games with NUMBER+ STAT" or "games scoring NUMBER+"
    games_with_patterns = [
        (r"\bgames?\s+(?:with|scoring|of)\s+(\d+)\+?\s+(?:or\s+more\s+)?(points?|pts)\b", "pts"),
        (r"\bgames?\s+(?:with|grabbing)\s+(\d+)\+?\s+(?:or\s+more\s+)?(rebounds?|reb)\b", "reb"),
        (r"\bgames?\s+(?:with|dishing)\s+(\d+)\+?\s+(?:or\s+more\s+)?(assists?|ast)\b", "ast"),
        (r"\bgames?\s+(?:with)\s+(\d+)\+?\s+(?:or\s+more\s+)?(steals?|stl)\b", "stl"),
        (r"\bgames?\s+(?:with)\s+(\d+)\+?\s+(?:or\s+more\s+)?(blocks?|blk)\b", "blk"),
        (
            r"\bgames?\s+(?:with)\s+(\d+)\+?\s+(?:or\s+more\s+)?(threes?|3pm|3s|fg3m|three-pointers?)\b",
            "fg3m",
        ),
        (r"\bgames?\s+(?:with)\s+(\d+)\+?\s+(?:or\s+more\s+)?(turnovers?|tov)\b", "tov"),
    ]

    for pattern, stat in games_with_patterns:
        m = re.search(pattern, text)
        if m:
            return {"stat": stat, "min_value": float(m.group(1))}

    return None


# ---------------------------------------------------------------------------
# Compound occurrence event extraction
# ---------------------------------------------------------------------------

# Stat aliases for compound occurrence parsing
_COMPOUND_STAT_MAP = {
    "points": "pts",
    "point": "pts",
    "pts": "pts",
    "rebounds": "reb",
    "rebound": "reb",
    "reb": "reb",
    "assists": "ast",
    "assist": "ast",
    "ast": "ast",
    "steals": "stl",
    "steal": "stl",
    "stl": "stl",
    "blocks": "blk",
    "block": "blk",
    "blk": "blk",
    "threes": "fg3m",
    "three": "fg3m",
    "3pm": "fg3m",
    "3s": "fg3m",
    "fg3m": "fg3m",
    "three-pointers": "fg3m",
    "three-pointer": "fg3m",
    "turnovers": "tov",
    "turnover": "tov",
    "tov": "tov",
}


def _parse_single_threshold(text: str) -> dict | None:
    """Parse a single threshold phrase like '30+ points' or '10 rebounds'.

    Returns {"stat": str, "min_value": float} or None if no match.
    """
    # Pattern: "NUMBER+ STAT" or "NUMBER STAT" or "under NUMBER STAT"
    # Examples: "30+ points", "10 rebounds", "5+ threes", "under 10 turnovers"

    # "under X stat" → max_value
    under_match = re.search(
        r"\bunder\s+(\d+)\+?\s+(points?|pts|rebounds?|reb|assists?|ast|steals?|stl|"
        r"blocks?|blk|threes?|3pm|3s|fg3m|three-pointers?|turnovers?|tov)\b",
        text,
    )
    if under_match:
        value = float(under_match.group(1))
        stat_text = under_match.group(2)  # already lowercase from pipeline normalization
        stat = _COMPOUND_STAT_MAP.get(stat_text)
        if stat:
            return {"stat": stat, "max_value": value - 0.0001}  # "under 10" means < 10

    # Standard patterns: "30+ points", "10 rebounds"
    standard_match = re.search(
        r"\b(\d+)\+?\s+(points?|pts|rebounds?|reb|assists?|ast|steals?|stl|"
        r"blocks?|blk|threes?|3pm|3s|fg3m|three-pointers?|turnovers?|tov)\b",
        text,
    )
    if standard_match:
        value = float(standard_match.group(1))
        stat_text = standard_match.group(2)  # already lowercase from pipeline normalization
        stat = _COMPOUND_STAT_MAP.get(stat_text)
        if stat:
            return {"stat": stat, "min_value": value}

    return None


def extract_compound_occurrence_event(text: str) -> list[dict] | None:
    """Extract compound occurrence conditions from natural language.

    Parses queries like:
    - "games with 30+ points and 10+ rebounds"
    - "40+ points and 5+ threes"
    - "25+ points and 10+ assists"
    - "120+ points and 15+ threes" (team)
    - "130+ points and under 10 turnovers"

    Returns a list of condition dicts:
    [{"stat": "pts", "min_value": 30}, {"stat": "reb", "min_value": 10}]

    Returns None if no compound pattern is detected or only single condition found.
    Only returns for queries that explicitly have AND between conditions.
    """
    # Check for compound pattern with " and " between thresholds
    # We need to detect patterns like "X+ stat and Y+ stat"
    # Receives pre-normalized (lowercased) text from _build_parse_state.
    text_lower = text

    # Must have "and" in the text for compound detection
    if " and " not in text_lower:
        return None

    # Split on " and " and try to parse each part
    # But be careful: "and" can appear in other contexts
    # We look for patterns like "NUMBER+ STAT and NUMBER+ STAT"

    # Pattern to detect compound occurrence: two or more threshold expressions connected by "and"
    # First, try to find all threshold patterns in the text

    # Also detect "under X stat" patterns

    # Find all threshold matches
    found_conditions: list[dict] = []
    seen_stats: set[str] = set()

    # Check for pattern like "NUMBER+ STAT and NUMBER+ STAT"
    compound_pattern = (
        r"(\d+)\+?\s*(points?|pts|rebounds?|reb|assists?|ast|steals?|stl|"
        r"blocks?|blk|threes?|3pm|3s|fg3m|three-pointers?|turnovers?|tov)\s+"
        r"(?:and|&)\s+"
        r"(\d+)\+?\s*(points?|pts|rebounds?|reb|assists?|ast|steals?|stl|"
        r"blocks?|blk|threes?|3pm|3s|fg3m|three-pointers?|turnovers?|tov)"
    )

    compound_match = re.search(compound_pattern, text_lower)
    if compound_match:
        # Extract both conditions
        val1 = float(compound_match.group(1))
        stat1 = _COMPOUND_STAT_MAP.get(compound_match.group(2))  # already lowercase
        val2 = float(compound_match.group(3))
        stat2 = _COMPOUND_STAT_MAP.get(compound_match.group(4))  # already lowercase

        if stat1 and stat2 and stat1 != stat2:
            return [
                {"stat": stat1, "min_value": val1},
                {"stat": stat2, "min_value": val2},
            ]

    # Try more flexible parsing: look at " and " separated parts
    # Split on " and " and parse each segment
    parts = re.split(r"\s+and\s+", text_lower)

    if len(parts) >= 2:
        # Check if multiple parts contain threshold patterns
        for part in parts:
            cond = _parse_single_threshold(part)
            if cond:
                stat = cond.get("stat")
                if stat and stat not in seen_stats:
                    found_conditions.append(cond)
                    seen_stats.add(stat)

    # Only return if we found 2+ distinct conditions
    if len(found_conditions) >= 2:
        return found_conditions

    return None


def wants_occurrence_leaderboard(text: str) -> bool:
    """Detect if the query is asking for an occurrence leaderboard.

    Triggers on patterns like:
    - "most 40 point games since 2015"
    - "leaders in triple doubles since 2020"
    - "who has the most 5+ three games"
    """
    event = extract_occurrence_event(text)
    if event is None:
        return False

    return bool(
        re.search(
            r"\b(most|leaders?|top(?:\s+\d+)?|rank|ranked|ranking|who\s+has\s+the\s+most|who\s+leads?)\b",
            text,
        )
    )


# ---------------------------------------------------------------------------
# Route helpers — called from _finalize_route() in natural_query.py
# ---------------------------------------------------------------------------


def try_compound_occurrence_route(parsed: dict) -> tuple[str, dict] | None:
    """Try to resolve a compound-occurrence or occurrence-leaderboard route.

    Covers:
    - Compound occurrence routing (multiple AND thresholds)
    - Single occurrence leaderboard routing (player/team)

    Returns ``(route, route_kwargs)`` or ``None`` if no occurrence route matches.
    """
    q = parsed["normalized_query"]
    compound_occurrence_conditions = parsed.get("compound_occurrence_conditions")
    occurrence_event = parsed.get("occurrence_event")
    occurrence_leaderboard_intent = parsed.get("occurrence_leaderboard_intent", False)
    count_intent = parsed.get("count_intent", False)
    team_leaderboard_intent = parsed.get("team_leaderboard_intent", False)
    stat = parsed.get("stat")
    min_value = parsed.get("min_value")
    max_value = parsed.get("max_value")
    season = parsed["season"]
    start_season = parsed["start_season"]
    end_season = parsed["end_season"]
    season_type = parsed["season_type"]
    opponent = parsed["opponent"]
    home_only = parsed["home_only"]
    away_only = parsed["away_only"]
    wins_only = parsed["wins_only"]
    losses_only = parsed["losses_only"]
    start_date = parsed.get("start_date")
    end_date = parsed.get("end_date")
    top_n = parsed.get("top_n")
    player = parsed["player"]
    player_a = parsed["player_a"]
    player_b = parsed["player_b"]
    team = parsed["team"]
    team_a = parsed["team_a"]
    team_b = parsed["team_b"]

    from nbatools.commands._leaderboard_utils import detect_player_leaderboard_stat

    team_how_often_threshold = bool(
        re.search(r"\bhow\s+often\b", q)
        and re.search(r"\bteams?\b", q)
        and not re.search(r"\bplayers?\b", q)
    )

    if (
        (count_intent or team_how_often_threshold)
        and not occurrence_event
        and stat
        and min_value is not None
        and max_value is None
        and not player
        and not player_a
        and not player_b
        and re.search(r"\bteams?\b", q)
    ):
        occ_season = season
        occ_start = start_season
        occ_end = end_season
        if not occ_season and not occ_start and not occ_end:
            occ_season = default_end_season(season_type)

        return "team_occurrence_leaders", {
            "stat": stat,
            "min_value": min_value,
            "season": occ_season,
            "start_season": occ_start,
            "end_season": occ_end,
            "season_type": season_type,
            "opponent": opponent,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "start_date": start_date,
            "end_date": end_date,
            "limit": top_n or 10,
        }

    if count_intent and player and not compound_occurrence_conditions:
        points_rebounds_match = re.search(
            r"\b30\+?\s*(?:points?|pts)?\s+10\+?\s*(?:rebounds?|reb)?\b",
            q,
        )
        if points_rebounds_match:
            compound_occurrence_conditions = [
                {"stat": "pts", "min_value": 30.0},
                {"stat": "reb", "min_value": 10.0},
            ]

    # -----------------------------------------------------------------------
    # Compound occurrence routing
    # -----------------------------------------------------------------------
    if (
        compound_occurrence_conditions
        and len(compound_occurrence_conditions) >= 2
        and not re.search(r"\b(last|past|recent)\s+\d+\s+games?\b", q)
        and (occurrence_leaderboard_intent or count_intent or team_leaderboard_intent)
    ):
        occ_season = season
        occ_start = start_season
        occ_end = end_season
        if not occ_season and not occ_start and not occ_end:
            occ_season = default_end_season(season_type)

        is_team_occurrence = (
            bool(
                re.search(r"\bteam\b|\bteams?\b", q)
                and not re.search(r"\bplayer\b|\bplayers?\b", q)
            )
            or team_leaderboard_intent
            or (team and not player)
        )

        # Single player compound occurrence count
        if player and not player_a and not player_b and count_intent:
            return "player_occurrence_leaders", {
                "conditions": compound_occurrence_conditions,
                "season": occ_season,
                "start_season": occ_start,
                "end_season": occ_end,
                "season_type": season_type,
                "opponent": opponent,
                "home_only": home_only,
                "away_only": away_only,
                "wins_only": wins_only,
                "losses_only": losses_only,
                "start_date": start_date,
                "end_date": end_date,
                "limit": 500,  # Large limit to ensure player is included
                "player": player,  # Filter to this player
            }
        # Single team compound occurrence count
        if team and not team_a and not team_b and (count_intent or is_team_occurrence):
            return "team_occurrence_leaders", {
                "conditions": compound_occurrence_conditions,
                "season": occ_season,
                "start_season": occ_start,
                "end_season": occ_end,
                "season_type": season_type,
                "opponent": opponent,
                "home_only": home_only,
                "away_only": away_only,
                "wins_only": wins_only,
                "losses_only": losses_only,
                "start_date": start_date,
                "end_date": end_date,
                "limit": 500 if count_intent else (top_n or 10),
                "team": team,  # Filter to this team
            }
        # Team compound occurrence leaderboard (no specific team)
        if is_team_occurrence and not player and not player_a and not player_b:
            return "team_occurrence_leaders", {
                "conditions": compound_occurrence_conditions,
                "season": occ_season,
                "start_season": occ_start,
                "end_season": occ_end,
                "season_type": season_type,
                "opponent": opponent,
                "home_only": home_only,
                "away_only": away_only,
                "wins_only": wins_only,
                "losses_only": losses_only,
                "start_date": start_date,
                "end_date": end_date,
                "limit": top_n or 10,
            }
        # Player compound occurrence leaderboard (no specific player)
        return "player_occurrence_leaders", {
            "conditions": compound_occurrence_conditions,
            "season": occ_season,
            "start_season": occ_start,
            "end_season": occ_end,
            "season_type": season_type,
            "opponent": opponent,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "start_date": start_date,
            "end_date": end_date,
            "limit": top_n or 10,
        }

    # -----------------------------------------------------------------------
    # Single occurrence leaderboard routing
    # -----------------------------------------------------------------------
    if (
        occurrence_leaderboard_intent
        and occurrence_event
        and not player
        and not player_a
        and not player_b
        and not (detect_player_leaderboard_stat(q) or "").startswith("games_")
    ):
        occ_season = season
        occ_start = start_season
        occ_end = end_season
        if not occ_season and not occ_start and not occ_end:
            occ_season = default_end_season(season_type)

        is_team_occurrence = (
            bool(
                re.search(r"\bteam\b|\bteams?\b", q)
                and not re.search(r"\bplayer\b|\bplayers?\b", q)
            )
            or team_leaderboard_intent
        )

        if is_team_occurrence:
            occ_stat = occurrence_event.get("stat", "pts")
            occ_min = occurrence_event.get("min_value", 100)
            return "team_occurrence_leaders", {
                "stat": occ_stat,
                "min_value": occ_min,
                "season": occ_season,
                "start_season": occ_start,
                "end_season": occ_end,
                "season_type": season_type,
                "opponent": opponent,
                "home_only": home_only,
                "away_only": away_only,
                "wins_only": wins_only,
                "losses_only": losses_only,
                "start_date": start_date,
                "end_date": end_date,
                "limit": top_n or 10,
            }
        if "special_event" in occurrence_event:
            return "player_occurrence_leaders", {
                "special_event": occurrence_event["special_event"],
                "season": occ_season,
                "start_season": occ_start,
                "end_season": occ_end,
                "season_type": season_type,
                "opponent": opponent,
                "home_only": home_only,
                "away_only": away_only,
                "wins_only": wins_only,
                "losses_only": losses_only,
                "start_date": start_date,
                "end_date": end_date,
                "limit": top_n or 10,
            }
        return "player_occurrence_leaders", {
            "stat": occurrence_event.get("stat"),
            "min_value": occurrence_event.get("min_value"),
            "season": occ_season,
            "start_season": occ_start,
            "end_season": occ_end,
            "season_type": season_type,
            "opponent": opponent,
            "home_only": home_only,
            "away_only": away_only,
            "wins_only": wins_only,
            "losses_only": losses_only,
            "start_date": start_date,
            "end_date": end_date,
            "limit": top_n or 10,
        }

    return None


def try_occurrence_count_route(parsed: dict) -> tuple[str, dict] | None:
    """Try to resolve a single-player special-event occurrence count route.

    Covers queries like: "count Jokic triple doubles since 2021"

    Returns ``(route, route_kwargs)`` or ``None``.
    """
    count_intent = parsed.get("count_intent", False)
    occurrence_event = parsed.get("occurrence_event")
    player = parsed["player"]
    player_a = parsed["player_a"]
    player_b = parsed["player_b"]

    if not (
        count_intent
        and occurrence_event
        and "special_event" in occurrence_event
        and player
        and not player_a
        and not player_b
    ):
        return None

    season = parsed["season"]
    start_season = parsed["start_season"]
    end_season = parsed["end_season"]
    season_type = parsed["season_type"]

    occ_season = season
    occ_start = start_season
    occ_end = end_season
    if not occ_season and not occ_start and not occ_end:
        occ_season = default_end_season(season_type)

    return "player_occurrence_leaders", {
        "special_event": occurrence_event["special_event"],
        "season": occ_season,
        "start_season": occ_start,
        "end_season": occ_end,
        "season_type": season_type,
        "opponent": parsed["opponent"],
        "home_only": parsed["home_only"],
        "away_only": parsed["away_only"],
        "wins_only": parsed["wins_only"],
        "losses_only": parsed["losses_only"],
        "start_date": parsed.get("start_date"),
        "end_date": parsed.get("end_date"),
        "limit": 500,  # large limit to ensure player is included
        "player": player,  # Filter to this player
    }
