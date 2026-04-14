"""Team record query module.

Provides record-oriented aggregation for teams across historical spans,
opponent contexts, and contextual samples.

Capabilities:
- Single team record (wins/losses/win_pct) over any span
- Team-vs-team matchup record over any span
- Record in contextual samples (e.g., "record when scoring 120+")
- Record leaderboard (ranking all teams by win_pct / wins / losses)

All functions return structured result objects (SummaryResult,
ComparisonResult, LeaderboardResult, NoResult).
"""

from __future__ import annotations

import pandas as pd

from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.data_utils import load_team_games_for_seasons
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.structured_results import (
    ComparisonResult,
    LeaderboardResult,
    NoResult,
    SummaryResult,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_date_value(value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        raise ValueError(f"Invalid date value: {value}")
    return pd.Timestamp(ts).normalize()


def _apply_game_filters(
    df: pd.DataFrame,
    *,
    team: str | None = None,
    opponent: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    season_type: str | None = None,
) -> pd.DataFrame:
    """Filter a game-log DataFrame by standard criteria."""
    out = df.copy()
    if "game_date" in out.columns:
        out["game_date"] = pd.to_datetime(out["game_date"], errors="coerce").dt.normalize()

    start_ts = _normalize_date_value(start_date)
    end_ts = _normalize_date_value(end_date)
    if start_ts is not None and end_ts is not None and start_ts > end_ts:
        raise ValueError("start_date must be <= end_date")

    if start_ts is not None and "game_date" in out.columns:
        out = out[out["game_date"] >= start_ts].copy()
    if end_ts is not None and "game_date" in out.columns:
        out = out[out["game_date"] <= end_ts].copy()

    if team:
        t = team.upper()
        out = out[
            out["team_abbr"].astype(str).str.upper().eq(t)
            | out["team_name"].astype(str).str.upper().eq(t)
        ].copy()

    if opponent:
        o = opponent.upper()
        mask = pd.Series(False, index=out.index)
        if "opponent_team_abbr" in out.columns:
            mask = mask | out["opponent_team_abbr"].astype(str).str.upper().eq(o)
        if "opponent_team_name" in out.columns:
            mask = mask | out["opponent_team_name"].astype(str).str.upper().eq(o)
        out = out[mask].copy()

    if home_only and "is_home" in out.columns:
        out = out[out["is_home"] == 1].copy()
    if away_only and "is_away" in out.columns:
        out = out[out["is_away"] == 1].copy()

    if stat and stat in out.columns:
        if min_value is not None:
            out = out[out[stat] >= min_value].copy()
        if max_value is not None:
            out = out[out[stat] <= max_value].copy()

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


def _stat_averages(df: pd.DataFrame) -> dict:
    """Compute per-game stat averages for a game sample."""
    avgs: dict = {}
    for col in ("pts", "reb", "ast", "fg3m", "stl", "blk", "tov", "plus_minus"):
        if col in df.columns:
            avgs[f"{col}_avg"] = round(df[col].mean(), 3)
    for col in ("efg_pct", "ts_pct"):
        if col in df.columns:
            avgs[f"{col}_avg"] = round(df[col].mean(), 3)
    return avgs


# ---------------------------------------------------------------------------
# Public API: team record summary
# ---------------------------------------------------------------------------


def build_team_record_result(
    *,
    team: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    opponent: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> SummaryResult | NoResult:
    """Build a record-focused summary for a single team.

    Returns a SummaryResult with wins/losses/win_pct prominently.
    """
    if home_only and away_only:
        raise ValueError("Cannot use both home_only and away_only")

    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = load_team_games_for_seasons(seasons, season_type)
    except FileNotFoundError:
        return NoResult(query_class="summary", reason="no_data")

    df = _apply_game_filters(
        df,
        team=team,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        stat=stat,
        min_value=min_value,
        max_value=max_value,
        start_date=start_date,
        end_date=end_date,
    )

    if df.empty:
        return NoResult(query_class="summary")

    rec = _compute_record(df)
    avgs = _stat_averages(df)

    team_name = df["team_name"].mode().iloc[0] if "team_name" in df.columns else team
    season_min = df["season"].min()
    season_max = df["season"].max()

    row = {
        "team_name": team_name,
        "season_start": season_min,
        "season_end": season_max,
        "season_type": season_type,
        **rec,
        **avgs,
    }

    summary = pd.DataFrame([row])

    # by-season breakdown
    agg_map: dict = {
        "games": ("game_id", "count"),
        "wins": ("wl", lambda s: int((s == "W").sum())),
        "losses": ("wl", lambda s: int((s == "L").sum())),
    }
    for col in ("pts", "reb", "ast", "fg3m", "tov", "plus_minus", "efg_pct", "ts_pct"):
        if col in df.columns:
            agg_map[f"{col}_avg"] = (col, "mean")

    by_season = (
        df.groupby("season", as_index=False)
        .agg(**agg_map)
        .round(3)
        .sort_values("season")
        .reset_index(drop=True)
    )
    if not by_season.empty:
        by_season["win_pct"] = (by_season["wins"] / by_season["games"]).round(3)

    current_through = compute_current_through_for_seasons(seasons, season_type)

    caveats: list[str] = []
    if len(seasons) > 1:
        caveats.append(
            f"multi-season record aggregated from game logs across {seasons[0]} to {seasons[-1]}"
        )
    if opponent:
        caveats.append(f"record filtered to games vs {opponent.upper()}")
    if home_only:
        caveats.append("home record only")
    if away_only:
        caveats.append("away record only")
    if stat and (min_value is not None or max_value is not None):
        parts = [f"record in games where {stat}"]
        if min_value is not None:
            parts.append(f">= {min_value}")
        if max_value is not None:
            parts.append(f"<= {max_value}")
        caveats.append(" ".join(parts))
    if start_date or end_date:
        dp = []
        if start_date:
            dp.append(f"from {start_date}")
        if end_date:
            dp.append(f"to {end_date}")
        caveats.append(f"date window: {' '.join(dp)}")

    return SummaryResult(
        summary=summary,
        by_season=by_season,
        current_through=current_through,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Public API: matchup record (team vs team)
# ---------------------------------------------------------------------------


def build_matchup_record_result(
    *,
    team_a: str,
    team_b: str,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    home_only: bool = False,
    away_only: bool = False,
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> ComparisonResult | NoResult:
    """Build a matchup record comparison for two teams.

    Filters to only games where team_a played team_b, and shows each
    team's record in those head-to-head matchups.
    """
    if home_only and away_only:
        raise ValueError("Cannot use both home_only and away_only")

    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = load_team_games_for_seasons(seasons, season_type)
    except FileNotFoundError:
        return NoResult(query_class="comparison", reason="no_data")

    # Filter team A's games vs team B
    a_df = _apply_game_filters(
        df,
        team=team_a,
        opponent=team_b,
        home_only=home_only,
        away_only=away_only,
        stat=stat,
        min_value=min_value,
        max_value=max_value,
        start_date=start_date,
        end_date=end_date,
    )
    # Filter team B's games vs team A
    b_df = _apply_game_filters(
        df,
        team=team_b,
        opponent=team_a,
        home_only=False,  # Don't apply home/away to team B (it's relative to team A)
        away_only=False,
        stat=stat,
        min_value=min_value,
        max_value=max_value,
        start_date=start_date,
        end_date=end_date,
    )

    if a_df.empty and b_df.empty:
        return NoResult(query_class="comparison")

    rec_a = _compute_record(a_df)
    rec_b = _compute_record(b_df)
    avgs_a = _stat_averages(a_df)
    avgs_b = _stat_averages(b_df)

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

    summary_a = {"team_name": team_a_name, **rec_a, **avgs_a}
    summary_b = {"team_name": team_b_name, **rec_b, **avgs_b}

    summary = pd.DataFrame([summary_a, summary_b])

    comparison_rows = [
        ("games", rec_a["games"], rec_b["games"]),
        ("wins", rec_a["wins"], rec_b["wins"]),
        ("losses", rec_a["losses"], rec_b["losses"]),
        ("win_pct", rec_a["win_pct"], rec_b["win_pct"]),
    ]
    for stat_key in ("pts_avg", "reb_avg", "ast_avg", "fg3m_avg", "tov_avg", "plus_minus_avg"):
        comparison_rows.append((stat_key, avgs_a.get(stat_key), avgs_b.get(stat_key)))

    comp = pd.DataFrame(comparison_rows, columns=["metric", team_a, team_b])

    current_through = compute_current_through_for_seasons(seasons, season_type)

    caveats: list[str] = [
        f"matchup record: {team_a.upper()} vs {team_b.upper()} head-to-head games only"
    ]
    if len(seasons) > 1:
        caveats.append(f"multi-season matchup record across {seasons[0]} to {seasons[-1]}")
    if home_only:
        caveats.append(f"home games for {team_a.upper()} only")
    if away_only:
        caveats.append(f"away games for {team_a.upper()} only")
    if stat and (min_value is not None or max_value is not None):
        parts = [f"games where {stat}"]
        if min_value is not None:
            parts.append(f">= {min_value}")
        if max_value is not None:
            parts.append(f"<= {max_value}")
        caveats.append(" ".join(parts))
    if start_date or end_date:
        dp = []
        if start_date:
            dp.append(f"from {start_date}")
        if end_date:
            dp.append(f"to {end_date}")
        caveats.append(f"date window: {' '.join(dp)}")

    return ComparisonResult(
        summary=summary,
        comparison=comp,
        current_through=current_through,
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Public API: record leaderboard
# ---------------------------------------------------------------------------


def build_record_leaderboard_result(
    *,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    stat: str = "win_pct",
    opponent: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    limit: int = 10,
    ascending: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
) -> LeaderboardResult | NoResult:
    """Rank teams by record stats (wins, losses, win_pct).

    This provides a record-focused leaderboard that is explicit about
    its semantics rather than relying on the generic stat leaderboard.
    """
    if home_only and away_only:
        raise ValueError("Cannot use both home_only and away_only")
    if limit <= 0:
        raise ValueError("limit must be greater than 0")

    seasons = resolve_seasons(season, start_season, end_season)

    try:
        df = load_team_games_for_seasons(seasons, season_type)
    except FileNotFoundError:
        return NoResult(query_class="leaderboard", reason="no_data")

    # Apply global filters
    df = _apply_game_filters(
        df,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        start_date=start_date,
        end_date=end_date,
    )

    if df.empty:
        return NoResult(query_class="leaderboard", reason="no_data")

    # Group by team and compute record
    if "wl" in df.columns:
        df["_is_win"] = (df["wl"] == "W").astype(int)

    agg = df.groupby(["team_id", "team_name", "team_abbr"], as_index=False).agg(
        games_played=("game_id", "nunique"),
        wins=("_is_win", "sum"),
    )
    agg["losses"] = agg["games_played"] - agg["wins"]
    agg["win_pct"] = (agg["wins"] / agg["games_played"]).round(3)

    # Minimum games guardrail: at least 1 game per season for record queries
    min_games = max(1, len(seasons))
    agg = agg[agg["games_played"] >= min_games].copy()

    if agg.empty:
        return NoResult(query_class="leaderboard")

    # Determine sort column
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
    if len(seasons) > 1:
        result["seasons"] = f"{seasons[0]} to {seasons[-1]}"
    else:
        result["season"] = seasons[0]
    result["season_type"] = season_type

    current_through = compute_current_through_for_seasons(seasons, season_type)

    caveats: list[str] = []
    if len(seasons) > 1:
        caveats.append(f"multi-season record leaderboard across {seasons[0]} to {seasons[-1]}")
    if opponent:
        caveats.append(f"record vs {opponent.upper()} only")
    if home_only:
        caveats.append("home record only")
    if away_only:
        caveats.append("away record only")
    if start_date or end_date:
        dp = []
        if start_date:
            dp.append(f"from {start_date}")
        if end_date:
            dp.append(f"to {end_date}")
        caveats.append(f"date window: {' '.join(dp)}")

    return LeaderboardResult(
        leaders=result,
        current_through=current_through,
        caveats=caveats,
    )
