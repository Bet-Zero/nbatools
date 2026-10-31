"""Exact registered operation/population checks; synthetic, never NBA evidence."""

import copy

import pytest

from tools.r2_publication import verify_answer


def test_existing_summary_protocol_and_receipt_are_unchanged():
    case = {"query": "record", "summary": {"games": 1, "wins": 1}}
    row = {"games": 1, "wins": 1, "pts_avg": 101}
    answer = {"result_status": "ok", "result": {"sections": {"summary": [row]}}}
    assert verify_answer(case, answer) == {"query": "record", "summary": row}
    answer["result"]["sections"]["summary"].append(row)
    with pytest.raises(ValueError):
        verify_answer(case, answer)


@pytest.mark.parametrize(
    "defect",
    [
        None,
        "status",
        "route",
        "count",
        "missing",
        "extra",
        "id",
        "value",
        "reorder",
        "empty",
        "conflicting",
        "no_expectations",
    ],
)
def test_count_and_finder_checks_fail_closed(defect):
    case = {
        "query": "count bounded games",
        "expected_route": "game_finder",
        "sections": {
            "count": [{"count": 2}],
            "finder": [{"game_id": 11, "pts": 51}, {"game_id": 13, "pts": 41}],
        },
    }
    answer = {
        "result_status": "ok",
        "route": "game_finder",
        "result": {"sections": copy.deepcopy(case["sections"])},
    }
    sections = answer["result"]["sections"]
    if defect == "status":
        answer["result_status"] = "no_result"
    elif defect == "route":
        answer["route"] = "player_summary"
    elif defect == "count":
        sections["count"][0]["count"] = 3
    elif defect == "missing":
        sections.pop("finder")
    elif defect == "extra":
        sections["finder"].append({"game_id": 12, "pts": 45})
    elif defect in {"id", "value"}:
        sections["finder"][0]["game_id" if defect == "id" else "pts"] = 999
    elif defect == "reorder":
        sections["finder"].reverse()
    elif defect == "empty":
        case["sections"]["finder"] = []
    elif defect == "conflicting":
        case["summary"] = {"games": 1}
    elif defect == "no_expectations":
        case.pop("sections")
    if defect:
        with pytest.raises(ValueError):
            verify_answer(case, answer)
    else:
        assert verify_answer(case, answer) == {"query": case["query"], "sections": sections}
