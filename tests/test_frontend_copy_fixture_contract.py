from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _yaml_cases(path: str) -> list[dict[str, Any]]:
    payload = yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    cases = payload.get("cases")
    assert isinstance(cases, list)
    assert all(isinstance(case, dict) for case in cases)
    return cases


def _jsonl_rows(path: str) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in (ROOT / path).read_text(encoding="utf-8").splitlines() if line
    ]


def _unique_by_id(rows: list[dict[str, Any]], *, source: str) -> dict[str, dict[str, Any]]:
    ids = [row.get("id") for row in rows]
    assert all(isinstance(case_id, str) and case_id for case_id in ids), source
    assert len(ids) == len(set(ids)), f"{source} contains duplicate case IDs"
    return {row["id"]: row for row in rows}


def test_frontend_copy_fixture_matches_current_raw_qa_contracts() -> None:
    frontend_cases = _yaml_cases("qa/frontend_copy_corpus.yaml")
    raw_cases = _unique_by_id(
        _yaml_cases("qa/raw_query_answer_corpus.yaml"),
        source="Raw QA corpus",
    )
    fixture_rows = _jsonl_rows("qa/fixtures/frontend_copy_backend_report.jsonl")
    fixture_by_id = _unique_by_id(fixture_rows, source="frontend-copy backend fixture")

    frontend_ids = [case["id"] for case in frontend_cases]
    assert [row["id"] for row in fixture_rows] == frontend_ids
    assert not (set(frontend_ids) - set(raw_cases))

    mismatches: list[str] = []
    for frontend_case in frontend_cases:
        case_id = frontend_case["id"]
        expected = raw_cases[case_id]
        actual = fixture_by_id[case_id]

        comparisons = {
            "query": expected["query"],
            "result_status": expected["expected_status"],
            "route": expected.get("expected_route"),
        }
        if "expected_reason" in expected:
            comparisons["result_reason"] = expected["expected_reason"]
        elif expected["expected_status"] == "ok":
            comparisons["result_reason"] = None
        if "expected_shape" in expected:
            comparisons["shape_hint"] = expected["expected_shape"]

        for field, expected_value in comparisons.items():
            actual_value = actual.get(field)
            if actual_value != expected_value:
                mismatches.append(
                    f"{case_id}.{field}: fixture={actual_value!r}, Raw QA={expected_value!r}"
                )

        expected_sections = expected.get("expected_sections")
        if isinstance(expected_sections, list):
            actual_sections = set((actual.get("sections") or {}).keys())
            missing_sections = [
                section for section in expected_sections if section not in actual_sections
            ]
            if missing_sections:
                mismatches.append(
                    f"{case_id}.sections: fixture is missing Raw QA sections {missing_sections!r}"
                )

        expectation_status = (actual.get("expectation_results") or {}).get("status")
        if expectation_status != "pass":
            mismatches.append(f"{case_id}.expectation_results.status: {expectation_status!r}")
        if expected["expected_status"] == "ok" and str(
            frontend_case.get("category", "")
        ).startswith("no_result"):
            mismatches.append(
                f"{case_id}.category: successful Raw QA case is still categorized as no_result"
            )

    assert not mismatches, "\n".join(mismatches)
