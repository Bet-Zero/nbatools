"""Comparison wording keeps its subjects, common sample and meeting scope."""

import pytest

from nbatools.commands._date_utils import extract_date_range
from nbatools.commands.natural_query import parse_query


@pytest.mark.parametrize(
    "query,route",
    [
        (
            "Put Stephen Curry's and Jalen Brunson's 2023-24 averages side by side.",
            "player_compare",
        ),
        ("Show Nikola Jokic and Joel Embiid averages side-by-side in 2023-24", "player_compare"),
        ("How do Milwaukee and Boston compare over the 2023-24 regular season?", "team_compare"),
        ("How did the Nuggets and the Suns compare in 2023-24?", "team_compare"),
    ],
)
def test_explicit_comparison_intent(query, route):
    parsed = parse_query(query)
    assert parsed["route"] == route
    assert not parsed["route_kwargs"].get("head_to_head")


@pytest.mark.parametrize("meeting", ["games against each other", "games against one another"])
def test_explicit_reciprocal_meetings(meeting):
    parsed = parse_query(f"Compare Boston and Milwaukee only in their {meeting} during 2023-24")
    assert parsed["route"] == "team_compare"
    assert parsed["route_kwargs"]["head_to_head"] is True


@pytest.mark.parametrize(
    "query,expected",
    [
        ("for january 1 through january 31, 2024", ("2024-01-01", "2024-01-31")),
        ("january 1 to january 15, 2024", ("2024-01-01", "2024-01-15")),
        ("2023-11-01 through 2024-01-31", ("2023-11-01", "2024-01-31")),
        ("from november 1 to january 31, 2024", ("2023-11-01", "2024-01-31")),
        ("through january 31, 2024", (None, "2024-01-31")),
    ],
)
def test_closed_dates_do_not_become_open_ended(query, expected):
    assert extract_date_range(query, season="2023-24") == expected
