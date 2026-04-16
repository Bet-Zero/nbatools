"""Playoff history and era-bucket query module.

Provides playoff-round/series/appearance/era-bucketed history for teams
(and players where grounded).

Capabilities:
- Playoff record / summary by round (first round, conference finals, finals, etc.)
- Playoff appearances counting by round stage
- Playoff matchup history (team vs team playoff record)
- Era-bucket (by-decade) breakdowns of any team record or leaderboard
- Appearance leaderboard (most finals appearances, most playoff appearances, etc.)

Data model:
- Playoff round is extracted from game_id positions 7-8 (works for 2001-02+)
- Seasons 1996-97 through 2000-01 have no round info in game_ids ("00")
- Era buckets group seasons by decade (e.g., 2000s = 1999-00 through 2008-09)

All functions return structured result objects (SummaryResult,
ComparisonResult, LeaderboardResult, NoResult).
"""

from __future__ import annotations

import pandas as pd

from nbatools.commands._seasons import (
    EARLIEST_SEASON,
    int_to_season,
    resolve_seasons,
    season_to_int,
)
from nbatools.commands.data_utils import load_team_games_for_seasons
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.structured_results import (
    ComparisonResult,
    LeaderboardResult,
    NoResult,
    SummaryResult,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Playoff round codes extracted from game_id[6:8]
ROUND_CODES = {
    "01": "First Round",
    "02": "Second Round",
    "03": "Conference Finals",
    "04": "Finals",
}

ROUND_ALIASES: dict[str, str] = {
    "first round": "01",
    "1st round": "01",
    "round 1": "01",
    "round one": "01",
    "second round": "02",
    "2nd round": "02",
    "round 2": "02",
    "round two": "02",
    "semifinals": "02",
    "semis": "02",
    "conference finals": "03",
    "conf finals": "03",
    "conference final": "03",
    "conf final": "03",
    "finals": "04",
    "the finals": "04",
    "nba finals": "04",
    "championship": "04",
}

# Minimum season for round-level data
ROUND_DATA_START_SEASON = "2001-02"
ROUND_DATA_START_YEAR = 2001

# ---------------------------------------------------------------------------
# Helpers: round extraction
# ---------------------------------------------------------------------------


def extract_playoff_round(game_id: str) -> str | None:
    """Extract the playoff round code from a game_id.

    Returns the 2-char round code ('01'-'04') or None if not determinable.
    game_id format: 004YYRRGSN where positions 6-7 (0-indexed) hold RR.
    """
    gid = str(game_id)
    if len(gid) < 8:
        return None
    code = gid[6:8]
    if code in ROUND_CODES:
        return code
    return None


def round_code_to_label(code: str) -> str:
    """Convert a round code to a human-readable label."""
    return ROUND_CODES.get(code, f"Round {code}")


def resolve_round_filter(text: str) -> str | None:
    """Resolve a natural-language round reference to a round code.

    Returns a 2-char code like '01', '04', or None if not matched.
    """
    t = text.lower().strip()
    return ROUND_ALIASES.get(t)


# ---------------------------------------------------------------------------
# Helpers: era/decade bucketing
# ---------------------------------------------------------------------------


def season_to_decade(season: str) -> str:
    """Map a season string to its decade bucket label.

    '2003-04' → '2000s', '2019-20' → '2010s', '1999-00' → '1990s'.
    The decade is determined by the start year of the season.
    """
    year = season_to_int(season)
    decade_start = (year // 10) * 10
    return f"{decade_start}s"


def decade_season_range(decade_label: str) -> tuple[str, str]:
    """Given a decade label like '2000s', return (start_season, end_season).

    '2000s' → ('2000-01', '2009-10')
    Clamped to EARLIEST_SEASON / LATEST_PLAYOFF_SEASON bounds.
    """
    decade_start = int(decade_label.rstrip("s"))
    decade_end = decade_start + 9
    earliest = season_to_int(EARLIEST_SEASON)
    start = max(decade_start, earliest)
    end = min(decade_end, 2025)  # Don't exceed available data
    return int_to_season(start), int_to_season(end)


def _add_round_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'playoff_round_code' and 'playoff_round' column from game_id."""
    out = df.copy()
    out["playoff_round_code"] = out["game_id"].astype(str).str[6:8]
    out["playoff_round"] = out["playoff_round_code"].map(ROUND_CODES)
    # Mark rows with unresolvable round
    out.loc[out["playoff_round"].isna(), "playoff_round"] = "Unknown Round"
    return out


def _add_decade_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'decade' column from the season column."""
    out = df.copy()
    out["decade"] = out["season"].apply(season_to_decade)
    return out


def _compute_record(df: pd.DataFrame) -> dict:
    """Compute wins/losses/win_pct from a filtered game log."""
    if df.empty:
        return {"games": 0, "wins": 0, "losses": 0, "win_pct": None}
    games = len(df)
    wins = int((df["wl"] == "W").sum())
    losses = int((df["wl"] == "L").sum())
    win_pct = round(wins / games, 3) if games > 0 else None
    return {"games": games, "wins": wins, "losses": losses, "win_pct": win_pct}


def _has_round_data(seasons: list[str]) -> bool:
    """Check whether any season in the list supports round-level data."""
    return any(season_to_int(s) >= ROUND_DATA_START_YEAR for s in seasons)


def _round_data_caveat(seasons: list[str]) -> str | None:
    """Return caveat text if some seasons lack round-level data."""
    early = [s for s in seasons if season_to_int(s) < ROUND_DATA_START_YEAR]
    if early:
        return (
            f"playoff round data not available for seasons before {ROUND_DATA_START_SEASON}; "
            f"seasons {early[0]}–{early[-1]} excluded from round-level breakdowns"
        )
    return None


# ---------------------------------------------------------------------------
# Public API: team playoff history / record by round
# ---------------------------------------------------------------------------


def build_playoff_history_result(
    *,
    team: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    playoff_round: str | None = None,
    by_decade: bool = False,
    opponent: str | None = None,
) -> SummaryResult | NoResult:
    """Build a playoff history summary for a single team.

    Optionally filtered by round and/or bucketed by decade.

    Parameters
    ----------
    team : str
        Team abbreviation or name.
    playoff_round : str | None
        Round code ('01'-'04') to filter by, or None for all rounds.
    by_decade : bool
        If True, break down by decade instead of by season.
    opponent : str | None
        Optional opponent filter.
    """
    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = load_team_games_for_seasons(seasons, "Playoffs")
    except FileNotFoundError:
        return NoResult(query_class="summary", reason="no_data")

    # Filter to the requested team
    t = team.upper()
    df = df[
        df["team_abbr"].astype(str).str.upper().eq(t)
        | df["team_name"].astype(str).str.upper().eq(t)
    ].copy()

    if df.empty:
        return NoResult(query_class="summary", reason="no_match")

    if opponent:
        o = opponent.upper()
        mask = pd.Series(False, index=df.index)
        if "opponent_team_abbr" in df.columns:
            mask = mask | df["opponent_team_abbr"].astype(str).str.upper().eq(o)
        if "opponent_team_name" in df.columns:
            mask = mask | df["opponent_team_name"].astype(str).str.upper().eq(o)
        df = df[mask].copy()
        if df.empty:
            return NoResult(query_class="summary", reason="no_match")

    df = _add_round_column(df)
    df = _add_decade_column(df)

    caveats: list[str] = []
    round_caveat = _round_data_caveat(seasons)
    if round_caveat:
        caveats.append(round_caveat)

    # Filter by round if requested
    if playoff_round:
        df = df[df["playoff_round_code"] == playoff_round].copy()
        if df.empty:
            round_label = round_code_to_label(playoff_round)
            return NoResult(
                query_class="summary",
                reason="no_match",
                notes=[f"No {round_label} games found for {team.upper()}"],
            )

    # Overall record
    team_name = df["team_name"].mode().iloc[0] if "team_name" in df.columns else team
    rec = _compute_record(df)
    season_min = df["season"].min()
    season_max = df["season"].max()

    summary_row = {
        "team_name": team_name,
        "season_start": season_min,
        "season_end": season_max,
        "season_type": "Playoffs",
        **rec,
    }
    if playoff_round:
        summary_row["playoff_round"] = round_code_to_label(playoff_round)

    # Appearances by season
    appearances = df.groupby("season")["game_id"].nunique().reset_index()
    appearances.columns = ["season", "games"]
    summary_row["seasons_appeared"] = len(appearances)

    summary = pd.DataFrame([summary_row])

    # Breakdown: by decade or by season
    if by_decade:
        by_group = _build_decade_breakdown(df, playoff_round=playoff_round)
    else:
        by_group = _build_season_breakdown(df, playoff_round=playoff_round)

    if len(seasons) > 1:
        caveats.append(f"playoff history aggregated across {seasons[0]} to {seasons[-1]}")
    if opponent:
        caveats.append(f"filtered to playoff games vs {opponent.upper()}")

    current_through = compute_current_through_for_seasons(seasons, "Playoffs")

    # Use by_season field for backward compatibility; by_decade goes there too
    return SummaryResult(
        summary=summary,
        by_season=by_group,
        current_through=current_through,
        caveats=caveats,
    )


def _build_season_breakdown(df: pd.DataFrame, *, playoff_round: str | None = None) -> pd.DataFrame:
    """Build a by-season breakdown of playoff record."""
    agg_map: dict = {
        "games": ("game_id", "nunique"),
        "wins": ("wl", lambda s: int((s == "W").sum())),
        "losses": ("wl", lambda s: int((s == "L").sum())),
    }
    by_season = (
        df.groupby("season", as_index=False)
        .agg(**agg_map)
        .sort_values("season")
        .reset_index(drop=True)
    )
    if not by_season.empty:
        by_season["win_pct"] = (by_season["wins"] / by_season["games"]).round(3)

    # Add round-level detail per season if no round filter
    if playoff_round is None and "playoff_round" in df.columns:
        # Add deepest round reached per season
        round_order = {"First Round": 1, "Second Round": 2, "Conference Finals": 3, "Finals": 4}
        deepest = (
            df.groupby("season")["playoff_round"]
            .apply(lambda x: max(x, key=lambda r: round_order.get(r, 0)))
            .reset_index()
        )
        deepest.columns = ["season", "deepest_round"]
        by_season = by_season.merge(deepest, on="season", how="left")

    return by_season


def _build_decade_breakdown(df: pd.DataFrame, *, playoff_round: str | None = None) -> pd.DataFrame:
    """Build a by-decade breakdown of playoff record."""
    agg_map: dict = {
        "games": ("game_id", "nunique"),
        "wins": ("wl", lambda s: int((s == "W").sum())),
        "losses": ("wl", lambda s: int((s == "L").sum())),
        "seasons_appeared": ("season", "nunique"),
    }
    by_decade = (
        df.groupby("decade", as_index=False)
        .agg(**agg_map)
        .sort_values("decade")
        .reset_index(drop=True)
    )
    if not by_decade.empty:
        by_decade["win_pct"] = (by_decade["wins"] / by_decade["games"]).round(3)

    return by_decade


# ---------------------------------------------------------------------------
# Public API: team record by decade (regular season or playoffs)
# ---------------------------------------------------------------------------


def build_record_by_decade_result(
    *,
    team: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Playoffs",
    opponent: str | None = None,
) -> SummaryResult | NoResult:
    """Build a team record broken down by decade.

    Works for both regular season and playoffs.
    """
    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = load_team_games_for_seasons(seasons, season_type)
    except FileNotFoundError:
        return NoResult(query_class="summary", reason="no_data")

    t = team.upper()
    df = df[
        df["team_abbr"].astype(str).str.upper().eq(t)
        | df["team_name"].astype(str).str.upper().eq(t)
    ].copy()

    if df.empty:
        return NoResult(query_class="summary", reason="no_match")

    if opponent:
        o = opponent.upper()
        mask = pd.Series(False, index=df.index)
        if "opponent_team_abbr" in df.columns:
            mask = mask | df["opponent_team_abbr"].astype(str).str.upper().eq(o)
        if "opponent_team_name" in df.columns:
            mask = mask | df["opponent_team_name"].astype(str).str.upper().eq(o)
        df = df[mask].copy()
        if df.empty:
            return NoResult(query_class="summary", reason="no_match")

    df = _add_decade_column(df)

    team_name = df["team_name"].mode().iloc[0] if "team_name" in df.columns else team
    rec = _compute_record(df)

    summary_row = {
        "team_name": team_name,
        "season_start": df["season"].min(),
        "season_end": df["season"].max(),
        "season_type": season_type,
        **rec,
    }
    summary = pd.DataFrame([summary_row])

    by_decade = _build_decade_breakdown(df)

    caveats: list[str] = []
    if len(seasons) > 1:
        caveats.append(f"record by decade aggregated across {seasons[0]} to {seasons[-1]}")
    if opponent:
        caveats.append(f"filtered to games vs {opponent.upper()}")

    current_through = compute_current_through_for_seasons(seasons, season_type)

    return SummaryResult(
        summary=summary,
        by_season=by_decade,  # by_decade goes in the by_season slot
        current_through=current_through,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Public API: matchup record by decade
# ---------------------------------------------------------------------------


def build_matchup_by_decade_result(
    *,
    team_a: str,
    team_b: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
) -> ComparisonResult | NoResult:
    """Build a matchup record comparison broken down by decade.

    Returns overall comparison plus decade-level breakdown.
    """
    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = load_team_games_for_seasons(seasons, season_type)
    except FileNotFoundError:
        return NoResult(query_class="comparison", reason="no_data")

    # Filter team A vs team B
    a_upper, b_upper = team_a.upper(), team_b.upper()

    a_df = df[
        (
            df["team_abbr"].astype(str).str.upper().eq(a_upper)
            | df["team_name"].astype(str).str.upper().eq(a_upper)
        )
        & (
            df["opponent_team_abbr"].astype(str).str.upper().eq(b_upper)
            | df["opponent_team_name"].astype(str).str.upper().eq(b_upper)
        )
    ].copy()

    b_df = df[
        (
            df["team_abbr"].astype(str).str.upper().eq(b_upper)
            | df["team_name"].astype(str).str.upper().eq(b_upper)
        )
        & (
            df["opponent_team_abbr"].astype(str).str.upper().eq(a_upper)
            | df["opponent_team_name"].astype(str).str.upper().eq(a_upper)
        )
    ].copy()

    if a_df.empty and b_df.empty:
        return NoResult(query_class="comparison", reason="no_match")

    a_df = _add_decade_column(a_df)
    b_df = _add_decade_column(b_df)

    rec_a = _compute_record(a_df)
    rec_b = _compute_record(b_df)

    team_a_name = (
        a_df["team_name"].mode().iloc[0]
        if not a_df.empty and "team_name" in a_df.columns
        else team_a
    )
    team_b_name = (
        b_df["team_name"].mode().iloc[0]
        if not b_df.empty and "team_name" in b_df.columns
        else team_b
    )

    summary = pd.DataFrame(
        [
            {"team_name": team_a_name, **rec_a},
            {"team_name": team_b_name, **rec_b},
        ]
    )

    # By-decade breakdown: show both teams' records per decade
    all_decades = sorted(set(a_df["decade"].unique()) | set(b_df["decade"].unique()))
    decade_rows = []
    for dec in all_decades:
        a_dec = a_df[a_df["decade"] == dec]
        b_dec = b_df[b_df["decade"] == dec]
        ra = _compute_record(a_dec)
        rb = _compute_record(b_dec)
        decade_rows.append(
            {
                "decade": dec,
                f"{team_a.upper()}_wins": ra["wins"],
                f"{team_a.upper()}_losses": ra["losses"],
                f"{team_a.upper()}_win_pct": ra["win_pct"],
                f"{team_b.upper()}_wins": rb["wins"],
                f"{team_b.upper()}_losses": rb["losses"],
                f"{team_b.upper()}_win_pct": rb["win_pct"],
            }
        )

    comparison = pd.DataFrame(decade_rows) if decade_rows else pd.DataFrame()

    caveats = [
        f"matchup history: {team_a.upper()} vs {team_b.upper()} by decade",
    ]
    if season_type == "Playoffs":
        caveats.append("playoff games only")
    if len(seasons) > 1:
        caveats.append(f"across {seasons[0]} to {seasons[-1]}")

    current_through = compute_current_through_for_seasons(seasons, season_type)

    return ComparisonResult(
        summary=summary,
        comparison=comparison,
        current_through=current_through,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Public API: playoff appearances (leaderboard)
# ---------------------------------------------------------------------------


def build_playoff_appearances_result(
    *,
    team: str | None = None,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    playoff_round: str | None = None,
    limit: int = 10,
    ascending: bool = False,
) -> LeaderboardResult | SummaryResult | NoResult:
    """Count playoff appearances, optionally filtered by round stage.

    If *team* is given, returns a SummaryResult for that team.
    If no team, returns a LeaderboardResult ranking all teams.

    An "appearance" = the team played at least one game in that
    season at the specified round (or any playoff game if no round).
    """
    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = load_team_games_for_seasons(seasons, "Playoffs")
    except FileNotFoundError:
        return NoResult(
            query_class="leaderboard" if not team else "summary",
            reason="no_data",
        )

    df = _add_round_column(df)

    caveats: list[str] = []
    round_caveat = _round_data_caveat(seasons)
    if round_caveat:
        caveats.append(round_caveat)

    # Apply round filter
    round_label = "Playoffs"
    if playoff_round:
        round_label = round_code_to_label(playoff_round)
        df = df[df["playoff_round_code"] == playoff_round].copy()
        if df.empty:
            return NoResult(
                query_class="leaderboard" if not team else "summary",
                reason="no_match",
                notes=[f"No {round_label} games found in the specified span"],
            )

    # Count appearances: distinct seasons per team at this stage
    appearances = df.groupby(["team_abbr", "team_name"])["season"].nunique().reset_index()
    appearances.columns = ["team_abbr", "team_name", "appearances"]

    if team:
        # Single-team summary
        t = team.upper()
        team_rows = appearances[
            appearances["team_abbr"].astype(str).str.upper().eq(t)
            | appearances["team_name"].astype(str).str.upper().eq(t)
        ]
        if team_rows.empty:
            return NoResult(query_class="summary", reason="no_match")

        row = team_rows.iloc[0]
        summary_row = {
            "team_name": row["team_name"],
            "appearances": int(row["appearances"]),
            "round": round_label,
            "season_start": df["season"].min(),
            "season_end": df["season"].max(),
        }

        # Breakdown: which seasons they appeared
        team_df = df[
            df["team_abbr"].astype(str).str.upper().eq(t)
            | df["team_name"].astype(str).str.upper().eq(t)
        ]
        season_detail = (
            team_df.groupby("season")
            .agg(
                games=("game_id", "nunique"),
                wins=("wl", lambda s: int((s == "W").sum())),
                losses=("wl", lambda s: int((s == "L").sum())),
            )
            .reset_index()
            .sort_values("season")
        )
        if not season_detail.empty:
            season_detail["win_pct"] = (season_detail["wins"] / season_detail["games"]).round(3)

        caveats.append(f"{round_label} appearances for {row['team_name']}")
        current_through = compute_current_through_for_seasons(seasons, "Playoffs")

        return SummaryResult(
            summary=pd.DataFrame([summary_row]),
            by_season=season_detail,
            current_through=current_through,
            caveats=caveats,
        )

    # Leaderboard: all teams ranked by appearances
    result = (
        appearances.sort_values(
            by=["appearances", "team_name"],
            ascending=[ascending, True],
        )
        .head(limit)
        .reset_index(drop=True)
    )
    result.insert(0, "rank", range(1, len(result) + 1))
    result["round"] = round_label
    if len(seasons) > 1:
        result["seasons"] = f"{seasons[0]} to {seasons[-1]}"
    else:
        result["season"] = seasons[0]

    caveats.append(f"{round_label} appearances leaderboard")
    if len(seasons) > 1:
        caveats.append(f"across {seasons[0]} to {seasons[-1]}")

    current_through = compute_current_through_for_seasons(seasons, "Playoffs")

    return LeaderboardResult(
        leaders=result,
        current_through=current_through,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Public API: record leaderboard by decade
# ---------------------------------------------------------------------------


def build_record_by_decade_leaderboard_result(
    *,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    stat: str = "wins",
    limit: int = 10,
    ascending: bool = False,
    playoff_round: str | None = None,
) -> LeaderboardResult | NoResult:
    """Rank teams by record stats grouped by decade.

    E.g., "most wins by decade since 1980".
    Returns a leaderboard with one row per team-decade combination.
    """
    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = load_team_games_for_seasons(seasons, season_type)
    except FileNotFoundError:
        return NoResult(query_class="leaderboard", reason="no_data")

    if season_type == "Playoffs":
        df = _add_round_column(df)
        if playoff_round:
            df = df[df["playoff_round_code"] == playoff_round].copy()

    df = _add_decade_column(df)

    if df.empty:
        return NoResult(query_class="leaderboard", reason="no_match")

    caveats: list[str] = []
    if season_type == "Playoffs":
        caveat = _round_data_caveat(seasons)
        if caveat:
            caveats.append(caveat)

    # Aggregate per team per decade
    if "wl" in df.columns:
        df["_is_win"] = (df["wl"] == "W").astype(int)

    agg = df.groupby(["team_abbr", "team_name", "decade"], as_index=False).agg(
        games_played=("game_id", "nunique"),
        wins=("_is_win", "sum"),
    )
    agg["losses"] = agg["games_played"] - agg["wins"]
    agg["win_pct"] = (agg["wins"] / agg["games_played"]).round(3)

    # Sort by target stat within each decade
    target_col = stat if stat in ("wins", "losses", "win_pct") else "wins"
    result = agg[
        ["team_name", "team_abbr", "decade", "games_played", "wins", "losses", "win_pct"]
    ].sort_values(
        by=["decade", target_col, "games_played", "team_name"],
        ascending=[True, ascending, False, True],
    )

    # Take top N per decade
    top_results = []
    for decade, group in result.groupby("decade"):
        top_n = group.head(limit).copy()
        top_n.insert(0, "rank", range(1, len(top_n) + 1))
        top_results.append(top_n)

    if not top_results:
        return NoResult(query_class="leaderboard", reason="no_match")

    leaders = pd.concat(top_results, ignore_index=True)
    leaders["season_type"] = season_type
    if len(seasons) > 1:
        leaders["seasons"] = f"{seasons[0]} to {seasons[-1]}"

    caveats.append(f"record by decade leaderboard ({target_col})")
    if len(seasons) > 1:
        caveats.append(f"across {seasons[0]} to {seasons[-1]}")
    if playoff_round:
        caveats.append(f"filtered to {round_code_to_label(playoff_round)}")

    current_through = compute_current_through_for_seasons(seasons, season_type)

    return LeaderboardResult(
        leaders=leaders,
        current_through=current_through,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Public API: playoff matchup history (team vs team in playoffs)
# ---------------------------------------------------------------------------


def build_playoff_matchup_history_result(
    *,
    team_a: str,
    team_b: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    playoff_round: str | None = None,
    by_round: bool = False,
) -> ComparisonResult | NoResult:
    """Build playoff matchup history between two teams.

    Shows playoff record of team_a vs team_b, optionally filtered by
    round or broken down by round.
    """
    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = load_team_games_for_seasons(seasons, "Playoffs")
    except FileNotFoundError:
        return NoResult(query_class="comparison", reason="no_data")

    a_upper, b_upper = team_a.upper(), team_b.upper()

    # Team A games vs Team B in playoffs
    a_df = df[
        (
            df["team_abbr"].astype(str).str.upper().eq(a_upper)
            | df["team_name"].astype(str).str.upper().eq(a_upper)
        )
        & (
            df["opponent_team_abbr"].astype(str).str.upper().eq(b_upper)
            | df["opponent_team_name"].astype(str).str.upper().eq(b_upper)
        )
    ].copy()

    b_df = df[
        (
            df["team_abbr"].astype(str).str.upper().eq(b_upper)
            | df["team_name"].astype(str).str.upper().eq(b_upper)
        )
        & (
            df["opponent_team_abbr"].astype(str).str.upper().eq(a_upper)
            | df["opponent_team_name"].astype(str).str.upper().eq(a_upper)
        )
    ].copy()

    if a_df.empty and b_df.empty:
        return NoResult(query_class="comparison", reason="no_match")

    a_df = _add_round_column(a_df)
    b_df = _add_round_column(b_df)

    caveats: list[str] = []
    round_caveat = _round_data_caveat(seasons)
    if round_caveat:
        caveats.append(round_caveat)

    if playoff_round:
        a_df = a_df[a_df["playoff_round_code"] == playoff_round].copy()
        b_df = b_df[b_df["playoff_round_code"] == playoff_round].copy()
        if a_df.empty and b_df.empty:
            return NoResult(query_class="comparison", reason="no_match")

    rec_a = _compute_record(a_df)
    rec_b = _compute_record(b_df)

    team_a_name = (
        a_df["team_name"].mode().iloc[0]
        if not a_df.empty and "team_name" in a_df.columns
        else team_a
    )
    team_b_name = (
        b_df["team_name"].mode().iloc[0]
        if not b_df.empty and "team_name" in b_df.columns
        else team_b
    )

    summary = pd.DataFrame(
        [
            {"team_name": team_a_name, **rec_a},
            {"team_name": team_b_name, **rec_b},
        ]
    )

    # Build comparison breakdown
    if by_round:
        # By-round breakdown
        all_rounds = sorted(
            set(a_df["playoff_round_code"].unique()) | set(b_df["playoff_round_code"].unique())
        )
        comparison_rows = []
        for rc in all_rounds:
            if rc not in ROUND_CODES:
                continue
            a_round = a_df[a_df["playoff_round_code"] == rc]
            b_round = b_df[b_df["playoff_round_code"] == rc]
            ra = _compute_record(a_round)
            rb = _compute_record(b_round)
            comparison_rows.append(
                {
                    "round": round_code_to_label(rc),
                    f"{team_a.upper()}_wins": ra["wins"],
                    f"{team_a.upper()}_losses": ra["losses"],
                    f"{team_b.upper()}_wins": rb["wins"],
                    f"{team_b.upper()}_losses": rb["losses"],
                }
            )
        comparison = pd.DataFrame(comparison_rows) if comparison_rows else pd.DataFrame()
        caveats.append(f"playoff matchup history by round: {team_a.upper()} vs {team_b.upper()}")
    else:
        # By-season breakdown
        all_seasons = sorted(set(a_df["season"].unique()) | set(b_df["season"].unique()))
        comparison_rows = []
        for szn in all_seasons:
            a_szn = a_df[a_df["season"] == szn]
            b_szn = b_df[b_df["season"] == szn]
            ra = _compute_record(a_szn)
            rb = _compute_record(b_szn)
            # Determine round played
            round_label = "Unknown"
            rounds_played = set()
            for rdf in [a_szn, b_szn]:
                if not rdf.empty and "playoff_round_code" in rdf.columns:
                    rounds_played.update(rdf["playoff_round_code"].unique())
            valid_rounds = [r for r in rounds_played if r in ROUND_CODES]
            if valid_rounds:
                round_label = round_code_to_label(max(valid_rounds))

            comparison_rows.append(
                {
                    "season": szn,
                    "round": round_label,
                    f"{team_a.upper()}_wins": ra["wins"],
                    f"{team_a.upper()}_losses": ra["losses"],
                    f"{team_b.upper()}_wins": rb["wins"],
                    f"{team_b.upper()}_losses": rb["losses"],
                }
            )
        comparison = pd.DataFrame(comparison_rows) if comparison_rows else pd.DataFrame()
        caveats.append(f"playoff matchup history: {team_a.upper()} vs {team_b.upper()}")

    if len(seasons) > 1:
        caveats.append(f"across {seasons[0]} to {seasons[-1]}")

    current_through = compute_current_through_for_seasons(seasons, "Playoffs")

    return ComparisonResult(
        summary=summary,
        comparison=comparison,
        current_through=current_through,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Public API: playoff round record leaderboard
# ---------------------------------------------------------------------------


def build_playoff_round_record_result(
    *,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    playoff_round: str | None = None,
    stat: str = "win_pct",
    limit: int = 10,
    ascending: bool = False,
) -> LeaderboardResult | NoResult:
    """Rank teams by playoff record in a specific round.

    E.g., "best finals record since 1980", "most conference finals wins".
    """
    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = load_team_games_for_seasons(seasons, "Playoffs")
    except FileNotFoundError:
        return NoResult(query_class="leaderboard", reason="no_data")

    df = _add_round_column(df)

    caveats: list[str] = []
    round_caveat = _round_data_caveat(seasons)
    if round_caveat:
        caveats.append(round_caveat)

    round_label = "Playoffs"
    if playoff_round:
        round_label = round_code_to_label(playoff_round)
        df = df[df["playoff_round_code"] == playoff_round].copy()
        if df.empty:
            return NoResult(
                query_class="leaderboard",
                reason="no_match",
                notes=[f"No {round_label} games found in the specified span"],
            )

    if "wl" in df.columns:
        df["_is_win"] = (df["wl"] == "W").astype(int)

    agg = df.groupby(["team_id", "team_name", "team_abbr"], as_index=False).agg(
        games_played=("game_id", "nunique"),
        wins=("_is_win", "sum"),
    )
    agg["losses"] = agg["games_played"] - agg["wins"]
    agg["win_pct"] = (agg["wins"] / agg["games_played"]).round(3)

    # Minimum games guardrail
    min_games = max(1, len(seasons) // 5)
    agg = agg[agg["games_played"] >= min_games].copy()

    if agg.empty:
        return NoResult(query_class="leaderboard", reason="no_match")

    target_col = stat if stat in ("wins", "losses", "win_pct") else "win_pct"

    result = (
        agg[["team_name", "team_abbr", "team_id", "games_played", "wins", "losses", "win_pct"]]
        .sort_values(
            by=[target_col, "games_played", "team_name"],
            ascending=[ascending, False, True],
        )
        .head(limit)
        .reset_index(drop=True)
    )

    result.insert(0, "rank", range(1, len(result) + 1))
    result["round"] = round_label
    if len(seasons) > 1:
        result["seasons"] = f"{seasons[0]} to {seasons[-1]}"
    else:
        result["season"] = seasons[0]
    result["season_type"] = "Playoffs"

    caveats.append(f"{round_label} record leaderboard ({target_col})")
    if len(seasons) > 1:
        caveats.append(f"across {seasons[0]} to {seasons[-1]}")

    current_through = compute_current_through_for_seasons(seasons, "Playoffs")

    return LeaderboardResult(
        leaders=result,
        current_through=current_through,
        caveats=caveats,
    )
