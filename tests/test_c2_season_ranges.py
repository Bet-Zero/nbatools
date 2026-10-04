"""C2 season ranges written with bare years or seasons.

"from 2010 to 2015", "between 2000-01 and 2009-10", "2015-2017" used to fall
back to the default season, answering a different question. A bare year names
the season starting in it, as "since 2010" and "the 2010s" do; for playoffs and
titles it names the season ending in it, as "the 2016 playoffs" does.
"""

from __future__ import annotations

import pytest

from nbatools.commands._parse_helpers import extract_season_range
from nbatools.commands.natural_query import parse_query

pytestmark = pytest.mark.engine


@pytest.mark.parametrize(
    ("text", "start", "end"),
    [
        ("lebron points per game from 2010 to 2015", "2010-11", "2015-16"),
        ("lakers record from 2000 to 2010", "2000-01", "2010-11"),
        ("curry stats 2015-2017", "2015-16", "2017-18"),
        ("jokic between 2020 and 2023", "2020-21", "2023-24"),
        ("lakers record between 2000-01 and 2009-10", "2000-01", "2009-10"),
        ("most points from 2010-11 to 2014-15", "2010-11", "2014-15"),
        ("most points 2010-11 through 2014-15", "2010-11", "2014-15"),
        ("duncan stats from 1999 through 2003", "1999-00", "2003-04"),
        ("curry 2016 to 2018", "2016-17", "2018-19"),
        ("lakers record since 2010 until 2020", "2010-11", "2020-21"),
        ("from the 2015-16 season to 2018", "2015-16", "2018-19"),
        ("lebron points 2003 - 2010", "2003-04", "2010-11"),
        # Written backwards: the same seasons.
        ("lakers record from 2010 to 2005", "2005-06", "2010-11"),
        # Playoffs and titles: the year a postseason ends in.
        ("how many titles did the bulls win from 1991 to 1998", "1990-91", "1997-98"),
        ("lebron playoffs from 2016 to 2018", "2015-16", "2017-18"),
        ("lakers playoff record from 2008 to 2012", "2007-08", "2011-12"),
        # Two consecutive years with a hyphen are one season written out.
        ("lebron 2019-2020 season stats", "2019-20", "2019-20"),
        ("2019-2020 playoffs", "2019-20", "2019-20"),
    ],
)
def test_year_and_season_ranges(text, start, end):
    assert extract_season_range(text) == (start, end)


@pytest.mark.parametrize(
    "text",
    [
        "curry 2015-16 stats",
        "jokic games between 20 and 30 points",
        "games between 2000 and 2050 points",
        "lebron games from 2024-01-05 to 2024-02-01",
        "lakers record since 2010",
        "lakers record in the 2010s",
        "jokic triple doubles since 2020 and 2021",
    ],
)
def test_not_a_season_range(text):
    assert extract_season_range(text) == (None, None)


@pytest.mark.parametrize(
    ("query", "route"),
    [
        ("Lebron points per game from 2010 to 2015", "player_game_summary"),
        ("Lakers record from 2000 to 2010", "team_record"),
        ("most points per game between 2000-01 and 2009-10", "season_leaders"),
    ],
)
def test_ranges_reach_the_route_instead_of_the_default_season(query, route):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == route
    assert kwargs["season"] is None
    assert kwargs["start_season"] is not None and kwargs["end_season"] is not None


@pytest.mark.parametrize(
    ("query", "season"),
    [("LeBron 2019-2020 season stats", "2019-20"), ("Lakers record 2015-2016", "2015-16")],
)
def test_written_out_season_is_one_season(query, season):
    kwargs = parse_query(query)["route_kwargs"]
    assert (kwargs["season"], kwargs["start_season"], kwargs["end_season"]) == (season, None, None)


def test_future_end_year_stops_at_the_latest_season():
    from nbatools.commands._seasons import default_end_season

    kwargs = parse_query("Lebron stats from 2020 to 2035")["route_kwargs"]
    assert kwargs["start_season"] == "2020-21"
    assert kwargs["end_season"] == default_end_season("Regular Season")
