"""Named default rules for underspecified query routing.

Each function encapsulates a policy decision about how to route an
underspecified query.  Functions take the full parse state dict and
return ``(should_fire, notes_message)``.  When ``should_fire`` is
``True``, the caller should apply the default route and append
``notes_message`` to the result's ``notes`` list.

Reference: parser specification §15 — Defaults for underspecified queries.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# 1. <player> + <timeframe> → summary
# ---------------------------------------------------------------------------


def player_timeframe_summary_default(parsed: dict) -> tuple[bool, str]:
    """Policy: <player> + <timeframe> with no more-specific signal → summary.

    Fires when a player and a time scope (season, season range, or last-N)
    are present but no stat filter, opponent, threshold, streak, or other
    signal that would route the query elsewhere.  Does NOT fire when an
    explicit summary signal (summary_intent, career_intent, averages, etc.)
    is present — those reach the summary route through explicit intent, not
    through this default.

    Spec §15.2 / §15.3: e.g. ``Jokic last 10`` → summary.
    """
    q = parsed["normalized_query"]
    # Explicit summary signals are not defaults
    if (
        parsed["summary_intent"]
        or parsed.get("career_intent")
        or parsed["range_intent"]
        or bool(re.search(r"\brecord\b", q))
        or "averages" in q
        or "average" in q
    ):
        return (False, "")
    if not (parsed["season"] or parsed["start_season"] or parsed["last_n"]):
        return (False, "")
    if parsed.get("start_date") is not None or parsed.get("end_date") is not None:
        return (False, "")
    if parsed["opponent"] is not None:
        return (False, "")
    if parsed.get("opponent_player") is not None:
        return (False, "")
    if parsed.get("without_player") is not None:
        return (False, "")
    if parsed["stat"] is not None:
        return (False, "")
    if parsed["min_value"] is not None or parsed["max_value"] is not None:
        return (False, "")
    if parsed.get("occurrence_event"):
        return (False, "")
    if parsed.get("streak_request"):
        return (False, "")
    if parsed.get("season_high_intent"):
        return (False, "")
    if parsed["split_type"]:
        return (False, "")
    if re.search(r"\bgames?\s+in\b", q):
        return (False, "")
    return (True, "default: <player> + <timeframe> → summary")


# ---------------------------------------------------------------------------
# 2. <metric> only → league-wide leaderboard
# ---------------------------------------------------------------------------


def metric_only_leaderboard_default(parsed: dict) -> tuple[bool, str]:
    """Policy: stat/leaderboard signal with no subject entity → league-wide leaderboard.

    Fires when a leaderboard intent is detected but no player or team
    entity is resolved, so the query must be a league-wide ranking.

    Spec §15.2: e.g. ``points leaders`` → league-wide leaderboard.
    """
    if parsed["player"] or parsed["team"]:
        return (False, "")
    if parsed["player_a"] or parsed["player_b"]:
        return (False, "")
    if parsed["team_a"] or parsed["team_b"]:
        return (False, "")
    if not (parsed.get("leaderboard_intent") or parsed.get("team_leaderboard_intent")):
        return (False, "")
    return (True, "default: <metric> only → league-wide leaderboard")


# ---------------------------------------------------------------------------
# 3. <player> + <threshold> → finder
# ---------------------------------------------------------------------------


def player_threshold_finder_default(parsed: dict) -> tuple[bool, str]:
    """Policy: player + threshold with no explicit finder/count intent → game finder.

    Called from the player fallback branch.  Documents that the query was
    routed to ``player_game_finder`` because a threshold was present,
    not because the user explicitly asked for a list or count.

    Spec §15.2: e.g. ``Curry 5+ threes`` → finder.
    """
    if parsed["min_value"] is not None or parsed["max_value"] is not None:
        return (True, "default: <player> + <threshold> → finder")
    return (False, "")


# ---------------------------------------------------------------------------
# 4. <team> + <threshold> → finder
# ---------------------------------------------------------------------------


def team_threshold_finder_default(parsed: dict) -> tuple[bool, str]:
    """Policy: team + threshold with no explicit finder/count intent → game finder.

    Parallel to :func:`player_threshold_finder_default` for team queries.
    """
    if parsed["min_value"] is not None or parsed["max_value"] is not None:
        return (True, "default: <team> + <threshold> → finder")
    return (False, "")


# ---------------------------------------------------------------------------
# 5. Streak three-season window default
# ---------------------------------------------------------------------------


def streak_default_window(parsed: dict) -> tuple[bool, str]:
    """Policy: streak query with no explicit season → auto three-season window.

    When the user doesn't specify a season for a streak query, the parser
    automatically applies a three-season window.  This note documents
    that default.

    Spec §15.1: streak query without explicit time → three-season window.
    """
    if parsed.get("streak_default_window"):
        kind = "team" if parsed.get("team_streak_request") else "player"
        return (True, f"default: {kind} streak uses three-season window when no season specified")
    return (False, "")
