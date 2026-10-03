"""Shared season-string helpers used across command modules."""

from __future__ import annotations

import re
from datetime import date

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EARLIEST_SEASON = "1996-97"
# Fallbacks only: the latest season is read from the served data, so a new
# season becomes queryable when its games are published, without a code change.
# These apply when no game data is reachable (data-free tests, a broken source).
LATEST_REGULAR_SEASON = "2025-26"
LATEST_PLAYOFF_SEASON = "2025-26"

# A season is labelled by the year it starts. Games run October to June; July
# is draft and free agency for the season just finished, so a date belongs to
# the next season's label from August onward.
_SEASON_LABEL_ROLLOVER_MONTH = 8


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def season_to_int(season: str) -> int:
    return int(season.split("-")[0])


def int_to_season(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"


def today() -> date:
    """Return today's date. Tests replace this to control the calendar."""
    return date.today()


def season_for_date(day: date) -> str:
    """Return the season label a calendar date belongs to."""
    start = day.year if day.month >= _SEASON_LABEL_ROLLOVER_MONTH else day.year - 1
    return int_to_season(start)


_SLICE_NAME = re.compile(r"(\d{4}-\d{2})_(regular_season|playoffs)\.csv$")
_LATEST_SERVED_CACHE: dict[tuple[str, str], str | None] = {}


def latest_served_season(season_type: str) -> str | None:
    """Return the newest season with final games in the served data, if any.

    Cached per published generation, so it is read once per generation rather
    than per query. The unversioned legacy layout is written in place (the
    local refresh loop), so it is read fresh every time.
    """
    from nbatools.data_source import (
        LEGACY_GENERATION,
        DataSourceError,
        data_glob,
        data_read_csv,
        data_source_cache_key,
    )

    kind = "playoffs" if season_type == "Playoffs" else "regular_season"
    try:
        cache_key = (data_source_cache_key(), kind)
    except DataSourceError:
        return None
    if cache_key in _LATEST_SERVED_CACHE:
        return _LATEST_SERVED_CACHE[cache_key]

    latest: str | None = None
    try:
        seasons = sorted(
            (
                match.group(1)
                for path in data_glob(f"raw/games/*_{kind}.csv")
                if (match := _SLICE_NAME.search(path.name)) and match.group(2) == kind
            ),
            reverse=True,
        )
        # A slice published before its first game has no final rows; skip it.
        for season in seasons:
            games = data_read_csv(f"raw/games/{season}_{kind}.csv", usecols=["is_final"])
            flags = games["is_final"].astype(str).str.strip().str.lower()
            if flags.isin({"1", "true", "1.0"}).any():
                latest = season
                break
    except (DataSourceError, OSError, ValueError, KeyError):
        # Unreadable now; fall back without caching so a transient failure
        # does not pin the fallback for the life of the process.
        return None
    if not cache_key[0].endswith(f":{LEGACY_GENERATION}"):
        _LATEST_SERVED_CACHE[cache_key] = latest
    return latest


def reset_latest_served_season_cache() -> None:
    _LATEST_SERVED_CACHE.clear()


def default_end_season(season_type: str) -> str:
    """Return the latest season for the given season_type.

    The newest season with games in the served data; the constants above only
    when no game data is reachable.
    """
    served = latest_served_season(season_type)
    if served is not None:
        return served
    if season_type == "Playoffs":
        return LATEST_PLAYOFF_SEASON
    return LATEST_REGULAR_SEASON


def previous_season(season_type: str) -> str:
    """Return the season before the current one, for "last season".

    The current season is the latest one with regular-season games for both
    season types: in January 2027 "last season's playoffs" are the 2025-26
    playoffs, not the season before the latest finished postseason.
    """
    del season_type
    latest = default_end_season("Regular Season")
    return int_to_season(season_to_int(latest) - 1)


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
