"""Heuristic confidence scoring and alternate-parse generation.

Computes a parse-wide confidence score (0–1) based on signals in the
parse state, and generates alternate interpretations for medium-confidence
parses.  Both are informational — they do not change routing.

Reference: parser specification §16.2 — Parse-level confidence.
Reference: parser specification §16.3–16.4 — Ambiguous inputs / alternates.
"""

from __future__ import annotations

from nbatools.commands._constants import ROUTE_TO_INTENT, QueryIntent


def compute_parse_confidence(parsed: dict) -> float:
    """Return a confidence score between 0.0 and 1.0 for *parsed*.

    Scoring signals (each adds or subtracts from a base of 0.70):

    - **Entity resolved**: player/team/comparison entities present → boost
    - **Entity ambiguity**: ``entity_ambiguity`` present → strong penalty
    - **Explicit intent**: an intent flag was set by the user → boost
    - **Default rule fired**: ``notes`` entry starting with ``"default:"`` → penalty
    - **Stat specified**: explicit stat → boost; implicit fallback → penalty
    - **Timeframe specified**: season/date/last-N → boost; none → penalty
    - **Threshold clarity**: explicit threshold → boost
    - **Route is None / unsupported**: large penalty
    """
    score = 0.70

    # --- Route present -------------------------------------------------
    if parsed.get("route") is None:
        # Unsupported / unroutable query
        return max(0.0, min(1.0, score - 0.40))

    # --- Entity signals ------------------------------------------------
    has_entity = bool(
        parsed.get("player") or parsed.get("team") or parsed.get("player_a") or parsed.get("team_a")
    )
    if has_entity:
        score += 0.08
    elif not parsed.get("leaderboard_intent") and not parsed.get("team_leaderboard_intent"):
        # No entity and not a league-wide leaderboard → uncertain
        score -= 0.05

    if parsed.get("entity_ambiguity"):
        score -= 0.20

    # --- Explicit intent signals ---------------------------------------
    explicit_intent = any(
        parsed.get(flag)
        for flag in (
            "summary_intent",
            "finder_intent",
            "count_intent",
            "record_intent",
            "split_intent",
            "career_intent",
            "season_high_intent",
            "streak_request",
            "team_streak_request",
            "head_to_head",
            "leaderboard_intent",
            "team_leaderboard_intent",
            "occurrence_event",
            "by_decade_intent",
            "playoff_history_intent",
            "playoff_appearance_intent",
        )
    )
    if explicit_intent:
        score += 0.10

    # --- Default rule fired --------------------------------------------
    notes = parsed.get("notes", [])
    default_count = sum(1 for n in notes if isinstance(n, str) and n.startswith("default:"))
    if default_count:
        score -= 0.08 * default_count

    # --- Stat resolution -----------------------------------------------
    stat_conf = parsed.get("stat_resolution_confidence", "none")
    if stat_conf == "confident":
        score += 0.05
    else:
        # No recognized stat — mild penalty (many queries legitimately omit it)
        score -= 0.03

    # --- Team resolution -----------------------------------------------
    team_conf = parsed.get("team_resolution_confidence", "none")
    if team_conf == "confident" and not has_entity:
        # Team was resolved but wasn't already counted in entity signals
        score += 0.04

    # --- Timeframe specified -------------------------------------------
    has_timeframe = bool(
        parsed.get("season")
        or parsed.get("start_season")
        or parsed.get("last_n")
        or parsed.get("start_date")
    )
    if has_timeframe:
        score += 0.05
    else:
        score -= 0.05

    # --- Threshold clarity ---------------------------------------------
    if parsed.get("min_value") is not None or parsed.get("max_value") is not None:
        score += 0.05

    return max(0.0, min(1.0, round(score, 4)))


def generate_alternates(parsed: dict) -> list[dict]:
    """Generate alternate interpretations for medium-confidence parses.

    Returns up to 2 alternates when confidence < 0.85 and a known
    ambiguity pattern matches.  Each alternate is a dict with keys:
    ``intent``, ``route``, ``description``, ``confidence``.

    Reference: parser specification §16.3 (common ambiguous inputs)
    and §16.4 (disambiguation strategy).
    """
    confidence = parsed.get("confidence", 1.0)
    if confidence >= 0.85:
        return []

    route = parsed.get("route")
    player = parsed.get("player")
    team = parsed.get("team")
    alternates: list[dict] = []

    # --- Team summary ↔ team record -----------------------------------
    # "Celtics recently" → primary: game_summary; alternate: team_record
    if route == "game_summary" and team and not player and not parsed.get("team_a"):
        alternates.append(
            {
                "intent": ROUTE_TO_INTENT.get("team_record", QueryIntent.SUMMARY),
                "route": "team_record",
                "description": f"{team} win-loss record",
                "confidence": round(confidence - 0.05, 4),
            }
        )

    # --- Player + opponent: finder ↔ summary --------------------------
    # "Tatum vs Knicks" → primary: finder; alternate: player summary
    if (
        route == "player_game_finder"
        and player
        and parsed.get("opponent")
        and not parsed.get("finder_intent")
    ):
        opp = parsed.get("opponent")
        alternates.append(
            {
                "intent": QueryIntent.SUMMARY,
                "route": "player_game_summary",
                "description": f"{player} averages vs {opp}",
                "confidence": round(confidence - 0.05, 4),
            }
        )

    # --- Player + occurrence event with no explicit intent -------------
    # "Jokic triple doubles" → primary: summary; alternate: game finder
    occ = parsed.get("occurrence_event")
    if route == "player_game_summary" and occ and player:
        event_label = occ.get("special_event") or occ.get("label") or "event"
        alternates.append(
            {
                "intent": QueryIntent.FINDER,
                "route": "player_game_finder",
                "description": f"{player} games with {event_label}",
                "confidence": round(confidence - 0.05, 4),
            }
        )

    # --- Season-high / best games: finder ↔ summary -------------------
    # "best games Booker" → primary: top-games finder; alternate: summary
    if (
        route == "player_game_finder"
        and parsed.get("season_high_intent")
        and player
        and not parsed.get("finder_intent")
    ):
        alternates.append(
            {
                "intent": QueryIntent.SUMMARY,
                "route": "player_game_summary",
                "description": f"{player} season averages",
                "confidence": round(confidence - 0.10, 4),
            }
        )

    # --- Team record ↔ team summary -----------------------------------
    # "Lakers this season" routed to team_record → alternate: game_summary
    if route == "team_record" and team and not player and not parsed.get("record_intent"):
        alternates.append(
            {
                "intent": ROUTE_TO_INTENT.get("game_summary", QueryIntent.SUMMARY),
                "route": "game_summary",
                "description": f"{team} recent game log",
                "confidence": round(confidence - 0.05, 4),
            }
        )

    return alternates[:2]
