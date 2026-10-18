"""The executable subject and union survive parsing and public metadata."""

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query, execute_structured_query

pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


@pytest.mark.parametrize(
    "query,team,opponents",
    [
        ("New York away record against Miami and Washington in 2023-24", "NYK", ["MIA", "WAS"]),
        (
            "What was New York’s away record against Miami and Washington in 2023-24?",
            "NYK",
            ["MIA", "WAS"],
        ),
        (
            "Against Miami and Washington, what was New York away record in 2023-24?",
            "NYK",
            ["MIA", "WAS"],
        ),
        (
            "Against Miami and Washington, what was New York away record in each of 2023-24 and 2025-26?",
            "NYK",
            ["MIA", "WAS"],
        ),
        ("Lakers opponent splits against Celtics and Wizards in 2023-24", "LAL", ["BOS", "WAS"]),
        ("WAS record against Miami and Boston in 2023-24", "WAS", ["MIA", "BOS"]),
        ("LeBron James games against Celtics and Knicks in 2025-26", None, ["BOS", "NYK"]),
    ],
)
def test_subject_and_complete_union(query, team, opponents):
    parsed = parse_query(query)
    assert not parsed["route_kwargs"].get("unsupported_filters"), parsed
    assert parsed["route_kwargs"].get("team") == team
    assert parsed["route_kwargs"]["opponent"] == opponents
    metadata = execute_natural_query(query).metadata
    assert metadata["team"] == team
    assert metadata["opponent"] == ", ".join(opponents)
    assert metadata["opponents"] == opponents
    assert not metadata.get("opponent_context")
    assert {"label": "Opponent", "value": ", ".join(opponents), "kind": "team"} in metadata[
        "applied_filters"
    ]
    if team:
        assert metadata["team_context"]["team_abbr"] == team
    else:
        assert not metadata.get("team_context")


def test_structured_union_uses_the_same_scalar_display_contract():
    result = execute_structured_query(
        "team_record", team="LAL", opponent=["BOS", "NYK"], season="2025-26"
    )
    assert result.result_status == "ok"
    assert result.metadata["opponents"] == ["BOS", "NYK"]
    assert result.metadata["opponent"] == "BOS, NYK"
    assert not result.metadata.get("opponent_context")
    assert all(isinstance(item["value"], str) for item in result.metadata["applied_filters"])
