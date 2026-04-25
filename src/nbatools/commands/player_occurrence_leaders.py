"""Player occurrence leaderboard: rank players by count of threshold-event games.

This module answers questions like:
- "most 40 point games since 2015"
- "most triple doubles since 2020"
- "leaders in 5+ three games last 3 seasons"
- "most 10+ assist games vs Celtics since 2021"
- "most games with 30+ points and 10+ rebounds since 2020" (compound occurrence)
- "games with 40+ points and 5+ threes since 2022" (compound occurrence)

It loads game logs, applies all standard filters (season range, opponent,
playoffs, home/away, W/L), counts qualifying games per player, and returns
a LeaderboardResult ranked by occurrence count.

Compound Occurrences
--------------------
Compound occurrence queries allow multiple threshold conditions combined with AND.
Each condition specifies a stat and minimum value that must all be met in the same game.

For example: "games with 30+ points and 10+ rebounds" requires BOTH conditions
to be true in a single game for it to count as a qualifying occurrence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.data_utils import load_player_games_for_seasons
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
        The stat column name (e.g., "pts", "reb", "ast").
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

# Stats available for occurrence thresholds (must exist in game log data).
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

# Minimum games for a player to appear on occurrence leaderboard.
DEFAULT_MIN_GAMES = 1

# Special multi-stat event types.
SPECIAL_EVENT_STATS = {
    "triple_double": {
        "threshold": 10,
        "min_categories": 3,
        "stats": ["pts", "reb", "ast", "stl", "blk"],
    },
    "double_double": {
        "threshold": 10,
        "min_categories": 2,
        "stats": ["pts", "reb", "ast", "stl", "blk"],
    },
}


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


def _flag_special_event(df: pd.DataFrame, event_type: str) -> pd.Series:
    """Return a boolean Series marking rows that qualify for a special event."""
    spec = SPECIAL_EVENT_STATS[event_type]
    threshold = spec["threshold"]
    min_cats = spec["min_categories"]
    available = [s for s in spec["stats"] if s in df.columns]

    if len(available) < min_cats:
        return pd.Series(False, index=df.index)

    # Count how many stat categories meet the threshold per row.
    qualifying = pd.DataFrame(index=df.index)
    for s in available:
        qualifying[s] = pd.to_numeric(df[s], errors="coerce").fillna(0) >= threshold

    return qualifying.sum(axis=1) >= min_cats


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
    special_event: str | None = None,
) -> str:
    """Build a descriptive event label for the occurrence column.

    Examples:
    - Single: "games_pts_30+"
    - Compound: "games_pts_30+_reb_10+"
    - Special: "triple doubles"
    """
    if special_event:
        return special_event.replace("_", " ") + "s"

    if conditions and len(conditions) > 0:
        # Compound: build label from all conditions
        parts = []
        for cond in conditions:
            stat_name = cond.stat.lower()
            if cond.min_value is not None and cond.max_value is not None:
                # Range: "pts_20-30"
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
    special_event: str | None = None,
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
    limit: int | None = 10,
    min_games: int = DEFAULT_MIN_GAMES,
    player: str | None = None,
    **_context_filters: Any,
) -> LeaderboardResult | NoResult:
    """Build a player occurrence leaderboard.

    Supports three modes:
    1. Single stat threshold: stat + min_value (legacy, still supported)
    2. Special events: special_event (triple_double, double_double)
    3. Compound conditions: conditions list with multiple thresholds (AND logic)

    Parameters
    ----------
    stat : str or None
        The stat column to threshold on (e.g. "pts", "fg3m").
        Mutually exclusive with *special_event* and *conditions*.
    min_value : float or None
        The minimum value for *stat* to count as a qualifying game.
        Required when *stat* is provided.
    max_value : float or None
        The maximum value for *stat* (for "under X" queries).
    special_event : str or None
        A special multi-stat event type: "triple_double" or "double_double".
        Mutually exclusive with *stat* and *conditions*.
    conditions : list[OccurrenceCondition | dict] or None
        List of threshold conditions that must ALL be met (AND logic).
        Each can be an OccurrenceCondition or a dict with {stat, min_value, max_value}.
        Mutually exclusive with *stat* and *special_event*.
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
    limit : int or None
        Number of leaders to return. If None, return all qualifying players.
    min_games : int
        Minimum total games played for a player to be eligible.
    player : str or None
        If provided, filter to only this player (for single-player occurrence counts).

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

    # Validate parameters - exactly one mode must be active
    modes_active = sum(
        [
            normalized_conditions is not None and len(normalized_conditions) > 0,
            special_event is not None,
        ]
    )

    if modes_active == 0:
        raise ValueError("Either stat+min_value, special_event, or conditions must be provided")
    if modes_active > 1:
        raise ValueError("Cannot combine stat, special_event, and conditions - use only one mode")

    # Validate conditions
    if normalized_conditions:
        _validate_conditions(normalized_conditions)

    if special_event is not None and special_event not in SPECIAL_EVENT_STATS:
        raise ValueError(
            f"Unsupported special_event: {special_event}. Allowed: {sorted(SPECIAL_EVENT_STATS)}"
        )
    if limit is not None and limit <= 0:
        raise ValueError("limit must be greater than 0")

    # Resolve seasons
    try:
        seasons = resolve_seasons(season, start_season, end_season)
    except ValueError:
        return NoResult(query_class="leaderboard", reason="no_data")

    # Load game data
    try:
        basic = load_player_games_for_seasons(seasons, season_type)
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

    # Filter to specific player if requested
    if player:
        player_upper = player.upper()
        player_mask = basic["player_name"].str.upper() == player_upper
        if not player_mask.any():
            return NoResult(query_class="leaderboard", reason="no_match")
        basic = basic[player_mask].copy()

    # Determine which games qualify
    if special_event:
        qualifying_mask = _flag_special_event(basic, special_event)
    else:
        qualifying_mask = _flag_compound_conditions(basic, normalized_conditions or [])

    # Build event label for output column
    event_label = _build_event_label(
        conditions=normalized_conditions,
        stat=stat,
        min_value=min_value,
        special_event=special_event,
    )

    # Count qualifying games and total games per player
    basic["_qualifies"] = qualifying_mask.astype(int)

    grouped = basic.groupby(["player_id", "player_name"], as_index=False).agg(
        occurrence_count=("_qualifies", "sum"),
        games_played=("game_id", "nunique"),
    )

    # Apply minimum games filter
    grouped = grouped[grouped["games_played"] >= min_games].copy()

    # Remove players with zero occurrences
    grouped = grouped[grouped["occurrence_count"] > 0].copy()

    if grouped.empty:
        return NoResult(query_class="leaderboard", reason="no_match")

    # Get latest team for each player
    if "team_abbr" in basic.columns:
        latest_team = basic.sort_values("game_date", ascending=True).drop_duplicates(
            subset=["player_id"], keep="last"
        )[["player_id", "team_abbr"]]
        grouped = grouped.merge(latest_team, on="player_id", how="left")

    # Sort and rank
    grouped = grouped.sort_values(
        by=["occurrence_count", "games_played", "player_name"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    if limit is not None:
        grouped = grouped.head(limit).reset_index(drop=True)

    grouped.insert(0, "rank", range(1, len(grouped) + 1))

    # Rename occurrence_count to the descriptive event label
    grouped = grouped.rename(columns={"occurrence_count": event_label})

    # Build output columns
    out_cols = ["rank", "player_name"]
    if "team_abbr" in grouped.columns:
        out_cols.append("team_abbr")
    out_cols.extend(["games_played", event_label])

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
    if special_event:
        spec = SPECIAL_EVENT_STATS[special_event]
        stat_list = ", ".join(spec["stats"])
        caveats.append(
            f"{special_event.replace('_', ' ')}: {spec['min_categories']}+ categories "
            f"of {stat_list} reaching {spec['threshold']}+"
        )
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
