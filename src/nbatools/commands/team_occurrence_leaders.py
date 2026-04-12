"""Team occurrence leaderboard: rank teams by count of threshold-event games.

This module answers questions like:
- "most 120 point team games since 2018"
- "teams with most 130+ point games since 2020"
- "most games with 15+ threes in playoffs since 2010"

It loads team game logs, applies all standard filters (season range, opponent,
playoffs, home/away, W/L), counts qualifying games per team, and returns
a LeaderboardResult ranked by occurrence count.
"""

from __future__ import annotations

import pandas as pd

from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.data_utils import load_team_games_for_seasons
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.structured_results import LeaderboardResult, NoResult

# Stats available for occurrence thresholds (must exist in team game log data).
ALLOWED_STATS = {
    "pts",
    "reb",
    "ast",
    "stl",
    "blk",
    "fgm",
    "fga",
    "fg3m",
    "fg3a",
    "ftm",
    "fta",
    "tov",
    "pf",
    "minutes",
    "plus_minus",
    "oreb",
    "dreb",
}

DEFAULT_MIN_GAMES = 1


def _normalize_date_value(value: str | None) -> pd.Timestamp | None:
    if value is None:
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        raise ValueError(f"Invalid date value: {value}")
    return pd.Timestamp(ts).normalize()


def _apply_base_filters(
    df: pd.DataFrame,
    *,
    opponent: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    wins_only: bool = False,
    losses_only: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """Apply standard game-level filters."""
    out = df.copy()

    if "game_date" in out.columns:
        out["game_date"] = pd.to_datetime(out["game_date"], errors="coerce").dt.normalize()

    start_ts = _normalize_date_value(start_date)
    end_ts = _normalize_date_value(end_date)

    if start_ts is not None and "game_date" in out.columns:
        out = out[out["game_date"] >= start_ts].copy()

    if end_ts is not None and "game_date" in out.columns:
        out = out[out["game_date"] <= end_ts].copy()

    if opponent:
        opp_upper = opponent.upper()
        opp_mask = pd.Series(False, index=out.index)
        if "opponent_team_abbr" in out.columns:
            opp_mask = opp_mask | out["opponent_team_abbr"].astype(str).str.upper().eq(opp_upper)
        if "opponent_team_name" in out.columns:
            opp_mask = opp_mask | out["opponent_team_name"].astype(str).str.upper().eq(opp_upper)
        out = out[opp_mask].copy()

    if home_only and "is_home" in out.columns:
        out = out[out["is_home"] == 1].copy()

    if away_only and "is_away" in out.columns:
        out = out[out["is_away"] == 1].copy()

    if wins_only and "wl" in out.columns:
        out = out[out["wl"] == "W"].copy()

    if losses_only and "wl" in out.columns:
        out = out[out["wl"] == "L"].copy()

    return out


def build_result(
    stat: str = "pts",
    min_value: float = 100,
    season: str | None = None,
    start_season: str | None = None,
    end_season: str | None = None,
    season_type: str = "Regular Season",
    opponent: str | None = None,
    home_only: bool = False,
    away_only: bool = False,
    wins_only: bool = False,
    losses_only: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 10,
    min_games: int = DEFAULT_MIN_GAMES,
) -> LeaderboardResult | NoResult:
    """Build a team occurrence leaderboard.

    Parameters
    ----------
    stat : str
        The stat column to threshold on (e.g. "pts", "fg3m").
    min_value : float
        The minimum value for *stat* to count as a qualifying game.
    season, start_season, end_season : str or None
        Season parameters forwarded to ``resolve_seasons()``.
    season_type : str
        "Regular Season" or "Playoffs".
    opponent : str or None
        Restrict to games against a specific team abbreviation.
    home_only, away_only, wins_only, losses_only : bool
        Standard game-level filters.
    start_date, end_date : str or None
        Date-window filters.
    limit : int
        Number of leaders to return.
    min_games : int
        Minimum total games played for a team to be eligible.

    Returns
    -------
    LeaderboardResult or NoResult
    """
    # Validate
    if stat.lower() not in ALLOWED_STATS:
        raise ValueError(f"Unsupported stat: {stat}. Allowed: {sorted(ALLOWED_STATS)}")
    if min_value is None:
        raise ValueError("min_value is required")
    if limit <= 0:
        raise ValueError("limit must be greater than 0")

    # Resolve seasons
    try:
        seasons = resolve_seasons(season, start_season, end_season)
    except ValueError:
        return NoResult(query_class="leaderboard", reason="no_data")

    # Load team game data
    try:
        basic = load_team_games_for_seasons(seasons, season_type)
    except FileNotFoundError:
        return NoResult(query_class="leaderboard", reason="no_data")

    if basic.empty:
        return NoResult(query_class="leaderboard", reason="no_data")

    # Apply base filters
    basic = _apply_base_filters(
        basic,
        opponent=opponent,
        home_only=home_only,
        away_only=away_only,
        wins_only=wins_only,
        losses_only=losses_only,
        start_date=start_date,
        end_date=end_date,
    )

    if basic.empty:
        return NoResult(query_class="leaderboard", reason="no_match")

    stat_col = stat.lower()
    if stat_col not in basic.columns:
        return NoResult(query_class="leaderboard", reason="no_data")

    basic[stat_col] = pd.to_numeric(basic[stat_col], errors="coerce").fillna(0)
    basic["_qualifies"] = (basic[stat_col] >= min_value).astype(int)

    event_label = f"games_{stat_col}_{int(min_value)}+"

    # Determine groupby columns — prefer team_abbr, fall back to team_name
    group_col = None
    name_col = None
    for candidate in ["team_abbr", "team_name"]:
        if candidate in basic.columns:
            group_col = candidate
            name_col = candidate
            break

    if group_col is None:
        return NoResult(query_class="leaderboard", reason="no_data")

    grouped = basic.groupby(group_col, as_index=False).agg(
        occurrence_count=("_qualifies", "sum"),
        games_played=("game_id", "nunique"),
    )

    # Apply minimum games filter
    grouped = grouped[grouped["games_played"] >= min_games].copy()

    # Remove teams with zero occurrences
    grouped = grouped[grouped["occurrence_count"] > 0].copy()

    if grouped.empty:
        return NoResult(query_class="leaderboard", reason="no_match")

    # Sort and rank
    grouped = (
        grouped.sort_values(
            by=["occurrence_count", "games_played", group_col],
            ascending=[False, False, True],
        )
        .head(limit)
        .reset_index(drop=True)
    )

    grouped.insert(0, "rank", range(1, len(grouped) + 1))
    grouped = grouped.rename(columns={"occurrence_count": event_label})

    # Build output columns
    out_cols = ["rank", group_col, "games_played", event_label]

    # Season info
    if len(seasons) > 1:
        grouped["seasons"] = f"{seasons[0]} to {seasons[-1]}"
    else:
        grouped["season"] = seasons[0]
    grouped["season_type"] = season_type

    out_cols.extend(["seasons" if len(seasons) > 1 else "season", "season_type"])
    out_cols = [c for c in out_cols if c in grouped.columns]

    # Freshness
    current_through = compute_current_through_for_seasons(seasons, season_type)

    # Caveats
    caveats: list[str] = []
    if opponent:
        caveats.append(f"filtered to games vs {opponent.upper()}")
    if len(seasons) > 1:
        caveats.append(f"aggregated across {len(seasons)} seasons ({seasons[0]} to {seasons[-1]})")
    if home_only:
        caveats.append("home games only")
    if away_only:
        caveats.append("away games only")
    if wins_only:
        caveats.append("wins only")
    if losses_only:
        caveats.append("losses only")

    return LeaderboardResult(
        leaders=grouped[out_cols].copy(),
        current_through=current_through,
        caveats=caveats,
    )
