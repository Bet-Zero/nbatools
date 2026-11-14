"""The Core-1 acceptance view scores against fixed expectations, never the run itself."""

import copy
import json

import pytest

from tools import core1_acceptance_view as view

SPEC = json.loads(view.MAP.read_bytes())
REGISTRY = json.loads((view.ROOT / ".github/data-publication-packages.json").read_bytes())


def test_map_covers_all_46_original_questions_once():
    original = json.loads((view.ROOT / SPEC["original46_source"]).read_bytes())["node_ids"]
    assert [e["id"] for e in SPEC["k08"]] == list(range(1, 47))
    assert [e["original_node_id"] for e in SPEC["k08"]] == original
    assert {e["expect"] for e in SPEC["k08"]} == {"pass", "missing_data", "live"}
    assert sorted(SPEC["groups"]) == [f"K{n:02d}" for n in range(1, 13)]
    for key, group in SPEC["groups"].items():
        assert bool(group["tests"]) is (key != "K08")
        for path in group["tests"]:
            assert (view.ROOT / path).is_file()


def test_answer_expectations_are_the_audited_live_checks():
    live = {
        c["query"]: c
        for c in REGISTRY["packages"]["participation-2025-durant-v1"]["deployed_checks"]
    }
    # Original wordings that reuse one specific audited live check.
    aliases = {
        "how many games did Tatum miss in 2024-25": (
            "how many games did Jayson Tatum miss in 2024-25"
        ),
        "Thunder record without Durant in 2007-08": (
            "Seattle SuperSonics record without Kevin Durant in 2007-08"
        ),
    }
    used = 0
    for entry in SPEC["k08"]:
        check = entry.get("check", {})
        for case in check.get("cases", []):
            assert case["query"] in entry["queries"]
            source = live[aliases.get(case["query"], case["query"])]
            assert dict(case, query=source["query"]) == source
            used += 1
        if "rest_count_case" in check:
            assert live[check["rest_count_case"]["query"]] == check["rest_count_case"]
    assert used == 6


def test_independent_oracle_is_pinned():
    cases = view._oracle_cases(SPEC["independent_oracle"])
    oracle_ids = [
        e["id"] for e in SPEC["k08"] if e.get("check", {}).get("kind") == "independent_oracle"
    ]
    assert sorted(cases) == oracle_ids == [7, 8, 23, 24, 25, 30, 31, 32, 41]
    damaged = dict(SPEC["independent_oracle"], sha256="0" * 64)
    with pytest.raises(ValueError):
        view._oracle_cases(damaged)


class _Client:
    def __init__(self, bodies):
        self.bodies = bodies

    def post(self, path, json):
        body = self.bodies[json["query"]]
        return type("R", (), {"json": lambda self: body})()


def _record(games, wins, losses, pts):
    return dict(
        result_status="ok",
        result_reason=None,
        route="team_record",
        result=dict(
            sections=dict(
                summary=[
                    dict(
                        team_name="Los Angeles Lakers",
                        season_start="2025-26",
                        season_end="2025-26",
                        season_type="Regular Season",
                        games=games,
                        wins=wins,
                        losses=losses,
                        pts_avg=pts,
                    )
                ]
            )
        ),
    )


def _entry(ordinal):
    return copy.deepcopy(next(e for e in SPEC["k08"] if e["id"] == ordinal))


def test_matching_answer_passes_and_changed_answer_is_a_software_failure():
    entry = _entry(35)
    good = _Client({"Lakers record without Reaves": _record(31, 17, 14, 114.419)})
    assert view._k08(entry, good, {}, [])["verdict"] == view.PASS
    bad = _Client({"Lakers record without Reaves": _record(31, 18, 13, 114.419)})
    row = view._k08(entry, bad, {}, [])
    assert row["verdict"] == view.FAIL and row["problems"]


def test_refusal_is_missing_data_but_a_numeric_answer_is_a_failure():
    entry = _entry(33)
    refused = dict(result_status="no_result", result_reason="filter_not_supported", result={})
    assert (
        view._k08(entry, _Client({"Lakers record without Davis": refused}), {}, [])["verdict"]
        == view.MISSING
    )
    invented = _Client({"Lakers record without Davis": _record(5, 3, 2, 110.0)})
    assert view._k08(entry, invented, {}, [])["verdict"] == view.FAIL
    # "No games" is also a claim about absence, so it is not an honest refusal.
    empty = dict(result_status="no_result", result_reason="no_match", result={})
    assert (
        view._k08(entry, _Client({"Lakers record without Davis": empty}), {}, [])["verdict"]
        == view.FAIL
    )


def test_a_skipped_or_absent_verifier_never_counts_as_passing():
    assert view._verdict_from_counts(dict(passed=3, failed=0, skipped=0)) == view.PASS
    assert view._verdict_from_counts(dict(passed=3, failed=0, skipped=1)) == view.FAIL
    assert view._verdict_from_counts(dict(passed=0, failed=0, skipped=0)) == view.FAIL
    entry = _entry(45)
    assert view._k08(entry, _Client({}), {}, [])["verdict"] == view.FAIL


def test_junit_matching_is_exact_per_module_and_node():
    results = [
        ("", "tests.test_c2_franchise_identity_real_data", "test_x", "failed"),
        ("", "tests.test_c2_franchise_identity", "test_x", "passed"),
        ("", "tests.test_record_queries.TestBuildTeamRecordResult", "test_y", "passed"),
        ("", "tests.test_record_queries.Other", "test_y", "failed"),
    ]
    assert view._tally(results, "tests/test_c2_franchise_identity.py::test_x") == dict(
        passed=1, failed=0, skipped=0
    )
    assert view._tally(results, "tests/test_c2_franchise_identity.py") == dict(
        passed=1, failed=0, skipped=0
    )
    node = "tests/test_record_queries.py::TestBuildTeamRecordResult::test_y"
    assert view._tally(results, node) == dict(passed=1, failed=0, skipped=0)
