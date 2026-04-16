"""Structured result layer for nbatools engine.

Provides typed result containers for summary, comparison, and split-summary
query classes.  Each container holds the real data (as DataFrames / dicts)
and can render itself into:
  - labeled CSV text  (current raw-output transport, backwards compatible)
  - a plain dict      (for JSON export / future API consumers)

Commands build these via ``build_result()`` helpers.  The existing ``run()``
functions call ``build_result().to_labeled_text()`` so stdout behaviour is
unchanged.

Trust/status metadata
---------------------
Every result carries first-class trust fields:

- ``result_status``   — "ok" | "no_result" | "error"
- ``result_reason``   — finer detail  ("no_match" | "no_data" | "unrouted" | free text)
- ``current_through`` — latest final game_date the data covers (when determinable)
- ``notes`` / ``caveats`` — semantic annotations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Result status vocabulary
# ---------------------------------------------------------------------------


class ResultStatus(StrEnum):
    """Canonical result statuses."""

    OK = "ok"
    NO_RESULT = "no_result"
    ERROR = "error"


class ResultReason(StrEnum):
    """Canonical reason codes attached to non-OK results."""

    NO_MATCH = "no_match"
    NO_DATA = "no_data"
    UNROUTED = "unrouted"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


# ---------------------------------------------------------------------------
# No-result sentinel
# ---------------------------------------------------------------------------


@dataclass
class NoResult:
    """Represents a query that matched no data.

    ``reason`` distinguishes *why* the result is empty:
    - ``no_match``  — data files exist but filters produced nothing
    - ``no_data``   — the underlying season/type data is unavailable
    - ``unrouted``  — the query could not be routed to a command
    - ``error``     — an unexpected error occurred
    """

    query_class: str
    reason: str = "no_match"
    result_status: str = "no_result"
    result_reason: str | None = None  # populated from *reason* if not set
    current_through: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.result_reason is None:
            self.result_reason = self.reason

    def to_labeled_text(self) -> str:
        return "SUMMARY\nno matching games\n"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "query_class": self.query_class,
            "result_status": self.result_status,
            "result_reason": self.result_reason,
            "metadata": dict(self.metadata),
            "notes": list(self.notes),
            "caveats": list(self.caveats),
            "sections": {},
        }
        if self.current_through is not None:
            d["current_through"] = self.current_through
        return d


# ---------------------------------------------------------------------------
# Summary result  (player_game_summary, game_summary)
# ---------------------------------------------------------------------------


@dataclass
class SummaryResult:
    """Structured result for summary queries.

    Holds a one-row summary DataFrame and an optional by-season breakdown.
    """

    query_class: str = "summary"
    summary: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    by_season: pd.DataFrame | None = None
    result_status: str = "ok"
    result_reason: str | None = None
    current_through: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)

    # -- rendering ----------------------------------------------------------

    def to_labeled_text(self) -> str:
        parts: list[str] = []
        parts.append("SUMMARY\n")
        parts.append(self.summary.to_csv(index=False))
        if self.by_season is not None and not self.by_season.empty:
            parts.append("BY_SEASON\n")
            parts.append(self.by_season.to_csv(index=False))
        return "".join(parts)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "query_class": self.query_class,
            "result_status": self.result_status,
            "result_reason": self.result_reason,
            "metadata": dict(self.metadata),
            "notes": list(self.notes),
            "caveats": list(self.caveats),
            "sections": {
                "summary": _df_to_records(self.summary),
            },
        }
        if self.current_through is not None:
            out["current_through"] = self.current_through
        if self.by_season is not None and not self.by_season.empty:
            out["sections"]["by_season"] = _df_to_records(self.by_season)
        return out

    def to_sections_dict(self) -> dict[str, str]:
        """Return section-label -> CSV-text mapping for the pretty formatter."""
        sections: dict[str, str] = {
            "SUMMARY": self.summary.to_csv(index=False).strip(),
        }
        if self.by_season is not None and not self.by_season.empty:
            sections["BY_SEASON"] = self.by_season.to_csv(index=False).strip()
        return sections


# ---------------------------------------------------------------------------
# Comparison result  (player_compare, team_compare)
# ---------------------------------------------------------------------------


@dataclass
class ComparisonResult:
    """Structured result for comparison queries.

    Holds a multi-row summary DataFrame (one row per entity) and a
    metric-level comparison DataFrame.
    """

    query_class: str = "comparison"
    summary: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    comparison: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    result_status: str = "ok"
    result_reason: str | None = None
    current_through: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)

    def to_labeled_text(self) -> str:
        parts: list[str] = []
        parts.append("SUMMARY\n")
        parts.append(self.summary.to_csv(index=False))
        parts.append("COMPARISON\n")
        parts.append(self.comparison.to_csv(index=False))
        return "".join(parts)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "query_class": self.query_class,
            "result_status": self.result_status,
            "result_reason": self.result_reason,
            "metadata": dict(self.metadata),
            "notes": list(self.notes),
            "caveats": list(self.caveats),
            "sections": {
                "summary": _df_to_records(self.summary),
                "comparison": _df_to_records(self.comparison),
            },
        }
        if self.current_through is not None:
            d["current_through"] = self.current_through
        return d

    def to_sections_dict(self) -> dict[str, str]:
        return {
            "SUMMARY": self.summary.to_csv(index=False).strip(),
            "COMPARISON": self.comparison.to_csv(index=False).strip(),
        }


# ---------------------------------------------------------------------------
# Split-summary result  (player_split_summary, team_split_summary)
# ---------------------------------------------------------------------------


@dataclass
class SplitSummaryResult:
    """Structured result for split-summary queries.

    Holds a one-row summary header DataFrame and a multi-row
    split-comparison DataFrame (one row per bucket).
    """

    query_class: str = "split_summary"
    summary: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    split_comparison: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    result_status: str = "ok"
    result_reason: str | None = None
    current_through: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)

    def to_labeled_text(self) -> str:
        parts: list[str] = []
        parts.append("SUMMARY\n")
        parts.append(self.summary.to_csv(index=False))
        parts.append("SPLIT_COMPARISON\n")
        parts.append(self.split_comparison.to_csv(index=False))
        return "".join(parts)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "query_class": self.query_class,
            "result_status": self.result_status,
            "result_reason": self.result_reason,
            "metadata": dict(self.metadata),
            "notes": list(self.notes),
            "caveats": list(self.caveats),
            "sections": {
                "summary": _df_to_records(self.summary),
                "split_comparison": _df_to_records(self.split_comparison),
            },
        }
        if self.current_through is not None:
            d["current_through"] = self.current_through
        return d

    def to_sections_dict(self) -> dict[str, str]:
        return {
            "SUMMARY": self.summary.to_csv(index=False).strip(),
            "SPLIT_COMPARISON": self.split_comparison.to_csv(index=False).strip(),
        }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame to a list of dicts, handling NaN -> None."""
    if df is None or df.empty:
        return []
    return [{k: (None if pd.isna(v) else v) for k, v in row.items()} for _, row in df.iterrows()]


# ---------------------------------------------------------------------------
# Finder result  (player_game_finder, game_finder)
# ---------------------------------------------------------------------------


@dataclass
class FinderResult:
    """Structured result for game-finder queries.

    Holds a multi-row DataFrame of matching games, each with rank and stats.
    """

    query_class: str = "finder"
    games: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    result_status: str = "ok"
    result_reason: str | None = None
    current_through: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)

    def to_labeled_text(self) -> str:
        parts: list[str] = []
        parts.append("FINDER\n")
        parts.append(self.games.to_csv(index=False))
        return "".join(parts)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "query_class": self.query_class,
            "result_status": self.result_status,
            "result_reason": self.result_reason,
            "metadata": dict(self.metadata),
            "notes": list(self.notes),
            "caveats": list(self.caveats),
            "sections": {
                "finder": _df_to_records(self.games),
            },
        }
        if self.current_through is not None:
            d["current_through"] = self.current_through
        return d

    def to_sections_dict(self) -> dict[str, str]:
        return {
            "FINDER": self.games.to_csv(index=False).strip(),
        }


# ---------------------------------------------------------------------------
# Leaderboard result  (season_leaders, season_team_leaders,
#                       top_player_games, top_team_games)
# ---------------------------------------------------------------------------


@dataclass
class LeaderboardResult:
    """Structured result for leaderboard queries.

    Holds a multi-row ranked DataFrame of leaders by some metric.
    """

    query_class: str = "leaderboard"
    leaders: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    result_status: str = "ok"
    result_reason: str | None = None
    current_through: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)

    def to_labeled_text(self) -> str:
        parts: list[str] = []
        parts.append("LEADERBOARD\n")
        parts.append(self.leaders.to_csv(index=False))
        return "".join(parts)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "query_class": self.query_class,
            "result_status": self.result_status,
            "result_reason": self.result_reason,
            "metadata": dict(self.metadata),
            "notes": list(self.notes),
            "caveats": list(self.caveats),
            "sections": {
                "leaderboard": _df_to_records(self.leaders),
            },
        }
        if self.current_through is not None:
            d["current_through"] = self.current_through
        return d

    def to_sections_dict(self) -> dict[str, str]:
        return {
            "LEADERBOARD": self.leaders.to_csv(index=False).strip(),
        }


# ---------------------------------------------------------------------------
# Streak result  (player_streak_finder, team_streak_finder)
# ---------------------------------------------------------------------------


@dataclass
class StreakResult:
    """Structured result for streak queries.

    Holds a multi-row DataFrame of streaks matching a condition.
    """

    query_class: str = "streak"
    streaks: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    result_status: str = "ok"
    result_reason: str | None = None
    current_through: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)

    def to_labeled_text(self) -> str:
        parts: list[str] = []
        parts.append("STREAK\n")
        parts.append(self.streaks.to_csv(index=False))
        return "".join(parts)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "query_class": self.query_class,
            "result_status": self.result_status,
            "result_reason": self.result_reason,
            "metadata": dict(self.metadata),
            "notes": list(self.notes),
            "caveats": list(self.caveats),
            "sections": {
                "streak": _df_to_records(self.streaks),
            },
        }
        if self.current_through is not None:
            d["current_through"] = self.current_through
        return d

    def to_sections_dict(self) -> dict[str, str]:
        return {
            "STREAK": self.streaks.to_csv(index=False).strip(),
        }


# ---------------------------------------------------------------------------
# Count result  (derived from finder queries with count intent)
# ---------------------------------------------------------------------------


@dataclass
class CountResult:
    """Structured result for count queries.

    Wraps a count value with the underlying matching games for detail.
    Built by post-processing a FinderResult when count intent is detected.
    """

    query_class: str = "count"
    count: int = 0
    games: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    result_status: str = "ok"
    result_reason: str | None = None
    current_through: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)

    def to_labeled_text(self) -> str:
        parts: list[str] = []
        parts.append("COUNT\n")
        parts.append(f"count\n{self.count}\n")
        if not self.games.empty:
            parts.append("FINDER\n")
            parts.append(self.games.to_csv(index=False))
        return "".join(parts)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "query_class": self.query_class,
            "result_status": self.result_status,
            "result_reason": self.result_reason,
            "metadata": dict(self.metadata),
            "notes": list(self.notes),
            "caveats": list(self.caveats),
            "sections": {
                "count": [{"count": self.count}],
            },
        }
        if self.current_through is not None:
            d["current_through"] = self.current_through
        if not self.games.empty:
            d["sections"]["finder"] = _df_to_records(self.games)
        return d

    def to_sections_dict(self) -> dict[str, str]:
        sections: dict[str, str] = {
            "COUNT": f"count\n{self.count}",
        }
        if not self.games.empty:
            sections["FINDER"] = self.games.to_csv(index=False).strip()
        return sections
