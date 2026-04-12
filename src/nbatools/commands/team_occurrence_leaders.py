"""Team occurrence leaderboard: rank teams by count of threshold-event games.

This module answers questions like:
- "most 120 point team games since 2018"
- "teams with most 130+ point games since 2020"
- "most games with 15+ threes in playoffs since 2010"
- "teams with most games scoring 120+ and making 15+ threes" (compound occurrence)

It loads team game logs, applies all standard filters (season range, opponent,
playoffs, home/away, W/L), counts qualifying games per team, and returns
a LeaderboardResult ranked by occurrence count.

Compound Occurrences
--------------------
Compound occurrence queries allow multiple threshold conditions combined with AND.
Each condition specifies a stat and minimum value that must all be met in the same game.

For example: "games with 120+ points and 15+ threes" requires BOTH conditions
to be true in a single game for it to count as a qualifying occurrence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.data_utils import load_team_games_for_seasons
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.structured_results import LeaderboardResult, NoResult

# ---------------------------------------------------------------------------
# Condition dataclass for compound occurrence queries
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OccurrenceCondition:
    """A single threshold condition for occurrence queries.

    Attributes
    ----------
    stat : str
        The stat column name (e.g., "pts", "reb", "fg3m").
    min_value : float or None
        Minimum threshold (inclusive). If set, games must have stat >= min_value.
    max_value : float or None
        Maximum threshold (inclusive). If set, games must have stat <= max_value.
        Typically used for "under X" conditions.
    """

    stat: str
    min_value: float | None = None
    max_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for serialization."""
        d: dict[str, Any] = {"stat": self.stat}
        if self.min_value is not None:
            d["min_value"] = self.min_value
        if self.max_value is not None:
            d["max_value"] = self.max_value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OccurrenceCondition:
        """Create from dict."""
        return cls(
            stat=d["stat"],
            min_value=d.get("min_value"),
            max_value=d.get("max_value"),
        )


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

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


def _flag_compound_conditions(df: pd.DataFrame, conditions: list[OccurrenceCondition]) -> pd.Series:
    """Return a boolean Series marking rows that satisfy ALL conditions (AND logic).

    Parameters
    ----------
    df : pd.DataFrame
        Game log data with stat columns.
    conditions : list[OccurrenceCondition]
        List of threshold conditions that must ALL be satisfied.

    Returns
    -------
    pd.Series
        Boolean mask where True = row satisfies all conditions.
    """
    if not conditions:
        return pd.Series(True, index=df.index)

    combined_mask = pd.Series(True, index=df.index)

    for cond in conditions:
        stat_col = cond.stat.lower()
        if stat_col not in df.columns:
            # If stat doesn't exist, no rows can qualify for this condition
            return pd.Series(False, index=df.index)

        values = pd.to_numeric(df[stat_col], errors="coerce").fillna(0)

        cond_mask = pd.Series(True, index=df.index)
        if cond.min_value is not None:
            cond_mask &= values >= cond.min_value
        if cond.max_value is not None:
            cond_mask &= values <= cond.max_value

        combined_mask &= cond_mask

    return combined_mask


def _build_event_label(
    conditions: list[OccurrenceCondition] | None = None,
    stat: str | None = None,
    min_value: float | None = None,
) -> str:
    """Build a descriptive event label for the occurrence column.

    Examples:
    - Single: "games_pts_120+"
    - Compound: "games_pts_120+_fg3m_15+"
    """
    if conditions and len(conditions) > 0:
        # Compound: build label from all conditions
        parts = []
        for cond in conditions:
            stat_name = cond.stat.lower()
            if cond.min_value is not None and cond.max_value is not None:
                parts.append(f"{stat_name}_{int(cond.min_value)}-{int(cond.max_value)}")
            elif cond.min_value is not None:
                parts.append(f"{stat_name}_{int(cond.min_value)}+")
            elif cond.max_value is not None:
                parts.append(f"{stat_name}_under_{int(cond.max_value)}")
        return "games_" + "_".join(parts)

    if stat and min_value is not None:
        return f"games_{stat.lower()}_{int(min_value)}+"

    return "qualifying_games"


def _validate_conditions(conditions: list[OccurrenceCondition]) -> None:
    """Validate a list of occurrence conditions.

    Raises
    ------
    ValueError
        If any condition has an unsupported stat or invalid values.
    """
    if not conditions:
        raise ValueError("At least one condition must be provided")

    for cond in conditions:
        if cond.stat.lower() not in ALLOWED_STATS:
            raise ValueError(f"Unsupported stat: {cond.stat}. Allowed: {sorted(ALLOWED_STATS)}")
        if cond.min_value is None and cond.max_value is None:
            raise ValueError(f"Condition for {cond.stat} must have min_value or max_value")


def build_result(
    stat: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    conditions: list[OccurrenceCondition | dict] | None = None,
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
    team: str | None = None,
) -> LeaderboardResult | NoResult:
    """Build a team occurrence leaderboard.

    Supports two modes:
    1. Single stat threshold: stat + min_value (legacy, still supported)
    2. Compound conditions: conditions list with multiple thresholds (AND logic)

    Parameters
    ----------
    stat : str or None
        The stat column to threshold on (e.g. "pts", "fg3m").
    min_value : float or None
        The minimum value for *stat* to count as a qualifying game.
    max_value : float or None
        The maximum value for *stat* (for "under X" queries).
    conditions : list[OccurrenceCondition | dict] or None
        List of threshold conditions that must ALL be met (AND logic).
        Each can be an OccurrenceCondition or a dict with {stat, min_value, max_value}.
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
    team : str or None
        If provided, filter to only this team (for single-team occurrence counts).

    Returns
    -------
    LeaderboardResult or NoResult
    """
    # Normalize conditions from dicts to OccurrenceCondition objects
    normalized_conditions: list[OccurrenceCondition] | None = None
    if conditions:
        normalized_conditions = []
        for c in conditions:
            if isinstance(c, dict):
                normalized_conditions.append(OccurrenceCondition.from_dict(c))
            else:
                normalized_conditions.append(c)

    # Convert single stat/min_value to a conditions list for unified processing
    if stat is not None and normalized_conditions is None:
        normalized_conditions = [
            OccurrenceCondition(stat=stat, min_value=min_value, max_value=max_value)
        ]

    # Validate - must have conditions
    if normalized_conditions is None or len(normalized_conditions) == 0:
        raise ValueError("Either stat+min_value or conditions must be provided")

    # Validate conditions
    _validate_conditions(normalized_conditions)

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

    # Filter to specific team if requested
    if team:
        team_upper = team.upper()
        team_mask = pd.Series(False, index=basic.index)
        for col in ["team_abbr", "team_name"]:
            if col in basic.columns:
                team_mask |= basic[col].astype(str).str.upper() == team_upper
        if not team_mask.any():
            return NoResult(query_class="leaderboard", reason="no_match")
        basic = basic[team_mask].copy()

    # Determine which games qualify
    qualifying_mask = _flag_compound_conditions(basic, normalized_conditions)

    # Build event label for output column
    event_label = _build_event_label(
        conditions=normalized_conditions,
        stat=stat,
        min_value=min_value,
    )

    basic["_qualifies"] = qualifying_mask.astype(int)

    # Determine groupby columns — prefer team_abbr, fall back to team_name
    group_col = None
    for candidate in ["team_abbr", "team_name"]:
        if candidate in basic.columns:
            group_col = candidate
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
    if normalized_conditions and len(normalized_conditions) > 1:
        # Add caveat explaining compound conditions
        parts = []
        for cond in normalized_conditions:
            if cond.min_value is not None and cond.max_value is not None:
                parts.append(f"{cond.stat} between {cond.min_value} and {cond.max_value}")
            elif cond.min_value is not None:
                parts.append(f"{cond.stat} >= {cond.min_value}")
            elif cond.max_value is not None:
                parts.append(f"{cond.stat} <= {cond.max_value}")
        caveats.append(f"compound occurrence: {' AND '.join(parts)}")
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
