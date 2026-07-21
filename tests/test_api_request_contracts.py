"""Cross-transport request validation contract tests."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from nbatools import vercel_functions
from nbatools.api import app
from nbatools.api_contracts import (
    NATURAL_QUERY_MAX_LENGTH,
    STRUCTURED_ROUTE_MAX_LENGTH,
    NaturalQueryRequest,
    StructuredQueryRequest,
)
from nbatools.query_service import VALID_ROUTES

pytestmark = pytest.mark.api

client = TestClient(app, raise_server_exceptions=False)

MINIMUM_ROUTE_KWARGS: dict[str, dict[str, Any]] = {
    "top_player_games": {"season": "2024-25", "stat": "pts"},
    "top_team_games": {"season": "2024-25", "stat": "pts"},
    "player_compare": {"player_a": "Jokic", "player_b": "Embiid"},
    "team_compare": {"team_a": "DEN", "team_b": "PHI"},
    "player_split_summary": {"split": "home_away"},
    "team_split_summary": {"split": "home_away"},
    "team_record": {"team": "LAL"},
    "team_matchup_record": {"team_a": "LAL", "team_b": "BOS"},
    "playoff_history": {"team": "LAL"},
    "playoff_matchup_history": {"team_a": "LAL", "team_b": "BOS"},
    "record_by_decade": {"team": "LAL"},
    "matchup_by_decade": {"team_a": "LAL", "team_b": "BOS"},
}


INVALID_REQUESTS = [
    pytest.param("/query", {}, id="natural-missing-query"),
    pytest.param("/query", {"query": "   "}, id="natural-whitespace-query"),
    pytest.param("/query", {"query": 123}, id="natural-query-wrong-type"),
    pytest.param(
        "/query",
        {"query": "Jokic", "unexpected": True},
        id="natural-unknown-top-level-field",
    ),
    pytest.param(
        "/query",
        {"query": "x" * (NATURAL_QUERY_MAX_LENGTH + 1)},
        id="natural-query-max-plus-one",
    ),
    pytest.param("/query", ["Jokic"], id="natural-non-object-body"),
    pytest.param("/structured-query", {}, id="structured-missing-route"),
    pytest.param(
        "/structured-query",
        {"route": "   ", "kwargs": {}},
        id="structured-whitespace-route",
    ),
    pytest.param(
        "/structured-query",
        {"route": 123, "kwargs": {}},
        id="structured-route-wrong-type",
    ),
    pytest.param(
        "/structured-query",
        {"route": "x" * (STRUCTURED_ROUTE_MAX_LENGTH + 1), "kwargs": {}},
        id="structured-route-max-plus-one",
    ),
    pytest.param(
        "/structured-query",
        {"route": "season_leaders", "kwargs": None},
        id="structured-null-kwargs",
    ),
    pytest.param(
        "/structured-query",
        {"route": "season_leaders", "kwargs": "bad"},
        id="structured-kwargs-wrong-container-type",
    ),
    pytest.param(
        "/structured-query",
        {"route": "season_leaders", "kwargs": {}, "unexpected": True},
        id="structured-unknown-top-level-field",
    ),
    pytest.param(
        "/structured-query",
        {"route": "season_leaders", "kwargs": {"unknown_key": 1}},
        id="structured-unknown-route-kwarg",
    ),
    pytest.param(
        "/structured-query",
        {"route": "season_leaders", "kwargs": {"limit": "10"}},
        id="structured-known-kwarg-wrong-type",
    ),
    pytest.param(
        "/structured-query",
        {"route": "game_summary", "kwargs": {"quarter": 1}},
        id="structured-orchestration-kwarg-wrong-type",
    ),
    pytest.param(
        "/structured-query",
        {"route": "top_player_games", "kwargs": {}},
        id="structured-missing-required-route-kwargs",
    ),
    pytest.param(
        "/structured-query",
        {"route": "player_game_summary", "kwargs": {"df": []}},
        id="structured-internal-only-kwarg",
    ),
    pytest.param("/structured-query", ["season_leaders"], id="structured-non-object-body"),
]


def _vercel_response(endpoint: str, body: Any) -> tuple[int, dict[str, Any]]:
    if endpoint == "/query":
        return vercel_functions.query_response(body)
    return vercel_functions.structured_query_response(body)


@pytest.mark.parametrize(("endpoint", "body"), INVALID_REQUESTS)
def test_fastapi_and_vercel_share_validation_contract(endpoint: str, body: Any) -> None:
    fastapi_response = client.post(endpoint, json=body)
    vercel_status, vercel_payload = _vercel_response(endpoint, body)
    fastapi_payload = fastapi_response.json()
    request_id = fastapi_payload.pop("request_id")

    assert fastapi_response.status_code == vercel_status == 422
    assert fastapi_payload == vercel_payload
    assert fastapi_response.headers["X-Request-ID"] == request_id
    assert vercel_payload["ok"] is False
    assert vercel_payload["error"] == "validation_error"
    assert vercel_payload["detail"]


def test_request_size_boundaries_are_inclusive() -> None:
    natural = NaturalQueryRequest.model_validate({"query": "x" * NATURAL_QUERY_MAX_LENGTH})
    structured = StructuredQueryRequest.model_validate(
        {"route": "x" * STRUCTURED_ROUTE_MAX_LENGTH, "kwargs": {}}
    )

    assert len(natural.query) == NATURAL_QUERY_MAX_LENGTH
    assert len(structured.route) == STRUCTURED_ROUTE_MAX_LENGTH


def test_unknown_route_remains_an_execution_boundary() -> None:
    request = StructuredQueryRequest.model_validate(
        {"route": "future_route", "kwargs": {"future_field": True}}
    )

    assert request.route == "future_route"
    assert request.kwargs == {"future_field": True}


def test_known_orchestration_kwargs_remain_validated_request_fields() -> None:
    request = StructuredQueryRequest.model_validate(
        {
            "route": "game_summary",
            "kwargs": {
                "opponent_quality": {
                    "type": "opponent_quality",
                    "surface_term": "contenders",
                },
                "opponent_conference": "East",
                "opponent_division": "Atlantic",
                "quarter": "Q1",
                "role": "starter",
                "back_to_back": True,
                "rest_days": 1,
            },
        }
    )

    assert request.kwargs["quarter"] == "Q1"


@pytest.mark.parametrize("route", sorted(VALID_ROUTES))
def test_every_shipped_route_accepts_its_minimum_request_contract(route: str) -> None:
    kwargs = MINIMUM_ROUTE_KWARGS.get(route, {})
    request = StructuredQueryRequest.model_validate({"route": route, "kwargs": kwargs})

    assert request.route == route
    assert request.kwargs == kwargs
