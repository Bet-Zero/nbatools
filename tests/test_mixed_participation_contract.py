"""Clause ownership is separate from whether real-season absence is available."""

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


@pytest.mark.parametrize(
    "query,team,absent,played",
    [
        (
            "Lakers record without LeBron James and with Luka Doncic in 2025-26",
            "LAL",
            "LeBron James",
            "Luka Dončić",
        ),
        (
            "Lakers record with Luka Doncic and without LeBron James in 2025-26",
            "LAL",
            "LeBron James",
            "Luka Dončić",
        ),
        (
            "Lakers record with LeBron James OUT and Luka Doncic playing in 2025-26",
            "LAL",
            "LeBron James",
            "Luka Dončić",
        ),
        (
            "Lakers record with Anthony Davis out and with Austin Reaves in 2024-25",
            "LAL",
            "Anthony Davis",
            "Austin Reaves",
        ),
        (
            "Celtics record with Jayson Tatum and without Jaylen Brown in 2024-25",
            "BOS",
            "Jaylen Brown",
            "Jayson Tatum",
        ),
        (
            "Celtics record when Jaylen Brown is out and Jayson Tatum plays in 2024-25",
            "BOS",
            "Jaylen Brown",
            "Jayson Tatum",
        ),
    ],
)
def test_scalar_conjunction_syntax_does_not_claim_real_absence(query, team, absent, played):
    parsed = parse_query(query)
    assert parsed["route"] == "team_record"
    assert parsed["player"] is None
    kwargs = parsed["route_kwargs"]
    assert (
        kwargs["team"] == team
        and kwargs["without_player"] == absent
        and kwargs["with_player"] == played
    )
    assert not kwargs.get("unsupported_filters")


@pytest.mark.parametrize(
    "tail",
    [
        "without LeBron James and with Anthony Davis and Austin Reaves",
        "with LeBron James out and with Anthony Davis and Blorg",
        "with LeBron James out and with Anthony Davis; and Blorg",
        "without LeBron James and with Anthony Davis, and Blorg",
        "with LeBron James out and Anthony Davis playing and Austin Reaves playing",
        "without LeBron James or with Anthony Davis",
        "without LeBron James and with Anthony Davis healthy",
        "without LeBron James and with Anthony Davis active",
        "without LeBron James and with Anthony Davis on the court",
        "without LeBron James and with LeBron James",
    ],
)
def test_unimplemented_or_different_facts_are_not_mixed_whole_game_answers(tail):
    result = execute_natural_query(f"Lakers record {tail} vs Celtics in 2023-24")
    assert result.result_status != "ok", result.metadata
    assert not result.to_dict()["sections"]


def test_player_subject_is_not_consumed_by_mixed_team_predicates():
    parsed = parse_query(
        "Austin Reaves stats without LeBron James and with Anthony Davis in 2023-24"
    )
    assert parsed["player"] == "Austin Reaves"
    assert parsed["route"] != "team_record"
    result = execute_natural_query(
        "Austin Reaves stats without LeBron James and with Anthony Davis in 2023-24"
    )
    assert result.result_status != "ok"
