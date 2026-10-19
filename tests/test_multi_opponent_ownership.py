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


def test_third_team_condition_retains_the_subject_on_refusal():
    result = execute_natural_query(
        "Lakers record against Celtics and Wizards when Knicks score at least 110 in 2023-24"
    )
    assert result.result_status == "no_result"
    assert "other_team_stat" in result.metadata["unsupported_filters"]
    assert result.metadata["team"] == "LAL"


@pytest.mark.parametrize(
    "query,team,opponents",
    [
        (
            "Against Celtics and Wizards, what was Lakers record when NYK score at least 110 in 2023-24?",
            "LAL",
            ["BOS", "WAS"],
        ),
        (
            "Against Celtics and Wizards, what was Lakers record when Knicks score at least 110 in 2023-24?",
            "LAL",
            ["BOS", "WAS"],
        ),
        (
            "Against BOS and WAS, what was LAL record when NYK score at least 110 in 2023-24?",
            "LAL",
            ["BOS", "WAS"],
        ),
        (
            "Against Celtics and Wizards, what was Knicks record when LAL score at least 110 in 2023-24?",
            "NYK",
            ["BOS", "WAS"],
        ),
        (
            "Against Miami and Boston, what was WAS record when NYK score at least 110 in 2023-24?",
            "WAS",
            ["MIA", "BOS"],
        ),
    ],
)
def test_leading_list_third_team_condition_preserves_refused_request_identity(
    query, team, opponents
):
    kwargs = parse_query(query)["route_kwargs"]
    assert kwargs["team"] == team and kwargs["opponent"] == opponents
    result = execute_natural_query(query)
    assert result.result_status == "no_result" and result.result_reason == "filter_not_supported"
    assert "other_team_stat" in result.metadata["unsupported_filters"]
    assert result.metadata["team"] == team
    assert result.metadata["team_context"]["team_abbr"] == team
    assert result.metadata["opponent"] == ", ".join(opponents)
    assert result.metadata["opponents"] == opponents
    assert not result.metadata.get("opponent_context")
    assert result.metadata["season"] == "2023-24"
    assert result.metadata["season_type"] == "Regular Season"
    assert not result.result.to_dict()["sections"]


def test_comparison_keeps_both_subjects_and_the_opponent_union():
    query = "Lakers and Knicks record against Celtics and Wizards in 2023-24"
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "team_compare"
    assert (kwargs["team_a"], kwargs["team_b"]) == ("LAL", "NYK")
    assert not kwargs.get("team")
    assert kwargs["opponent"] == ["BOS", "WAS"]
    assert not kwargs.get("unsupported_filters")
    meta = execute_natural_query(query).metadata
    assert meta["opponents"] == ["BOS", "WAS"]
    assert meta["team"] == "LAL, NYK"
    assert not meta.get("opponent_context")


def test_player_comparison_keeps_both_players_and_no_invented_team_filter():
    parsed = parse_query(
        "Compare LeBron James and Stephen Curry against Boston and Washington in 2023-24"
    )
    kwargs = parsed["route_kwargs"]
    assert parsed["route"] == "player_compare"
    assert (kwargs["player_a"], kwargs["player_b"]) == ("LeBron James", "Stephen Curry")
    assert kwargs["team"] is None
    assert kwargs["opponent"] == ["BOS", "WAS"]
    assert not kwargs.get("unsupported_filters")


@pytest.mark.parametrize("opponent", ["BOS", ["BOS", "WAS"], ["NYK", "WAS"]])
def test_head_to_head_intersects_explicit_opponents_before_pairing(opponent):
    result = execute_structured_query(
        "team_compare",
        team_a="LAL",
        team_b="NYK",
        head_to_head=True,
        opponent=opponent,
        season="2025-26",
    )
    assert result.result_status == "no_result"
    assert result.result_reason == "no_match"


def test_redundant_union_keeps_a_coherent_head_to_head_sample():
    kwargs = dict(team_a="LAL", team_b="NYK", head_to_head=True, season="2025-26")
    plain = execute_structured_query("team_compare", **kwargs)
    scoped = execute_structured_query("team_compare", opponent=["LAL", "NYK"], **kwargs)
    assert plain.result_status == scoped.result_status == "ok"
    assert plain.result.to_dict()["sections"] == scoped.result.to_dict()["sections"]


def test_contradictory_natural_head_to_head_scope_never_claims_success():
    result = execute_natural_query(
        "Compare Lakers and Knicks head-to-head against Celtics and Wizards in 2023-24"
    )
    assert result.result_status == "no_result"
    assert result.result_reason == "no_match"
