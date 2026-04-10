"""Shared season-string helpers used across command modules."""

from __future__ import annotations


def season_to_int(season: str) -> int:
    return int(season.split("-")[0])


def int_to_season(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"


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
