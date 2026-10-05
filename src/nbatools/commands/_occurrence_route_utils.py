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


_RANKED_COUNT = re.compile(r"\b(?:top|best|worst|highest|lowest|biggest|greatest)\s*$")


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
        for m in re.finditer(pattern, text):
            # "top 5 scoring games": a count of games to list, not 5+ points.
            if _RANKED_COUNT.search(text[: m.start()]):
                continue
            return _threshold_condition(stat, m.group(1), m.group(0))

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
            return _threshold_condition(stat, m.group(1), m.group(0))

    return None


def _threshold_condition(stat: str, number: str, phrase: str) -> dict:
    """One "N stat" game condition: at least N, except a bare zero.

    "10 assist games" means ten or more, but "0 turnover games" means none at
    all. Reading zero as a lower bound made every game qualify, so "10+
    assists and 0 turnovers" silently counted every 10-assist game. "0+"
    keeps its literal at-least reading.
    """
    value = float(number)
    if value == 0 and "+" not in phrase and "or more" not in phrase:
        return {"stat": stat, "min_value": None, "max_value": 0.0}
    return {"stat": stat, "min_value": value}


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

_COMPOUND_STAT_WORDS = (
    r"points?|pts|rebounds?|reb|assists?|ast|steals?|stl|"
    r"blocks?|blk|threes?|3pm|3s|fg3m|three-pointers?|turnovers?|tov"
)

#: "0", "zero" and "no" all state an exact zero ("a 10-assist, no-turnover game").
_CONDITION_NUMBER = r"(\d+\+?|zero|no)"

# A run of two or more "N stat" adjectives describing one game: "30 point 10
# rebound games", "30-point, 10-rebound games", "25 point 10 rebound 5 assist
# games", "10 assist 0 turnover games". Every adjective is a condition on the
# same game, exactly as "games with 30+ points and 10+ rebounds" states them.
_ADJECTIVE_CHAIN = re.compile(
    rf"(?:(?<=\s)|^){_CONDITION_NUMBER}\s*[- ]?\s*({_COMPOUND_STAT_WORDS})"
    rf"(?:(?:\s*,\s*|\s+(?:and|&)\s+|\s+){_CONDITION_NUMBER}\s*[- ]?\s*({_COMPOUND_STAT_WORDS}))+"
    r"\s+(?:games?|performances?|nights?|outings?|stat\s*lines?)\b"
)
_CHAIN_PART = re.compile(rf"{_CONDITION_NUMBER}\s*[- ]?\s*({_COMPOUND_STAT_WORDS})\b")

# Fan shorthand for points and rebounds, "30 and 10 games" / "30/10 games".
# The same reading and bounds the finder threshold parser already applies.
_FAN_COMBO = re.compile(r"(?<!\bbetween )\b(\d{1,2})\s*(?:and\s+|/\s*)?(\d{1,2})\s+games?\b")


def _chain_conditions(text: str) -> list[dict] | None:
    match = _ADJECTIVE_CHAIN.search(text)
    if match is None:
        return None
    conditions: list[dict] = []
    seen: set[str] = set()
    for number, stat_word in _CHAIN_PART.findall(match.group(0)):
        stat = _COMPOUND_STAT_MAP.get(stat_word)
        if stat is None or stat in seen:
            return None
        seen.add(stat)
        digits = "0" if number in ("zero", "no") else number.rstrip("+")
        conditions.append(_threshold_condition(stat, digits, number))
    return conditions if len(conditions) >= 2 else None


def _fan_combo_conditions(text: str) -> list[dict] | None:
    for match in _FAN_COMBO.finditer(text):
        pts_value, reb_value = int(match.group(1)), int(match.group(2))
        if 10 <= pts_value <= 60 and 5 <= reb_value <= 30 and pts_value >= reb_value:
            return [
                {"stat": "pts", "min_value": float(pts_value)},
                {"stat": "reb", "min_value": float(reb_value)},
            ]
    return None


# A verb can carry the stat the number belongs to, with the stat noun left out:
# "games scoring 120+ and making 15+ threes" states two conditions, but only the
# second one names its stat. Reading only the named half turned a two-condition
# question into an ordinary threes leaderboard. Every verb here already carries
# the same stat in ``extract_occurrence_event``'s "games scoring/grabbing/dishing
# N ..." patterns, so this adds no new vocabulary - only the elliptical form.
_ELLIPTICAL_STAT_VERBS = (
    (r"\b(?:scoring|scored|scores)\s+(\d+)\+?", "pts"),
    (r"\b(?:grabbing|grabbed|grabs)\s+(\d+)\+?", "reb"),
    (r"\b(?:dishing|dished|dishes)\s+(\d+)\+?", "ast"),
)


def _parse_single_threshold(text: str) -> dict | None:
    """Parse a single threshold phrase like '30+ points' or '10 rebounds'.

    Returns {"stat": str, "min_value": float} or None if no match.
    """
    # Pattern: "NUMBER+ STAT" or "NUMBER STAT" or "under NUMBER STAT"
    # Examples: "30+ points", "10 rebounds", "5+ threes", "under 10 turnovers"

    # Upper bounds. "under 2 turnovers" / "fewer than 2" are strict; "at most 1
    # turnover" / "1 or fewer turnovers" include the number. Read as a bare
    # number they became lower bounds ("at most 1 turnover" counted tov >= 1).
    stat_words = _COMPOUND_STAT_WORDS
    for pattern, strict in (
        (rf"\b(?:under|fewer\s+than|less\s+than)\s+(\d+)\+?\s+({stat_words})\b", True),
        (
            rf"\b(?:at\s+most|no\s+more\s+than|a\s+max(?:imum)?\s+of|max(?:imum)?(?:\s+of)?)"
            rf"\s+(\d+)\s+({stat_words})\b",
            False,
        ),
        (rf"\b(\d+)\s+or\s+(?:fewer|less)\s+({stat_words})\b", False),
        (rf"\b(\d+)\s+({stat_words})\s+or\s+(?:fewer|less)\b", False),
    ):
        bound_match = re.search(pattern, text)
        if bound_match:
            stat = _COMPOUND_STAT_MAP.get(bound_match.group(2))
            if stat:
                value = float(bound_match.group(1))
                # "under 10" means < 10
                return {"stat": stat, "max_value": value - 0.0001 if strict else value}

    # Standard patterns: "30+ points", "10 rebounds", "0 turnovers", "no turnovers"
    standard_match = re.search(
        r"\b(\d+\+?|zero|no)\s+(points?|pts|rebounds?|reb|assists?|ast|steals?|stl|"
        r"blocks?|blk|threes?|3pm|3s|fg3m|three-pointers?|turnovers?|tov)\b(\s+or\s+more)?",
        text,
    )
    if standard_match:
        number = standard_match.group(1)
        stat_text = standard_match.group(2)  # already lowercase from pipeline normalization
        stat = _COMPOUND_STAT_MAP.get(stat_text)
        if stat:
            digits = "0" if number in ("zero", "no") else number.rstrip("+")
            return _threshold_condition(stat, digits, standard_match.group(0))

    # Verb-carried stat with the noun elided ("scoring 120+"). Tried last so an
    # explicit stat noun always wins: "scoring 30+ rebounds" stays rebounds.
    for pattern, stat in _ELLIPTICAL_STAT_VERBS:
        elliptical_match = re.search(pattern, text)
        if elliptical_match:
            return {"stat": stat, "min_value": float(elliptical_match.group(1))}

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

    chain = _chain_conditions(text_lower)
    if chain:
        return chain
    combo = _fan_combo_conditions(text_lower)
    if combo:
        return combo

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
        rf"(\d+\+?)\s*({_COMPOUND_STAT_WORDS})\s+(?:and|&)\s+(\d+\+?)\s*({_COMPOUND_STAT_WORDS})"
    )

    compound_match = re.search(compound_pattern, text_lower)
    if compound_match:
        stat1 = _COMPOUND_STAT_MAP.get(compound_match.group(2))  # already lowercase
        stat2 = _COMPOUND_STAT_MAP.get(compound_match.group(4))
        if stat1 and stat2 and stat1 != stat2:
            return [
                _threshold_condition(
                    stat1, compound_match.group(1).rstrip("+"), compound_match.group(1)
                ),
                _threshold_condition(
                    stat2, compound_match.group(3).rstrip("+"), compound_match.group(3)
                ),
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
    event = extract_occurrence_event(text) or extract_compound_occurrence_event(text)
    if event is None:
        return False

    return bool(
        re.search(
            # "at most 1 turnover" is a bound, not a ranking.
            r"\b((?<!\bat )(?<!\bno )most|leaders?|top(?:\s+\d+)?|rank|ranked|ranking"
            r"|who\s+leads?)\b",
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
        # A league-wide count ("how often has a player had ...") counts games,
        # not one row of a top-10 board; the league game finder answers it.
        if count_intent and not occurrence_leaderboard_intent and not player:
            return None
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
        and not re.match(r"games_\d", detect_player_leaderboard_stat(q) or "")
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
                "max_value": occurrence_event.get("max_value"),
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
            "max_value": occurrence_event.get("max_value"),
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
    """Defer single-player special-event counts to ``player_game_finder``.

    Count phrasing like ``count Jokic triple doubles since 2021`` should stay
    on the player finder/count contract instead of broadening into occurrence
    leaderboard rows.
    """
    return None


# A league-wide list of matching player games: "games with 10+ assists and 0
# turnovers", "show me 30 point 10 rebound games this season", "who had a
# triple double last night". The question names game conditions and asks to
# see the games, with no player or team as the subject.
_GAME_LIST_WORDING = re.compile(
    r"^(?:(?:show|list|find|give)\s+(?:me\s+)?(?:all\s+|every\s+)?)?(?:the\s+|any\s+)?"
    r"(?:player\s+)?games?\s+(?:with|where|in\s+which|that)\b"
    r"|\b(?:who|which\s+players?|what\s+players?|any\s+players?|anyone)\s+(?:had|has|have|got|posted|recorded)\b"
    r"|\b(?:show|list|find|give)\s+(?:me\s+)?(?:all\s+|every\s+)?(?:the\s+)?[\w\s+/-]*\bgames?\b"
)


# Wording a league game list or count is allowed to contain besides its
# conditions and the scope the parser resolved.
_GAME_LIST_GRAMMAR = (
    r"\b\d+(?:\.\d+)?\+?",
    rf"\b(?:{_COMPOUND_STAT_WORDS})\b",
    r"\b(?:zero|no|under|over|at\s+least|or\s+more|more\s+than|fewer\s+than|less\s+than)\b",
    r"\btriple[- ]?doubles?\b|\bdouble[- ]?doubles?\b",
    r"\b(?:games?|performances?|nights?|outings?|times?|stat\s*lines?|occasions?)\b",
    r"\b(?:how\s+many|how\s+often|count|number\s+of|total)\b",
    r"\b(?:show|list|find|give|me|all|every|there|been|anyone|any|player)\b",
    r"\b(?:with|where|which|that|had|has|have|got|posted|recorded|put\s+up|did)\b",
    r"\b(?:this|current|so\s+far|seasons?|years?)\b",
)


def _unaccounted_words(q: str, parsed: dict) -> list[str]:
    from nbatools.commands._leaderboard_eligibility import _claimed_ranges, _residual_tokens

    ranges = _claimed_ranges(q, parsed, None)
    for pattern in _GAME_LIST_GRAMMAR:
        ranges.extend(m.span() for m in re.finditer(pattern, q))
    return _residual_tokens(q, ranges)


def try_league_game_finder_route(parsed: dict) -> tuple[str, dict] | None:
    """Route a subjectless list of player games that meet game conditions."""
    q = parsed["normalized_query"]
    if any(
        parsed.get(key) for key in ("player", "player_a", "player_b", "team", "team_a", "team_b")
    ):
        return None
    if parsed.get("occurrence_leaderboard_intent"):
        return None
    count_intent = bool(parsed.get("count_intent"))
    if re.search(r"\bteams?\b", q) or not (count_intent or _GAME_LIST_WORDING.search(q)):
        return None

    if _unaccounted_words(q, parsed):
        # An unread word may be a misspelled player or team; a league-wide
        # answer would silently drop that subject.
        return None

    compound = parsed.get("compound_occurrence_conditions") or []
    event = parsed.get("occurrence_event") or {}
    kwargs: dict = {}
    if len(compound) >= 2:
        kwargs["conditions"] = [dict(c) for c in compound]
    elif event.get("special_event"):
        kwargs["special_event"] = event["special_event"]
    elif event.get("stat"):
        kwargs.update(
            stat=event["stat"],
            min_value=event.get("min_value"),
            max_value=event.get("max_value"),
        )
    else:
        return None

    season = parsed["season"]
    if not season and not parsed["start_season"] and not parsed["end_season"]:
        season = default_end_season(parsed["season_type"])
    return "player_game_finder", {
        "season": season,
        "start_season": parsed["start_season"],
        "end_season": parsed["end_season"],
        "start_date": parsed.get("start_date"),
        "end_date": parsed.get("end_date"),
        "season_type": parsed["season_type"],
        "opponent": parsed["opponent"],
        "home_only": parsed["home_only"],
        "away_only": parsed["away_only"],
        "wins_only": parsed["wins_only"],
        "losses_only": parsed["losses_only"],
        "limit": None if count_intent else 25,
        "sort_by": "game_date",
        "ascending": False,
        **kwargs,
    }


# Wording a league streak ranking may contain besides its condition and scope:
# "who has the longest 30 point streak this season", "longest winning streak".
_STREAK_GRAMMAR = (
    r"\b(?:streaks?|straight|consecutive|longest|most|current|active|ongoing|running)\b",
    r"\b(?:win(?:ning)?|los(?:ing|s))\b",
    r"\b(?:who|which|what|players?|teams?|of|the|a|an|in|is|are|league|nba)\b",
)


def _opponent_group_span(q: str, parsed: dict) -> tuple[int, int] | None:
    """Where "vs the West" / "against Pacific teams" names the resolved group."""
    conference, division = parsed.get("opponent_conference"), parsed.get("opponent_division")
    if conference:
        word = r"(?:the\s+)?" + str(conference).lower() + r"(?:ern)?(?:\s+conference)?"
    elif division:
        word = r"(?:the\s+)?" + re.escape(str(division).lower()) + r"(?:\s+division)?"
    else:
        return None
    match = re.search(rf"\b(?:against|vs\.?|versus)\s+{word}\b", q)
    return match.span() if match else None


def try_league_streak_route(parsed: dict) -> tuple[str, dict] | None:
    """Rank every player (or team) by their longest or current streak."""
    q = parsed["normalized_query"]
    if any(
        parsed.get(key) for key in ("player", "player_a", "player_b", "team", "team_a", "team_b")
    ):
        return None
    player_request = parsed.get("streak_request")
    team_request = parsed.get("team_streak_request")
    if team_request and (
        team_request.get("special_condition") in ("wins", "losses") or re.search(r"\bteams?\b", q)
    ):
        route, request, subject_key = "team_streak_finder", team_request, "team"
    elif player_request:
        route, request, subject_key = "player_streak_finder", player_request, "player"
    else:
        return None

    from nbatools.commands._leaderboard_eligibility import _claimed_ranges, _residual_tokens

    ranges = _claimed_ranges(q, parsed, None)
    for pattern in (*_GAME_LIST_GRAMMAR, *_STREAK_GRAMMAR):
        ranges.extend(m.span() for m in re.finditer(pattern, q))
    if group_span := _opponent_group_span(q, parsed):
        # "longest winning streak vs the East": the group is read upstream and
        # applied season by season on the streak finders. Only that one
        # phrase is accounted for; a second group word stays unread.
        ranges.append(group_span)
    if _residual_tokens(q, ranges):
        # An unread word may be a misspelled player or team; a league-wide
        # ranking would silently drop that subject.
        return None

    season = parsed["season"]
    if not season and not parsed["start_season"] and not parsed["end_season"]:
        # "this season" carries no explicit season of its own.
        season = default_end_season(parsed["season_type"])
    kwargs = {
        "season": season,
        "start_season": parsed["start_season"],
        "end_season": parsed["end_season"],
        "season_type": parsed["season_type"],
        subject_key: None,
        "opponent": parsed["opponent"],
        "home_only": parsed["home_only"],
        "away_only": parsed["away_only"],
        "start_date": parsed.get("start_date"),
        "end_date": parsed.get("end_date"),
        "last_n": parsed.get("last_n"),
        "stat": request.get("stat"),
        "min_value": request.get("min_value"),
        "max_value": request.get("max_value"),
        "special_condition": request.get("special_condition"),
        "min_streak_length": request.get("min_streak_length"),
        "longest": True,
        "current": bool(request.get("current")),
        "limit": 10,
    }
    if request.get("conditions"):
        kwargs["conditions"] = request["conditions"]
    return route, kwargs
