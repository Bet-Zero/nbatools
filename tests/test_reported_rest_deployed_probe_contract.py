"""The deployed probe consumes actual API metadata, not engine-only coverage."""

import copy

import pandas as pd
import pytest

from nbatools.api_handlers import query_result_to_payload
from nbatools.commands import _reported_absence_reasons as reasons
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query
from tests import cloud_reported_rest_deployed_real_data as probe
from tests.test_qualified_participation_pair import qualified_pair as _qualified_pair

qualified_pair = _qualified_pair
pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def test_probe_checks_real_api_query_metadata_and_unpublished_reason(qualified_pair, monkeypatch):
    query = "Lakers record when Davis rests vs Celtics in 2023-24"
    monkeypatch.setattr(probe, "REST_QUERY", query)
    monkeypatch.setattr(
        reasons, "load_observations", lambda *args: pd.DataFrame(columns=reasons.COLUMNS)
    )
    expected = parse_query(query)["route_kwargs"]
    body = query_result_to_payload(execute_natural_query(query))
    assert body["result_status"] == "no_result" and body["result_reason"] == "no_data"
    # The real service qualifies two explicit DNPs; missing companion facts stay
    # unknown. QueryResult.to_dict replaces the engine's coverage metadata.
    assert body["result"]["metadata"]["without_player_reason"] == "reported_rest"
    assert "reported_reason_coverage" not in body["result"]["metadata"]
    probe._assert_unpublished_reason(body, expected)
    wrong_scope = copy.deepcopy(body)
    wrong_scope["result"]["metadata"]["season"] = "2025-26"
    with pytest.raises(AssertionError):
        probe._assert_unpublished_reason(wrong_scope, expected)
    engine_only = copy.deepcopy(body)
    engine_only["result"]["metadata"] = {
        "reported_reason_basis": "officially reported Rest",
        "reported_reason_coverage": {"unknown": 2},
    }
    with pytest.raises(KeyError):
        probe._assert_unpublished_reason(engine_only, expected)
