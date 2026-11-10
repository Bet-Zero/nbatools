"""Required original nine-ID K08 integration against the published generation."""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.api_handlers import query_result_to_payload
from nbatools.commands._seasons import default_end_season, previous_season
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.core1_k08_served_default_cases import (
    SEASON,
    assert_answer,
    assert_ownership_answer,
    source_oracle,
)

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_original_nine_on_published_generation():
    oracle = source_oracle()
    assert default_end_season("Regular Season") == SEASON
    assert previous_season("Regular Season") == "2024-25"
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "core1-k08-served-default"
    output.mkdir(parents=True, exist_ok=False)
    (output / "independent-raw-oracle.json").write_text(json.dumps(oracle, indent=2) + "\n")
    client = TestClient(app)
    receipt = dict(
        candidate_sha=os.environ["VALIDATION_SHA"],
        classification="original_nine_K08_inputs_at_published_served_default_not_literal_current",
        generation=oracle["generation"],
        manifest_sha256=oracle["manifest_sha256"],
        original46_ids_sha256=oracle["original46_ids_sha256"],
        answers=[],
        accepted_original_ids=[],
        consumer_acceptance="pending",
        source_requests=0,
        production_writes=0,
        literal_current_accepted=False,
        all46_accepted=False,
        full_core1_accepted=False,
        fresh_deployment_accepted=False,
    )
    try:
        for case in oracle["cases"]:
            natural = query_result_to_payload(execute_natural_query(case["query"]))
            assert_answer(natural, case)
            structured = query_result_to_payload(
                execute_structured_query(case["route"], **case["kwargs"])
            )
            assert_answer(structured, case, natural=False)
            http_natural = client.post("/query", json={"query": case["query"]})
            assert http_natural.status_code == 200
            assert_answer(http_natural.json(), case)
            http_structured = client.post(
                "/structured-query", json={"route": case["route"], "kwargs": case["kwargs"]}
            )
            assert http_structured.status_code == 200
            assert_answer(http_structured.json(), case, natural=False)
            receipt["answers"].append(
                dict(
                    original_id=case["ordinal"],
                    query=case["query"],
                    natural=natural,
                    structured=structured,
                    http_natural=http_natural.json(),
                    http_structured=http_structured.json(),
                )
            )
            receipt["accepted_original_ids"].append(case["ordinal"])
        assert receipt["accepted_original_ids"] == [7, 8, 23, 24, 25, 30, 31, 32, 41]
        control = oracle["supplemental_ownership"]
        natural = query_result_to_payload(execute_natural_query(control["query"]))
        structured = query_result_to_payload(
            execute_structured_query(control["route"], **control["kwargs"])
        )
        assert_ownership_answer(natural, control)
        assert_ownership_answer(structured, control, natural=False)
        http = client.post("/query", json={"query": control["query"]})
        http_structured = client.post(
            "/structured-query", json={"route": control["route"], "kwargs": control["kwargs"]}
        )
        assert http.status_code == http_structured.status_code == 200
        assert_ownership_answer(http.json(), control)
        assert_ownership_answer(http_structured.json(), control, natural=False)
        receipt["supplemental_ownership"] = dict(
            original46_case=False,
            natural=natural,
            structured=structured,
            http_natural=http.json(),
            http_structured=http_structured.json(),
            checked_consumer_answers=4,
        )
        receipt["consumer_acceptance"] = "passed"
        receipt["required_original_cases"] = 9
        receipt["checked_consumer_answers"] = 36
        receipt["qualified_empty_original_ids"] = [30, 31]
    except Exception as exc:
        receipt.update(consumer_acceptance="failed", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        (output / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
