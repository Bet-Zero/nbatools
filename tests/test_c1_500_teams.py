"""C1: ".500 teams" opponents ("Lakers losses vs .500 teams").

"vs .500 teams", "wins over .500 teams", "teams .500 or better" and ".500 or
better teams" dropped the opponent filter (the last two refused as a
top-level OR). They read the "winning teams" bar (.500 or better), so each
answers exactly as the "winning teams" wording does.
"""

from __future__ import annotations

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


def _rows(query: str) -> list:
    sections = execute_natural_query(query).result.to_dict()["sections"]
    return sections.get("finder") or sections.get("summary") or []


@pytest.mark.parametrize(
    ("query", "same_as"),
    [
        ("Lakers losses vs .500 teams", "Lakers losses vs winning teams"),
        ("Lakers wins over .500 teams", "Lakers wins over winning teams"),
        ("Lakers record vs .500 teams", "Lakers record vs winning teams"),
        ("Lakers record against teams .500 or better", "Lakers record vs winning teams"),
        ("LeBron stats vs .500 or better teams", "LeBron stats vs winning teams"),
    ],
)
def test_500_teams_is_the_winning_teams_bar(query, same_as):
    quality = parse_query(query)["route_kwargs"]["opponent_quality"]
    assert quality["surface_term"] == "winning teams"
    assert _rows(query) == _rows(same_as)


def test_over_and_under_500_keep_their_strict_bars():
    for query, term in (
        ("Lakers record vs teams over .500", "teams over .500"),
        ("Lakers record vs over .500 teams", "teams over .500"),
        ("Lakers record vs under .500 teams", "teams under .500"),
    ):
        assert parse_query(query)["route_kwargs"]["opponent_quality"]["surface_term"] == term


def test_or_better_is_a_bound_not_an_alternative():
    parsed = parse_query("LeBron games with 30 points or better")
    assert parsed["route_kwargs"]["min_value"] == 30.0
