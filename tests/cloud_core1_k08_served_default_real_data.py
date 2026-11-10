"""Required original nine-ID K08 integration against the published generation."""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nbatools.api import app
from nbatools.api_handlers import query_result_to_payload
from nbatools.commands._seasons import default_end_season, previous_season
from nbatools.commands.natural_query import parse_query
from nbatools.query_service import execute_natural_query, execute_structured_query
from tests.cloud_composed_participation_stage_real_data import _receipt_json_default
from tests.core1_k08_served_default_cases import (
    SEASON,
    assert_answer,
    assert_ownership_answer,
    compact_actual,
    source_oracle,
)

pytestmark = [pytest.mark.needs_data, pytest.mark.query]


def test_original_nine_on_published_generation():
    output = Path(os.environ["NBATOOLS_ACQUISITION_OUTPUT"]) / "core1-k08-served-default"
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(
        candidate_sha=os.environ["VALIDATION_SHA"],
        classification="original_nine_K08_inputs_at_published_served_default_not_literal_current",
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

    def persist():
        (output / "acceptance.json").write_text(
            json.dumps(receipt, indent=2, default=_receipt_json_default) + "\n"
        )

    def http_body(response):
        try:
            return response.json()
        except ValueError:
            return dict(non_json_body=response.text)

    try:
        oracle = source_oracle()
        receipt.update(
            generation=oracle["generation"],
            manifest_sha256=oracle["manifest_sha256"],
            original46_ids_sha256=oracle["original46_ids_sha256"],
        )
        (output / "independent-raw-oracle.json").write_text(json.dumps(oracle, indent=2) + "\n")
        assert default_end_season("Regular Season") == SEASON
        assert previous_season("Regular Season") == "2024-25"
        client = TestClient(app)
        for case in oracle["cases"]:
            actual = dict(
                original_id=case["ordinal"],
                query=case["query"],
                structured_kwargs=case["kwargs"],
                accepted=False,
            )
            receipt["answers"].append(actual)
            if case["ordinal"] in {7, 8}:
                compiled = parse_query(case["query"])
                scope = compiled["route_kwargs"]
                actual["authenticated_natural_compiled_scope"] = dict(
                    route=compiled["route"],
                    season=scope.get("season"),
                    team=scope.get("team"),
                    without_player=scope.get("without_player"),
                    membership_player=scope.get("membership_player"),
                    home_only=scope.get("home_only"),
                )
                persist()
                assert compiled["route"] == "game_finder" and scope["season"] == SEASON, actual[
                    "authenticated_natural_compiled_scope"
                ]
                assert scope.get("team") == "LAL" and not scope.get("membership_player"), actual[
                    "authenticated_natural_compiled_scope"
                ]
                assert scope.get("without_player") == "LeBron James" and bool(
                    scope.get("home_only")
                ) is (case["ordinal"] == 8), actual["authenticated_natural_compiled_scope"]
            natural = query_result_to_payload(execute_natural_query(case["query"]))
            actual["natural"] = natural
            persist()
            assert_answer(natural, case)
            structured = query_result_to_payload(
                execute_structured_query(case["route"], **case["kwargs"])
            )
            actual["structured"] = structured
            persist()
            assert_answer(structured, case, natural=False)
            http_natural = client.post("/query", json={"query": case["query"]})
            actual.update(
                http_natural_status=http_natural.status_code, http_natural=http_body(http_natural)
            )
            persist()
            assert http_natural.status_code == 200
            assert_answer(actual["http_natural"], case)
            http_structured = client.post(
                "/structured-query", json={"route": case["route"], "kwargs": case["kwargs"]}
            )
            actual.update(
                http_structured_status=http_structured.status_code,
                http_structured=http_body(http_structured),
            )
            persist()
            assert http_structured.status_code == 200
            assert_answer(actual["http_structured"], case, natural=False)
            actual["accepted"] = True
            receipt["accepted_original_ids"].append(case["ordinal"])
        assert receipt["accepted_original_ids"] == [7, 8, 23, 24, 25, 30, 31, 32, 41]
        control = oracle["supplemental_ownership"]
        actual = dict(original46_case=False, checked_consumer_answers=0)
        receipt["supplemental_ownership"] = actual
        compiled = parse_query(control["query"])
        actual["authenticated_natural_compiled_route"] = compiled["route"]
        persist()
        assert compiled["route"] == control["route"] == "player_game_finder", dict(
            query=control["query"],
            route=compiled["route"],
            route_kwargs=compiled.get("route_kwargs"),
        )
        natural = query_result_to_payload(execute_natural_query(control["query"]))
        actual["natural"] = natural
        persist()
        assert_ownership_answer(natural, control)
        structured = query_result_to_payload(
            execute_structured_query(control["route"], **control["kwargs"])
        )
        actual["structured"] = structured
        persist()
        assert_ownership_answer(structured, control, natural=False)
        http = client.post("/query", json={"query": control["query"]})
        actual.update(http_natural_status=http.status_code, http_natural=http_body(http))
        persist()
        assert http.status_code == 200
        assert_ownership_answer(actual["http_natural"], control)
        http_structured = client.post(
            "/structured-query", json={"route": control["route"], "kwargs": control["kwargs"]}
        )
        actual.update(
            http_structured_status=http_structured.status_code,
            http_structured=http_body(http_structured),
        )
        persist()
        assert http_structured.status_code == 200
        assert_ownership_answer(actual["http_structured"], control, natural=False)
        actual["checked_consumer_answers"] = 4
        # This intentionally broader chronology contract remains a separate
        # no-data control, never a substitute for either original positive.
        unscoped = query_result_to_payload(
            execute_structured_query(
                "game_finder",
                season=SEASON,
                membership_player="LeBron James",
                without_player="LeBron James",
                limit=100000,
            )
        )
        receipt["unscoped_membership_control"] = dict(original46_case=False, actual=unscoped)
        persist()
        assert (
            unscoped["result_status"] == "no_result" and unscoped["result_reason"] == "no_data"
        ), compact_actual(unscoped)
        receipt["consumer_acceptance"] = "passed"
        receipt["required_original_cases"] = 9
        receipt["checked_consumer_answers"] = 36
        receipt["qualified_empty_original_ids"] = [30, 31]
    except Exception as exc:
        receipt.update(consumer_acceptance="failed", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        persist()
