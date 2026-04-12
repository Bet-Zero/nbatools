"""Advanced metric capability map.

Defines which metrics are supported, at what grain they are valid,
and where they are intentionally unsupported.  Used by command modules
and natural-query routing to produce guardrails and caveats.
"""

from __future__ import annotations

from enum import StrEnum
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Grain enum
# ---------------------------------------------------------------------------


class MetricGrain(StrEnum):
    """Level at which a metric is meaningful."""

    GAME = "game"
    FILTERED_SAMPLE = "filtered_sample"
    SEASON = "season"
    MULTI_SEASON = "multi_season"


# ---------------------------------------------------------------------------
# Metric source
# ---------------------------------------------------------------------------


class MetricSource(StrEnum):
    """How we get the metric value."""

    BOX_SCORE = "box_score"  # computable from game-level box score
    GAME_LOG_DERIVED = "game_log_derived"  # computable from aggregated game logs
    SEASON_ADVANCED = "season_advanced"  # only from season-advanced files


# ---------------------------------------------------------------------------
# Metric descriptor
# ---------------------------------------------------------------------------


class MetricDescriptor(NamedTuple):
    """Describes one advanced metric."""

    canonical: str  # canonical column name
    label: str  # human-readable label
    source: MetricSource
    valid_grains: frozenset[MetricGrain]
    player: bool  # available for player queries
    team: bool  # available for team queries
    higher_is_better: bool  # default sort direction


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

METRIC_REGISTRY: dict[str, MetricDescriptor] = {
    # Box-score percentages — valid at every grain
    "efg_pct": MetricDescriptor(
        canonical="efg_pct",
        label="eFG%",
        source=MetricSource.BOX_SCORE,
        valid_grains=frozenset(MetricGrain),
        player=True,
        team=True,
        higher_is_better=True,
    ),
    "ts_pct": MetricDescriptor(
        canonical="ts_pct",
        label="TS%",
        source=MetricSource.BOX_SCORE,
        valid_grains=frozenset(MetricGrain),
        player=True,
        team=True,
        higher_is_better=True,
    ),
    "fg_pct": MetricDescriptor(
        canonical="fg_pct",
        label="FG%",
        source=MetricSource.BOX_SCORE,
        valid_grains=frozenset(MetricGrain),
        player=True,
        team=True,
        higher_is_better=True,
    ),
    "fg3_pct": MetricDescriptor(
        canonical="fg3_pct",
        label="3P%",
        source=MetricSource.BOX_SCORE,
        valid_grains=frozenset(MetricGrain),
        player=True,
        team=True,
        higher_is_better=True,
    ),
    "ft_pct": MetricDescriptor(
        canonical="ft_pct",
        label="FT%",
        source=MetricSource.BOX_SCORE,
        valid_grains=frozenset(MetricGrain),
        player=True,
        team=True,
        higher_is_better=True,
    ),
    # Game-log-derived advanced metrics — computable from aggregated game logs
    # with team context.  Valid at filtered_sample, season, multi-season.
    # NOT valid at single-game grain because team context is too noisy.
    "usg_pct": MetricDescriptor(
        canonical="usg_pct",
        label="USG%",
        source=MetricSource.GAME_LOG_DERIVED,
        valid_grains=frozenset(
            {MetricGrain.FILTERED_SAMPLE, MetricGrain.SEASON, MetricGrain.MULTI_SEASON}
        ),
        player=True,
        team=False,
        higher_is_better=True,
    ),
    "ast_pct": MetricDescriptor(
        canonical="ast_pct",
        label="AST%",
        source=MetricSource.GAME_LOG_DERIVED,
        valid_grains=frozenset(
            {MetricGrain.FILTERED_SAMPLE, MetricGrain.SEASON, MetricGrain.MULTI_SEASON}
        ),
        player=True,
        team=False,
        higher_is_better=True,
    ),
    "reb_pct": MetricDescriptor(
        canonical="reb_pct",
        label="REB%",
        source=MetricSource.GAME_LOG_DERIVED,
        valid_grains=frozenset(
            {MetricGrain.FILTERED_SAMPLE, MetricGrain.SEASON, MetricGrain.MULTI_SEASON}
        ),
        player=True,
        team=False,
        higher_is_better=True,
    ),
    "tov_pct": MetricDescriptor(
        canonical="tov_pct",
        label="TOV%",
        source=MetricSource.GAME_LOG_DERIVED,
        valid_grains=frozenset(
            {MetricGrain.FILTERED_SAMPLE, MetricGrain.SEASON, MetricGrain.MULTI_SEASON}
        ),
        player=True,
        team=False,
        higher_is_better=False,  # lower is better
    ),
    # Season-advanced-only metrics — only available from season-advanced files.
    # NOT computable from game-level box scores.
    "off_rating": MetricDescriptor(
        canonical="off_rating",
        label="OffRtg",
        source=MetricSource.SEASON_ADVANCED,
        valid_grains=frozenset({MetricGrain.SEASON}),
        player=True,
        team=True,
        higher_is_better=True,
    ),
    "def_rating": MetricDescriptor(
        canonical="def_rating",
        label="DefRtg",
        source=MetricSource.SEASON_ADVANCED,
        valid_grains=frozenset({MetricGrain.SEASON}),
        player=True,
        team=True,
        higher_is_better=False,  # lower is better
    ),
    "net_rating": MetricDescriptor(
        canonical="net_rating",
        label="NetRtg",
        source=MetricSource.SEASON_ADVANCED,
        valid_grains=frozenset({MetricGrain.SEASON}),
        player=True,
        team=True,
        higher_is_better=True,
    ),
    "pace": MetricDescriptor(
        canonical="pace",
        label="Pace",
        source=MetricSource.SEASON_ADVANCED,
        valid_grains=frozenset({MetricGrain.SEASON}),
        player=False,
        team=True,
        higher_is_better=True,
    ),
    "usage_rate": MetricDescriptor(
        canonical="usage_rate",
        label="USG%",
        source=MetricSource.SEASON_ADVANCED,
        valid_grains=frozenset({MetricGrain.SEASON}),
        player=True,
        team=False,
        higher_is_better=True,
    ),
}


# Metrics that can only come from season-advanced files and cannot be
# computed from game logs.
SEASON_ADVANCED_ONLY: frozenset[str] = frozenset(
    k for k, v in METRIC_REGISTRY.items() if v.source == MetricSource.SEASON_ADVANCED
)

# Metrics that can be computed from aggregated game logs.
GAME_LOG_DERIVABLE: frozenset[str] = frozenset(
    k
    for k, v in METRIC_REGISTRY.items()
    if v.source in (MetricSource.BOX_SCORE, MetricSource.GAME_LOG_DERIVED)
)

# Player-only advanced metrics (not team).
PLAYER_ADVANCED: frozenset[str] = frozenset(
    k
    for k, v in METRIC_REGISTRY.items()
    if v.source in (MetricSource.GAME_LOG_DERIVED, MetricSource.SEASON_ADVANCED) and v.player
)

# Team-only advanced metrics (from season-advanced).
TEAM_ADVANCED: frozenset[str] = frozenset(
    k for k, v in METRIC_REGISTRY.items() if v.source == MetricSource.SEASON_ADVANCED and v.team
)


# ---------------------------------------------------------------------------
# Validity helpers
# ---------------------------------------------------------------------------


def is_metric_valid_for_context(
    metric: str,
    *,
    grain: MetricGrain,
    is_player: bool = True,
    is_team: bool = False,
) -> bool:
    """Return whether *metric* is valid in the requested context."""
    desc = METRIC_REGISTRY.get(metric)
    if desc is None:
        return False
    if grain not in desc.valid_grains:
        return False
    if is_player and not desc.player:
        return False
    if is_team and not desc.team:
        return False
    return True


def metric_caveat(
    metric: str,
    *,
    grain: MetricGrain,
) -> str | None:
    """Return a caveat string if the metric requires one in this context, else None."""
    desc = METRIC_REGISTRY.get(metric)
    if desc is None:
        return None
    if desc.source == MetricSource.GAME_LOG_DERIVED and grain in (
        MetricGrain.FILTERED_SAMPLE,
        MetricGrain.MULTI_SEASON,
    ):
        return f"{desc.label} recomputed from filtered game-log sample"
    return None


def leaderboard_grain(
    *,
    multi_season: bool,
    date_window: bool,
    opponent_filtered: bool,
) -> MetricGrain:
    """Determine the effective grain for a leaderboard query."""
    if date_window or opponent_filtered:
        return MetricGrain.FILTERED_SAMPLE
    if multi_season:
        return MetricGrain.MULTI_SEASON
    return MetricGrain.SEASON


def blocked_leaderboard_reason(
    metric: str,
    *,
    multi_season: bool = False,
    date_window: bool = False,
    opponent_filtered: bool = False,
    is_player: bool = True,
) -> str | None:
    """Return an error message if *metric* is blocked for this leaderboard context, else None."""
    desc = METRIC_REGISTRY.get(metric)
    if desc is None:
        return f"Unknown metric: {metric}"
    grain = leaderboard_grain(
        multi_season=multi_season,
        date_window=date_window,
        opponent_filtered=opponent_filtered,
    )
    if not is_metric_valid_for_context(
        metric, grain=grain, is_player=is_player, is_team=not is_player
    ):
        reasons = []
        if multi_season:
            reasons.append("multi-season")
        if date_window:
            reasons.append("date-window")
        if opponent_filtered:
            reasons.append("opponent-filtered")
        ctx = ", ".join(reasons) if reasons else "this"
        return f"{desc.label} is not available in {ctx} context"
    return None
