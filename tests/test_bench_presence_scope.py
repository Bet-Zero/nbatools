"""Bench location cannot be answered from whole-game reported reasons."""

import pytest

from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query
from tests.test_reported_rest_consumers import qualified_pair as _qualified_pair
from tests.test_reported_rest_consumers import reported as _reported

qualified_pair = _qualified_pair
reported = _reported
pytestmark = [pytest.mark.query, pytest.mark.fixture_data]


@pytest.mark.parametrize(
    "condition",
    [
        "Davis rests on the bench",
        "Davis rests while sitting on the bench",
        "Davis rests while he is on the bench",
        "Davis rests during his bench minutes",
        "Davis rests during bench stints",
        "Davis plays while he is on the bench",
        "LeBron James sits on the bench",
        "Davis rests off the court",
        "Davis rests on the floor",
    ],
)
def test_explicit_bench_or_court_presence_cannot_use_whole_game_reason(reported, condition):
    query = f"Lakers record when {condition} vs Celtics in 2023-24"
    result = execute_natural_query(query)
    assert result.result_status == "no_result" and result.result_reason == "filter_not_supported", (
        result.metadata
    )
    assert "on_court_presence" in result.metadata["unsupported_filters"], result.metadata


def test_unqualified_whole_game_rest_still_selects_known_rest_game(reported):
    result = execute_natural_query("Lakers record when Davis rests vs Celtics in 2023-24")
    assert result.result_status == "ok", result.metadata
    assert {int(r["game_id"]) for r in result.result.to_dict()["sections"]["game_log"]} == {
        reported["ids"][0]
    }
    assert result.result.metadata["reported_reason_coverage"]["reported_rest"] == 1


@pytest.mark.parametrize(
    "query",
    [
        "Brunson off the bench",
        "Celtics bench scoring in 2023-24",
        "Lakers record on 2 days rest in 2023-24",
        "Austin Reaves off the bench when Davis rests in 2023-24",
    ],
)
def test_bench_role_scoring_and_schedule_rest_keep_existing_grain(reported, query):
    parsed = parse_query(query)
    kwargs = parsed["route_kwargs"]
    assert "on_court_presence" not in kwargs.get("unsupported_filters", []), parsed
    if "off the bench" in query:
        assert kwargs["role"] == "bench", parsed
    if "days rest" in query:
        assert parsed["rest_days"] == 2, parsed
        assert kwargs.get("without_player_reason") is None
