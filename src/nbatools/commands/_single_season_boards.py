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
    for one in seasons:
        result = build(**{**kwargs, "season": one, "start_season": None, "end_season": None})
        if not isinstance(result, LeaderboardResult) or result.leaders.empty:
            continue
        frames.append(result.leaders)
        caveats.extend(c for c in result.caveats if c not in caveats)
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
    combined = (
        combined.sort_values(by=by, ascending=order).head(kwargs["limit"]).reset_index(drop=True)
    )
    combined.insert(0, "rank", range(1, len(combined) + 1))
    caveats.insert(0, f"single seasons ranked across {seasons[0]} to {seasons[-1]}")
    return LeaderboardResult(
        leaders=combined,
        current_through=compute_current_through_for_seasons(seasons, kwargs["season_type"]),
        caveats=caveats,
    )
