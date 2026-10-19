"""Conditional status owners cannot replace subjects or certify participation."""

import pytest

from nbatools.commands._compound_event_authorization import (
    availability_status_subject_view,
    unsupported_availability_status,
)
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query

pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


@pytest.fixture
def no_arithmetic(monkeypatch):
    from nbatools.commands import _natural_query_execution as execution

    def fail(**kwargs):
        pytest.fail("A status-qualified request executed a statistical builder")

    for route in ("team_record", "player_compare", "player_game_summary", "game_finder"):
        monkeypatch.setitem(execution._get_build_result_map(), route, fail)


def unavailable(result, route):
    assert result.route == route
    assert result.result_status == "no_result" and result.result_reason == "filter_not_supported"
    assert not result.result.to_dict()["sections"]
    assert not result.metadata.get("applied_filters")
    assert not result.metadata.get("answer_phrase")
    assert not result.metadata.get("with_player") and not result.metadata.get("without_player")
    assert "availability_status" in result.metadata["unsupported_filters"]
    assert result.metadata["unsupported_availability"]["condition"]


@pytest.mark.parametrize(
    "condition",
    [
        "when Derrick White is medically cleared",
        "while Derrick White is healthy",
        "when Derrick White was injured",
        "when Derrick White is questionable",
        "when Derrick White is available",
        "when Derrick White is active",
        "when Derrick White is not medically cleared",
        "if Derrick White has medical clearance",
        "with Derrick White medically cleared",
        "with medical clearance for Derrick White",
        "without Derrick White medical clearance",
        "when Blorg is medically cleared",
    ],
)
@pytest.mark.parametrize("prefix", [False, True])
def test_status_owner_is_not_the_primary_team_subject(no_arithmetic, condition, prefix):
    subject = "Boston record against Lakers in 2025-26"
    query = f"{condition}, {subject}?" if prefix else f"{subject} {condition}?"
    parsed = parse_query(query)
    assert parsed["player"] is None
    result = execute_natural_query(query)
    unavailable(result, "team_record")
    assert result.metadata["team"] == "BOS" and result.metadata["opponent"] == "LAL"
    assert result.metadata["season"] == "2025-26"
    assert result.metadata.get("player") is None and result.metadata.get("player_context") is None
    assert result.query == query and result.metadata["query_text"] == query
    assert any("requested_availability_condition:" in n for n in result.metadata["notes"])


@pytest.mark.parametrize("owner", ["Embiid", "Tyrese Maxey", "Blorg"])
@pytest.mark.parametrize("prefix", [False, True])
def test_status_owner_never_replaces_comparison_operands(no_arithmetic, owner, prefix):
    subject = "Show Luka Doncic and Anthony Davis side by side against Warriors in 2024-25"
    condition = f"when {owner} is medically cleared"
    query = f"{condition}, {subject}?" if prefix else f"{subject} {condition}?"
    parsed = parse_query(query)
    assert parsed["player"] is None
    assert [parsed["player_a"], parsed["player_b"]] == ["Luka Dončić", "Anthony Davis"]
    result = execute_natural_query(query)
    unavailable(result, "player_compare")
    assert result.metadata["player"] == "Luka Dončić, Anthony Davis"
    assert [p["player_name"] for p in result.metadata["players_context"]] == [
        "Luka Dončić",
        "Anthony Davis",
    ]
    assert result.metadata["opponent"] == "GSW" and result.metadata["season"] == "2024-25"


def test_status_mask_preserves_positions_main_scope_and_unread_tail():
    text = "when derrick white is not medically cleared, boston record against lakers in 2025-26 and do a backflip"
    masked, clauses = availability_status_subject_view(text)
    assert len(masked) == len(text)
    assert "boston record against lakers in 2025-26 and do a backflip" in masked
    assert text[clauses[0]["start"] : clauses[0]["end"]] == clauses[0]["text"]
    assert clauses[0]["owner_text"] == "derrick white"
    assert clauses[0]["condition"] == "medical clearance"
    assert "not medically cleared" in clauses[0]["text"]


def test_unread_tail_cannot_execute_a_reduced_status_question(no_arithmetic):
    result = execute_natural_query(
        "Boston record against Lakers in 2025-26 when White is medically cleared and do a backflip"
    )
    unavailable(result, "team_record")
    assert result.metadata["team"] == "BOS"


def test_shared_team_comparison_and_with_connector_keep_both_primary_players(no_arithmetic):
    result = execute_natural_query(
        "Compare Luka Doncic with Anthony Davis for Lakers against Warriors in 2024-25 when LeBron is healthy"
    )
    unavailable(result, "player_compare")
    assert result.metadata["team"] == "LAL" and result.metadata["opponent"] == "GSW"
    assert [p["player_name"] for p in result.metadata["players_context"]] == [
        "Luka Dončić",
        "Anthony Davis",
    ]


def test_direct_status_target_is_not_erased(no_arithmetic):
    parsed = parse_query("Is Derrick White healthy in 2025-26?")
    assert parsed["player"] == "Derrick White"
    result = execute_natural_query("Is Derrick White healthy in 2025-26?")
    assert result.result_status == "no_result" and not result.result.to_dict()["sections"]
    assert result.metadata["player"] == "Derrick White"


def test_active_population_is_not_a_conditional_game_day_status():
    text = "active players scoring leaderboard in 2025-26"
    assert unsupported_availability_status({"normalized_query": text}) is None
    assert availability_status_subject_view(text) == (text, [])
