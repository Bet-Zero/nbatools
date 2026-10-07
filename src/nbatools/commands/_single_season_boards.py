"""Best single seasons: rank one row per season across a span.

"most points in a single season", "most wins in a single season": each
season is built on its own, then the seasons' rows are merged and re-ranked,
so one row is one player season or one team season.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from nbatools.commands._seasons import resolve_seasons
from nbatools.commands.freshness import compute_current_through_for_seasons
from nbatools.commands.structured_results import LeaderboardResult, NoResult


def best_single_seasons(
    build: Callable[..., LeaderboardResult | NoResult],
    kwargs: dict,
    *,
    target_col: str,
    name_col: str,
    full_seasons_only: bool = False,
) -> LeaderboardResult | NoResult:
    """Build each season in the span on its own and rank the merged rows.

    ``full_seasons_only`` drops rows with fewer than half the games of the
    span's longest row, so a team ten games into a season does not top a
    per-game or win-percentage board.
    """
    seasons = resolve_seasons(None, kwargs["start_season"], kwargs["end_season"])
    frames: list[pd.DataFrame] = []
    caveats: list[str] = []
    empty: pd.DataFrame | None = None
    metadata: dict = {}
    for one in seasons:
        result = build(**{**kwargs, "season": one, "start_season": None, "end_season": None})
        if isinstance(result, LeaderboardResult):
            # Display names a season board found ("Los Angeles Lakers").
            metadata.update(result.metadata or {})
        if isinstance(result, LeaderboardResult) and result.leaders.empty:
            empty = result.leaders
        if not isinstance(result, LeaderboardResult) or result.leaders.empty:
            continue
        frames.append(result.leaders)
        caveats.extend(c for c in result.caveats if c not in caveats)
    if not frames and empty is not None and kwargs.get("min_total") is not None:
        # "players with 300 threes in a season": nobody reached it, a valid zero.
        frames.append(empty)
    if not frames:
        return NoResult(
            query_class="leaderboard",
            reason="no_match",
            notes=["No games matched the specified filters"],
        )
    combined = pd.concat(frames, ignore_index=True).drop(columns=["rank"])
    if full_seasons_only and "games_played" in combined.columns:
        floor = combined["games_played"].max() / 2
        kept = combined[combined["games_played"] >= floor]
        if len(kept) < len(combined):
            caveats.append(f"seasons with fewer than {int(floor + 0.5)} games left out")
        combined = kept
    ascending = kwargs["ascending"]
    by = list(dict.fromkeys([target_col, "games_played", name_col]))
    order = [ascending, True] if target_col == "games_played" else [ascending, False, True]
    combined = combined.sort_values(by=by, ascending=order)
    if kwargs.get("min_total") is None:
        # A threshold list keeps every season at the line.
        combined = combined.head(kwargs["limit"])
    combined = combined.reset_index(drop=True)
    combined.insert(0, "rank", range(1, len(combined) + 1))
    caveats.insert(0, f"single seasons ranked across {seasons[0]} to {seasons[-1]}")
    return LeaderboardResult(
        leaders=combined,
        current_through=compute_current_through_for_seasons(seasons, kwargs["season_type"]),
        caveats=caveats,
        metadata=metadata,
    )


def apply_win_bounds(df: pd.DataFrame, min_wins: int | None, max_wins: int | None) -> pd.DataFrame:
    """ "teams with at least 50 wins": keep rows whose wins fall in the bounds."""
    if min_wins is not None:
        df = df[df["wins"] >= min_wins].copy()
    if max_wins is not None:
        df = df[df["wins"] <= max_wins].copy()
    return df


def win_bounds_caveat(min_wins: int | None, max_wins: int | None) -> str | None:
    if min_wins is not None and max_wins is not None:
        return f"teams with {min_wins} to {max_wins} wins"
    if min_wins is not None:
        return f"teams with at least {min_wins} wins"
    if max_wins is not None:
        return f"teams with at most {max_wins} wins"
    return None
