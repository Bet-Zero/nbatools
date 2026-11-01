"""Real consumer receipt serialization retains typed counts and sample dates."""

import json

import pytest

from nbatools.query_service import execute_natural_query
from tests.cloud_composed_participation_stage_real_data import _receipt_json_default
from tests.cloud_reported_rest_stage_real_data import _capture
from tests.test_qualified_participation_pair import qualified_pair as _qualified_pair

qualified_pair = _qualified_pair
pytestmark = [pytest.mark.fixture_data, pytest.mark.query]


def test_finder_receipt_dates_and_numeric_fields_survive_json(qualified_pair):
    result = execute_natural_query("How many games did Anthony Davis miss in 2023-24?")
    assert result.result_status == "ok"
    actual = _capture(result)
    raw = json.dumps(actual, default=_receipt_json_default)
    saved = json.loads(raw)
    assert saved["result"]["sections"]["count"] == [{"count": 2}]
    rows = saved["result"]["sections"]["finder"]
    assert {row["game_id"] for row in rows} == {
        int(qualified_pair["ids"][0]),
        int(qualified_pair["ids"][2]),
    }
    assert all(type(row["game_id"]) is int and isinstance(row["game_date"], str) for row in rows)
    assert all(row["game_date"].startswith("2023-") for row in rows)
    with pytest.raises(TypeError, match="Unsupported receipt value"):
        json.dumps({"unexpected": object()}, default=_receipt_json_default)
