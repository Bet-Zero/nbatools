"""C2 single bare years: "LeBron points per game in 2019".

A lone year was ignored and the question answered for the current season. A
lone year names the season that ended in it, the way season labels, "the 2016
playoffs" and "the 2016 title" do, and a note says which season was read. A
range ("since 2010", "from 2010 to 2015") bounds time instead, so it starts
with the season that began in its first year.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query

pytestmark = pytest.mark.engine


def _span(query: str) -> tuple:
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    return kwargs.get("season"), kwargs.get("start_season"), kwargs.get("end_season")


@pytest.mark.parametrize(
    ("query", "season"),
    [
        ("Lakers record in 2024", "2023-24"),
        ("LeBron points per game in 2019", "2018-19"),
        ("best record in 2016", "2015-16"),
        ("Jokic stats for 2023", "2022-23"),
        ("LeBron stats in the 2019 season", "2018-19"),
        ("Lakers 2019 record", "2018-19"),
        ("LeBron 2019 stats", "2018-19"),
        ("Celtics playoff record in 2024", "2023-24"),
        ("Celtics conference finals record in 2024", "2023-24"),
    ],
)
def test_lone_year_names_the_season_that_ended_in_it(query, season):
    parsed = parse_query(query)
    assert _span(query) == (season, None, None)
    year = query.split("20", 1)[1][:2]
    assert f"default: read 20{year} as the {season} season, the one that ended in 20{year}" in (
        parsed.get("notes") or []
    )


def test_two_consecutive_years_are_a_span():
    assert _span("LeBron 30 point games in 2024 and 2025") == (None, "2023-24", "2024-25")


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("LeBron since 2019", (None, "2019-20", "2025-26")),
        ("LeBron from 2019 to 2021", (None, "2019-20", "2021-22")),
        ("Lakers record in 2024-25", ("2024-25", None, None)),
        ("LeBron games on March 3 2024", ("2023-24", None, None)),
    ],
)
def test_ranges_seasons_and_dates_are_unchanged(query, expected):
    assert _span(query) == expected


@pytest.mark.parametrize("query", ["LeBron games scoring 2019 points"])
def test_stat_values_are_not_years(query):
    parsed = parse_query(query)
    assert not any("read 2019" in note for note in parsed.get("notes") or [])
