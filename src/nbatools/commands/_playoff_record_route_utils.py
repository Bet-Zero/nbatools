"""Playoff, record, and decade-bucketed route detection and routing helpers.

Extracted from natural_query.py to reduce file size and give the
playoff/record/decade route-family clearer ownership.
"""

from __future__ import annotations

import re

from nbatools.commands._leaderboard_utils import wants_ascending_leaderboard
from nbatools.commands._seasons import default_end_season, previous_season, resolve_career
from nbatools.commands.playoff_history import ROUND_ALIASES, decade_season_range

# ---------------------------------------------------------------------------
# Intent detection helpers
# ---------------------------------------------------------------------------


# "most road wins", "fewest wins", "most home losses": the count is the stat.
_RANKED_RECORD_COUNT = re.compile(
    r"\b(?:most|fewest|least)\s+(?:(?:home|away|road|playoffs?|postseason)\s+)?(wins|losses)\b"
)


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
            r"\b(?:records?|win(?:ning)?\s+(?:percent(?:age)?|pct)|win\s*%"
            r"|(?:most|fewest|least)\s+(?:home\s+|away\s+|road\s+|playoffs?\s+|postseason\s+)?"
            r"(?:wins|losses)"
            r"|best\s+(?:home\s+|away\s+|playoff\s+|postseason\s+)?record"
            r"|worst\s+(?:home\s+|away\s+|playoff\s+|postseason\s+)?record"
            r"|highest\s+win|lowest\s+win"
            r"|winningest"
            r"|home\s+record|away\s+record|road\s+record"
            r"|playoff\s+record|postseason\s+record"
            r"|matchup\s+record|all[- ]?time\s+record)\b"
            # "win %" ends on a non-word character, so no closing \b.
            r"|\bwin(?:ning)?\s*%",
            text,
        )
    )


def detect_by_decade_intent(text: str) -> bool:
    """Detect 'by decade' bucketing intent.

    "Lakers best decade" and "which decade did the Lakers win the most" are
    answered by the decade table.
    """
    return bool(
        re.search(
            r"\bby\s+decade\b|\b(?:19|20)\d0s\b"
            r"|"
            + _DECADE_SUPERLATIVE.pattern
            + r"|\bwhich\s+decade\b(?=.*\b(?:(?:win|won|lose|lost)\s+the\s+most|records?)\b)",
            text,
        )
    )


# "Lakers best decade", "best playoff decade": a record ranked by decade.
_DECADE_SUPERLATIVE = re.compile(
    r"\b(?:best|worst|winningest|greatest)\s+"
    r"(?:(?:playoffs?|postseason|regular[\s-]season|[a-z]+(?:ive|ing))\s+)?decades?\b"
)


def extract_decade_season_range(text: str) -> tuple[str | None, str | None]:
    """Extract a decade phrase such as ``2010s`` into season bounds."""
    match = re.search(r"\b((?:19|20)\d0s)\b", text)
    if not match:
        return None, None
    return decade_season_range(match.group(1))


def detect_playoff_appearance_intent(text: str) -> bool:
    """Detect intent for playoff/round appearance queries.

    Triggers on phrases like:
    - "finals appearances"
    - "playoff appearances"
    - "conference finals appearances"
    - "second round appearances"
    """
    t = _normalize_playoff_round_phrase_hyphens(text)
    return bool(
        re.search(
            r"\b(?:playoff|postseason|finals?|conference\s+finals?|"
            r"(?:first|1st|second|2nd|third|3rd)\s+round|semifinal)"
            r"\s+(?:appearance|berth|trip|drought)",
            t,
        )
        or _MADE_THE_STAGE.search(_OPPONENT_STAGE_CLAUSE.sub(" ", t))
        or _PLAYOFF_RUN_OF_SEASONS.search(t)
    )


# "how many times have the Lakers made the playoffs", "when did the Knicks
# last make the conference finals", "LeBron reached the Finals": a season
# reached that stage. Not "made the playoffs as the 8 seed" games or records.
_STAGE = (
    r"(?:the\s+)?(?:nba\s+)?(?:playoffs|postseason|finals|conference\s+finals|"
    r"(?:second|2nd|third|3rd)\s+round|semifinals|semis)"
)
_MADE_THE_STAGE = re.compile(
    r"\b(?:made|make|makes|making|reached|reach|reaches|reaching|qualified\s+for|"
    r"qualify\s+for|went\s+to|go\s+to|gone\s+to|been\s+to|missed|miss|missing)\s+"
    r"(?:it\s+to\s+)?" + _STAGE + r"\b(?!\s+(?:games?|record|stats?|series))"
)
# "against teams that made the playoffs" names opponents, not an appearance.
_OPPONENT_STAGE_CLAUSE = re.compile(
    r"\b(?:teams?|opponents?|clubs?|squads?)\s+(?:that|which|who|to)\s+(?:\w+\s+){0,2}?"
    r"(?:made|make|reached|reach|qualified|missed|miss)\b[^,;]*"
)
# "most consecutive playoff appearances", "Lakers playoff streak", "longest
# streak of making the playoffs"
_PLAYOFF_RUN_OF_SEASONS = re.compile(
    r"\b(?:playoff|postseason|finals)\s+(?:streak|drought)s?\b"
    r"|\bconsecutive\s+(?:playoff|postseason|finals)\s+(?:appearances|seasons|trips|berths)\b"
    r"|\b(?:straight|consecutive)\s+(?:seasons?|years?)\s+(?:making|in)\s+" + _STAGE
)


def detect_playoff_history_intent(text: str) -> bool:
    """Detect explicit playoff history queries.

    Triggers on:
    - "playoff history"
    - "playoff series"
    - "playoff matchup history"
    - "playoff matchup record"
    - "postseason history"
    """
    if re.search(
        r"\b(?:playoff|postseason)\s+(?:"
        r"history|series(?:\s+(?:history|record))?|"
        r"matchups?\s+(?:history|record|series(?:\s+(?:history|record))?)"
        r")\b",
        text,
    ):
        return True
    # "Lakers and Nuggets series history": only playoff series have one
    if re.search(r"\bseries\s+(?:history|results)\b", text):
        return True
    # "series results in the 2024 playoffs"
    if not re.search(r"\b(?:playoffs?|postseason)\b", text):
        return False
    return bool(re.search(r"\bseries\b", text))


def detect_how_did_playoffs(text: str) -> bool:
    """ "how did the Lakers do in the playoffs": a team's run (callers check
    that a team, not a player, is named)."""
    return bool(
        re.search(r"\b(?:playoffs?|postseason)\b", text)
        and re.search(r"\bhow(?:'d|\s+did)\b.*\bdo\b", text)
    )


def _normalize_playoff_round_phrase_hyphens(text: str) -> str:
    """Normalize hyphens only inside known playoff round phrases."""
    return re.sub(
        r"\b(first|1st|second|2nd|third|3rd|conference|conf|nba|the)-(?=round|finals?\b)",
        r"\1 ",
        text,
    )


def detect_playoff_round_filter(text: str) -> str | None:
    """Extract a playoff round filter from natural language.

    Returns a round code ('01'-'04') or None.
    """
    # Receives pre-normalized (lowercased) text from _build_parse_state.
    t = _normalize_playoff_round_phrase_hyphens(text)
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


def _resolve_playoff_span_defaults(
    season: str | None,
    start_season: str | None,
    end_season: str | None,
) -> tuple[str | None, str | None, str | None]:
    """Resolve round-scoped playoff spans without regular-season defaults."""
    if start_season and end_season == default_end_season("Regular Season"):
        end_season = default_end_season("Playoffs")
    return _resolve_season_defaults(season, start_season, end_season, "Playoffs")


_PAIR_TIME_WORDS_RE = re.compile(
    r"\b(?:19|20)\d{2}s?\b|\b\d{2}s\b|\b(?:this|these|current|last|past|since|"
    r"recent|recently|decade|era|season|seasons|year|years)\b"
)


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
        if not (season or start_season or end_season) and re.search(
            r"\b(?:this|current)\s+(?:season|year|postseason|playoffs)\b", q
        ):
            # "did the Nuggets make the playoffs this season": the latest
            # postseason, not every season since 1996-97.
            season = default_end_season("Playoffs")
        pa_season, pa_start, pa_end = _resolve_season_defaults(
            season, start_season, end_season, "Playoffs"
        )
        route_kwargs = {
            "team": team,
            "season": pa_season,
            "start_season": pa_start,
            "end_season": pa_end,
            "playoff_round": playoff_round_filter,
            "limit": top_n or 10,
            "ascending": False,
        }
        if player:
            # "how many Finals appearances does LeBron have": seasons he played
            # at least one game at that stage.
            route_kwargs["player"] = player
        elif not team and re.search(r"\bplayers?\b", q):
            # "which player has the most Finals appearances"
            route_kwargs["player_board"] = True
        elif not team:
            ranked = re.search(r"\b(?:most|longest|fewest|least|how\s+many)\b", q)
            if re.search(r"\bdroughts?\b", q):
                # "which team has the longest playoff drought"
                route_kwargs["rank_by"] = "longest_drought"
            elif _PLAYOFF_RUN_OF_SEASONS.search(q):
                # "most consecutive playoff appearances": teams by their longest run.
                route_kwargs["rank_by"] = "longest_streak"
            elif re.search(r"\bmiss(?:ed|es|ing)?\b", q):
                # "which teams missed the playoffs": the teams that did.
                route_kwargs["rank_by"] = "missed"
            if (
                not ranked
                and not (season or start_season or end_season)
                and (route_kwargs.get("rank_by") == "missed" or _MADE_THE_STAGE.search(q))
            ):
                # "which teams made / missed the playoffs" lists one postseason.
                route_kwargs.update(
                    season=default_end_season("Playoffs"), start_season=None, end_season=None
                )
            if not ranked and not top_n:
                route_kwargs["limit"] = None
        return "playoff_appearances", route_kwargs

    # -- Playoff matchup history: team_a vs team_b --
    if (
        (
            playoff_history_intent
            or (season_type == "Playoffs" and record_intent)
            or (playoff_round_filter and re.search(r"\b(?:history|series|record)\b", q))
        )
        and team_a
        and team_b
    ):
        # "Lakers and Nuggets playoff record" with no season is their whole
        # playoff history, not just the latest postseason.
        # Only when the query names no time at all: "this postseason",
        # "these playoffs" or a bare "2026" still mean a specific window.
        pm_season = (
            None if parsed.get("season_defaulted") and not _PAIR_TIME_WORDS_RE.search(q) else season
        )
        pm_season, pm_start, pm_end = _resolve_season_defaults(
            pm_season, start_season, end_season, "Playoffs"
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

    # -- Single-team playoff round record ("Celtics conference finals record") --
    if (
        team
        and not team_a
        and not team_b
        and playoff_round_filter
        and not playoff_appearance_intent
        and (record_intent or re.search(r"\bhistory\b", q))
    ):
        if not (season or start_season or end_season):
            # "Lakers record in the first round this season": not every season.
            if re.search(r"\b(?:this|current)\s+(?:season|year|postseason|playoffs)\b", q):
                season = default_end_season("Playoffs")
            elif re.search(r"\b(?:last|previous)\s+(?:year|postseason|playoffs)\b", q):
                season = previous_season("Playoffs")
        pr_season, pr_start, pr_end = _resolve_playoff_span_defaults(
            season, start_season, end_season
        )
        return "playoff_history", {
            "team": team,
            "season": pr_season,
            "start_season": pr_start,
            "end_season": pr_end,
            "playoff_round": playoff_round_filter,
            "by_decade": by_decade_intent,
            "opponent": opponent,
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
        if not (season or start_season or end_season) and re.search(r"\bhow(?:'d|\s+did)\b", q):
            # "how did the Lakers do in the playoffs" asks about the latest run.
            season = default_end_season("Playoffs")
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
        and (
            record_intent
            or leaderboard_intent
            or team_leaderboard_intent
            or _DECADE_SUPERLATIVE.search(q)
        )
        and not team
        and not team_a
        and not team_b
        and not player
    ):
        bdl_season, bdl_start, bdl_end = _resolve_season_defaults(
            season, start_season, end_season, season_type
        )
        low = bool(re.search(r"\b(?:fewest|worst|lowest)\b|(?<!\bat\s)\bleast\b", q))
        counted = _RANKED_RECORD_COUNT.search(q)
        if counted:
            # "most wins by decade", "fewest losses in the 2020s"
            record_stat = counted.group(1)
            low = counted.group(0).split()[0] in ("fewest", "least")
        elif re.search(
            r"\bwin_pct\b|\bwin(?:ning)?\s*%|\bwin(?:ning)?\s+(?:percent(?:age)?|pct)\b"
            r"|\brecords?\b",
            q,
        ) or _DECADE_SUPERLATIVE.search(q):
            # "best record by decade", "lowest win% in the 2010s"
            record_stat = "win_pct"
        elif re.search(r"\bloss", q):
            record_stat = "losses"
        else:
            record_stat = "wins"

        return "record_by_decade_leaderboard", {
            "season": bdl_season,
            "start_season": bdl_start,
            "end_season": bdl_end,
            "season_type": season_type,
            "stat": record_stat,
            "limit": top_n or 10,
            "ascending": low,
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
    opponent_division = parsed.get("opponent_division")
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
    if not playoff_round_filter and not lb_season and not lb_start and not lb_end:
        lb_season = default_end_season(season_type)

    # Determine the sort stat from query phrasing
    record_stat = "win_pct"
    counted = _RANKED_RECORD_COUNT.search(q)
    if counted:
        # "most road wins", "fewest wins", "most home losses"
        record_stat = "wins" if counted.group(1) == "wins" else "losses"

    lb_ascending = wants_ascending_leaderboard(q)
    # Smart ascending for record stats
    if re.search(r"\b(best|top|highest)\b", q):
        lb_ascending = False
    elif re.search(r"\b(worst|lowest|fewest|least)\b", q):
        lb_ascending = True
    if counted:
        # "most losses" ranks the most first; "fewest wins" the fewest.
        lb_ascending = counted.group(0).split()[0] in ("fewest", "least")

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
            "opponent_division": opponent_division,
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
        # "best record when allowing 110 or more points": rank on the games
        # meeting every stat condition, not the whole season.
        if conditions := parsed.get("threshold_conditions"):
            route_kwargs["conditions"] = [
                {k: c.get(k) for k in ("stat", "min_value", "max_value")} for c in conditions
            ]
        elif parsed.get("stat") and (
            parsed.get("min_value") is not None or parsed.get("max_value") is not None
        ):
            # "best record with 15 threes": a bare count is a single bound
            # the threshold list does not carry; never rank the whole season.
            route_kwargs["conditions"] = [
                {
                    "stat": parsed["stat"],
                    "min_value": parsed.get("min_value"),
                    "max_value": parsed.get("max_value"),
                }
            ]

    return route, route_kwargs, notes
