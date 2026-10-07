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
        # A year closing the question ("Lakers record 2024") was dropped and
        # the current season answered.
        ("Lakers record 2024", "2023-24"),
        ("LeBron stats 2016", "2015-16"),
        ("Lakers playoff record 2016", "2015-16"),
        ("Jokic triple doubles 2025?", "2024-25"),
        ("Celtics vs Lakers 2024", "2023-24"),
        ("top scorers 2024", "2023-24"),
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


@pytest.mark.parametrize(
    "query",
    [
        "LeBron games scoring 2019 points",
        "how many players scored 2000",
    ],
)
def test_stat_values_are_not_years(query):
    parsed = parse_query(query)
    assert not any("read 20" in note for note in parsed.get("notes") or [])


def _notes(query: str) -> list[str]:
    return parse_query(query).get("notes") or []


@pytest.mark.parametrize(
    "query",
    [
        "Lakers 2024 and 2025 record",
        "LeBron 2024 and 2025 stats",
        "LeBron in 2024 and in 2025",
        "Jokic in 2024 & 2025",
        "Jokic in 2024, 2025",
    ],
)
def test_two_consecutive_years_in_any_join_are_a_span(query):
    assert _span(query) == (None, "2023-24", "2024-25")
    assert not any("read 202" in note for note in _notes(query))


@pytest.mark.parametrize(
    "query",
    [
        "LeBron since the 2019 season",
        "LeBron after the 2024 season",
        "LeBron before the 2025 season",
        "LeBron through the 2025 season",
        "Lakers in 2024 and 2025 and 2026",
        "LeBron in 2019 or 2020",
        "Jokic in 2023 and 2025",
        "LeBron averages in 2025 vs 2024",
        "LeBron scored 30 points in 2000 games",
    ],
)
def test_years_a_lone_year_cannot_own_are_not_read_as_one_season(query):
    # A range word, a third year, a gap or a count: never one season with a note.
    assert not any("as the" in note for note in _notes(query))
    season, start, end = _span(query)
    assert not (start is not None and start == end)


@pytest.mark.parametrize(
    ("query", "season"),
    [
        ("Lakers win streak in 2024", "2023-24"),
        ("Jokic longest streak of triple doubles in 2025", "2024-25"),
    ],
)
def test_streaks_use_the_named_year(query, season):
    assert _span(query) == (season, None, None)


def test_years_outside_the_data_say_so():
    notes = _notes("LeBron in 1990")
    assert any(note.startswith("coverage: the data covers 1996-97") for note in notes)


@pytest.mark.parametrize(
    ("query", "season"),
    [
        ("LeBron in 2025 points per game", "2024-25"),
        ("Jokic in 2025 rebounds", "2024-25"),
        ("Lakers in 2025 wins", "2024-25"),
        ("Jokic for 2025 games", "2024-25"),
    ],
)
def test_stat_words_after_a_year_keep_the_year(query, season):
    assert _span(query)[0] == season


def test_playoff_year_has_no_default_season_note():
    notes = _notes("LeBron playoff stats in 2026")
    assert any("read 2026 as the 2025-26 season" in note for note in notes)
    assert not any("no season specified" in note for note in notes)


def test_trailing_year_answers_a_leaderboard():
    # The leaderboard grammar accepts the closing year it now reads.
    parsed = parse_query("top scorers 2024")
    assert parsed["route"] == "season_leaders"
    assert not parsed["route_kwargs"].get("unsupported_filters")


@pytest.mark.parametrize(
    "query",
    [
        # A value word owns the number.
        "top scorers min 2000",
        "Lakers record when allowing 2000",
        "Lakers record when giving up 2000",
        "scoring leaders min minutes 2000",
        "LeBron game 2000",
        # A second year, a range end or a comparison.
        "Lakers record 2010 2016",
        "Lakers record 2016 compared to 2024",
        "Warriors 2017 vs Cavs 2016",
        "LeBron pre 2016",
        "LeBron up to 2016",
        "Lakers record to 2024",
        # Other time wording already names the time.
        "Lakers record this season 2016",
        "top scorers last 3 seasons 2016",
        "most points career 2016",
        "top scorers since 2010 2016",
        # No NBA season ended then.
        "Lakers record 2099",
        "Lakers record 1900",
    ],
)
def test_closing_years_owned_elsewhere_are_not_one_season(query):
    assert not any("as the" in note for note in _notes(query))


@pytest.mark.parametrize(
    "query",
    [
        "who led the league in scoring 2016",
        "top scorers with 2000",
        "top scorers min 2000",
        "most points this season 2016",
    ],
)
def test_leaderboard_refuses_a_closing_year_the_parser_set_aside(query):
    # The board must not answer the current season for a year it never read.
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs.get("unsupported_filters") == ["leaderboard_request_unclear"]
