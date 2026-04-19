"""Heuristic confidence scoring for parsed queries.

Computes a parse-wide confidence score (0–1) based on signals in the
parse state.  The score is informational — it does not change routing.

Reference: parser specification §16.2 — Parse-level confidence.
"""

from __future__ import annotations


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
