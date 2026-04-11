"""Shared season-string helpers used across command modules."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EARLIEST_SEASON = "1996-97"
LATEST_REGULAR_SEASON = "2025-26"
LATEST_PLAYOFF_SEASON = "2024-25"


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def season_to_int(season: str) -> int:
    return int(season.split("-")[0])


def int_to_season(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"


def default_end_season(season_type: str) -> str:
    """Return the latest season for the given season_type."""
    if season_type == "Playoffs":
        return LATEST_PLAYOFF_SEASON
    return LATEST_REGULAR_SEASON


def resolve_seasons(
    season: str | None,
    start_season: str | None,
    end_season: str | None,
) -> list[str]:
    if season and (start_season or end_season):
        raise ValueError("Use either --season or --start-season/--end-season, not both")

    if season:
        return [season]

    if start_season and end_season:
        start = season_to_int(start_season)
        end = season_to_int(end_season)
        if end < start:
            raise ValueError("end_season must be greater than or equal to start_season")
        return [int_to_season(y) for y in range(start, end + 1)]

    raise ValueError("Provide either --season or both --start-season and --end-season")


# ---------------------------------------------------------------------------
# Historical span resolution
# ---------------------------------------------------------------------------


def resolve_since_year(year: int, season_type: str) -> tuple[str, str]:
    """Convert a bare year (e.g. 2020) into a (start_season, end_season) pair.

    ``since 2020`` maps to start_season="2020-21", end_season=latest.
    """
    return int_to_season(year), default_end_season(season_type)


def resolve_since_season(season: str, season_type: str) -> tuple[str, str]:
    """Convert an explicit season string to a (start_season, end_season) pair.

    ``since 2020-21`` maps to ("2020-21", latest).
    """
    return season, default_end_season(season_type)


def resolve_last_n_seasons(n: int, season_type: str) -> tuple[str, str]:
    """Convert 'last N seasons' to a (start_season, end_season) pair."""
    end = default_end_season(season_type)
    end_year = season_to_int(end)
    start_year = end_year - n + 1
    return int_to_season(start_year), end


def resolve_career(season_type: str) -> tuple[str, str]:
    """Return the full career span (earliest to latest)."""
    return EARLIEST_SEASON, default_end_season(season_type)
